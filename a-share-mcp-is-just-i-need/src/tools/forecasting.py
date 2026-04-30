"""走势预测工具。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

import numpy as np
import pandas as pd

from ..data_source_factory import get_data_source
from ..market_utils import to_yfinance_ticker


@dataclass
class ForecastResult:
    latest_close: float
    predicted_close: float
    predicted_return_pct: float
    direction: str
    confidence: float
    signal_score: float
    model_accuracy: float
    summary: str


def _safe_float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _build_history_frame(stock_code: str, days: int = 260) -> pd.DataFrame:
    source = get_data_source(stock_code)
    end_date = pd.Timestamp.utcnow().strftime("%Y-%m-%d")
    start_date = (pd.Timestamp.utcnow() - pd.Timedelta(days=days * 2)).strftime("%Y-%m-%d")
    raw = source.get_historical_k_data(stock_code, start_date, end_date, frequency="d", adjustflag="2")
    if not raw:
        return pd.DataFrame()

    frame = pd.DataFrame(raw)
    required = ["date", "open", "high", "low", "close", "volume"]
    for column in required:
        if column not in frame.columns:
            frame[column] = 0

    frame["date"] = pd.to_datetime(frame["date"])
    for column in ["open", "high", "low", "close", "volume"]:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.sort_values("date").dropna(subset=["close"]).tail(days).reset_index(drop=True)
    return frame


def _create_tcn_inspired_features(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df["returns_1d"] = df["close"].pct_change()
    df["returns_5d"] = df["close"].pct_change(5)
    df["ma_5"] = df["close"].rolling(5).mean()
    df["ma_10"] = df["close"].rolling(10).mean()
    df["ma_20"] = df["close"].rolling(20).mean()
    df["ma_5_ratio"] = df["close"] / df["ma_5"]
    df["ma_20_ratio"] = df["close"] / df["ma_20"]
    df["volatility_10"] = df["returns_1d"].rolling(10).std()
    df["volume_ma_10"] = df["volume"].rolling(10).mean()
    df["volume_ratio"] = df["volume"] / df["volume_ma_10"]
    df["momentum_3d"] = df["close"] - df["close"].shift(3)
    df["momentum_5d"] = df["close"] - df["close"].shift(5)
    df["roc_10"] = df["close"].pct_change(10) * 100
    df["intraday_momentum"] = (df["close"] - df["open"]) / (df["high"] - df["low"] + 1e-8)
    df["candle_body_ratio"] = (df["close"] - df["open"]).abs() / (df["high"] - df["low"] + 1e-8)

    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / (loss + 1e-8)
    df["rsi_14"] = 100 - (100 / (1 + rs))

    ema_fast = df["close"].ewm(span=12, adjust=False).mean()
    ema_slow = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema_fast - ema_slow
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["target_return"] = df["close"].shift(-1) / df["close"] - 1
    return df.dropna().reset_index(drop=True)


def _feature_columns() -> List[str]:
    return [
        "returns_1d",
        "returns_5d",
        "ma_5_ratio",
        "ma_20_ratio",
        "volatility_10",
        "volume_ratio",
        "momentum_3d",
        "momentum_5d",
        "roc_10",
        "intraday_momentum",
        "candle_body_ratio",
        "rsi_14",
        "macd",
        "macd_signal",
    ]


def _prepare_tcn_sequences(feature_frame: pd.DataFrame, lookback: int = 60):
    feature_columns = _feature_columns()
    model_frame = feature_frame.copy()
    model_frame = model_frame.replace([np.inf, -np.inf], np.nan).dropna(subset=feature_columns + ["target_return"])

    if len(model_frame) <= lookback + 20:
        return None, model_frame, feature_columns

    X_raw = model_frame[feature_columns].to_numpy(dtype=float)
    y_raw = model_frame["target_return"].to_numpy(dtype=float)

    mean = X_raw.mean(axis=0)
    std = X_raw.std(axis=0) + 1e-8
    X_scaled = (X_raw - mean) / std

    X_seq = []
    y_seq = []
    for idx in range(lookback, len(X_scaled)):
        X_seq.append(X_scaled[idx - lookback:idx])
        y_seq.append(y_raw[idx])

    if not X_seq:
        return None, model_frame, feature_columns

    X_seq = np.array(X_seq, dtype=np.float32)
    y_seq = np.array(y_seq, dtype=np.float32)
    split_idx = max(20, int(len(X_seq) * 0.85))
    split_idx = min(split_idx, len(X_seq) - 1)
    if split_idx <= 0:
        return None, model_frame, feature_columns

    payload = {
        "X_train": X_seq[:split_idx],
        "y_train": y_seq[:split_idx],
        "X_val": X_seq[split_idx:],
        "y_val": y_seq[split_idx:],
        "last_sequence": X_seq[-1:],
        "feature_mean": mean,
        "feature_std": std,
        "lookback": lookback,
    }
    return payload, model_frame, feature_columns


def _fit_tcn_forecaster(feature_frame: pd.DataFrame) -> ForecastResult:
    try:
        import tensorflow as tf
        from tensorflow import keras
    except Exception as exc:
        raise RuntimeError(
            "未安装 TensorFlow，无法使用 TCN 预测。请先执行 `pip install -r requirements.txt`"
        ) from exc

    prepared, model_frame, feature_columns = _prepare_tcn_sequences(feature_frame)
    if prepared is None:
        latest_close = _safe_float(feature_frame["close"].iloc[-1]) if not feature_frame.empty else 0.0
        return ForecastResult(
            latest_close=latest_close,
            predicted_close=latest_close,
            predicted_return_pct=0.0,
            direction="震荡",
            confidence=0.2,
            signal_score=0.0,
            model_accuracy=0.0,
            summary="历史样本不足，无法训练单模型 TCN，默认给出震荡判断。",
        )

    tf.keras.backend.clear_session()
    keras.utils.set_random_seed(49)

    X_train = prepared["X_train"]
    y_train = prepared["y_train"]
    X_val = prepared["X_val"]
    y_val = prepared["y_val"]
    last_sequence = prepared["last_sequence"]

    class TemporalBlock(keras.layers.Layer):
        def __init__(self, n_outputs, kernel_size, dilation_rate, dropout=0.2):
            super().__init__()
            self.n_outputs = n_outputs
            self.kernel_size = kernel_size
            self.dilation_rate = dilation_rate
            self.dropout_rate = dropout

        def build(self, input_shape):
            self.conv1 = keras.layers.Conv1D(
                self.n_outputs,
                self.kernel_size,
                padding="causal",
                dilation_rate=self.dilation_rate,
                activation="relu",
            )
            self.dropout1 = keras.layers.Dropout(self.dropout_rate)
            self.conv2 = keras.layers.Conv1D(
                self.n_outputs,
                self.kernel_size,
                padding="causal",
                dilation_rate=self.dilation_rate,
                activation="relu",
            )
            self.dropout2 = keras.layers.Dropout(self.dropout_rate)
            self.downsample = (
                keras.layers.Conv1D(self.n_outputs, kernel_size=1)
                if input_shape[-1] != self.n_outputs
                else None
            )

        def call(self, inputs, training=None):
            x = self.conv1(inputs)
            x = self.dropout1(x, training=training)
            x = self.conv2(x)
            x = self.dropout2(x, training=training)
            residual = self.downsample(inputs) if self.downsample is not None else inputs
            return keras.activations.relu(x + residual)

    inputs = keras.Input(shape=(prepared["lookback"], len(feature_columns)))
    x = TemporalBlock(32, 3, 1, 0.2)(inputs)
    x = TemporalBlock(32, 3, 2, 0.2)(x)
    x = keras.layers.Flatten()(x)
    x = keras.layers.Dense(16, activation="relu")(x)
    outputs = keras.layers.Dense(1)(x)
    model = keras.Model(inputs=inputs, outputs=outputs, name="OnlineTCN")
    model.compile(optimizer="adam", loss="mse")

    callbacks = [
        keras.callbacks.EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True, verbose=0),
        keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=4, verbose=0),
    ]
    model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=35,
        batch_size=32,
        verbose=0,
        callbacks=callbacks,
    )

    val_pred = model.predict(X_val, verbose=0).reshape(-1)
    direction_accuracy = float(np.mean(np.sign(val_pred) == np.sign(y_val))) if len(y_val) else 0.0
    predicted_return = float(model.predict(last_sequence, verbose=0).reshape(-1)[0])

    latest_close = float(model_frame["close"].iloc[-1])
    predicted_close = latest_close * (1 + predicted_return)

    signal_components = {
        "trend": np.tanh((model_frame["ma_5_ratio"].iloc[-1] - 1) * 8),
        "momentum": np.tanh(model_frame["roc_10"].iloc[-1] / 10),
        "volume": np.tanh((model_frame["volume_ratio"].iloc[-1] - 1) * 2),
        "rsi": np.tanh((model_frame["rsi_14"].iloc[-1] - 50) / 20),
        "macd": np.tanh((model_frame["macd"].iloc[-1] - model_frame["macd_signal"].iloc[-1]) * 5),
    }
    signal_score = float(np.mean(list(signal_components.values())))
    confidence = max(0.15, min(0.96, 0.4 + direction_accuracy * 0.3 + abs(signal_score) * 0.2))

    if predicted_return > 0.01:
        direction = "上涨"
    elif predicted_return < -0.01:
        direction = "下跌"
    else:
        direction = "震荡"

    summary = (
        f"该结果使用固定随机种子 49 训练单模型 TCN，沿用了 SPF 项目的因果卷积、"
        f"滚动序列和多因子特征思路。模型基于最近 {len(model_frame)} 个交易日样本训练，"
        f"验证集方向准确率约 {direction_accuracy * 100:.1f}%，预测下一个交易日涨跌幅约 {predicted_return * 100:.2f}%。"
    )
    return ForecastResult(
        latest_close=latest_close,
        predicted_close=predicted_close,
        predicted_return_pct=predicted_return * 100,
        direction=direction,
        confidence=confidence,
        signal_score=signal_score,
        model_accuracy=direction_accuracy,
        summary=summary,
    )


def _fit_linear_fallback(feature_frame: pd.DataFrame) -> ForecastResult:
    feature_columns = [
        "returns_1d",
        "returns_5d",
        "ma_5_ratio",
        "ma_20_ratio",
        "volatility_10",
        "volume_ratio",
        "momentum_3d",
        "momentum_5d",
        "roc_10",
        "intraday_momentum",
        "candle_body_ratio",
        "rsi_14",
        "macd",
        "macd_signal",
    ]
    model_frame = feature_frame.copy()
    model_frame = model_frame.replace([np.inf, -np.inf], np.nan).dropna(subset=feature_columns + ["target_return"])

    if len(model_frame) < 80:
        latest_close = _safe_float(model_frame["close"].iloc[-1]) if not model_frame.empty else 0.0
        return ForecastResult(
            latest_close=latest_close,
            predicted_close=latest_close,
            predicted_return_pct=0.0,
            direction="震荡",
            confidence=0.25,
            signal_score=0.0,
            model_accuracy=0.0,
            summary="历史样本不足，无法形成稳定预测，默认给出震荡判断。",
        )

    X = model_frame[feature_columns].to_numpy(dtype=float)
    y = model_frame["target_return"].to_numpy(dtype=float)
    mean = X.mean(axis=0)
    std = X.std(axis=0) + 1e-8
    X_scaled = (X - mean) / std

    split_idx = max(60, int(len(X_scaled) * 0.8))
    X_train, X_test = X_scaled[:split_idx], X_scaled[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    regularization = 1e-3 * np.eye(X_train.shape[1])
    weights = np.linalg.solve(X_train.T @ X_train + regularization, X_train.T @ y_train)

    test_pred = X_test @ weights if len(X_test) else np.array([])
    direction_accuracy = float(np.mean(np.sign(test_pred) == np.sign(y_test))) if len(X_test) else 0.0

    latest_features = X_scaled[-1]
    predicted_return = float(latest_features @ weights)
    latest_close = float(model_frame["close"].iloc[-1])
    predicted_close = latest_close * (1 + predicted_return)

    signal_components = {
        "trend": np.tanh((model_frame["ma_5_ratio"].iloc[-1] - 1) * 8),
        "momentum": np.tanh(model_frame["roc_10"].iloc[-1] / 10),
        "volume": np.tanh((model_frame["volume_ratio"].iloc[-1] - 1) * 2),
        "rsi": np.tanh((model_frame["rsi_14"].iloc[-1] - 50) / 20),
        "macd": np.tanh((model_frame["macd"].iloc[-1] - model_frame["macd_signal"].iloc[-1]) * 5),
    }
    signal_score = float(np.mean(list(signal_components.values())))
    confidence = max(0.1, min(0.95, 0.45 + abs(signal_score) * 0.25 + direction_accuracy * 0.2))

    if predicted_return > 0.01:
        direction = "上涨"
    elif predicted_return < -0.01:
        direction = "下跌"
    else:
        direction = "震荡"

    summary = (
        f"当前环境未启用完整 TCN 时，系统会回退到轻量回归近似预测。"
        f"预测下一个交易日收盘价约为 {predicted_close:.2f}，相对最新收盘价变动 {predicted_return * 100:.2f}%。"
        f"当前趋势信号分数为 {signal_score:.2f}，最近样本方向准确率约 {direction_accuracy * 100:.1f}%。"
    )
    return ForecastResult(
        latest_close=latest_close,
        predicted_close=predicted_close,
        predicted_return_pct=predicted_return * 100,
        direction=direction,
        confidence=confidence,
        signal_score=signal_score,
        model_accuracy=direction_accuracy,
        summary=summary,
    )


def forecast_price_trend(stock_code: str) -> str:
    """基于 SPF 项目思想做一个固定 seed=49 的单模型 TCN 走势预测。"""
    frame = _build_history_frame(stock_code)
    if frame.empty:
        return f"未获取到 {stock_code} 的历史行情，无法生成走势预测"

    feature_frame = _create_tcn_inspired_features(frame)
    used_model = "TCN(seed=49)"
    try:
        result = _fit_tcn_forecaster(feature_frame)
    except Exception as exc:
        result = _fit_linear_fallback(feature_frame)
        used_model = f"Fallback Linear ({exc})"

    recommendation = (
        "偏多观察"
        if result.direction == "上涨" and result.confidence >= 0.6
        else "偏空观察"
        if result.direction == "下跌" and result.confidence >= 0.6
        else "中性等待"
    )

    return f"""## {stock_code} 走势预测

| 项目 | 数值 |
|------|------|
| 最新收盘价 | {result.latest_close:.2f} |
| 预测下一个交易日收盘价 | {result.predicted_close:.2f} |
| 预测涨跌幅 | {result.predicted_return_pct:.2f}% |
| 趋势判断 | {result.direction} |
| 置信度 | {result.confidence:.2%} |
| 信号分数 | {result.signal_score:.2f} |
| 近端方向准确率 | {result.model_accuracy:.2%} |
| 使用模型 | {used_model} |
| 快速结论 | {recommendation} |

**说明：**
- 该预测模块固定使用你指定的随机种子 `49`，不再执行 200 次种子筛选。
- 若当前环境安装了 TensorFlow，会直接训练一个单模型 TCN 做日级预测。
- 若 TensorFlow 不可用，系统会自动回退到轻量近似模型，避免整个分析流程中断。
- 使用的特征包括均线比值、RSI、MACD、波动率、量价动量、ROC 等。
- 结果仅反映短期概率倾向，不构成投资建议。

**模型摘要：** {result.summary}
"""


def forecast_price_payload(stock_code: str) -> dict:
    """返回结构化的走势预测结果，供日报和推荐模块直接使用。"""
    frame = _build_history_frame(stock_code)
    if frame.empty:
        return {
            "stock_code": stock_code,
            "available": False,
            "latest_close": 0.0,
            "predicted_close": 0.0,
            "predicted_return_pct": 0.0,
            "direction": "未知",
            "confidence": 0.0,
            "signal_score": 0.0,
            "model_accuracy": 0.0,
            "used_model": "unavailable",
            "recommendation": "中性等待",
            "summary": "未获取到历史行情，无法生成结构化预测。",
        }

    feature_frame = _create_tcn_inspired_features(frame)
    used_model = "TCN(seed=49)"
    try:
        result = _fit_tcn_forecaster(feature_frame)
    except Exception as exc:
        result = _fit_linear_fallback(feature_frame)
        used_model = f"Fallback Linear ({exc})"

    recommendation = (
        "偏多观察"
        if result.direction == "上涨" and result.confidence >= 0.6
        else "偏空观察"
        if result.direction == "下跌" and result.confidence >= 0.6
        else "中性等待"
    )

    return {
        "stock_code": stock_code,
        "available": True,
        "latest_close": round(result.latest_close, 4),
        "predicted_close": round(result.predicted_close, 4),
        "predicted_return_pct": round(result.predicted_return_pct, 4),
        "direction": result.direction,
        "confidence": round(result.confidence, 4),
        "signal_score": round(result.signal_score, 4),
        "model_accuracy": round(result.model_accuracy, 4),
        "used_model": used_model,
        "recommendation": recommendation,
        "summary": result.summary,
    }
