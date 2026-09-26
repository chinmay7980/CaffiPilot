import React, { useState } from 'react';
import { TaskExecutionPanel } from './TaskExecutionPanel';
import { LiveLogsPanel } from './LiveLogsPanel';
import { FileChangesPanel } from './FileChangesPanel';
import { TestResultsPanel } from './TestResultsPanel';
import { ReportPanel } from './ReportPanel';
import { LogEntry, TaskReportResponse, TaskResponse } from '../types/api';
import { ArrowLeft, UploadCloud, GitPullRequest, Loader2, CheckCircle2, GitBranch, ExternalLink, Sparkles } from 'lucide-react';

interface ExecutionScreenProps {
  task: TaskResponse;
  logs: LogEntry[];
  report: TaskReportResponse | null;
  onCancelTask: () => void;
  cancelling: boolean;
  onReset: () => void;
  onOpenPRModal: () => void;
  userToken?: string;
}

export const ExecutionScreen: React.FC<ExecutionScreenProps> = ({
  task,
  logs,
  report,
  onCancelTask,
  cancelling,
  onReset,
  onOpenPRModal,
  userToken,
}) => {
  const [commitMsg, setCommitMsg] = useState<string>('');
  const [targetBranch, setTargetBranch] = useState<string>('main');
  const [committing, setCommitting] = useState<boolean>(false);
  const [creatingPR, setCreatingPR] = useState<boolean>(false);
  const [actionStatus, setActionStatus] = useState<{
    type: 'success' | 'error' | 'info';
    message: string;
    url?: string;
  } | null>(null);

  const statusUpper = task.status.toUpperCase();
  const isRunning = statusUpper === 'RUNNING' || statusUpper === 'QUEUED';
  const isFinished = statusUpper === 'COMPLETED' || statusUpper === 'FAILED';
  const hasDiff = Boolean(task.git_diff || report?.json_report?.git_diff);
  const filesCount = task.files_modified?.length || (hasDiff ? 1 : 0);

  // Direct Commit & Push
  const handleCommitPush = async () => {
    setCommitting(true);
    setActionStatus(null);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/github/commit-and-push/${task.task_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          commit_message: commitMsg || `feat(ai-agent): ${task.issue_description}`,
          branch_name: targetBranch,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setActionStatus({
          type: 'success',
          message: `Successfully committed [${data.commit_sha}] and pushed changes directly to '${data.branch}'!`,
        });
      } else {
        setActionStatus({
          type: 'error',
          message: `Commit status: ${data.detail || 'Failed to push to remote.'}`,
        });
      }
    } catch (err: any) {
      setActionStatus({
        type: 'error',
        message: `Push Error: ${err.message || 'Server network error.'}`,
      });
    } finally {
      setCommitting(false);
    }
  };

  // Commit & Create Pull Request in Single Click
  const handleCommitAndPR = async () => {
    setCreatingPR(true);
    setActionStatus(null);
    try {
      const tokenQuery = userToken ? `?token=${encodeURIComponent(userToken)}` : '';
      const res = await fetch(`http://127.0.0.1:8000/api/v1/github/commit-and-pr/${task.task_id}${tokenQuery}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(userToken ? { Authorization: `Bearer ${userToken}` } : {}),
        },
        body: JSON.stringify({
          title: commitMsg || `feat(ai-agent): ${task.issue_description}`,
          target_branch: targetBranch,
          branch_name: `caffipilot/patch-${task.task_id.replace('task_', '')}`,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setActionStatus({
          type: 'success',
          message: `Branch '${data.feature_branch}' pushed & Pull Request created successfully!`,
          url: data.pr_url,
        });
      } else {
        setActionStatus({
          type: 'error',
          message: `Pull Request Creation Error: ${data.detail || 'Failed to submit PR.'}`,
        });
      }
    } catch (err: any) {
      setActionStatus({
        type: 'error',
        message: `Network Error: ${err.message || 'Server endpoint unreachable.'}`,
      });
    } finally {
      setCreatingPR(false);
    }
  };

  return (
    <div className="w-full max-w-7xl mx-auto space-y-6">
      {/* Top Header Navigation */}
      <div className="flex items-center justify-between">
        <button
          onClick={onReset}
          className="px-3.5 py-1.5 bg-dark-800 hover:bg-dark-700 text-gray-300 text-xs font-semibold rounded-xl flex items-center gap-2 border border-dark-700 transition-colors shadow-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Repositories
        </button>

        <div className="flex items-center gap-3">
          {isRunning && (
            <span className="text-xs font-semibold text-amber-400 bg-amber-400/10 px-3 py-1 rounded-full border border-amber-400/30 flex items-center gap-1.5 animate-pulse">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Working on AI Code Changes...
            </span>
          )}
          {isFinished && (
            <span className="text-xs font-semibold text-emerald-400 bg-emerald-400/10 px-3 py-1 rounded-full border border-emerald-400/30 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> AI Execution Completed
            </span>
          )}
        </div>
      </div>

      {/* Task Execution Progress & Timeline Panel */}
      <TaskExecutionPanel task={task} onCancelTask={onCancelTask} cancelling={cancelling} />

      {/* Live Terminal & Test Results Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <LiveLogsPanel logs={logs} onClearLogs={() => {}} isRunning={isRunning} />
        <TestResultsPanel verificationStatus={task.verification_status} errorMessage={task.error_message} />
      </div>

      {/* File Changes Panel (Shows exact line-by-line diffs & modified files) */}
      <FileChangesPanel
        filesModified={task.files_modified || []}
        gitDiff={task.git_diff || report?.json_report?.git_diff}
      />

      {/* Commit & Pull Request Action Panel (Always accessible once changes are made or task finishes) */}
      <div className="bg-gradient-to-r from-dark-800 via-dark-800 to-emerald-950/30 border border-emerald-500/40 rounded-2xl p-6 shadow-2xl space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-dark-700 pb-4">
          <div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              <h3 className="text-base font-bold text-white">Review & Publish Code Modifications</h3>
              <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-mono font-bold border border-emerald-500/30">
                {filesCount} {filesCount === 1 ? 'file' : 'files'} modified
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Review line modifications above. You can directly commit changes to your target repository or create a GitHub Pull Request.
            </p>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <label className="text-xs text-gray-400 font-medium flex items-center gap-1">
              <GitBranch className="w-3.5 h-3.5 text-brand-cyan" /> Branch:
            </label>
            <input
              type="text"
              value={targetBranch}
              onChange={(e) => setTargetBranch(e.target.value)}
              className="bg-dark-900 border border-dark-600 rounded-lg px-2.5 py-1 text-xs text-white font-mono w-28 focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>

        {/* Action Status Message */}
        {actionStatus && (
          <div
            className={`p-3.5 rounded-xl border text-xs font-semibold flex items-center justify-between gap-2 ${
              actionStatus.type === 'success'
                ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/40 text-rose-300'
            }`}
          >
            <span>{actionStatus.message}</span>
            {actionStatus.url && (
              <a
                href={actionStatus.url}
                target="_blank"
                rel="noreferrer"
                className="px-3 py-1 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg flex items-center gap-1.5 shrink-0 transition-colors shadow-md"
              >
                <span>View on GitHub</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            )}
          </div>
        )}

        {/* Input Bar & Dual Commit / PR Buttons */}
        <div className="flex flex-col md:flex-row items-center gap-3">
          <input
            type="text"
            value={commitMsg}
            onChange={(e) => setCommitMsg(e.target.value)}
            placeholder={`Commit & PR Title (Default: feat(ai-agent): ${task.issue_description})`}
            className="flex-1 w-full bg-dark-900 border border-dark-600 rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500 shadow-inner"
          />

          <div className="flex items-center gap-2 shrink-0 w-full md:w-auto">
            {/* Direct Commit & Push */}
            <button
              onClick={handleCommitPush}
              disabled={committing || creatingPR}
              className="flex-1 md:flex-none px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 shadow-lg transition-colors disabled:opacity-50"
            >
              {committing ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
              <span>Commit & Push</span>
            </button>

            {/* Combined Commit & Open Pull Request */}
            <button
              onClick={handleCommitAndPR}
              disabled={committing || creatingPR}
              className="flex-1 md:flex-none px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 shadow-lg transition-all disabled:opacity-50"
            >
              {creatingPR ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitPullRequest className="w-4 h-4 text-cyan-300" />}
              <span>Commit & Create PR</span>
            </button>

            {/* Custom PR Modal Option */}
            <button
              onClick={onOpenPRModal}
              title="Customize PR parameters"
              className="px-3 py-2.5 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-xl flex items-center justify-center border border-dark-600 transition-colors"
            >
              <GitPullRequest className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </div>
      </div>

      {/* Final Evaluation Report */}
      {isFinished && <ReportPanel task={task} report={report} onReset={onReset} onScrollToDiff={() => {}} />}
    </div>
  );
};
