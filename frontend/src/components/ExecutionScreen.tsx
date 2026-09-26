import React, { useState } from 'react';
import { TaskExecutionPanel } from './TaskExecutionPanel';
import { LiveLogsPanel } from './LiveLogsPanel';
import { FileChangesPanel } from './FileChangesPanel';
import { TestResultsPanel } from './TestResultsPanel';
import { ReportPanel } from './ReportPanel';
import { LogEntry, TaskReportResponse, TaskResponse } from '../types/api';
import { ArrowLeft, UploadCloud, GitPullRequest, Loader2, CheckCircle2 } from 'lucide-react';

interface ExecutionScreenProps {
  task: TaskResponse;
  logs: LogEntry[];
  report: TaskReportResponse | null;
  onCancelTask: () => void;
  cancelling: boolean;
  onReset: () => void;
  onOpenPRModal: () => void;
}

export const ExecutionScreen: React.FC<ExecutionScreenProps> = ({
  task,
  logs,
  report,
  onCancelTask,
  cancelling,
  onReset,
  onOpenPRModal,
}) => {
  const [commitMsg, setCommitMsg] = useState<string>('');
  const [committing, setCommitting] = useState<boolean>(false);
  const [commitStatusMsg, setCommitStatusMsg] = useState<string | null>(null);

  const statusUpper = task.status.toUpperCase();
  const isRunning = statusUpper === 'RUNNING' || statusUpper === 'QUEUED';
  const isFinished = statusUpper === 'COMPLETED' || statusUpper === 'FAILED';

  const handleCommitPush = async () => {
    setCommitting(true);
    setCommitStatusMsg(null);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/github/commit-and-push/${task.task_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          commit_message: commitMsg || `feat(ai-agent): ${task.issue_description}`,
          branch_name: 'main',
        }),
      });
      const data = await res.json();
      if (data.success) {
        setCommitStatusMsg(`✅ Successfully committed [${data.commit_sha}] and pushed changes to remote branch '${data.branch}'!`);
      } else {
        setCommitStatusMsg(`⚠️ Commit status: ${data.detail || 'Changes saved locally'}`);
      }
    } catch (err: any) {
      setCommitStatusMsg(`❌ Push error: ${err.message || 'Server error'}`);
    } finally {
      setCommitting(false);
    }
  };

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      {/* Back to Repository Setup Header */}
      <div className="flex items-center justify-between">
        <button
          onClick={onReset}
          className="px-3.5 py-1.5 bg-dark-800 hover:bg-dark-700 text-gray-300 text-xs font-semibold rounded-xl flex items-center gap-2 border border-dark-700 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Repositories
        </button>

        {isFinished && (
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-4 h-4" /> Codebase Edits Ready
            </span>
          </div>
        )}
      </div>

      {/* Task Status & Execution Timeline */}
      <TaskExecutionPanel task={task} onCancelTask={onCancelTask} cancelling={cancelling} />

      {/* Grid: Live Terminal Logs & Test Results */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LiveLogsPanel logs={logs} onClearLogs={() => {}} isRunning={isRunning} />
        <TestResultsPanel verificationStatus={task.verification_status} errorMessage={task.error_message} />
      </div>

      {/* File Changes Panel (Git Diff Viewer showing codebase modifications) */}
      <FileChangesPanel filesModified={task.files_modified || []} gitDiff={task.git_diff || report?.json_report?.git_diff} />

      {/* Explicit Commit & Push Action Panel */}
      {isFinished && (
        <div className="bg-dark-800 border border-emerald-500/50 rounded-2xl p-6 shadow-2xl space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-base font-bold text-white">Commit & Push Changes to Repository</h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Review the file changes above and click commit to push modifications to your target GitHub repository.
              </p>
            </div>
          </div>

          {commitStatusMsg && (
            <div className="p-3 rounded-xl bg-dark-900 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
              {commitStatusMsg}
            </div>
          )}

          <div className="flex flex-col sm:flex-row items-center gap-3">
            <input
              type="text"
              value={commitMsg}
              onChange={(e) => setCommitMsg(e.target.value)}
              placeholder={`Commit message (Default: feat(ai-agent): ${task.issue_description})`}
              className="flex-1 w-full bg-dark-900 border border-dark-600 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
            />

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={handleCommitPush}
                disabled={committing}
                className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl flex items-center gap-2 shadow-lg transition-colors disabled:opacity-50"
              >
                {committing ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
                Commit & Push Changes
              </button>

              <button
                onClick={onOpenPRModal}
                className="px-4 py-2.5 bg-dark-700 hover:bg-dark-600 text-gray-200 font-semibold text-xs rounded-xl flex items-center gap-2 border border-dark-600 transition-colors"
              >
                <GitPullRequest className="w-4 h-4 text-emerald-400" />
                Open Pull Request
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Final Evaluation Report */}
      {isFinished && <ReportPanel task={task} report={report} onReset={onReset} onScrollToDiff={() => {}} />}
    </div>
  );
};
