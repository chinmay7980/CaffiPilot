export type TaskStatus =
  | 'QUEUED'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface CreateTaskPayload {
  repo_path?: string;
  git_url?: string;
  branch?: string;
  issue_description: string;
  model?: string;
  api_key?: string;
  base_url?: string;
  max_steps?: number;
  auto_verify?: boolean;
  test_command?: string;
}

export interface TaskResponse {
  task_id: str;
  issue_description?: string;
  status: TaskStatus;
  repo_path: string;
  current_step: number;
  max_steps: number;
  tool_call_count: number;
  max_tool_calls: number;
  errors_count: number;
  retries_count: number;
  execution_plan: string[];
  model: string;
  files_modified: string[];
  final_summary?: string;
  final_result?: string;
  verification_status?: string;
  error_message?: string;
  created_at: string;
  start_time?: string;
  completed_at?: string;
  completion_time?: string;
  total_tokens_consumed: number;
}

export interface LogEntry {
  task_id: string;
  timestamp: string;
  event_type: 'TASK_STARTED' | 'STEP_COMPLETED' | 'TOOL_RESULT' | 'TASK_COMPLETED' | 'TASK_FAILED' | 'RETRY' | string;
  message: string;
  stage?: string;
  step_number?: number;
  data?: Record<string, any>;
}

export interface TaskReportResponse {
  task_id: string;
  status: string;
  markdown_report: string;
  json_report: {
    task_id?: string;
    repo_path?: string;
    issue_description?: string;
    status?: string;
    verification_status?: string;
    duration_seconds?: number;
    steps_total?: number;
    tool_calls_total?: number;
    tokens_total?: number;
    modified_files?: string[];
    git_diff?: string;
    tool_breakdown?: Record<string, number>;
    [key: string]: any;
  };
}

export interface HealthResponse {
  status: string;
  version: string;
  configured_model: string;
  has_api_key: boolean;
  max_steps: number;
  timestamp: string;
}
type str = string;
