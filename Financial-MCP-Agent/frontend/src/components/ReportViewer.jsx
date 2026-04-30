import ReactMarkdown from "react-markdown";

export default function ReportViewer({ task }) {
  return (
    <section className="panel report-panel">
      <div className="panel-header">
        <h2>分析结果</h2>
        <span>{task?.report_file ? "报告已落盘" : "等待生成"}</span>
      </div>

      {!task ? (
        <p className="muted-copy">分析完成后，这里会展示最终 Markdown 报告，并附带各子 Agent 的输出。</p>
      ) : task.status !== "completed" ? (
        <p className="muted-copy">任务正在处理中，前端会每 3 秒自动刷新一次状态。</p>
      ) : (
        <div className="report-content">
          {task.report_file ? (
            <div className="report-path">
              报告文件: <code>{task.report_file}</code>
            </div>
          ) : null}
          <article className="markdown-body">
            <ReactMarkdown>{task.final_report || "暂无报告内容"}</ReactMarkdown>
          </article>
          <div className="agent-sections">
            <details>
              <summary>查看基本面 Agent 输出</summary>
              <pre>{task.fundamental_analysis || "暂无数据"}</pre>
            </details>
            <details>
              <summary>查看技术面 Agent 输出</summary>
              <pre>{task.technical_analysis || "暂无数据"}</pre>
            </details>
            <details>
              <summary>查看估值 Agent 输出</summary>
              <pre>{task.value_analysis || "暂无数据"}</pre>
            </details>
            <details>
              <summary>查看新闻 Agent 输出</summary>
              <pre>{task.news_analysis || "暂无数据"}</pre>
            </details>
            <details>
              <summary>查看预测 Agent 输出</summary>
              <pre>{task.forecast_analysis || "暂无数据"}</pre>
            </details>
          </div>
        </div>
      )}
    </section>
  );
}
