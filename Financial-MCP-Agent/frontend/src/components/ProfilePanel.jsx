import { useMemo, useState } from "react";

function defaultWatchlistForm() {
  return {
    stock_code: "",
    stock_name: "",
    market: "cn",
    notes: "",
  };
}

function defaultPositionForm() {
  return {
    stock_code: "",
    stock_name: "",
    buy_price: "",
    quantity: "",
    buy_date: "",
    stop_loss_pct: 8,
    take_profit_drawdown_pct: 15,
    notes: "",
  };
}

export default function ProfilePanel({
  profile,
  loading,
  onUpdateSettings,
  onAddWatchlist,
  onRemoveWatchlist,
  onAddPosition,
  onRemovePosition,
}) {
  const [watchlistForm, setWatchlistForm] = useState(defaultWatchlistForm);
  const [positionForm, setPositionForm] = useState(defaultPositionForm);

  const settings = useMemo(
    () => ({
      risk_preference: profile?.risk_preference || "稳健",
      recommendation_count: profile?.recommendation_count || 5,
      morning: profile?.delivery_schedule?.morning || "09:00",
      evening: profile?.delivery_schedule?.evening || "21:00",
    }),
    [profile],
  );

  const handleSettingsSubmit = async (event) => {
    event.preventDefault();
    await onUpdateSettings({
      risk_preference: settings.risk_preference,
      recommendation_count: Number(settings.recommendation_count),
      delivery_schedule: {
        morning: settings.morning,
        evening: settings.evening,
      },
    });
  };

  const handleWatchlistSubmit = async (event) => {
    event.preventDefault();
    if (!watchlistForm.stock_code.trim()) return;
    await onAddWatchlist({
      ...watchlistForm,
      stock_code: watchlistForm.stock_code.trim(),
      stock_name: watchlistForm.stock_name.trim(),
    });
    setWatchlistForm(defaultWatchlistForm());
  };

  const handlePositionSubmit = async (event) => {
    event.preventDefault();
    if (!positionForm.stock_code.trim() || !positionForm.buy_price || !positionForm.quantity || !positionForm.buy_date) {
      return;
    }
    await onAddPosition({
      ...positionForm,
      stock_code: positionForm.stock_code.trim(),
      stock_name: positionForm.stock_name.trim(),
      buy_price: Number(positionForm.buy_price),
      quantity: Number(positionForm.quantity),
      stop_loss_pct: Number(positionForm.stop_loss_pct),
      take_profit_drawdown_pct: Number(positionForm.take_profit_drawdown_pct),
    });
    setPositionForm(defaultPositionForm());
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>用户档案</h2>
        <span>{loading ? "同步中" : "支持自选与持仓维护"}</span>
      </div>

      {!profile ? (
        <p className="muted-copy">正在加载档案...</p>
      ) : (
        <div className="profile-layout">
          <form className="mini-form" onSubmit={handleSettingsSubmit}>
            <h3>偏好设置</h3>
            <label>
              风险偏好
              <input value={settings.risk_preference} disabled />
            </label>
            <label>
              每日推荐数量
              <input value={settings.recommendation_count} disabled />
            </label>
            <label>
              早报时间
              <input value={settings.morning} disabled />
            </label>
            <label>
              晚报时间
              <input value={settings.evening} disabled />
            </label>
            <button type="submit" className="secondary-button" disabled>
              当前固定为稳健档
            </button>
          </form>

          <div className="profile-columns">
            <div className="profile-block">
              <div className="profile-block-header">
                <h3>自选股</h3>
                <span>{profile.watchlist?.length || 0} 只</span>
              </div>
              <form className="mini-form" onSubmit={handleWatchlistSubmit}>
                <label>
                  股票代码
                  <input
                    value={watchlistForm.stock_code}
                    onChange={(event) => setWatchlistForm((prev) => ({ ...prev, stock_code: event.target.value }))}
                    placeholder="如 sh.600519 / 00700.HK / AAPL"
                  />
                </label>
                <label>
                  股票名称
                  <input
                    value={watchlistForm.stock_name}
                    onChange={(event) => setWatchlistForm((prev) => ({ ...prev, stock_name: event.target.value }))}
                    placeholder="可选"
                  />
                </label>
                <label>
                  备注
                  <input
                    value={watchlistForm.notes}
                    onChange={(event) => setWatchlistForm((prev) => ({ ...prev, notes: event.target.value }))}
                    placeholder="如 白马消费"
                  />
                </label>
                <button type="submit" className="primary-button small-button">
                  加入自选
                </button>
              </form>

              <div className="item-list">
                {(profile.watchlist || []).map((item) => (
                  <div className="list-card" key={item.stock_code}>
                    <div>
                      <strong>{item.stock_name || item.stock_code}</strong>
                      <p>{item.stock_code}</p>
                    </div>
                    <button type="button" className="text-button" onClick={() => onRemoveWatchlist(item.stock_code)}>
                      删除
                    </button>
                  </div>
                ))}
              </div>
            </div>

            <div className="profile-block">
              <div className="profile-block-header">
                <h3>持仓</h3>
                <span>{profile.positions?.length || 0} 笔</span>
              </div>
              <form className="mini-form" onSubmit={handlePositionSubmit}>
                <label>
                  股票代码
                  <input
                    value={positionForm.stock_code}
                    onChange={(event) => setPositionForm((prev) => ({ ...prev, stock_code: event.target.value }))}
                    placeholder="如 sh.600519"
                  />
                </label>
                <label>
                  股票名称
                  <input
                    value={positionForm.stock_name}
                    onChange={(event) => setPositionForm((prev) => ({ ...prev, stock_name: event.target.value }))}
                    placeholder="可选"
                  />
                </label>
                <div className="inline-inputs">
                  <label>
                    买入价
                    <input
                      type="number"
                      step="0.01"
                      value={positionForm.buy_price}
                      onChange={(event) => setPositionForm((prev) => ({ ...prev, buy_price: event.target.value }))}
                    />
                  </label>
                  <label>
                    数量
                    <input
                      type="number"
                      value={positionForm.quantity}
                      onChange={(event) => setPositionForm((prev) => ({ ...prev, quantity: event.target.value }))}
                    />
                  </label>
                </div>
                <div className="inline-inputs">
                  <label>
                    买入日期
                    <input
                      type="date"
                      value={positionForm.buy_date}
                      onChange={(event) => setPositionForm((prev) => ({ ...prev, buy_date: event.target.value }))}
                    />
                  </label>
                  <label>
                    止损%
                    <input
                      type="number"
                      step="0.1"
                      value={positionForm.stop_loss_pct}
                      onChange={(event) => setPositionForm((prev) => ({ ...prev, stop_loss_pct: event.target.value }))}
                    />
                  </label>
                </div>
                <label>
                  备注
                  <input
                    value={positionForm.notes}
                    onChange={(event) => setPositionForm((prev) => ({ ...prev, notes: event.target.value }))}
                    placeholder="如 中线持有"
                  />
                </label>
                <button type="submit" className="primary-button small-button">
                  录入持仓
                </button>
              </form>

              <div className="item-list">
                {(profile.positions || []).map((item) => (
                  <div className="list-card" key={item.stock_code}>
                    <div>
                      <strong>{item.stock_name || item.stock_code}</strong>
                      <p>
                        {item.stock_code} · 成本 {item.buy_price} · 数量 {item.quantity}
                      </p>
                    </div>
                    <button type="button" className="text-button" onClick={() => onRemovePosition(item.stock_code)}>
                      删除
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
