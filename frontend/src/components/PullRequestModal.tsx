import React, { useState } from 'react';
import { TaskResponse } from '../types/api';
import { X, GitPullRequest, Loader2, ExternalLink, CheckCircle2, AlertCircle } from 'lucide-react';

interface PullRequestModalProps {
  isOpen: boolean;
  task: TaskResponse | null;
  onClose: () => void;
}

export const PullRequestModal: React.FC<PullRequestModalProps> = ({ isOpen, task, onClose }) => {
  const [prTitle, setPrTitle] = useState('');
  const [prBody, setPrBody] = useState('');
  const [targetBranch, setTargetBranch] = useState('main');
  const [featureBranch, setFeatureBranch] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ success: boolean; message: string; url?: string } | null>(null);

  if (!isOpen || !task) return null;

  const handleSubmitPR = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/github/create-pr/${task.task_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: prTitle || `feat(ai-agent): ${task.issue_description}`,
          body: prBody || `Autonomous AI agent task execution for issue:\n${task.issue_description}`,
          target_branch: targetBranch,
          branch_name: featureBranch || `caffipilot/feature-${task.task_id.replace('task_', '')}`,
        }),
      });

      const data = await res.json();
      if (data.success) {
        setResult({
          success: true,
          message: data.message || 'Pull Request created successfully!',
          url: data.pr_url,
        });
      } else {
        setResult({
          success: false,
          message: data.detail || 'Failed to create Pull Request.',
        });
      }
    } catch (err: any) {
      setResult({
        success: false,
        message: err.message || 'Server connection error.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-dark-800 border border-dark-700 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-dark-700 pb-3">
          <div className="flex items-center gap-2 text-white font-bold text-base">
            <GitPullRequest className="w-5 h-5 text-emerald-400" />
            <span>Create GitHub Pull Request</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-1 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Result Alert */}
        {result && (
          <div
            className={`p-3.5 rounded-xl border text-xs font-semibold flex items-center justify-between gap-2 ${
              result.success
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-300'
            }`}
          >
            <div className="flex items-center gap-2">
              {result.success ? <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" /> : <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />}
              <span>{result.message}</span>
            </div>
            {result.url && (
              <a
                href={result.url}
                target="_blank"
                rel="noreferrer"
                className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] rounded-lg flex items-center gap-1 shrink-0"
              >
                <span>View PR</span>
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmitPR} className="space-y-4 text-xs">
          <div>
            <label className="block text-gray-300 font-semibold mb-1">Pull Request Title</label>
            <input
              type="text"
              value={prTitle}
              onChange={(e) => setPrTitle(e.target.value)}
              placeholder={`feat(ai-agent): ${task.issue_description}`}
              className="w-full bg-dark-900 border border-dark-600 rounded-xl px-3.5 py-2 text-white focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-gray-300 font-semibold mb-1">Target Base Branch</label>
              <input
                type="text"
                value={targetBranch}
                onChange={(e) => setTargetBranch(e.target.value)}
                placeholder="main"
                className="w-full bg-dark-900 border border-dark-600 rounded-xl px-3.5 py-2 text-white font-mono focus:outline-none focus:border-emerald-500"
              />
            </div>
            <div>
              <label className="block text-gray-300 font-semibold mb-1">New Feature Branch</label>
              <input
                type="text"
                value={featureBranch}
                onChange={(e) => setFeatureBranch(e.target.value)}
                placeholder={`caffipilot/feature-${task.task_id.replace('task_', '')}`}
                className="w-full bg-dark-900 border border-dark-600 rounded-xl px-3.5 py-2 text-white font-mono focus:outline-none focus:border-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="block text-gray-300 font-semibold mb-1">Description / PR Notes</label>
            <textarea
              rows={3}
              value={prBody}
              onChange={(e) => setPrBody(e.target.value)}
              placeholder="Describe the changes made by the AI agent..."
              className="w-full bg-dark-900 border border-dark-600 rounded-xl px-3.5 py-2 text-white focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div className="flex items-center justify-end gap-2 pt-2 border-t border-dark-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-dark-700 hover:bg-dark-600 text-gray-300 rounded-xl font-semibold"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl flex items-center gap-2 shadow-lg disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitPullRequest className="w-4 h-4" />}
              <span>Create Pull Request</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
