import React, { useEffect, useState } from 'react';
import {
  GitBranch,
  Github,
  LogOut,
  Send,
  Loader2,
  Sparkles,
  Search,
  CheckCircle2,
  FolderGit2,
  AlertCircle,
  RefreshCw,
  Link,
  Code2,
} from 'lucide-react';
import { CreateTaskPayload } from '../types/api';

interface RepoSelectionScreenProps {
  user: { username: string; name: string; avatar: string; token: string; reposCount?: number };
  onSignOut: () => void;
  onSubmitTask: (payload: CreateTaskPayload) => void;
  isRunning: boolean;
}

export const RepoSelectionScreen: React.FC<RepoSelectionScreenProps> = ({
  user,
  onSignOut,
  onSubmitTask,
  isRunning,
}) => {
  const [repos, setRepos] = useState<Array<{ id: number; name: string; full_name: string; clone_url: string; default_branch: string; description: string; private: boolean }>>([]);
  const [loadingRepos, setLoadingRepos] = useState<boolean>(true);
  const [reposError, setReposError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const [githubUrlInput, setGithubUrlInput] = useState<string>('');
  const [targetBranch, setTargetBranch] = useState<string>('main');
  const [taskPrompt, setTaskPrompt] = useState<string>('');

  // Fetch ALL real repositories for the user account
  const loadUserRepos = async () => {
    setLoadingRepos(true);
    setReposError(null);
    try {
      const url = user.token
        ? `http://127.0.0.1:8000/api/v1/github/repos?token=${encodeURIComponent(user.token)}`
        : `http://127.0.0.1:8000/api/v1/github/repos?username=${encodeURIComponent(user.username)}`;

      const res = await fetch(url);
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to load repositories from GitHub.');
      }

      if (Array.isArray(data) && data.length > 0) {
        setRepos(data);
        // Default to first repo clone URL
        const firstUrl = data[0].clone_url || `https://github.com/${data[0].full_name}.git`;
        setGithubUrlInput((prev) => (prev ? prev : firstUrl));
        setTargetBranch(data[0].default_branch || 'main');
      } else {
        setRepos([]);
      }
    } catch (err: any) {
      setReposError(err.message || 'Failed to load user repositories from GitHub.');
    } finally {
      setLoadingRepos(false);
    }
  };

  useEffect(() => {
    loadUserRepos();
  }, [user]);

  const filteredRepos = repos.filter(
    (r) =>
      r.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.full_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleLaunch = (e: React.FormEvent) => {
    e.preventDefault();
    const cleanUrl = githubUrlInput.trim();
    if (!cleanUrl) {
      alert('Please enter or select a GitHub repository URL.');
      return;
    }
    if (!taskPrompt.trim()) {
      alert('Please enter a task description / issue to resolve.');
      return;
    }

    onSubmitTask({
      git_url: cleanUrl,
      branch: targetBranch.trim() || 'main',
      issue_description: taskPrompt.trim(),
      model: 'qwen2.5-coder:1.5b',
      max_steps: 35,
      auto_verify: true,
    });
  };

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6 font-sans">
      {/* User Authenticated Profile Bar */}
      <div className="bg-[#0f1422]/90 border border-dark-600/70 rounded-3xl p-5 shadow-2xl flex flex-wrap items-center justify-between gap-4 backdrop-blur-xl">
        <div className="flex items-center gap-4">
          <img
            src={user.avatar}
            alt={user.username}
            className="w-12 h-12 rounded-2xl border-2 border-brand-cyan/40 shadow-lg object-cover"
          />
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-extrabold text-white">{user.name}</h2>
              <span className="text-[11px] font-bold text-emerald-400 bg-emerald-500/10 px-2.5 py-0.5 rounded-full border border-emerald-500/30 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" /> Authenticated
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">
              @{user.username} &bull; {repos.length} Repositories Available
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={loadUserRepos}
            title="Refresh Account Repositories"
            className="p-2.5 bg-[#090c14] hover:bg-dark-700 text-gray-300 rounded-2xl border border-dark-600 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loadingRepos ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={onSignOut}
            className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-200 text-xs font-semibold rounded-2xl flex items-center gap-2 border border-dark-600 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </div>

      {/* Main Task Launch Card */}
      <div className="bg-[#0f1422]/90 border border-dark-600/70 rounded-3xl p-7 shadow-2xl space-y-6 backdrop-blur-xl">
        
        {/* Header Title */}
        <div className="border-b border-dark-700/80 pb-4">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-brand-cyan" />
            <h3 className="text-lg font-black text-white">Repository Task Execution</h3>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Provide any GitHub Repository URL and describe the issue/feature you want the autonomous AI agent to implement.
          </p>
        </div>

        <form onSubmit={handleLaunch} className="space-y-6">
          {/* Step 1: GitHub Repository URL Input */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-extrabold text-white flex items-center gap-2">
                <Link className="w-4 h-4 text-brand-cyan" />
                <span>GitHub Repository URL</span>
                <span className="text-rose-400">*</span>
              </label>
              <span className="text-[11px] text-gray-400 font-mono">Accepts any public or private GitHub repository</span>
            </div>

            <div className="relative">
              <Github className="w-4 h-4 text-gray-400 absolute left-3.5 top-3.5" />
              <input
                type="url"
                required
                value={githubUrlInput}
                onChange={(e) => setGithubUrlInput(e.target.value)}
                placeholder="https://github.com/VanshSharma88/Loginform.git"
                className="w-full bg-[#090c14] border border-dark-600 rounded-2xl pl-10 pr-3.5 py-3 text-xs text-white placeholder-gray-500 font-mono focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all"
              />
            </div>
          </div>

          {/* Quick Select from Account Repositories Grid */}
          <div className="space-y-3 bg-[#090c14]/70 border border-dark-700 p-4 rounded-2xl">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <span className="text-xs font-bold text-gray-300 flex items-center gap-1.5">
                <FolderGit2 className="w-3.5 h-3.5 text-brand-cyan" />
                Or click to select from @{user.username}'s Repositories ({filteredRepos.length}):
              </span>

              <div className="flex items-center gap-2">
                <div className="relative w-48">
                  <Search className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Search repos..."
                    className="w-full bg-dark-900 border border-dark-600 rounded-xl pl-8 pr-2 py-1.5 text-[11px] text-white focus:outline-none focus:border-brand-blue"
                  />
                </div>

                <div className="w-28">
                  <input
                    type="text"
                    value={targetBranch}
                    onChange={(e) => setTargetBranch(e.target.value)}
                    placeholder="Branch: main"
                    className="w-full bg-dark-900 border border-dark-600 rounded-xl px-2.5 py-1.5 text-[11px] text-white font-mono focus:outline-none focus:border-brand-blue"
                  />
                </div>
              </div>
            </div>

            {loadingRepos ? (
              <div className="py-6 text-center text-xs text-gray-400 flex items-center justify-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-brand-cyan" />
                <span>Loading repositories for @{user.username}...</span>
              </div>
            ) : reposError ? (
              <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{reposError}</span>
              </div>
            ) : filteredRepos.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 max-h-48 overflow-y-auto pr-1">
                {filteredRepos.map((r) => {
                  const cloneUrl = r.clone_url || `https://github.com/${r.full_name}.git`;
                  const isSelected = githubUrlInput.trim().toLowerCase() === cloneUrl.toLowerCase() || githubUrlInput.trim().toLowerCase() === `https://github.com/${r.full_name}`.toLowerCase();

                  return (
                    <button
                      type="button"
                      key={r.id || r.name}
                      onClick={() => {
                        setGithubUrlInput(cloneUrl);
                        if (r.default_branch) setTargetBranch(r.default_branch);
                      }}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        isSelected
                          ? 'bg-brand-blue/20 border-brand-blue shadow-md ring-1 ring-brand-blue/50'
                          : 'bg-dark-900/60 border-dark-700 hover:border-dark-600'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 font-bold text-xs text-white">
                          <FolderGit2 className="w-3.5 h-3.5 text-brand-cyan shrink-0" />
                          <span className="truncate">{r.full_name || r.name}</span>
                        </div>
                        {isSelected && <CheckCircle2 className="w-4 h-4 text-brand-cyan shrink-0" />}
                      </div>
                      {r.description && (
                        <p className="text-[11px] text-gray-400 mt-1 line-clamp-1">{r.description}</p>
                      )}
                      <div className="flex items-center gap-2 mt-2 text-[10px] text-gray-400 font-mono">
                        <GitBranch className="w-3 h-3 text-gray-400" />
                        <span>{r.default_branch || 'main'}</span>
                        {r.private && <span className="text-amber-400 bg-amber-400/10 px-1.5 py-0.2 rounded border border-amber-400/20">Private</span>}
                      </div>
                    </button>
                  );
                })}
              </div>
            ) : (
              <div className="p-3 text-xs text-gray-400 italic">
                No repositories found matching filter. Enter custom GitHub URL above.
              </div>
            )}
          </div>

          {/* Step 2: Task Description / Issue Input */}
          <div className="space-y-2">
            <label className="text-xs font-extrabold text-white flex items-center gap-2">
              <Code2 className="w-4 h-4 text-brand-purple" />
              <span>Issue Description / Task Instructions</span>
              <span className="text-rose-400">*</span>
            </label>
            <textarea
              rows={4}
              required
              value={taskPrompt}
              onChange={(e) => setTaskPrompt(e.target.value)}
              placeholder="Describe the issue or feature to implement (e.g. 'Create a file named chinuu.jsx in which print Hello World')..."
              className="w-full bg-[#090c14] border border-dark-600 rounded-2xl p-4 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all leading-relaxed resize-none"
            />
          </div>

          {/* Submit Action Bar */}
          <div className="pt-2 flex flex-wrap items-center justify-between gap-4 border-t border-dark-700/60">
            <div className="text-xs text-gray-400 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-cyan" />
              <span>Target: <span className="font-mono text-white">{githubUrlInput.split('/').pop()?.replace('.git', '') || 'GitHub Repo'}</span></span>
            </div>

            <button
              type="submit"
              disabled={isRunning || !githubUrlInput.trim() || !taskPrompt.trim()}
              className="px-8 py-3.5 bg-gradient-to-r from-brand-blue via-brand-purple to-cyan-500 text-white font-extrabold text-xs rounded-2xl hover:opacity-95 flex items-center justify-center gap-2.5 shadow-xl shadow-brand-blue/25 transition-all disabled:opacity-50 active:scale-[0.98]"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Starting AI Agent...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Launch AI Agent Task</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
