const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function handleResponse(response) {
  if (!response.ok) {
    let message = "请求失败";
    try {
      const payload = await response.json();
      message = payload.detail || message;
    } catch {
      message = response.statusText || message;
    }
    throw new Error(message);
  }
  return response.json();
}

export async function createAnalysisTask(query) {
  const response = await fetch(`${API_BASE_URL}/api/analysis`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ query }),
  });
  return handleResponse(response);
}

export async function fetchAnalysisTask(taskId) {
  const response = await fetch(`${API_BASE_URL}/api/analysis/${taskId}`);
  return handleResponse(response);
}

export function openAnalysisStream(taskId, { onTask, onError }) {
  const eventSource = new EventSource(`${API_BASE_URL}/api/analysis/${encodeURIComponent(taskId)}/stream`);
  eventSource.addEventListener("task", (event) => {
    try {
      onTask?.(JSON.parse(event.data));
    } catch (error) {
      onError?.(error);
    }
  });
  eventSource.onerror = (error) => {
    onError?.(error);
  };
  return eventSource;
}

export async function fetchProfile() {
  const response = await fetch(`${API_BASE_URL}/api/profile`);
  return handleResponse(response);
}

export async function updateProfileSettings(payload) {
  const response = await fetch(`${API_BASE_URL}/api/profile`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function addWatchlistItem(payload) {
  const response = await fetch(`${API_BASE_URL}/api/profile/watchlist`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function removeWatchlistItem(stockCode) {
  const response = await fetch(`${API_BASE_URL}/api/profile/watchlist/${encodeURIComponent(stockCode)}`, {
    method: "DELETE",
  });
  return handleResponse(response);
}

export async function addPositionItem(payload) {
  const response = await fetch(`${API_BASE_URL}/api/profile/positions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  return handleResponse(response);
}

export async function removePositionItem(stockCode) {
  const response = await fetch(`${API_BASE_URL}/api/profile/positions/${encodeURIComponent(stockCode)}`, {
    method: "DELETE",
  });
  return handleResponse(response);
}

export async function generateBrief(session) {
  const response = await fetch(`${API_BASE_URL}/api/briefs/generate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ session }),
  });
  return handleResponse(response);
}
