import { useState } from "react";

const EXAMPLES = [
  "帮我分析贵州茅台是否值得长期持有",
  "宁德时代300750现在估值高吗",
  "分析招商银行的基本面和新闻风险",
];

export default function AnalysisForm({ onSubmit, loading, disabled = false }) {
  const [query, setQuery] = useState(EXAMPLES[0]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!query.trim() || loading || disabled) {
      return;
    }
    await onSubmit(query.trim());
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>发起分析</h2>
        <span>默认对接 FastAPI 后端</span>
      </div>
      <form onSubmit={handleSubmit} className="analysis-form">
        <textarea
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="例如：帮我分析贵州茅台(600519)这只股票值得投资吗"
          rows={4}
        />
        <div className="example-row">
          {EXAMPLES.map((example) => (
            <button
              type="button"
              key={example}
              className="ghost-chip"
              onClick={() => setQuery(example)}
            >
              {example}
            </button>
          ))}
        </div>
        <button type="submit" className="primary-button" disabled={loading || disabled}>
          {loading ? "提交中..." : disabled ? "当前任务执行中..." : "开始分析"}
        </button>
      </form>
    </section>
  );
}
