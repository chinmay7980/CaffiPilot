import React, { useEffect, useRef, useState } from 'react';
import { Header } from './components/Header';
import { SettingsModal } from './components/SettingsModal';
import { LoginScreen } from './components/LoginScreen';
import { RepoSelectionScreen } from './components/RepoSelectionScreen';
import { ExecutionScreen } from './components/ExecutionScreen';
import { PullRequestModal } from './components/PullRequestModal';
import {
  cancelTask,
  checkHealth,
  getTaskLogs,
  getTaskReport,
  getTaskStatus,
  submitTask,
} from './services/api';
import { CreateTaskPayload, HealthResponse, LogEntry, TaskReportResponse, TaskResponse } from './types/api';
import { AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isPRModalOpen, setIsPRModalOpen] = useState(false);

  // Authenticated GitHub User session state (Null = show Login Screen first)
  const [authUser, setAuthUser] = useState<{
    username: string;
    name: string;
    avatar: string;
    token: string;
  } | null>(null);

  const [task, setTask] = useState<TaskResponse | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [report, setReport] = useState<TaskReportResponse | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

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

    // Handle GitHub OAuth redirect parameters
    const params = new URLSearchParams(window.location.search);
    const oauthToken = params.get('token');
    const authStatus = params.get('auth');
    const uname = params.get('username') || 'VanshSharma88';

    if (oauthToken || authStatus === 'success') {
      setAuthUser({
        username: uname,
        name: uname,
        avatar: `https://github.com/${uname}.png`,
        token: oauthToken || '',
      });
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Polling loop for active tasks
  useEffect(() => {
    if (!task) return;

    const statusUpper = task.status.toUpperCase();
    const isRunning = statusUpper === 'RUNNING' || statusUpper === 'QUEUED';

    if (!isRunning) {
      if (statusUpper === 'COMPLETED' && !report) {
        getTaskReport(task.task_id)
          .then(setReport)
          .catch((err) => console.warn('Failed to fetch report:', err));
      }
      return;
    }

    const interval = setInterval(async () => {
      try {
        const [updatedTask, updatedLogs] = await Promise.all([
          getTaskStatus(task.task_id),
          getTaskLogs(task.task_id).catch(() => logs),
        ]);
        setTask(updatedTask);
        if (Array.isArray(updatedLogs)) {
          setLogs(updatedLogs);
        }
      } catch (err) {
        console.warn('Task status polling error:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [task, report, logs]);

  // Handle Task Submission
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

  const handleReset = () => {
    setTask(null);
    setLogs([]);
    setReport(null);
    setErrorMsg(null);
  };

  // SCREEN 1: Dedicated GitHub Login Page (Renders first until authenticated)
  if (!authUser) {
    return <LoginScreen onLoginSuccess={(user) => setAuthUser(user)} />;
  }

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
            <button onClick={() => setErrorMsg(null)} className="text-xs underline hover:text-white">
              Dismiss
            </button>
          </div>
        )}

        {/* SCREEN 2: Repository Selection & Task Setup (When logged in and no active task) */}
        {!task && (
          <RepoSelectionScreen
            user={authUser}
            onSignOut={() => setAuthUser(null)}
            onSubmitTask={handleTaskSubmit}
            isRunning={isSubmitting}
          />
        )}

        {/* SCREEN 3 & 4: Active Task Execution, Live Code Changes (Diffs), and Commit & Push */}
        {task && (
          <ExecutionScreen
            task={task}
            logs={logs}
            report={report}
            onCancelTask={handleCancelTask}
            cancelling={cancelling}
            onReset={handleReset}
            onOpenPRModal={() => setIsPRModalOpen(true)}
          />
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
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} onSaved={refreshHealth} />

      {/* Pull Request Modal */}
      <PullRequestModal isOpen={isPRModalOpen} task={task} onClose={() => setIsPRModalOpen(false)} />
    </div>
  );
};

export default App;
