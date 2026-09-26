import React, { useState } from 'react';
import {
  Github,
  GitBranch,
  Bot,
  Code2,
  GitPullRequest,
  CheckCircle2,
  ArrowRight,
  Sparkles,
  Send,
  Loader2,
  UploadCloud,
  Check,
  ChevronRight,
  Lock,
} from 'lucide-react';
import { CreateTaskPayload, TaskResponse } from '../types/api';

interface WorkflowWizardProps {
  onStartTask: (payload: CreateTaskPayload) => void;
  isRunning: boolean;
  task: TaskResponse | null;
  onOpenPRModal?: () => void;
}

export const WorkflowWizard: React.FC<WorkflowWizardProps> = ({
  onStartTask,
  isRunning,
  task,
  onOpenPRModal,
}) => {
  // Step State: 1 = Auth, 2 = Select Repo, 3 = Task Prompt, 4 = AI Execution, 5 = Review & Commit
  const [currentStep, setCurrentStep] = useState<number>(1);
  const [githubToken, setGithubToken] = useState<string>('');
  const [githubUser, setGithubUser] = useState({
    authenticated: true,
    username: 'VanshSharma88',
    name: 'Vansh Sharma',
    avatar: 'https://github.com/VanshSharma88.png',
  });

  const [selectedRepoUrl, setSelectedRepoUrl] = useState<string>('https://github.com/VanshSharma88/Basic_Calculator.git');
  const [selectedBranch, setSelectedBranch] = useState<string>('main');
  const [taskPrompt, setTaskPrompt] = useState<string>('make the UI of calculator black and white');

  const [commitMessage, setCommitMessage] = useState<string>('');
  const [committing, setCommitting] = useState<boolean>(false);
  const [commitStatusMsg, setCommitStatusMsg] = useState<string | null>(null);

  const mockRepos = [
    { name: 'VanshSharma88/Basic_Calculator', url: 'https://github.com/VanshSharma88/Basic_Calculator.git', branch: 'main' },
    { name: 'VanshSharma88/Loginform', url: 'https://github.com/VanshSharma88/Loginform.git', branch: 'main' },
    { name: 'chinmay7980/CaffiPilot', url: 'https://github.com/chinmay7980/CaffiPilot.git', branch: 'main' },
  ];

  // Auto-advance step based on execution
  const effectiveStep = isRunning
    ? 4
    : task?.status?.toUpperCase() === 'COMPLETED'
    ? 5
    : currentStep;

  const handleLaunchAgent = (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskPrompt.trim()) return;
    setCurrentStep(4);
    onStartTask({
      git_url: selectedRepoUrl,
      branch: selectedBranch,
      issue_description: taskPrompt,
      model: 'qwen2.5-coder:1.5b',
      max_steps: 35,
      auto_verify: true,
    });
  };

  const handleDirectCommitPush = async () => {
    if (!task) return;
    setCommitting(true);
    setCommitStatusMsg(null);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/github/commit-and-push/${task.task_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          commit_message: commitMessage || `feat(ai-agent): ${task.issue_description}`,
          branch_name: selectedBranch,
        }),
      });
      const data = await res.json();
      if (data.success) {
        setCommitStatusMsg(`✅ Successfully committed [${data.commit_sha}] and pushed to remote branch '${data.branch}'!`);
      } else {
        setCommitStatusMsg(`⚠️ Commit failed: ${data.detail || 'Unknown error'}`);
      }
    } catch (err: any) {
      setCommitStatusMsg(`❌ Failed to push changes: ${err.message || 'Server error'}`);
    } finally {
      setCommitting(false);
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Top Stepper Indicator Navigation */}
      <div className="bg-dark-800/80 border border-dark-700/80 rounded-2xl p-4 shadow-xl">
        <div className="grid grid-cols-5 gap-2 text-center text-xs">
          {[
            { step: 1, label: '1. GitHub Auth', icon: Github },
            { step: 2, label: '2. Select Repo', icon: GitBranch },
            { step: 3, label: '3. Describe Task', icon: Bot },
            { step: 4, label: '4. AI Changes', icon: Code2 },
            { step: 5, label: '5. Review & Commit', icon: GitPullRequest },
          ].map(({ step, label, icon: Icon }) => {
            const isDone = effectiveStep > step;
            const isCurrent = effectiveStep === step;
            return (
              <button
                key={step}
                onClick={() => {
                  if (step <= effectiveStep || task) setCurrentStep(step);
                }}
                disabled={step > effectiveStep && !task}
                className={`py-2 px-3 rounded-xl border flex flex-col items-center gap-1.5 transition-all ${
                  isCurrent
                    ? 'bg-brand-blue/20 border-brand-blue text-white shadow-lg shadow-brand-blue/20 ring-1 ring-brand-blue'
                    : isDone
                    ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
                    : 'bg-dark-900/40 border-dark-700 text-gray-500 opacity-60'
                }`}
              >
                <div className="flex items-center gap-1">
                  {isDone ? <Check className="w-3.5 h-3.5" /> : <Icon className="w-3.5 h-3.5" />}
                  <span className="font-semibold hidden sm:inline">{label}</span>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* STEP 1: Login & Authorize with GitHub */}
      <div
        className={`p-6 rounded-2xl border transition-all duration-300 ${
          effectiveStep === 1
            ? 'bg-dark-800 border-brand-blue/60 shadow-xl shadow-brand-blue/10 ring-1 ring-brand-blue/30'
            : 'bg-dark-800/50 border-dark-700/60 opacity-90'
        }`}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-gray-900 border border-dark-600 flex items-center justify-center text-white shrink-0">
              <Github className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-brand-cyan">
                  Step 1
                </span>
                <h3 className="text-base font-bold text-white">Login with GitHub</h3>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Authenticate your account to grant CaffiPilot access to your GitHub repositories.
              </p>
            </div>
          </div>

          {githubUser.authenticated ? (
            <div className="flex items-center gap-3 px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
              <img src={githubUser.avatar} alt={githubUser.username} className="w-5 h-5 rounded-full" />
              <span>@{githubUser.username}</span>
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            </div>
          ) : (
            <button
              onClick={() => setGithubUser({ ...githubUser, authenticated: true })}
              className="px-4 py-2 bg-white text-dark-900 font-bold text-xs rounded-xl hover:bg-gray-100 flex items-center gap-2"
            >
              <Github className="w-4 h-4" />
              Authorize GitHub Session
            </button>
          )}
        </div>

        {effectiveStep === 1 && (
          <div className="mt-5 pt-4 border-t border-dark-700/60 flex items-center justify-between">
            <span className="text-xs text-emerald-400 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" /> Authorized as @{githubUser.username}
            </span>
            <button
              onClick={() => setCurrentStep(2)}
              className="px-4 py-2 bg-brand-blue text-white font-semibold text-xs rounded-xl hover:bg-brand-blue/90 flex items-center gap-2 shadow-md"
            >
              Next: Select Repository <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* STEP 2: Select a Repository */}
      <div
        className={`p-6 rounded-2xl border transition-all duration-300 ${
          effectiveStep === 2
            ? 'bg-dark-800 border-brand-blue/60 shadow-xl shadow-brand-blue/10 ring-1 ring-brand-blue/30'
            : 'bg-dark-800/50 border-dark-700/60 opacity-90'
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
                <h3 className="text-base font-bold text-white">Select a Repository</h3>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                Choose from your authorized GitHub repositories or specify a custom GitHub repo URL.
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-1">
              <div className="md:col-span-2">
                <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                  Select User Repository
                </label>
                <select
                  value={selectedRepoUrl}
                  onChange={(e) => setSelectedRepoUrl(e.target.value)}
                  className="w-full bg-dark-900 border border-dark-600 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-blue"
                >
                  {mockRepos.map((r) => (
                    <option key={r.url} value={r.url}>
                      {r.name} ({r.branch})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-gray-300 mb-1">
                  Branch
                </label>
                <input
                  type="text"
                  value={selectedBranch}
                  onChange={(e) => setSelectedBranch(e.target.value)}
                  className="w-full bg-dark-900 border border-dark-600 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-brand-blue"
                />
              </div>
            </div>

            {effectiveStep === 2 && (
              <div className="pt-3 flex justify-end">
                <button
                  onClick={() => setCurrentStep(3)}
                  className="px-4 py-2 bg-brand-blue text-white font-semibold text-xs rounded-xl hover:bg-brand-blue/90 flex items-center gap-2 shadow-md"
                >
                  Next: Describe Task <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* STEP 3: Describe Coding Task */}
      <div
        className={`p-6 rounded-2xl border transition-all duration-300 ${
          effectiveStep === 3
            ? 'bg-dark-800 border-brand-blue/60 shadow-xl shadow-brand-blue/10 ring-1 ring-brand-blue/30'
            : 'bg-dark-800/50 border-dark-700/60 opacity-90'
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
                <h3 className="text-base font-bold text-white">Describe the Coding Task</h3>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                Specify what bug to fix or feature to implement in your selected repository.
              </p>
            </div>

            <form onSubmit={handleLaunchAgent} className="space-y-3">
              <textarea
                rows={2}
                value={taskPrompt}
                onChange={(e) => setTaskPrompt(e.target.value)}
                placeholder="For example: 'Fix login authentication error' or 'Make UI black and white'..."
                className="w-full bg-dark-900 border border-dark-600 rounded-xl p-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-blue resize-none"
              />

              <div className="flex items-center justify-between pt-1">
                <div className="flex items-center gap-2 text-[11px] text-gray-400">
                  <Sparkles className="w-3.5 h-3.5 text-brand-purple" />
                  <span>Preset: UI Enhancement / Bug Fix</span>
                </div>

                <button
                  type="submit"
                  disabled={isRunning}
                  className="px-5 py-2.5 bg-gradient-to-r from-brand-blue to-brand-purple text-white text-xs font-bold rounded-xl hover:opacity-90 flex items-center gap-2 shadow-lg disabled:opacity-50"
                >
                  {isRunning ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Executing Autonomous Agent...
                    </>
                  ) : (
                    <>
                      <Send className="w-4 h-4" />
                      Launch AI Agent Fix
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>

      {/* STEP 4: AI Makes Changes */}
      <div
        className={`p-6 rounded-2xl border transition-all duration-300 ${
          effectiveStep === 4
            ? 'bg-dark-800 border-brand-blue/60 shadow-xl shadow-brand-blue/10 ring-1 ring-brand-blue/30'
            : 'bg-dark-800/50 border-dark-700/60 opacity-90'
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 flex items-center justify-center shrink-0">
              <Code2 className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold uppercase tracking-wider text-brand-cyan">
                  Step 4
                </span>
                <h3 className="text-base font-bold text-white">AI Makes Changes</h3>
              </div>
              <p className="text-xs text-gray-400 mt-0.5">
                Backend clones repository, edits files, and executes verification tests in sandbox environment.
              </p>
            </div>
          </div>

          {isRunning && (
            <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-brand-blue/10 border border-brand-blue/30 text-brand-cyan text-xs font-bold animate-pulse">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>AI Agent ReAct Loop Running...</span>
            </div>
          )}
        </div>
      </div>

      {/* STEP 5: Review & Commit Changes */}
      <div
        className={`p-6 rounded-2xl border transition-all duration-300 ${
          effectiveStep === 5
            ? 'bg-dark-800 border-emerald-500/60 shadow-xl shadow-emerald-500/10 ring-1 ring-emerald-500/30'
            : 'bg-dark-800/50 border-dark-700/60 opacity-90'
        }`}
      >
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0">
                <GitPullRequest className="w-6 h-6" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
                    Step 5
                  </span>
                  <h3 className="text-base font-bold text-white">Review & Commit Changes</h3>
                </div>
                <p className="text-xs text-gray-400 mt-0.5">
                  Review generated file diffs and explicitly authorization committing/pushing changes to GitHub.
                </p>
              </div>
            </div>
          </div>

          {effectiveStep === 5 && (
            <div className="pt-2 space-y-4 border-t border-dark-700/60">
              {commitStatusMsg && (
                <div className="p-3 rounded-xl bg-dark-900 border border-emerald-500/30 text-emerald-400 text-xs font-medium">
                  {commitStatusMsg}
                </div>
              )}

              <div className="flex flex-col sm:flex-row items-center gap-3">
                <input
                  type="text"
                  value={commitMessage}
                  onChange={(e) => setCommitMessage(e.target.value)}
                  placeholder={`Commit Message (Default: feat(ai-agent): ${task?.issue_description || 'Applied fixes'})`}
                  className="flex-1 w-full bg-dark-900 border border-dark-600 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none focus:border-emerald-500"
                />

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={handleDirectCommitPush}
                    disabled={committing}
                    className="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-xl flex items-center gap-2 shadow-lg transition-colors disabled:opacity-50"
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
        </div>
      </div>
    </div>
  );
};
