import { useEffect, useRef, useState } from "react";

const STATUS_LABELS = {
  queued: "排队中",
  running: "分析中",
  completed: "已完成",
  failed: "失败",
};

const STEPS = [
  { key: "fundamental_analysis", label: "基本面 Agent" },
  { key: "technical_analysis", label: "技术面 Agent" },
  { key: "value_analysis", label: "估值 Agent" },
  { key: "news_analysis", label: "新闻 Agent" },
  { key: "forecast_analysis", label: "预测 Agent" },
  { key: "final_report", label: "汇总报告" },
];

const STEP_TO_STATUS_KEY = {
  fundamental_analysis: "fundamental",
  technical_analysis: "technical",
  value_analysis: "value",
  news_analysis: "news",
  forecast_analysis: "forecast",
  final_report: "summary",
};

function getStepProgress(task, stepKey) {
  const statusKey = STEP_TO_STATUS_KEY[stepKey];
  const backendStatus = task?.step_statuses?.[statusKey];
  const backendProgress = task?.step_progresses?.[statusKey];

  if (typeof backendProgress === "number" && backendProgress > 0) {
    return backendProgress;
  }

  if (backendStatus === "completed") {
    return 100;
  }
  if (backendStatus === "failed") {
    return 100;
  }
  if (backendStatus === "running") {
    return 5;
  }
  if (task?.status === "completed" && task?.[stepKey]) {
    return 100;
  }
  return 0;
}

function formatElapsed(seconds) {
  if (seconds == null || Number.isNaN(seconds)) return "";
  if (seconds < 60) return `${seconds.toFixed(1)}s`;
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}m${secs.toString().padStart(2, "0")}s`;
}

export default function StatusPanel({ task }) {
  // Track when each step entered "running" and how long it ran.
  const startedAtRef = useRef({});
  const durationsRef = useRef({});
  const [, forceTick] = useState(0);

  // Reset timers when a new task arrives.
  useEffect(() => {
    startedAtRef.current = {};
    durationsRef.current = {};
  }, [task?.task_id]);

  // Capture transitions to running/completed/failed from the latest poll.
  useEffect(() => {
    if (!task) return;
    const statuses = task.step_statuses || {};
    const now = performance.now();
    Object.entries(statuses).forEach(([statusKey, status]) => {
      if (status === "running" && !startedAtRef.current[statusKey]) {
        startedAtRef.current[statusKey] = now;
      }
      if (
        (status === "completed" || status === "failed") &&
        startedAtRef.current[statusKey] &&
        durationsRef.current[statusKey] == null
      ) {
        durationsRef.current[statusKey] =
          (now - startedAtRef.current[statusKey]) / 1000;
      }
    });
  }, [task]);

  // Tick at 4Hz while the task is running so the elapsed-time labels update
  // smoothly even between server polls.
  useEffect(() => {
    if (task?.status !== "running" && task?.status !== "queued") return;
    const handle = window.setInterval(() => forceTick((n) => n + 1), 250);
    return () => window.clearInterval(handle);
  }, [task?.status]);

  const now = performance.now();
  const getElapsedFor = (statusKey) => {
    if (durationsRef.current[statusKey] != null) {
      return durationsRef.current[statusKey];
    }
    if (startedAtRef.current[statusKey]) {
      return (now - startedAtRef.current[statusKey]) / 1000;
    }
    return null;
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>任务状态</h2>
        <span>{task ? STATUS_LABELS[task.status] : "等待任务"}</span>
      </div>

      {!task ? (
        <p className="muted-copy">提交问题后，这里会显示任务编号、识别到的股票信息和各分析阶段的状态。</p>
      ) : (
        <div className="status-stack">
          <div className="meta-card">
            <div>
              <strong>任务编号</strong>
              <p>{task.task_id}</p>
            </div>
            <div>
              <strong>股票</strong>
              <p>
                {task.stock_name || "待识别"}
                {task.stock_code ? ` (${task.stock_code})` : ""}
              </p>
            </div>
            <div>
              <strong>耗时</strong>
              <p>{task.execution_time ? `${task.execution_time.toFixed(2)} 秒` : "执行中"}</p>
            </div>
          </div>

          <div className="overall-progress-card">
            <div className="overall-progress-label">
              <strong>总体进度</strong>
              <span>{task.progress_percent?.toFixed(0) || 0}%</span>
            </div>
            <div className="progress-track">
              <div className={`progress-fill ${task.status === "running" ? "progress-animated" : ""}`} style={{ width: `${task.progress_percent || 0}%` }} />
            </div>
          </div>

          <div className="step-list">
            {STEPS.map((step) => {
              const statusKey = STEP_TO_STATUS_KEY[step.key];
              const backendStatus = task.step_statuses?.[statusKey];
              const message = task.step_messages?.[statusKey] || "";
              const progress = getStepProgress(task, step.key);
              const ready = backendStatus === "completed" || (task.status === "completed" && task[step.key]);
              const active = backendStatus === "running";
              const failed = backendStatus === "failed" || (task.status === "failed" && statusKey === "summary");
              const elapsed = getElapsedFor(statusKey);
              const elapsedLabel = formatElapsed(elapsed);
              return (
                <div
                  className={`step-item ${ready ? "step-ready" : ""} ${active ? "step-active" : ""} ${
                    failed ? "step-failed" : ""
                  }`}
                  key={step.key}
                >
                  <div className="step-copy">
                    <div className="step-copy-main">
                      <span>{step.label}</span>
                      <p>
                        {message || (ready ? "该阶段已完成" : failed ? "该阶段执行失败" : active ? "正在处理" : "等待开始")}
                        {elapsedLabel ? (
                          <span className="step-elapsed"> · {elapsedLabel}</span>
                        ) : null}
                      </p>
                    </div>
                    <strong>{ready ? "完成" : failed ? "失败" : active ? `${Math.round(progress)}%` : "等待"}</strong>
                  </div>
                  <div className="mini-progress">
                    <div className="mini-progress-track">
                      <div
                        className={`mini-progress-fill ${active ? "progress-animated" : ""} ${failed ? "progress-failed" : ""}`}
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {task.error ? <div className="error-banner">{task.error}</div> : null}
        </div>
      )}
    </section>
  );
}
