import React, { useEffect, useRef, useState } from 'react';
import { Header } from './components/Header';
import { SettingsModal } from './components/SettingsModal';
import { RepositoryForm } from './components/RepositoryForm';
import { TaskExecutionPanel } from './components/TaskExecutionPanel';
import { LiveLogsPanel } from './components/LiveLogsPanel';
import { FileChangesPanel } from './components/FileChangesPanel';
import { TestResultsPanel } from './components/TestResultsPanel';
import { ReportPanel } from './components/ReportPanel';
import {
  cancelTask,
  checkHealth,
  getTaskLogs,
  getTaskReport,
  getTaskStatus,
  submitTask,
} from './services/api';
import { CreateTaskPayload, HealthResponse, LogEntry, TaskReportResponse, TaskResponse } from './types/api';
import { AlertCircle, Code2, Sparkles } from 'lucide-react';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  const [task, setTask] = useState<TaskResponse | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [report, setReport] = useState<TaskReportResponse | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const fileDiffRef = useRef<HTMLDivElement>(null);

  // Health Check
  const refreshHealth = async () => {
    setLoadingHealth(true);
    try {
      const res = await checkHealth();
      setHealth(res);
      setErrorMsg(null);
    } catch (err: any) {
      setHealth(null);
      console.warn('Backend health check failed:', err);
    } finally {
      setLoadingHealth(false);
    }
  };

  useEffect(() => {
    refreshHealth();
  }, []);

  const taskId = task?.task_id;
  const taskStatus = task?.status;

  // Polling loop for active tasks
  useEffect(() => {
    if (!taskId || !taskStatus) return;

    const statusUpper = taskStatus.toUpperCase();
    const isRunning = statusUpper === 'RUNNING' || statusUpper === 'QUEUED' || statusUpper === 'PENDING';

    if (!isRunning) {
      if (statusUpper === 'FAILED') {
        setErrorMsg(task?.error_message || task?.final_result || 'Task failed to execute.');
      }
      if (statusUpper === 'COMPLETED') {
        getTaskReport(taskId)
          .then(setReport)
          .catch((err) => console.warn('Failed to fetch report:', err));
      }
      return;
    }

    const interval = setInterval(async () => {
      try {
        const [updatedTask, updatedLogs] = await Promise.all([
          getTaskStatus(taskId),
          getTaskLogs(taskId).catch(() => []),
        ]);
        setTask(updatedTask);
        if (Array.isArray(updatedLogs) && updatedLogs.length > 0) {
          setLogs(updatedLogs);
        }
      } catch (err) {
        console.warn('Task status polling error:', err);
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [taskId, taskStatus]);

  // Handle Form Submission
  const handleTaskSubmit = async (payload: CreateTaskPayload) => {
    setIsSubmitting(true);
    setErrorMsg(null);
    setTask(null);
    setLogs([]);
    setReport(null);

    try {
      const newTask = await submitTask(payload);
      setTask(newTask);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit task to backend.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle Cancel
  const handleCancelTask = async () => {
    if (!task) return;
    setCancelling(true);
    try {
      const updated = await cancelTask(task.task_id);
      setTask(updated);
    } catch (err: any) {
      console.warn('Cancel error:', err);
    } finally {
      setCancelling(false);
    }
  };

  // Handle Reset / New Task
  const handleReset = () => {
    setTask(null);
    setLogs([]);
    setReport(null);
    setErrorMsg(null);
  };

  const scrollToDiff = () => {
    fileDiffRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#0b0f19] text-gray-100 selection:bg-brand-blue selection:text-white">
      {/* Header */}
      <Header
        health={health}
        loadingHealth={loadingHealth}
        onRefreshHealth={refreshHealth}
        onOpenSettings={() => setIsSettingsOpen(true)}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 space-y-6">
        {/* Error Alert Banner */}
        {errorMsg && (
          <div className="flex items-center justify-between p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-sm">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            <button
              onClick={() => setErrorMsg(null)}
              className="text-xs underline hover:text-white"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Top: Repository Input Form */}
        <RepositoryForm
          onSubmit={handleTaskSubmit}
          isRunning={isSubmitting || (task ? task.status.toUpperCase() === 'RUNNING' || task.status.toUpperCase() === 'QUEUED' : false)}
          disabled={!health && !loadingHealth}
        />

        {/* Empty State before submission */}
        {!task && !isSubmitting && (
          <div className="bg-dark-800/50 border border-dark-700/60 border-dashed rounded-2xl p-12 text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-brand-blue/10 border border-brand-blue/20 text-brand-cyan flex items-center justify-center mx-auto">
              <Sparkles className="w-6 h-6 animate-pulse" />
            </div>
            <div className="space-y-1 max-w-md mx-auto">
              <h3 className="text-base font-semibold text-white">No Active Task Running</h3>
              <p className="text-xs text-gray-400">
                Submit a Git Repository URL or local repo path above to launch autonomous AI agent exploration, editing, and test verification.
              </p>
            </div>
          </div>
        )}

        {/* Active Task Execution Dashboard */}
        {task && (
          <div className="space-y-6">
            {/* Task Status & Live Timeline Panel */}
            <TaskExecutionPanel
              task={task}
              onCancelTask={handleCancelTask}
              cancelling={cancelling}
            />

            {/* Grid: Terminal Logs & Test Results */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <LiveLogsPanel
                logs={logs}
                onClearLogs={() => setLogs([])}
                isRunning={task.status.toUpperCase() === 'RUNNING' || task.status.toUpperCase() === 'QUEUED'}
              />

              <div className="space-y-6">
                <TestResultsPanel
                  verificationStatus={task.verification_status}
                  errorMessage={task.error_message}
                />
              </div>
            </div>

            {/* File Changes Panel */}
            <div ref={fileDiffRef}>
              <FileChangesPanel
                filesModified={task.files_modified || []}
                gitDiff={report?.json_report?.git_diff}
              />
            </div>

            {/* Final Evaluation Report Panel */}
            {(task.status.toUpperCase() === 'COMPLETED' || task.status.toUpperCase() === 'FAILED') && (
              <ReportPanel
                task={task}
                report={report}
                onReset={handleReset}
                onScrollToDiff={scrollToDiff}
              />
            )}
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-dark-700 bg-dark-900/60 py-4 px-6 text-center text-xs text-gray-500">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <span>AI Coding Harness Dashboard &copy; 2026 LCC &times; DevClub Hackathon</span>
          <span className="font-mono">Backend Proxy: {health?.status === 'ok' ? 'Connected' : 'Disconnected'}</span>
        </div>
      </footer>

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onSaved={refreshHealth}
      />
    </div>
  );
};

export default App;
