import React, { useState } from 'react';
import {
  Github,
  GitBranch,
  Bot,
  Code2,
  GitPullRequest,
  CheckCircle2,
  ArrowDown,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Send,
  Loader2,
} from 'lucide-react';
import { CreateTaskPayload } from '../types/api';

interface WorkflowWizardProps {
  onStartTask: (payload: CreateTaskPayload) => void;
  isRunning: boolean;
  activeStep: number;
  taskStatus: string | null;
  filesModifiedCount: number;
  onOpenPRModal?: () => void;
}

export const WorkflowWizard: React.FC<WorkflowWizardProps> = ({
  onStartTask,
  isRunning,
  activeStep,
  taskStatus,
  filesModifiedCount,
  onOpenPRModal,
}) => {
  const [githubUser, setGithubUser] = useState({
    name: 'Vansh Sharma',
    username: 'VanshSharma88',
    avatar: 'https://github.com/VanshSharma88.png',
    authenticated: true,
  });

  const [selectedRepo, setSelectedRepo] = useState('https://github.com/VanshSharma88/Basic_Calculator.git');
  const [selectedBranch, setSelectedBranch] = useState('main');
  const [taskPrompt, setTaskPrompt] = useState('make the UI of calculator black and white');

  const reposList = [
    { name: 'VanshSharma88/Basic_Calculator', url: 'https://github.com/VanshSharma88/Basic_Calculator.git' },
    { name: 'VanshSharma88/Loginform', url: 'https://github.com/VanshSharma88/Loginform.git' },
    { name: 'chinmay7980/CaffiPilot', url: 'https://github.com/chinmay7980/CaffiPilot.git' },
  ];

  const handleLaunch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskPrompt.strip ? taskPrompt.trim() : taskPrompt) return;
    onStartTask({
      git_url: selectedRepo,
      branch: selectedBranch,
      issue_description: taskPrompt,
      model: 'qwen2.5-coder:1.5b',
      max_steps: 35,
      auto_verify: true,
    });
  };

  const currentStep = isRunning
    ? 4
    : taskStatus === 'completed'
    ? 5
    : activeStep || 1;

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* 5-Step Execution Workflow Card Sequence */}
      <div className="space-y-4">
        {/* Step 1: Login with GitHub */}
        <div
          className={`p-6 rounded-2xl border transition-all duration-300 ${
            currentStep === 1
              ? 'bg-dark-800/90 border-brand-blue/60 shadow-lg shadow-brand-blue/10 ring-1 ring-brand-blue/30'
              : 'bg-dark-800/40 border-dark-700/60 opacity-90'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-gray-900 border border-dark-600 flex items-center justify-center text-white">
                <Github className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-brand-cyan">
                    Step 1
                  </span>
                  <h3 className="text-base font-bold text-white">Login with GitHub</h3>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  User signs in and authorizes your application to access selected repositories.
                </p>
              </div>
            </div>

            {githubUser.authenticated ? (
              <div className="flex items-center gap-3 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
                <img
                  src={githubUser.avatar}
                  alt={githubUser.username}
                  className="w-5 h-5 rounded-full"
                />
                <span>@{githubUser.username}</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
            ) : (
              <button className="px-4 py-2 bg-white text-dark-900 font-semibold text-xs rounded-xl hover:bg-gray-100 flex items-center gap-2">
                <Github className="w-4 h-4" />
                Sign in with GitHub
              </button>
            )}
          </div>
        </div>

        {/* Step Arrow */}
        <div className="flex justify-center my-1 text-gray-500">
          <ArrowDown className="w-4 h-4 animate-bounce" />
        </div>

        {/* Step 2: Select a Repository */}
        <div
          className={`p-6 rounded-2xl border transition-all duration-300 ${
            currentStep === 2
              ? 'bg-dark-800/90 border-brand-blue/60 shadow-lg shadow-brand-blue/10 ring-1 ring-brand-blue/30'
              : 'bg-dark-800/40 border-dark-700/60 opacity-90'
          }`}
        >
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 flex items-center justify-center shrink-0">
              <GitBranch className="w-6 h-6" />
            </div>
            <div className="flex-1 space-y-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-brand-cyan">
                    Step 2
                  </span>
                  <h3 className="text-base font-bold text-white">Select a repository</h3>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  Choose a repository and branch from the user's authorized GitHub account.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div className="md:col-span-2">
                  <label className="block text-[11px] font-medium text-gray-400 mb-1">
                    Repository URL / Select
                  </label>
                  <select
                    value={selectedRepo}
                    onChange={(e) => setSelectedRepo(e.target.value)}
                    className="w-full bg-dark-900 border border-dark-600 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-blue"
                  >
                    {reposList.map((r) => (
                      <option key={r.url} value={r.url}>
                        {r.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-[11px] font-medium text-gray-400 mb-1">
                    Target Branch
                  </label>
                  <input
                    type="text"
                    value={selectedBranch}
                    onChange={(e) => setSelectedBranch(e.target.value)}
                    className="w-full bg-dark-900 border border-dark-600 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-blue"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Step Arrow */}
        <div className="flex justify-center my-1 text-gray-500">
          <ArrowDown className="w-4 h-4 animate-bounce" />
        </div>

        {/* Step 3: Describe the coding task */}
        <div
          className={`p-6 rounded-2xl border transition-all duration-300 ${
            currentStep === 3
              ? 'bg-dark-800/90 border-brand-blue/60 shadow-lg shadow-brand-blue/10 ring-1 ring-brand-blue/30'
              : 'bg-dark-800/40 border-dark-700/60 opacity-90'
          }`}
        >
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400 flex items-center justify-center shrink-0">
              <Bot className="w-6 h-6" />
            </div>
            <div className="flex-1 space-y-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-brand-cyan">
                    Step 3
                  </span>
                  <h3 className="text-base font-bold text-white">Describe the coding task</h3>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  For example: "Fix the login bug and add tests." or "Make the UI black and white."
                </p>
              </div>

              <form onSubmit={handleLaunch} className="space-y-3">
                <textarea
                  rows={2}
                  value={taskPrompt}
                  onChange={(e) => setTaskPrompt(e.target.value)}
                  placeholder="Describe what changes you want the AI agent to implement..."
                  className="w-full bg-dark-900 border border-dark-600 rounded-xl p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-blue resize-none"
                />

                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 text-[11px] text-gray-400">
                    <Sparkles className="w-3.5 h-3.5 text-brand-purple" />
                    <span>Preset: UI enhancement / Bug fix</span>
                  </div>

                  <button
                    type="submit"
                    disabled={isRunning}
                    className="px-5 py-2.5 bg-gradient-to-r from-brand-blue to-brand-purple text-white text-xs font-semibold rounded-xl hover:opacity-90 transition-opacity flex items-center gap-2 disabled:opacity-50"
                  >
                    {isRunning ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Executing Task...
                      </>
                    ) : (
                      <>
                        <Send className="w-4 h-4" />
                        Execute AI Task
                      </>
                    )}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>

        {/* Step Arrow */}
        <div className="flex justify-center my-1 text-gray-500">
          <ArrowDown className="w-4 h-4 animate-bounce" />
        </div>

        {/* Step 4: AI makes changes */}
        <div
          className={`p-6 rounded-2xl border transition-all duration-300 ${
            currentStep === 4
              ? 'bg-dark-800/90 border-brand-blue/60 shadow-lg shadow-brand-blue/10 ring-1 ring-brand-blue/30'
              : 'bg-dark-800/40 border-dark-700/60 opacity-90'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center">
                <Code2 className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-brand-cyan">
                    Step 4
                  </span>
                  <h3 className="text-base font-bold text-white">AI makes changes</h3>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  Your backend clones the repository, edits files, and runs tests in a controlled environment.
                </p>
              </div>
            </div>

            {isRunning && (
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-blue/10 border border-brand-blue/30 text-brand-cyan text-xs font-medium animate-pulse">
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Backend Autonomous Loop Active</span>
              </div>
            )}
          </div>
        </div>

        {/* Step Arrow */}
        <div className="flex justify-center my-1 text-gray-500">
          <ArrowDown className="w-4 h-4 animate-bounce" />
        </div>

        {/* Step 5: Review and submit */}
        <div
          className={`p-6 rounded-2xl border transition-all duration-300 ${
            currentStep === 5
              ? 'bg-dark-800/90 border-emerald-500/60 shadow-lg shadow-emerald-500/10 ring-1 ring-emerald-500/30'
              : 'bg-dark-800/40 border-dark-700/60 opacity-90'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center">
                <GitPullRequest className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                    Step 5
                  </span>
                  <h3 className="text-base font-bold text-white">Review and submit</h3>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  Show the changes and let the user review them. Create a branch and pull request with explicit authorization.
                </p>
              </div>
            </div>

            <button
              onClick={onOpenPRModal}
              disabled={filesModifiedCount === 0}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-xl flex items-center gap-2 transition-colors disabled:opacity-40"
            >
              <GitPullRequest className="w-4 h-4" />
              Create Pull Request
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
