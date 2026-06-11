import { useEffect, useRef, useState } from "react";
import AnalysisForm from "./components/AnalysisForm";
import BriefingPanel from "./components/BriefingPanel";
import ProfilePanel from "./components/ProfilePanel";
import ReportViewer from "./components/ReportViewer";
import StatusPanel from "./components/StatusPanel";
import {
  addPositionItem,
  addWatchlistItem,
  createAnalysisTask,
  fetchProfile,
  generateBrief,
  openAnalysisStream,
  removePositionItem,
  removeWatchlistItem,
  updateProfileSettings,
} from "./lib/api";

export default function App() {
  const [task, setTask] = useState(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [profile, setProfile] = useState(null);
  const [profileLoading, setProfileLoading] = useState(true);
  const [brief, setBrief] = useState(null);
  const [briefLoading, setBriefLoading] = useState(false);
  const streamRef = useRef(null);
  const taskActive = task?.status === "queued" || task?.status === "running";

  useEffect(() => {
    const loadInitialProfile = async () => {
      try {
        const nextProfile = await fetchProfile();
        setProfile(nextProfile);
      } catch (loadError) {
        setError(loadError.message || "加载用户档案失败");
      } finally {
        setProfileLoading(false);
      }
    };

    loadInitialProfile();

    return () => {
      if (streamRef.current) {
        streamRef.current.close();
      }
    };
  }, []);

  const stopStreaming = () => {
    if (streamRef.current) {
      streamRef.current.close();
      streamRef.current = null;
    }
  };

  const startStreaming = (taskId) => {
    stopStreaming();
    streamRef.current = openAnalysisStream(taskId, {
      onTask: (nextTask) => {
        setTask(nextTask);
        if (nextTask.status === "completed" || nextTask.status === "failed") {
          stopStreaming();
        }
      },
      onError: () => {
        setError("实时任务流连接中断");
        stopStreaming();
      },
    });
  };

  const handleSubmit = async (query) => {
    setSubmitting(true);
    setError("");
    stopStreaming();

    try {
      const created = await createAnalysisTask(query);
      const initialTask = {
        task_id: created.task_id,
        status: created.status,
        query,
        stock_code: null,
        stock_name: null,
        final_report: null,
        report_file: null,
        fundamental_analysis: null,
        technical_analysis: null,
        value_analysis: null,
        news_analysis: null,
        forecast_analysis: null,
        error: null,
        progress_percent: 0,
        charts: [],
        step_statuses: {
          fundamental: "pending",
          technical: "pending",
          value: "pending",
          news: "pending",
          forecast: "pending",
          summary: "pending",
        },
        step_progresses: {
          fundamental: 0,
          technical: 0,
          value: 0,
          news: 0,
          forecast: 0,
          summary: 0,
        },
        step_messages: {
          fundamental: "等待开始",
          technical: "等待开始",
          value: "等待开始",
          news: "等待开始",
          forecast: "等待开始",
          summary: "等待开始",
        },
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        execution_time: null,
      };
      setTask(initialTask);
      startStreaming(created.task_id);
    } catch (submitError) {
      setError(submitError.message || "创建任务失败");
    } finally {
      setSubmitting(false);
    }
  };

  const refreshProfile = async (updater) => {
    setError("");
    setProfileLoading(true);
    try {
      const nextProfile = await updater();
      setProfile(nextProfile);
    } catch (profileError) {
      setError(profileError.message || "更新用户档案失败");
    } finally {
      setProfileLoading(false);
    }
  };

  const handleGenerateBrief = async (session) => {
    setError("");
    setBriefLoading(true);
    try {
      const nextBrief = await generateBrief(session);
      setBrief(nextBrief);
    } catch (briefError) {
      setError(briefError.message || "生成简报失败");
    } finally {
      setBriefLoading(false);
    }
  };

  const handleAddRecommendationToWatchlist = async (item) => {
    await refreshProfile(() =>
      addWatchlistItem({
        stock_code: item.stock_code,
        stock_name: item.stock_name,
        market: item.market || "cn",
        notes: `来自${brief?.session === "evening" ? "晚报" : "早报"}推荐`,
      }),
    );
  };

  const handleAddRecommendationToPosition = async (payload) => {
    await refreshProfile(() => addPositionItem(payload));
  };

  return (
    <div className="page-shell">
      <div className="aurora aurora-left" />
      <div className="aurora aurora-right" />
      <main className="app-card">
        <section className="hero">
          <p className="eyebrow">Financial MCP Agent</p>
          <h1>A股多 Agent 智能分析平台</h1>
          <p className="subtitle">
            输入股票问题，后端会调用 LangGraph 工作流并生成包含基本面、技术面、估值和新闻面的综合报告。
          </p>
        </section>

        <div className="top-grid">
          <ProfilePanel
            profile={profile}
            loading={profileLoading}
            onUpdateSettings={(payload) => refreshProfile(() => updateProfileSettings(payload))}
            onAddWatchlist={(payload) => refreshProfile(() => addWatchlistItem(payload))}
            onRemoveWatchlist={(stockCode) => refreshProfile(() => removeWatchlistItem(stockCode))}
            onAddPosition={(payload) => refreshProfile(() => addPositionItem(payload))}
            onRemovePosition={(stockCode) => refreshProfile(() => removePositionItem(stockCode))}
          />
          <BriefingPanel
            brief={brief}
            loading={briefLoading}
            onGenerate={handleGenerateBrief}
            onAddToWatchlist={handleAddRecommendationToWatchlist}
            onAddToPosition={handleAddRecommendationToPosition}
          />
        </div>

        <AnalysisForm onSubmit={handleSubmit} loading={submitting} disabled={taskActive} />

        {error ? <div className="error-banner">{error}</div> : null}

        <div className="content-grid">
          <StatusPanel task={task} />
          <ReportViewer task={task} />
        </div>
      </main>
    </div>
  );
}
