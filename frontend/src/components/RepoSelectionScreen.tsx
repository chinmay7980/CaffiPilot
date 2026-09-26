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
  Lock,
  Globe,
} from 'lucide-react';
import { CreateTaskPayload } from '../types/api';

interface RepoSelectionScreenProps {
  user: { username: string; name: string; avatar: string; token: string };
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
  const [searchTerm, setSearchTerm] = useState<string>('');

  const [selectedRepoUrl, setSelectedRepoUrl] = useState<string>('https://github.com/VanshSharma88/Basic_Calculator.git');
  const [selectedBranch, setSelectedBranch] = useState<string>('main');
  const [taskPrompt, setTaskPrompt] = useState<string>('make the UI of calculator black and white');

  // Load user repositories dynamically from GitHub API
  useEffect(() => {
    const fetchRepos = async () => {
      setLoadingRepos(true);
      try {
        const res = await fetch(
          `http://127.0.0.1:8000/api/v1/github/repos?username=${encodeURIComponent(user.username)}&token=${encodeURIComponent(user.token)}`
        );
        const data = await res.json();
        if (Array.isArray(data) && data.length > 0) {
          setRepos(data);
          setSelectedRepoUrl(data[0].clone_url || `https://github.com/${data[0].full_name}.git`);
          setSelectedBranch(data[0].default_branch || 'main');
        }
      } catch (err) {
        console.warn('Failed to load user repos:', err);
      } finally {
        setLoadingRepos(false);
      }
    };
    fetchRepos();
  }, [user]);

  const filteredRepos = repos.filter(
    (r) =>
      r.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      r.full_name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleLaunch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskPrompt.trim()) return;
    onSubmitTask({
      git_url: selectedRepoUrl,
      branch: selectedBranch,
      issue_description: taskPrompt,
      model: 'qwen2.5-coder:1.5b',
      max_steps: 35,
      auto_verify: true,
    });
  };

  return (
    <div className="w-full max-w-5xl mx-auto space-y-6">
      {/* Authenticated User Header Banner */}
      <div className="bg-dark-800/90 border border-dark-700/80 rounded-2xl p-5 shadow-xl flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <img src={user.avatar} alt={user.username} className="w-10 h-10 rounded-full border border-dark-600 shadow-md" />
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-bold text-white">{user.name}</h2>
              <span className="text-[11px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/30">
                Connected
              </span>
            </div>
            <p className="text-xs text-gray-400">@{user.username} &bull; {repos.length} Repositories Authorized</p>
          </div>
        </div>

        <button
          onClick={onSignOut}
          className="px-3.5 py-1.5 bg-dark-700 hover:bg-dark-600 text-gray-300 text-xs font-semibold rounded-xl flex items-center gap-2 border border-dark-600 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Sign Out
        </button>
      </div>

      {/* Main Grid: Repository Picker & Task Input */}
      <div className="bg-dark-800/90 border border-dark-700/80 rounded-2xl p-6 shadow-2xl space-y-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold uppercase tracking-wider text-brand-cyan">Step 1 of 2</span>
            <h3 className="text-base font-bold text-white">Select a Repository from @{user.username}</h3>
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Choose the target repository where the AI agent will implement code modifications.
          </p>
        </div>

        {/* Repository Filter & List */}
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Search your repositories (e.g. Basic_Calculator, Loginform)..."
                className="w-full bg-dark-900 border border-dark-600 rounded-xl pl-9 pr-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-blue"
              />
            </div>
            <div className="w-36">
              <input
                type="text"
                value={selectedBranch}
                onChange={(e) => setSelectedBranch(e.target.value)}
                placeholder="Branch: main"
                className="w-full bg-dark-900 border border-dark-600 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-blue"
              />
            </div>
          </div>

          {/* Repositories Cards List */}
          {loadingRepos ? (
            <div className="p-8 text-center bg-dark-900/50 border border-dark-700 rounded-xl text-xs text-gray-400 space-y-2">
              <Loader2 className="w-6 h-6 animate-spin text-brand-cyan mx-auto" />
              <p>Fetching repositories directly from GitHub API for @{user.username}...</p>
            </div>
          ) : filteredRepos.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-60 overflow-y-auto pr-1">
              {filteredRepos.map((r) => {
                const isSelected = selectedRepoUrl === (r.clone_url || `https://github.com/${r.full_name}.git`);
                return (
                  <button
                    type="button"
                    key={r.id || r.name}
                    onClick={() => {
                      setSelectedRepoUrl(r.clone_url || `https://github.com/${r.full_name}.git`);
                      setSelectedBranch(r.default_branch || 'main');
                    }}
                    className={`p-3.5 rounded-xl border text-left transition-all ${
                      isSelected
                        ? 'bg-brand-blue/10 border-brand-blue shadow-md ring-1 ring-brand-blue/40'
                        : 'bg-dark-900/60 border-dark-700 hover:border-dark-600'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2 font-bold text-xs text-white">
                        <FolderGit2 className="w-4 h-4 text-brand-cyan shrink-0" />
                        <span className="truncate">{r.full_name || r.name}</span>
                      </div>
                      {isSelected && <CheckCircle2 className="w-4 h-4 text-brand-cyan shrink-0" />}
                    </div>
                    {r.description && (
                      <p className="text-[11px] text-gray-400 mt-1 line-clamp-1">{r.description}</p>
                    )}
                    <div className="flex items-center gap-2 mt-2 text-[10px] text-gray-500">
                      <GitBranch className="w-3 h-3" />
                      <span>{r.default_branch || 'main'}</span>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="p-4 bg-dark-900 border border-dark-700 rounded-xl text-xs text-gray-400">
              No matching repositories found. You can also paste any GitHub repository URL below.
            </div>
          )}

          <div>
            <label className="block text-[11px] font-semibold text-gray-300 mb-1">
              Or Custom GitHub Repository Clone URL
            </label>
            <input
              type="text"
              value={selectedRepoUrl}
              onChange={(e) => setSelectedRepoUrl(e.target.value)}
              placeholder="https://github.com/VanshSharma88/Basic_Calculator.git"
              className="w-full bg-dark-900 border border-dark-600 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-blue"
            />
          </div>
        </div>

        {/* Task Prompt Form */}
        <form onSubmit={handleLaunch} className="pt-4 border-t border-dark-700/60 space-y-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-bold uppercase tracking-wider text-brand-cyan">Step 2 of 2</span>
              <h3 className="text-sm font-bold text-white">Describe the Task / Issue</h3>
            </div>
            <textarea
              rows={3}
              required
              value={taskPrompt}
              onChange={(e) => setTaskPrompt(e.target.value)}
              placeholder="Describe what changes you want the AI agent to implement (e.g. 'Make the UI of calculator black and white' or 'Fix login authentication')..."
              className="w-full bg-dark-900 border border-dark-600 rounded-xl p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-blue resize-none"
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-[11px] text-gray-400">
              <Sparkles className="w-3.5 h-3.5 text-brand-purple" />
              <span>Target: {selectedRepoUrl.split('/').pop()?.replace('.git', '') || 'Selected Repo'}</span>
            </div>

            <button
              type="submit"
              disabled={isRunning}
              className="px-6 py-3 bg-gradient-to-r from-brand-blue to-brand-purple text-white text-xs font-bold rounded-xl hover:opacity-95 flex items-center gap-2 shadow-lg shadow-brand-blue/20 transition-opacity disabled:opacity-50"
            >
              {isRunning ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Executing AI Task...
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  Launch AI Agent Task
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
