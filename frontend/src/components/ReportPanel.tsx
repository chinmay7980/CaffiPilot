import React, { useState } from 'react';
import { FileText, Copy, Check, RotateCcw, FileCode, CheckCircle2, AlertOctagon } from 'lucide-react';
import { TaskReportResponse, TaskResponse } from '../types/api';

interface ReportPanelProps {
  task: TaskResponse;
  report: TaskReportResponse | null;
  onReset: () => void;
  onScrollToDiff: () => void;
}

export const ReportPanel: React.FC<ReportPanelProps> = ({
  task,
  report,
  onReset,
  onScrollToDiff,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopyReport = () => {
    const textToCopy = report?.markdown_report || task.final_summary || 'Task completed.';
    navigator.clipboard.writeText(textToCopy);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-dark-700 pb-4">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-brand-cyan" />
          <h2 className="text-base font-bold text-white">Final Evaluation & Execution Report</h2>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyReport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-dark-900 border border-dark-700 text-xs text-gray-200 hover:text-white transition-colors"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
            <span>{copied ? 'Report Copied' : 'Copy Report'}</span>
          </button>

          <button
            onClick={onScrollToDiff}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-dark-900 border border-dark-700 text-xs text-brand-cyan hover:text-white transition-colors"
          >
            <FileCode className="w-3.5 h-3.5" />
            <span>View Diff</span>
          </button>

          <button
            onClick={onReset}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-xl bg-brand-blue hover:bg-blue-600 text-white text-xs font-semibold transition-colors shadow-md shadow-blue-500/20"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Run Another Task</span>
          </button>
        </div>
      </div>

      {/* Summary Card */}
      <div className="p-4 rounded-xl bg-dark-900 border border-dark-700 space-y-2">
        <div className="flex items-center justify-between text-xs text-gray-400">
          <span className="font-semibold text-gray-200">Executive Summary</span>
          <span className="font-mono text-emerald-400">Status: {task.status}</span>
        </div>
        <p className="text-sm text-gray-200 leading-relaxed">
          {task.final_summary || task.issue_description || 'Task execution finished successfully.'}
        </p>
      </div>

      {/* Markdown Report Render */}
      {report?.markdown_report && (
        <div className="space-y-2">
          <span className="text-xs font-semibold text-gray-400 block">Full Evaluation Markdown Report</span>
          <div className="bg-[#070a11] border border-dark-700 rounded-xl p-4 font-mono text-xs text-gray-300 overflow-y-auto max-h-96 whitespace-pre-wrap select-text leading-relaxed">
            {report.markdown_report}
          </div>
        </div>
      )}
    </div>
  );
};
