import { CreateTaskPayload, HealthResponse, LogEntry, TaskReportResponse, TaskResponse } from '../types/api';

const STORAGE_KEY = 'ai_harness_api_url';

export function getApiBaseUrl(): string {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved && saved.trim()) {
    return saved.trim().replace(/\/+$/, '');
  }
  const metaEnv = (import.meta as any).env;
  return (metaEnv?.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
}

export function setApiBaseUrl(url: string): void {
  if (url.trim()) {
    localStorage.setItem(STORAGE_KEY, url.trim().replace(/\/+$/, ''));
  } else {
    localStorage.removeItem(STORAGE_KEY);
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}${endpoint}`;

  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  const response = await fetch(url, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorDetail = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail);
      }
    } catch {
      // Ignore json parsing error
    }
    throw new Error(errorDetail);
  }

  return response.json() as Promise<T>;
}

export async function checkHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health');
}

export async function submitTask(payload: CreateTaskPayload): Promise<TaskResponse> {
  // Map git_url to repo_path if git_url is specified
  const body: Record<string, any> = { ...payload };
  if (payload.git_url && !payload.repo_path) {
    body.repo_path = payload.git_url;
  }
  return request<TaskResponse>('/api/v1/tasks', {
    method: 'POST',
    body: JSON.stringify(body),
  });
}

export async function getTaskStatus(taskId: string): Promise<TaskResponse> {
  return request<TaskResponse>(`/api/v1/tasks/${taskId}`);
}

export async function getTaskLogs(taskId: string): Promise<LogEntry[]> {
  return request<LogEntry[]>(`/api/v1/tasks/${taskId}/logs`);
}

export async function getTaskReport(taskId: string): Promise<TaskReportResponse> {
  return request<TaskReportResponse>(`/api/v1/tasks/${taskId}/report`);
}

export async function cancelTask(taskId: string): Promise<TaskResponse> {
  return request<TaskResponse>(`/api/v1/tasks/${taskId}/cancel`, {
    method: 'POST',
  });
}
