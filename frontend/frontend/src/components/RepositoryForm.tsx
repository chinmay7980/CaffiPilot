import React, { useState } from 'react';
import { Play, GitBranch, FolderGit2, Terminal, MessageSquare, AlertCircle } from 'lucide-react';
import { CreateTaskPayload } from '../types/api';

interface RepositoryFormProps {
  onSubmit: (payload: CreateTaskPayload) => void;
  isRunning: boolean;
  disabled: boolean;
}

export const RepositoryForm: React.FC<RepositoryFormProps> = ({
  onSubmit,
  isRunning,
  disabled,
}) => {
  const [gitUrl, setGitUrl] = useState('');
  const [branch, setBranch] = useState('');
  const [issueDescription, setIssueDescription] = useState('');
  const [testCommand, setTestCommand] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    const repoOrUrl = gitUrl.trim();
    const taskText = issueDescription.trim();

    if (!repoOrUrl) {
      setValidationError('Please enter a Git Repository URL or local repository path.');
      return;
    }

    if (!taskText) {
      setValidationError('Please enter a coding task or issue description.');
      return;
    }

    onSubmit({
      git_url: repoOrUrl.startsWith('http') || repoOrUrl.startsWith('git@') ? repoOrUrl : undefined,
      repo_path: !repoOrUrl.startsWith('http') && !repoOrUrl.startsWith('git@') ? repoOrUrl : undefined,
      branch: branch.trim() || undefined,
      issue_description: taskText,
      test_command: testCommand.trim() || undefined,
      auto_verify: true,
    });
  };

  const fillExample = (sampleRepo: string, sampleTask: string) => {
    setGitUrl(sampleRepo);
    setIssueDescription(sampleTask);
    setValidationError(null);
  };

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl space-y-5">
      <div className="flex items-center justify-between border-b border-dark-700 pb-3">
        <div className="flex items-center gap-2 text-white font-semibold">
          <FolderGit2 className="w-5 h-5 text-brand-blue" />
          <h2>Repository Task Submission</h2>
        </div>
        <span className="text-xs text-gray-400 font-mono">Input Form</span>
      </div>

      {validationError && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{validationError}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Repository URL & Branch */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="md:col-span-2">
            <label className="block text-xs font-medium text-gray-300 mb-1.5 flex items-center justify-between">
              <span>Git Repository URL / Local Workspace Path *</span>
            </label>
            <div className="relative">
              <input
                type="text"
                value={gitUrl}
                onChange={(e) => setGitUrl(e.target.value)}
                disabled={isRunning || disabled}
                placeholder="https://github.com/VanshSharma88/calculator.git"
                className="w-full pl-9 pr-3.5 py-2.5 bg-dark-900 border border-dark-700 rounded-xl text-sm font-mono text-white placeholder-gray-500 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue disabled:opacity-50"
              />
              <FolderGit2 className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">
              Branch Name (Optional)
            </label>
            <div className="relative">
              <input
                type="text"
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                disabled={isRunning || disabled}
                placeholder="main"
                className="w-full pl-9 pr-3.5 py-2.5 bg-dark-900 border border-dark-700 rounded-xl text-sm font-mono text-white placeholder-gray-500 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue disabled:opacity-50"
              />
              <GitBranch className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
            </div>
          </div>
        </div>

        {/* Task Description */}
        <div>
          <label className="block text-xs font-medium text-gray-300 mb-1.5">
            Coding Task / Issue Description *
          </label>
          <div className="relative">
            <textarea
              rows={3}
              value={issueDescription}
              onChange={(e) => setIssueDescription(e.target.value)}
              disabled={isRunning || disabled}
              placeholder="e.g., Fix calculation bug when negative numbers are passed, add modern dark styling in style.css, and verify test suite passes."
              className="w-full pl-9 pr-3.5 py-2.5 bg-dark-900 border border-dark-700 rounded-xl text-sm text-white placeholder-gray-500 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue disabled:opacity-50"
            />
            <MessageSquare className="w-4 h-4 text-gray-500 absolute left-3 top-3" />
          </div>
        </div>

        {/* Optional Test Command */}
        <div>
          <label className="block text-xs font-medium text-gray-300 mb-1.5">
            Optional Custom Test Command
          </label>
          <div className="relative">
            <input
              type="text"
              value={testCommand}
              onChange={(e) => setTestCommand(e.target.value)}
              disabled={isRunning || disabled}
              placeholder="pytest tests/ -v (or npm test, leave empty for auto-detection)"
              className="w-full pl-9 pr-3.5 py-2 bg-dark-900 border border-dark-700 rounded-xl text-xs font-mono text-white placeholder-gray-500 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue disabled:opacity-50"
            />
            <Terminal className="w-4 h-4 text-gray-500 absolute left-3 top-2.5" />
          </div>
        </div>

        {/* Action Buttons & Quick Presets */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">Quick Samples:</span>
            <button
              type="button"
              onClick={() => fillExample('https://github.com/VanshSharma88/calculator.git', 'Modernize UI layout with glassmorphism styling and dark theme.')}
              className="text-xs px-2.5 py-1 rounded-lg bg-dark-700 border border-dark-600 text-gray-300 hover:text-white hover:border-brand-blue transition-colors"
            >
              Calculator App UI
            </button>
          </div>

          <button
            type="submit"
            disabled={isRunning || disabled}
            className="flex items-center gap-2 px-6 py-2.5 bg-brand-blue hover:bg-blue-600 active:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-blue-500/20 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className={`w-4 h-4 fill-current ${isRunning ? 'animate-spin' : ''}`} />
            <span>{isRunning ? 'Executing Agent Task...' : 'Start Autonomous Task'}</span>
          </button>
        </div>
      </form>
    </div>
  );
};
