import { useState } from "react";
import ReactMarkdown from "react-markdown";
import ChartRenderer from "./ChartRenderer";

function defaultPositionDraft(item) {
  const today = new Date().toISOString().slice(0, 10);
  return {
    stock_code: item.stock_code,
    stock_name: item.stock_name,
    buy_price: item.current_price || "",
    quantity: 100,
    buy_date: today,
    stop_loss_pct: 8,
    take_profit_drawdown_pct: 15,
    notes: `来自${item.strategy_tags?.join(" / ") || "每日推荐"}`,
  };
}

export default function BriefingPanel({ brief, loading, onGenerate, onAddToWatchlist, onAddToPosition }) {
  const recommendations = brief?.recommendations || [];
  const watchlistReviews = brief?.watchlist_reviews || [];
  const positionReviews = brief?.position_reviews || [];
  const [positionDrafts, setPositionDrafts] = useState({});
  const [submittingCode, setSubmittingCode] = useState("");

  const ensureDraft = (item) => {
    if (positionDrafts[item.stock_code]) return positionDrafts[item.stock_code];
    return defaultPositionDraft(item);
  };

  const handleDraftChange = (stockCode, field, value) => {
    setPositionDrafts((prev) => ({
      ...prev,
      [stockCode]: {
        ...(prev[stockCode] || {}),
        [field]: value,
      },
    }));
  };

  const handleAddWatchlist = async (item) => {
    setSubmittingCode(item.stock_code);
    try {
      await onAddToWatchlist(item);
    } finally {
      setSubmittingCode("");
    }
  };

  const handleAddPosition = async (item) => {
    const draft = ensureDraft(item);
    if (!draft.buy_price || !draft.quantity || !draft.buy_date) {
      return;
    }

    setSubmittingCode(item.stock_code);
    try {
      await onAddToPosition({
        ...draft,
        buy_price: Number(draft.buy_price),
        quantity: Number(draft.quantity),
        stop_loss_pct: Number(draft.stop_loss_pct),
        take_profit_drawdown_pct: Number(draft.take_profit_drawdown_pct),
      });
    } finally {
      setSubmittingCode("");
    }
  };

  return (
    <section className="panel brief-panel">
      <div className="panel-header">
        <h2>每日简报</h2>
        <span>{brief?.generated_at ? "已生成最新简报" : "支持早报与晚报"}</span>
      </div>

      <div className="brief-actions">
        <button type="button" className="primary-button" disabled={loading} onClick={() => onGenerate("morning")}>
          {loading ? "生成中..." : "生成早报"}
        </button>
        <button type="button" className="secondary-button" disabled={loading} onClick={() => onGenerate("evening")}>
          生成晚报
        </button>
      </div>

      {!brief ? (
        <p className="muted-copy">生成后会在这里展示最新简报摘要、推荐股票与持仓体检结果。</p>
      ) : (
        <div className="brief-layout">
          <ChartRenderer charts={brief.charts || []} />
          <div className="brief-meta-grid">
            <div className="brief-stat">
              <strong>简报类型</strong>
              <p>{brief.session === "morning" ? "早间盘前简报" : "晚间复盘简报"}</p>
            </div>
            <div className="brief-stat">
              <strong>Markdown 文件</strong>
              <p>{brief.markdown_file || "未生成"}</p>
            </div>
            <div className="brief-stat">
              <strong>Word 文件</strong>
              <p>{brief.docx_file || "当前环境未生成"}</p>
            </div>
            <div className="brief-stat">
              <strong>推荐数量</strong>
              <p>{recommendations.length} 只</p>
            </div>
          </div>

          <div className="brief-summary-grid">
            <div className="summary-card">
              <h3>自选观察</h3>
              <div className="item-list compact-list">
                {watchlistReviews.length ? (
                  watchlistReviews.map((item) => (
                    <div className="list-card" key={item.stock_code}>
                      <div>
                        <strong>{item.stock_name}</strong>
                        <p>
                          {item.stock_code} · 5日 {item.recent_change_pct_5d ?? "--"}% · 波动率{" "}
                          {item.volatility_20d_pct ?? "--"}%
                        </p>
                      </div>
                      <span className="score-pill">{item.action || item.status}</span>
                    </div>
                  ))
                ) : (
                  <p className="muted-copy">暂无自选股结果。</p>
                )}
              </div>
            </div>

            <div className="summary-card">
              <h3>持仓体检</h3>
              <div className="item-list compact-list">
                {positionReviews.length ? (
                  positionReviews.map((item) => (
                    <div className="list-card" key={item.stock_code}>
                      <div>
                        <strong>{item.stock_name}</strong>
                        <p>
                          {item.stock_code} · 盈亏 {item.pnl_pct ?? "--"}% · {item.action}
                        </p>
                      </div>
                      <span className="score-pill">{item.risk_tag}</span>
                    </div>
                  ))
                ) : (
                  <p className="muted-copy">当前暂无持仓。</p>
                )}
              </div>
            </div>
          </div>

          <div className="summary-card">
            <h3>推荐买入 5 只</h3>
            <div className="recommendation-grid">
              {recommendations.length ? (
                recommendations.map((item) => (
                  <article className="recommendation-card" key={item.stock_code}>
                    <div className="recommendation-header">
                      <div>
                        <strong>{item.stock_name}</strong>
                        <p>{item.stock_code}</p>
                      </div>
                      <span className="score-badge">{item.overall_score}</span>
                    </div>
                    <div className="tag-row">
                      {(item.strategy_tags || []).map((tag) => (
                        <span className="tag-pill" key={`${item.stock_code}-${tag}`}>
                          {tag}
                        </span>
                      ))}
                    </div>
                    <p className="muted-copy">
                      当前价 {item.current_price} · 预测 {item.forecast_direction} · 买入区间 {item.buy_zone}
                    </p>
                    <p>{item.analysis}</p>
                    <p className="risk-copy">风险点：{item.risk_point}</p>
                    <div className="recommendation-actions">
                      <button
                        type="button"
                        className="secondary-button small-button"
                        disabled={submittingCode === item.stock_code}
                        onClick={() => handleAddWatchlist(item)}
                      >
                        加入自选
                      </button>
                    </div>
                    <div className="quick-position-card">
                      <strong>快速录入持仓</strong>
                      <div className="inline-inputs quick-position-grid">
                        <label>
                          成本价
                          <input
                            type="number"
                            step="0.01"
                            value={ensureDraft(item).buy_price}
                            onChange={(event) => handleDraftChange(item.stock_code, "buy_price", event.target.value)}
                          />
                        </label>
                        <label>
                          数量
                          <input
                            type="number"
                            value={ensureDraft(item).quantity}
                            onChange={(event) => handleDraftChange(item.stock_code, "quantity", event.target.value)}
                          />
                        </label>
                      </div>
                      <div className="inline-inputs quick-position-grid">
                        <label>
                          买入日期
                          <input
                            type="date"
                            value={ensureDraft(item).buy_date}
                            onChange={(event) => handleDraftChange(item.stock_code, "buy_date", event.target.value)}
                          />
                        </label>
                        <label>
                          备注
                          <input
                            value={ensureDraft(item).notes}
                            onChange={(event) => handleDraftChange(item.stock_code, "notes", event.target.value)}
                          />
                        </label>
                      </div>
                      <button
                        type="button"
                        className="primary-button small-button"
                        disabled={submittingCode === item.stock_code}
                        onClick={() => handleAddPosition(item)}
                      >
                        录入持仓
                      </button>
                    </div>
                  </article>
                ))
              ) : (
                <p className="muted-copy">当前没有满足稳健条件的推荐股票。</p>
              )}
            </div>
          </div>

          <div className="summary-card">
            <h3>完整简报预览</h3>
            <article className="markdown-body brief-markdown">
              <ReactMarkdown>{brief.markdown || "暂无内容"}</ReactMarkdown>
            </article>
          </div>
        </div>
      )}
    </section>
  );
}
