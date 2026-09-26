import React, { useState, useEffect } from 'react';
import {
  Github,
  Key,
  User,
  ShieldCheck,
  Search,
  FolderGit2,
  GitBranch,
  Send,
  Loader2,
  Sparkles,
  ArrowLeft,
  UploadCloud,
  GitPullRequest,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Code2,
  Terminal,
  FileCode,
  Check,
  Copy,
  RefreshCw,
} from 'lucide-react';

interface RepoItem {
  id: number;
  name: string;
  full_name: string;
  clone_url: string;
  default_branch: string;
  description: string;
  private: boolean;
}

interface LogEntry {
  task_id: string;
  timestamp: string;
  event_type: string;
  message: string;
  stage?: string;
  step_number?: number;
}

interface TaskResponse {
  task_id: string;
  issue_description?: string;
  status: string;
  repo_path: string;
  current_step: number;
  max_steps: number;
  files_modified: string[];
  git_diff?: string;
  verification_status?: string;
  error_message?: string;
}

export const App: React.FC = () => {
  // Authentication State
  const [authInput, setAuthInput] = useState<string>('');
  const [tokenInput, setTokenInput] = useState<string>('');
  const [authUser, setAuthUser] = useState<{ username: string; avatar: string; token: string } | null>(null);
  const [authLoading, setAuthLoading] = useState<boolean>(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Repositories & Launch Form State
  const [repos, setRepos] = useState<RepoItem[]>([]);
  const [loadingRepos, setLoadingRepos] = useState<boolean>(false);
  const [repoSearch, setRepoSearch] = useState<string>('');
  const [gitUrl, setGitUrl] = useState<string>('https://github.com/VanshSharma88/Loginform.git');
  const [branch, setBranch] = useState<string>('main');
  const [issuePrompt, setIssuePrompt] = useState<string>('Create a file named chinuu.jsx in which print Hello World');

  // Execution State
  const [task, setTask] = useState<TaskResponse | null>(null);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [commitMsg, setCommitMsg] = useState<string>('');
  const [committing, setCommitting] = useState<boolean>(false);
  const [creatingPR, setCreatingPR] = useState<boolean>(false);
  const [actionStatus, setActionStatus] = useState<{ success: boolean; message: string; url?: string } | null>(null);
  const [diffCopied, setDiffCopied] = useState<boolean>(false);

  // Auto-verify OAuth redirect query parameters or stored token
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const oauthToken = params.get('token') || localStorage.getItem('github_token');
    const paramUsername = params.get('username');

    if (oauthToken) {
      localStorage.setItem('github_token', oauthToken);
      fetch(`http://127.0.0.1:8000/api/v1/github/user?token=${encodeURIComponent(oauthToken)}`)
        .then((r) => r.json())
        .then((data) => {
          if (data.authenticated) {
            setAuthUser({
              username: data.username,
              avatar: data.avatar_url || `https://github.com/${data.username}.png`,
              token: oauthToken,
            });
          }
        })
        .catch(() => {});
      window.history.replaceState({}, document.title, window.location.pathname);
    } else if (paramUsername) {
      fetch(`http://127.0.0.1:8000/api/v1/github/user?username=${encodeURIComponent(paramUsername)}`)
        .then((r) => r.json())
        .then((data) => {
          if (data.authenticated) {
            setAuthUser({
              username: data.username,
              avatar: data.avatar_url || `https://github.com/${data.username}.png`,
              token: '',
            });
          }
        })
        .catch(() => {});
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  // Fetch account repos on login
  useEffect(() => {
    if (!authUser) return;
    setLoadingRepos(true);
    const url = authUser.token
      ? `http://127.0.0.1:8000/api/v1/github/repos?token=${encodeURIComponent(authUser.token)}`
      : `http://127.0.0.1:8000/api/v1/github/repos?username=${encodeURIComponent(authUser.username)}`;

    fetch(url)
      .then((r) => r.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setRepos(data);
          if (data.length > 0 && !gitUrl) {
            setGitUrl(data[0].clone_url || `https://github.com/${data[0].full_name}.git`);
            if (data[0].default_branch) setBranch(data[0].default_branch);
          }
        }
      })
      .catch(() => {})
      .finally(() => setLoadingRepos(false));
  }, [authUser]);

  // Polling loop for active tasks
  useEffect(() => {
    if (!task) return;
    const statusUpper = task.status.toUpperCase();
    if (statusUpper === 'COMPLETED' || statusUpper === 'FAILED') return;

    const interval = setInterval(async () => {
      try {
        const [taskRes, logsRes] = await Promise.all([
          fetch(`http://127.0.0.1:8000/api/v1/tasks/${task.task_id}`).then((r) => r.json()),
          fetch(`http://127.0.0.1:8000/api/v1/tasks/${task.task_id}/logs`).then((r) => r.json()),
        ]);
        setTask(taskRes);
        if (Array.isArray(logsRes)) setLogs(logsRes);
      } catch (err) {
        console.warn('Polling error:', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [task]);

  // Handle Authentication
  const handleAuthenticate = async (e: React.FormEvent) => {
    e.preventDefault();
    const uname = authInput.trim();
    const token = tokenInput.trim();
    if (!uname && !token) {
      setAuthError('Please enter a GitHub Username or Personal Access Token.');
      return;
    }

    setAuthLoading(true);
    setAuthError(null);

    try {
      const url = token
        ? `http://127.0.0.1:8000/api/v1/github/user?token=${encodeURIComponent(token)}`
        : `http://127.0.0.1:8000/api/v1/github/user?username=${encodeURIComponent(uname)}`;

      const res = await fetch(url);
      const data = await res.json();

      if (!res.ok || data.authenticated === false) {
        throw new Error(data.detail || data.message || 'Failed to authenticate GitHub user.');
      }

      if (token) {
        localStorage.setItem('github_token', token);
      }
      setAuthUser({
        username: data.username,
        avatar: data.avatar_url || `https://github.com/${data.username}.png`,
        token: token,
      });
    } catch (err: any) {
      setAuthError(err.message || 'Verification failed. Check username or PAT.');
    } finally {
      setAuthLoading(false);
    }
  };

  // Launch Task
  const handleLaunchTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gitUrl.trim() || !issuePrompt.trim()) return;

    setIsSubmitting(true);
    setTask(null);
    setLogs([]);
    setActionStatus(null);

    try {
      const res = await fetch('http://127.0.0.1:8000/api/v1/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          git_url: gitUrl.trim(),
          branch: branch.trim() || 'main',
          issue_description: issuePrompt.trim(),
          model: 'qwen2.5-coder:1.5b',
          max_steps: 35,
          auto_verify: true,
          api_key: authUser?.token || undefined,
        }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Task launch failed.');
      setTask(data);
    } catch (err: any) {
      alert(`Error launching task: ${err.message}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Direct Commit & Push
  const handleCommitPush = async () => {
    if (!task) return;
    let tokenToUse: string = authUser?.token || '';
    if (!tokenToUse) {
      const enteredToken = window.prompt('Please enter your GitHub Personal Access Token (PAT) to authorize git commit & push:');
      if (enteredToken && enteredToken.trim()) {
        tokenToUse = enteredToken.trim();
        const activeToken = tokenToUse;
        setAuthUser((prev) => (prev ? { ...prev, token: activeToken } : null));
      }
    }

    setCommitting(true);
    setActionStatus(null);
    try {
      const tokenQuery = tokenToUse ? `?token=${encodeURIComponent(tokenToUse)}` : '';
      const res = await fetch(`http://127.0.0.1:8000/api/v1/github/commit-and-push/${task.task_id}${tokenQuery}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(tokenToUse ? { Authorization: `Bearer ${tokenToUse}` } : {}),
        },
        body: JSON.stringify({
          commit_message: commitMsg || `feat(ai-agent): ${task.issue_description}`,
          branch_name: branch || 'main',
        }),
      });
      const data = await res.json();
      if (data.success) {
        setActionStatus({
          success: true,
          message: `Successfully committed [${data.commit_sha}] and pushed to branch '${data.branch}'!`,
        });
      } else {
        setActionStatus({ success: false, message: data.detail || 'Commit failed.' });
      }
    } catch (err: any) {
      setActionStatus({ success: false, message: err.message || 'Server network error.' });
    } finally {
      setCommitting(false);
    }
  };

  // Commit & Create Pull Request
  const handleCommitAndPR = async () => {
    if (!task) return;
    let tokenToUse: string = authUser?.token || localStorage.getItem('github_token') || '';
    if (!tokenToUse) {
      const enteredToken = window.prompt('Please enter your GitHub Personal Access Token (PAT) to authorize opening a Pull Request on GitHub:');
      if (!enteredToken || !enteredToken.trim()) {
        setActionStatus({
          success: false,
          message: 'A GitHub Personal Access Token (PAT) or OAuth token is required to open a Pull Request.',
        });
        return;
      }
      tokenToUse = enteredToken.trim();
      localStorage.setItem('github_token', tokenToUse);
      const activeToken = tokenToUse;
      setAuthUser((prev) => (prev ? { ...prev, token: activeToken } : null));
    }

    setCreatingPR(true);
    setActionStatus(null);
    try {
      const tokenQuery = tokenToUse ? `?token=${encodeURIComponent(tokenToUse)}` : '';
      const res = await fetch(`http://127.0.0.1:8000/api/v1/github/commit-and-pr/${task.task_id}${tokenQuery}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(tokenToUse ? { Authorization: `Bearer ${tokenToUse}` } : {}),
        },
        body: JSON.stringify({
          title: commitMsg || `feat(ai-agent): ${task.issue_description}`,
          target_branch: branch || 'main',
          branch_name: `caffipilot/patch-${task.task_id.replace('task_', '')}`,
          token: tokenToUse,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setActionStatus({
          success: true,
          message: `Branch '${data.feature_branch}' pushed and Pull Request opened on GitHub!`,
          url: data.pr_url,
        });
      } else {
        setActionStatus({ success: false, message: data.detail || 'PR creation failed.' });
      }
    } catch (err: any) {
      setActionStatus({ success: false, message: err.message || 'Network error.' });
    } finally {
      setCreatingPR(false);
    }
  };

  const filteredRepos = repos.filter(
    (r) =>
      r.name.toLowerCase().includes(repoSearch.toLowerCase()) ||
      r.full_name.toLowerCase().includes(repoSearch.toLowerCase())
  );

  return (
    <div className="min-h-screen flex flex-col bg-[#07090e] text-gray-100 font-sans">
      {/* Header Bar */}
      <header className="border-b border-dark-700/80 bg-[#0d111c]/90 backdrop-blur-md px-6 py-4 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-blue to-cyan-400 p-0.5 shadow-lg shadow-brand-blue/30">
              <div className="w-full h-full bg-[#0d111c] rounded-[10px] flex items-center justify-center text-cyan-300">
                <Github className="w-5 h-5" />
              </div>
            </div>
            <div>
              <h1 className="text-base font-extrabold text-white tracking-tight flex items-center gap-2">
                CaffiPilot AI Dashboard
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-brand-blue/15 text-brand-cyan border border-brand-blue/30">
                  v0.1.0
                </span>
              </h1>
              <p className="text-[11px] text-gray-400">Autonomous Software Engineering Agent & Evaluation Harness</p>
            </div>
          </div>

          {authUser && (
            <div className="flex items-center gap-3 bg-dark-900 border border-dark-600 rounded-2xl px-3.5 py-1.5">
              <img src={authUser.avatar} alt={authUser.username} className="w-6 h-6 rounded-full object-cover" />
              <span className="text-xs font-bold text-white">@{authUser.username}</span>
              <button
                onClick={() => {
                  localStorage.removeItem('github_token');
                  setAuthUser(null);
                }}
                className="text-[11px] text-rose-400 hover:underline font-semibold ml-2"
              >
                Sign Out
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8">
        {/* SCREEN 1: LOGIN / AUTHENTICATION */}
        {!authUser ? (
          <div className="max-w-md mx-auto my-12 space-y-6">
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-black text-white">GitHub Account Login</h2>
              <p className="text-xs text-gray-400">Sign in with your official GitHub Account (1-Click OAuth)</p>
            </div>

            <div className="bg-[#0f1422] border border-dark-600 rounded-3xl p-7 shadow-2xl space-y-5">
              {authError && (
                <div className="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
                  <span>{authError}</span>
                </div>
              )}

              <div className="bg-gradient-to-r from-brand-blue/20 to-purple-500/20 border border-brand-blue/30 p-4 rounded-2xl text-xs text-cyan-200 space-y-1">
                <p className="font-bold flex items-center gap-1.5 text-white">
                  <Sparkles className="w-4 h-4 text-cyan-300" /> Recommended: 1-Click GitHub Login
                </p>
                <p className="text-[11px] text-gray-300">
                  Select your GitHub account to log in directly. No Personal Access Token (PAT) needed!
                </p>
              </div>

              <button
                onClick={async () => {
                  try {
                    const res = await fetch('http://127.0.0.1:8000/api/v1/github/oauth/login', { redirect: 'manual' });
                    if (res.status === 400) {
                      const data = await res.json();
                      setAuthError(data.detail || 'GITHUB_CLIENT_ID not configured in backend environment.');
                    } else {
                      window.location.href = 'http://127.0.0.1:8000/api/v1/github/oauth/login';
                    }
                  } catch (err: any) {
                    window.location.href = 'http://127.0.0.1:8000/api/v1/github/oauth/login';
                  }
                }}
                className="w-full py-3.5 px-4 bg-white hover:bg-gray-100 text-dark-900 font-extrabold text-xs rounded-2xl transition-all flex items-center justify-center gap-2 shadow-xl hover:scale-[1.01]"
              >
                <Github className="w-5 h-5" />
                <span>Sign in with Official GitHub Account</span>
              </button>

              <div className="relative flex py-1 items-center">
                <div className="flex-grow border-t border-dark-700"></div>
                <span className="mx-3 text-[10px] font-bold text-gray-500 uppercase tracking-widest">or manually enter username</span>
                <div className="flex-grow border-t border-dark-700"></div>
              </div>

              <form onSubmit={handleAuthenticate} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">GitHub Username</label>
                  <div className="relative">
                    <User className="w-4 h-4 text-gray-400 absolute left-3.5 top-3" />
                    <input
                      type="text"
                      value={authInput}
                      onChange={(e) => setAuthInput(e.target.value)}
                      placeholder="e.g. VanshSharma88..."
                      className="w-full bg-[#090c14] border border-dark-600 rounded-2xl pl-10 pr-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-brand-blue"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-gray-300 mb-1">
                    Personal Access Token <span className="text-gray-500 font-normal">(Recommended for private repos)</span>
                  </label>
                  <div className="relative">
                    <Key className="w-4 h-4 text-gray-400 absolute left-3.5 top-3" />
                    <input
                      type="password"
                      value={tokenInput}
                      onChange={(e) => setTokenInput(e.target.value)}
                      placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                      className="w-full bg-[#090c14] border border-dark-600 rounded-2xl pl-10 pr-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-brand-blue"
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={authLoading}
                  className="w-full py-3 bg-gradient-to-r from-brand-blue via-brand-purple to-cyan-500 text-white font-extrabold text-xs rounded-2xl hover:opacity-95 flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
                >
                  {authLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
                  <span>Verify Account & Load Repos</span>
                </button>
              </form>
            </div>
          </div>
        ) : !task ? (
          /* SCREEN 2: REPOSITORY & TASK LAUNCH SETUP */
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="bg-[#0f1422] border border-dark-600 rounded-3xl p-7 shadow-2xl space-y-6">
              <div className="border-b border-dark-700/80 pb-4">
                <div className="flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-brand-cyan" />
                  <h2 className="text-lg font-black text-white">Target Repository & Issue Setup</h2>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  Enter any GitHub Repository URL or select from @{authUser.username}'s account repositories.
                </p>
              </div>

              <form onSubmit={handleLaunchTask} className="space-y-6">
                {/* Repository URL Input */}
                <div>
                  <label className="block text-xs font-bold text-white mb-1.5">GitHub Repository URL</label>
                  <div className="relative">
                    <Github className="w-4 h-4 text-gray-400 absolute left-3.5 top-3.5" />
                    <input
                      type="url"
                      required
                      value={gitUrl}
                      onChange={(e) => setGitUrl(e.target.value)}
                      placeholder="https://github.com/VanshSharma88/Loginform.git"
                      className="w-full bg-[#090c14] border border-dark-600 rounded-2xl pl-10 pr-3.5 py-3 text-xs text-white font-mono focus:outline-none focus:border-brand-blue"
                    />
                  </div>
                </div>

                {/* Account Repos Picker Grid */}
                <div className="bg-[#090c14] border border-dark-700 p-4 rounded-2xl space-y-3">
                  <div className="flex flex-col sm:flex-row items-center justify-between gap-2">
                    <span className="text-xs font-bold text-gray-300 flex items-center gap-1.5">
                      <FolderGit2 className="w-3.5 h-3.5 text-brand-cyan" />
                      Pick from @{authUser.username}'s Repositories ({filteredRepos.length}):
                    </span>
                    <div className="flex items-center gap-2">
                      <div className="relative w-44">
                        <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2.5" />
                        <input
                          type="text"
                          value={repoSearch}
                          onChange={(e) => setRepoSearch(e.target.value)}
                          placeholder="Filter..."
                          className="w-full bg-dark-900 border border-dark-600 rounded-xl pl-8 pr-2 py-1.5 text-[11px] text-white focus:outline-none focus:border-brand-blue"
                        />
                      </div>
                      <input
                        type="text"
                        value={branch}
                        onChange={(e) => setBranch(e.target.value)}
                        placeholder="Branch: main"
                        className="w-24 bg-dark-900 border border-dark-600 rounded-xl px-2.5 py-1.5 text-[11px] text-white font-mono focus:outline-none focus:border-brand-blue"
                      />
                    </div>
                  </div>

                  {loadingRepos ? (
                    <div className="py-6 text-center text-xs text-gray-400 flex items-center justify-center gap-2">
                      <Loader2 className="w-4 h-4 animate-spin text-brand-cyan" />
                      <span>Loading account repositories...</span>
                    </div>
                  ) : filteredRepos.length > 0 ? (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-40 overflow-y-auto">
                      {filteredRepos.map((r) => {
                        const url = r.clone_url || `https://github.com/${r.full_name}.git`;
                        const isSelected = gitUrl.trim().toLowerCase() === url.toLowerCase();
                        return (
                          <button
                            type="button"
                            key={r.id || r.name}
                            onClick={() => {
                              setGitUrl(url);
                              if (r.default_branch) setBranch(r.default_branch);
                            }}
                            className={`p-3 rounded-xl border text-left transition-all ${
                              isSelected
                                ? 'bg-brand-blue/20 border-brand-blue ring-1 ring-brand-blue/40'
                                : 'bg-dark-900/60 border-dark-700 hover:border-dark-600'
                            }`}
                          >
                            <div className="flex items-center justify-between font-bold text-xs text-white">
                              <span className="truncate">{r.full_name || r.name}</span>
                              {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-brand-cyan shrink-0" />}
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  ) : (
                    <p className="text-xs text-gray-500 italic">No repositories found. Enter custom GitHub URL above.</p>
                  )}
                </div>

                {/* Task Prompt Textarea */}
                <div>
                  <label className="block text-xs font-bold text-white mb-1.5">Task Issue / Prompt Instructions</label>
                  <textarea
                    rows={3}
                    required
                    value={issuePrompt}
                    onChange={(e) => setIssuePrompt(e.target.value)}
                    placeholder="e.g. Create a file named chinuu.jsx in which print Hello World..."
                    className="w-full bg-[#090c14] border border-dark-600 rounded-2xl p-3.5 text-xs text-white focus:outline-none focus:border-brand-blue resize-none"
                  />
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    disabled={isSubmitting || !gitUrl || !issuePrompt}
                    className="px-8 py-3 bg-gradient-to-r from-brand-blue via-brand-purple to-cyan-500 text-white font-extrabold text-xs rounded-2xl hover:opacity-95 flex items-center gap-2 shadow-lg disabled:opacity-50"
                  >
                    {isSubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                    <span>Launch AI Task</span>
                  </button>
                </div>
              </form>
            </div>
          </div>
        ) : (
          /* SCREEN 3 & 4: LIVE AI EXECUTION & COMMIT / PR ACTION DASHBOARD */
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setTask(null)}
                className="px-3.5 py-1.5 bg-dark-800 hover:bg-dark-700 text-gray-300 text-xs font-semibold rounded-xl flex items-center gap-2 border border-dark-700"
              >
                <ArrowLeft className="w-4 h-4" /> Back to Setup
              </button>

              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-gray-300 font-mono">Task ID: {task.task_id}</span>
                <span className={`text-xs px-2.5 py-0.5 rounded-full font-bold uppercase ${
                  task.status.toUpperCase() === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse'
                }`}>
                  {task.status}
                </span>
              </div>
            </div>

            {/* Terminal & Diffs Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Terminal Logs Panel */}
              <div className="bg-[#0d111c] border border-dark-700 rounded-2xl p-5 shadow-xl space-y-3">
                <div className="flex items-center justify-between border-b border-dark-700 pb-2.5">
                  <div className="flex items-center gap-2 font-bold text-xs text-white">
                    <Terminal className="w-4 h-4 text-brand-cyan" />
                    <span>Live Agent Terminal Execution Logs</span>
                  </div>
                  <span className="text-[11px] text-gray-400 font-mono">{logs.length} entries</span>
                </div>
                <div className="bg-[#07090e] border border-dark-700 rounded-xl p-3.5 font-mono text-xs overflow-y-auto max-h-80 space-y-1.5 select-text">
                  {logs.length === 0 ? (
                    <p className="text-gray-500 italic">Waiting for terminal execution logs...</p>
                  ) : (
                    logs.map((l, idx) => (
                      <div key={idx} className="text-gray-300 border-b border-dark-800/50 pb-1">
                        <span className="text-brand-cyan text-[10px] mr-2">[{l.timestamp.split('T')[1]?.split('.')[0] || 'LOG'}]</span>
                        <span className="text-emerald-400 font-bold mr-1 font-sans">[{l.event_type}]:</span>
                        <span>{l.message}</span>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* Line Diffs Panel */}
              <div className="bg-[#0d111c] border border-dark-700 rounded-2xl p-5 shadow-xl space-y-3">
                <div className="flex items-center justify-between border-b border-dark-700 pb-2.5">
                  <div className="flex items-center gap-2 font-bold text-xs text-white">
                    <FileCode className="w-4 h-4 text-brand-purple" />
                    <span>Codebase Line Modifications ({task.files_modified?.length || 0})</span>
                  </div>
                  {task.git_diff && (
                    <button
                      onClick={() => {
                        navigator.clipboard.writeText(task.git_diff || '');
                        setDiffCopied(true);
                        setTimeout(() => setDiffCopied(false), 2000);
                      }}
                      className="px-2 py-1 bg-dark-900 text-gray-300 rounded text-[11px] flex items-center gap-1 border border-dark-700"
                    >
                      {diffCopied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>{diffCopied ? 'Copied' : 'Copy Diff'}</span>
                    </button>
                  )}
                </div>

                <div className="bg-[#07090e] border border-dark-700 rounded-xl p-3.5 font-mono text-xs overflow-x-auto max-h-80 select-text leading-relaxed">
                  {!task.git_diff ? (
                    <p className="text-gray-500 italic">No workspace files modified yet.</p>
                  ) : (
                    task.git_diff.split('\n').map((line, idx) => {
                      let cls = 'text-gray-300';
                      if (line.startsWith('+') && !line.startsWith('+++')) cls = 'text-emerald-400 bg-emerald-500/10 px-1 rounded';
                      else if (line.startsWith('-') && !line.startsWith('---')) cls = 'text-rose-400 bg-rose-500/10 px-1 rounded';
                      else if (line.startsWith('@@')) cls = 'text-brand-cyan font-bold';
                      return <div key={idx} className={cls}>{line}</div>;
                    })
                  )}
                </div>
              </div>
            </div>

            {/* Commit & Pull Request Action Panel */}
            <div className="bg-gradient-to-r from-[#0d111c] to-emerald-950/30 border border-emerald-500/40 rounded-2xl p-6 shadow-2xl space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-dark-700 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-white">Publish AI Changes to GitHub Repository</h3>
                  <p className="text-xs text-gray-400 mt-0.5">Directly commit changes or create an official GitHub Pull Request.</p>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-xs text-gray-400">Branch:</label>
                  <input
                    type="text"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    className="bg-dark-900 border border-dark-600 rounded-lg px-2 py-1 text-xs text-white font-mono w-24 focus:outline-none"
                  />
                </div>
              </div>

              {actionStatus && (
                <div className={`p-3 rounded-xl border text-xs font-semibold flex items-center justify-between gap-2 ${
                  actionStatus.success ? 'bg-emerald-500/10 border-emerald-500/40 text-emerald-300' : 'bg-rose-500/10 border-rose-500/40 text-rose-300'
                }`}>
                  <span>{actionStatus.message}</span>
                  {actionStatus.url && (
                    <a href={actionStatus.url} target="_blank" rel="noreferrer" className="px-2.5 py-1 bg-emerald-600 text-white rounded text-[11px] flex items-center gap-1 shrink-0">
                      <span>View PR</span> <ExternalLink className="w-3 h-3" />
                    </a>
                  )}
                </div>
              )}

              <div className="flex flex-col md:flex-row items-center gap-3">
                <input
                  type="text"
                  value={commitMsg}
                  onChange={(e) => setCommitMsg(e.target.value)}
                  placeholder={`Commit message (Default: feat(ai-agent): ${task.issue_description || 'Update code'})`}
                  className="flex-1 w-full bg-dark-900 border border-dark-600 rounded-xl px-3.5 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                />

                <div className="flex items-center gap-2 shrink-0 w-full md:w-auto">
                  <button
                    onClick={handleCommitPush}
                    disabled={committing || creatingPR}
                    className="flex-1 md:flex-none px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
                  >
                    {committing ? <Loader2 className="w-4 h-4 animate-spin" /> : <UploadCloud className="w-4 h-4" />}
                    <span>Commit & Push</span>
                  </button>

                  <button
                    onClick={handleCommitAndPR}
                    disabled={committing || creatingPR}
                    className="flex-1 md:flex-none px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs rounded-xl flex items-center justify-center gap-2 shadow-lg disabled:opacity-50"
                  >
                    {creatingPR ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitPullRequest className="w-4 h-4 text-cyan-300" />}
                    <span>Commit & Create PR</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;
