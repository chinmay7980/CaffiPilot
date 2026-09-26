import React, { useState } from 'react';
import { FileCode, FilePlus, FileEdit, Code, ChevronDown, ChevronRight, Copy, Check } from 'lucide-react';

interface FileChangesPanelProps {
  filesModified: string[];
  gitDiff?: string;
}

export const FileChangesPanel: React.FC<FileChangesPanelProps> = ({
  filesModified,
  gitDiff,
}) => {
  const [showDiff, setShowDiff] = useState(true);
  const [copied, setCopied] = useState(false);

  const handleCopyDiff = () => {
    if (gitDiff) {
      navigator.clipboard.writeText(gitDiff);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const fileCount = filesModified.length;

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-2xl p-5 shadow-xl space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-dark-700 pb-3">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-brand-blue" />
          <h3 className="text-sm font-semibold text-white">File Changes & Modifications</h3>
          <span className="text-xs px-2 py-0.5 rounded-full bg-brand-blue/10 border border-brand-blue/30 text-brand-cyan font-mono font-bold">
            {fileCount} {fileCount === 1 ? 'file' : 'files'} changed
          </span>
        </div>

        {gitDiff && (
          <button
            onClick={() => setShowDiff(!showDiff)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-dark-900 border border-dark-700 text-xs text-gray-300 hover:text-white transition-colors"
          >
            {showDiff ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            <span>{showDiff ? 'Hide Git Diff' : 'Show Git Diff'}</span>
          </button>
        )}
      </div>

      {/* List of modified files */}
      {fileCount === 0 ? (
        <p className="text-xs text-gray-400 italic">No workspace files modified yet.</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {filesModified.map((file, idx) => (
            <div
              key={idx}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-dark-900 border border-dark-700 text-xs font-mono text-gray-200"
            >
              <FileEdit className="w-3.5 h-3.5 text-brand-cyan" />
              <span>{file}</span>
            </div>
          ))}
        </div>
      )}

      {/* Git Diff View */}
      {gitDiff && showDiff && (
        <div className="space-y-2 pt-2">
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span className="flex items-center gap-1.5">
              <Code className="w-3.5 h-3.5 text-gray-400" />
              Unified Git Diff
            </span>
            <button
              onClick={handleCopyDiff}
              className="flex items-center gap-1 px-2.5 py-1 rounded bg-dark-900 border border-dark-700 hover:text-white transition-colors text-[11px]"
            >
              {copied ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
              <span>{copied ? 'Copied' : 'Copy Diff'}</span>
            </button>
          </div>

          <div className="bg-[#070a11] border border-dark-700 rounded-xl p-4 font-mono text-xs overflow-x-auto max-h-72 select-text leading-relaxed">
            {gitDiff.split('\n').map((line, idx) => {
              let colorClass = 'text-gray-300';
              if (line.startsWith('+') && !line.startsWith('+++')) {
                colorClass = 'text-emerald-400 bg-emerald-500/10 px-1 rounded';
              } else if (line.startsWith('-') && !line.startsWith('---')) {
                colorClass = 'text-rose-400 bg-rose-500/10 px-1 rounded';
              } else if (line.startsWith('@@')) {
                colorClass = 'text-brand-cyan font-bold';
              } else if (line.startsWith('diff --git')) {
                colorClass = 'text-amber-400 font-bold border-t border-dark-700 pt-1 mt-1 block';
              }
              return (
                <div key={idx} className={colorClass}>
                  {line}
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
