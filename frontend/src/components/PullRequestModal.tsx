import React, { useState } from 'react';
import { X, GitPullRequest, GitBranch, ExternalLink, CheckCircle2, Loader2 } from 'lucide-react';
import { TaskResponse } from '../types/api';

interface PullRequestModalProps {
  isOpen: boolean;
  task: TaskResponse | null;
  onClose: () => void;
}

export const PullRequestModal: React.FC<PullRequestModalProps> = ({ isOpen, task, onClose }) => {
  const [branchName, setBranchName] = useState(`caffipilot/fix-${task?.task_id || 'patch'}`);
  const [prTitle, setPrTitle] = useState(task ? `fix(ai-agent): ${task.issue_description}` : '');
  const [prBody, setPrBody] = useState(
    task
      ? `### CaffiPilot Autonomous AI Changes\n\n- **Issue**: ${task.issue_description}\n- **Summary**: ${
          task.final_summary || 'Applied automated edits and verification.'
        }\n- **Files Modified**: ${task.files_modified?.join(', ') || 'None'}`
      : ''
  );
  const [submitting, setSubmitting] = useState(false);
  const [createdPrUrl, setCreatedPrUrl] = useState<string | null>(null);

  if (!isOpen || !task) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/v1/github/pr/${task.task_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          branch_name: branchName,
          title: prTitle,
          body: prBody,
        }),
      });
      const data = await res.json();
      if (data.pr_url) {
        setCreatedPrUrl(data.pr_url);
      }
    } catch (err) {
      console.warn('PR creation error:', err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
      <div className="bg-dark-800 border border-dark-700 rounded-2xl w-full max-w-lg overflow-hidden shadow-2xl space-y-4">
        <div className="px-6 py-4 border-b border-dark-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <GitPullRequest className="w-5 h-5 text-emerald-400" />
            <h3 className="text-base font-bold text-white">Create GitHub Pull Request</h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        {createdPrUrl ? (
          <div className="p-6 text-center space-y-4">
            <div className="w-12 h-12 bg-emerald-500/20 text-emerald-400 rounded-2xl flex items-center justify-center mx-auto border border-emerald-500/30">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <h4 className="text-base font-bold text-white">Pull Request Staged Successfully!</h4>
            <p className="text-xs text-gray-400">
              Feature branch <code className="text-brand-cyan">{branchName}</code> has been pushed to GitHub.
            </p>
            <a
              href={createdPrUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-xl transition-colors"
            >
              Open Pull Request on GitHub
              <ExternalLink className="w-4 h-4" />
            </a>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1">Target Branch Name</label>
              <div className="relative">
                <GitBranch className="w-4 h-4 text-gray-400 absolute left-3 top-3" />
                <input
                  type="text"
                  value={branchName}
                  onChange={(e) => setBranchName(e.target.value)}
                  className="w-full bg-dark-900 border border-dark-600 rounded-xl pl-9 pr-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1">PR Title</label>
              <input
                type="text"
                value={prTitle}
                onChange={(e) => setPrTitle(e.target.value)}
                className="w-full bg-dark-900 border border-dark-600 rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-emerald-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1">PR Description</label>
              <textarea
                rows={4}
                value={prBody}
                onChange={(e) => setPrBody(e.target.value)}
                className="w-full bg-dark-900 border border-dark-600 rounded-xl p-3 text-xs text-white focus:outline-none focus:border-emerald-500 resize-none"
              />
            </div>

            <div className="flex items-center justify-end gap-3 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-dark-700 text-gray-300 font-semibold text-xs rounded-xl hover:bg-dark-600"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold text-xs rounded-xl flex items-center gap-2 transition-colors disabled:opacity-50"
              >
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitPullRequest className="w-4 h-4" />}
                Submit PR Authorization
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
