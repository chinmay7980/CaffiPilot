import React from 'react';
import { CheckCircle, AlertTriangle, HelpCircle, Terminal, Check, X } from 'lucide-react';

interface TestResultsPanelProps {
  verificationStatus?: string;
  testCommand?: string;
  testOutput?: string;
  errorMessage?: string;
}

export const TestResultsPanel: React.FC<TestResultsPanelProps> = ({
  verificationStatus,
  testCommand,
  testOutput,
  errorMessage,
}) => {
  const status = (verificationStatus || 'Not Run').toLowerCase();
  const isPassed = status === 'passed';
  const isFailed = status === 'failed';

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-2xl p-5 shadow-xl space-y-4">
      <div className="flex items-center justify-between border-b border-dark-700 pb-3">
        <div className="flex items-center gap-2">
          {isPassed ? (
            <CheckCircle className="w-5 h-5 text-emerald-400" />
          ) : isFailed ? (
            <AlertTriangle className="w-5 h-5 text-rose-400" />
          ) : (
            <HelpCircle className="w-5 h-5 text-gray-400" />
          )}
          <h3 className="text-sm font-semibold text-white">Automated Verification Test Results</h3>
        </div>

        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold uppercase ${
            isPassed
              ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-400'
              : isFailed
              ? 'bg-rose-500/10 border border-rose-500/30 text-rose-400'
              : 'bg-gray-700/50 border border-gray-600 text-gray-400'
          }`}
        >
          {verificationStatus || 'Not Run'}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="p-3 rounded-xl bg-dark-900 border border-dark-700">
          <span className="text-[11px] text-gray-400 block mb-1">Test Command Executed</span>
          <div className="flex items-center gap-2 font-mono text-xs text-brand-cyan">
            <Terminal className="w-3.5 h-3.5" />
            <span>{testCommand || 'pytest / npm test (Auto-detected)'}</span>
          </div>
        </div>

        <div className="p-3 rounded-xl bg-dark-900 border border-dark-700">
          <span className="text-[11px] text-gray-400 block mb-1">Test Status Breakdown</span>
          <div className="flex items-center gap-3 text-xs font-semibold">
            <span className="flex items-center gap-1 text-emerald-400">
              <Check className="w-3.5 h-3.5" /> {isPassed ? 'All Passed' : '0 Passed'}
            </span>
            <span className="flex items-center gap-1 text-rose-400">
              <X className="w-3.5 h-3.5" /> {isFailed ? '1 Failed' : '0 Failed'}
            </span>
          </div>
        </div>
      </div>

      {/* Output / Error Details */}
      {(testOutput || errorMessage) && (
        <div className="space-y-2 pt-1">
          <span className="text-xs font-semibold text-gray-300 block">
            {isFailed ? 'Error & Failure Output Details' : 'Verification Console Output'}
          </span>
          <div className="bg-[#070a11] border border-dark-700 rounded-xl p-3 font-mono text-xs text-gray-300 overflow-x-auto max-h-48 whitespace-pre-wrap select-text">
            {errorMessage || testOutput || 'Not available'}
          </div>
        </div>
      )}
    </div>
  );
};
