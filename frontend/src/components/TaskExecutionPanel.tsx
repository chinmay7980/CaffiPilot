import React from 'react';
import { Activity, CheckCircle2, Clock, XCircle, Ban, Layers, RefreshCw, Code2 } from 'lucide-react';
import { TaskResponse, TaskStatus } from '../types/api';

interface TaskExecutionPanelProps {
  task: TaskResponse | null;
  onCancelTask: () => void;
  cancelling: boolean;
}

interface StageItem {
  id: string;
  label: string;
  description: string;
}

const STAGES: StageItem[] = [
  { id: 'queued', label: 'Initializing Task', description: 'Queued & environment setup' },
  { id: 'cloning', label: 'Cloning Repository', description: 'Fetching workspace code' },
  { id: 'exploring', label: 'Exploring Repository', description: 'Inspecting files & project structure' },
  { id: 'planning', label: 'Planning Changes', description: 'LLM generating task strategy' },
  { id: 'editing', label: 'Editing Files', description: 'Applying code patches & refactoring' },
  { id: 'testing', label: 'Running Tests', description: 'Executing verification runners' },
  { id: 'completed', label: 'Completed', description: 'Final report generated & changes verified' },
];

export const TaskExecutionPanel: React.FC<TaskExecutionPanelProps> = ({
  task,
  onCancelTask,
  cancelling,
}) => {
  if (!task) return null;

  const currentStatus = task.status.toLowerCase();
  const currentStep = task.current_step || 0;
  const maxSteps = task.max_steps || 35;
  const isRunning = currentStatus === 'running' || currentStatus === 'queued';
  const isCompleted = currentStatus === 'completed';
  const isFailed = currentStatus === 'failed';
  const isCancelled = currentStatus === 'cancelled';

  // Determine active stage index
  let activeStageIndex = 0;
  if (currentStatus === 'queued') activeStageIndex = 0;
  else if (currentStatus === 'running') {
    if (currentStep === 0) activeStageIndex = 1;
    else if (currentStep === 1) activeStageIndex = 2;
    else if (currentStep > 1 && currentStep < maxSteps - 2) activeStageIndex = 4;
    else activeStageIndex = 5;
  } else if (isCompleted) activeStageIndex = 6;
  else if (isFailed || isCancelled) activeStageIndex = 5;

  const getStatusBadge = (status: TaskStatus) => {
    const st = status.toUpperCase();
    switch (st) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-xs font-semibold">
            <CheckCircle2 className="w-3.5 h-3.5" /> COMPLETED
          </span>
        );
      case 'RUNNING':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/30 text-blue-400 text-xs font-semibold">
            <RefreshCw className="w-3.5 h-3.5 animate-spin" /> RUNNING
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs font-semibold">
            <XCircle className="w-3.5 h-3.5" /> FAILED
          </span>
        );
      case 'CANCELLED':
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold">
            <Ban className="w-3.5 h-3.5" /> CANCELLED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-gray-500/10 border border-gray-500/30 text-gray-400 text-xs font-semibold">
            <Clock className="w-3.5 h-3.5" /> QUEUED
          </span>
        );
    }
  };

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-2xl p-6 shadow-xl space-y-6">
      {/* Header Info */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-dark-700 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-3">
            <span className="text-xs font-mono text-gray-400">Task ID:</span>
            <span className="px-2.5 py-1 rounded-lg bg-dark-900 border border-dark-700 font-mono text-sm text-brand-cyan font-bold">
              {task.task_id}
            </span>
            {getStatusBadge(task.status)}
          </div>
          <p className="text-xs text-gray-400 flex items-center gap-2">
            <span>Workspace:</span>
            <span className="font-mono text-gray-200">{task.repo_path}</span>
          </p>
        </div>

        {/* Action button */}
        {isRunning && (
          <button
            onClick={onCancelTask}
            disabled={cancelling}
            className="flex items-center gap-1.5 px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 rounded-xl text-xs font-medium transition-colors"
          >
            <Ban className="w-3.5 h-3.5" />
            <span>{cancelling ? 'Cancelling...' : 'Cancel Task'}</span>
          </button>
        )}
      </div>

      {/* Progress metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3 rounded-xl bg-dark-900 border border-dark-700">
          <span className="text-[11px] text-gray-400 block mb-0.5">Agent Step Progress</span>
          <span className="text-sm font-bold font-mono text-white">
            {currentStep} / {maxSteps}
          </span>
        </div>

        <div className="p-3 rounded-xl bg-dark-900 border border-dark-700">
          <span className="text-[11px] text-gray-400 block mb-0.5">Tool Invocations</span>
          <span className="text-sm font-bold font-mono text-white">
            {task.tool_call_count || 0} calls
          </span>
        </div>

        <div className="p-3 rounded-xl bg-dark-900 border border-dark-700">
          <span className="text-[11px] text-gray-400 block mb-0.5">Total Tokens Consumed</span>
          <span className="text-sm font-bold font-mono text-brand-cyan">
            {task.total_tokens_consumed ? task.total_tokens_consumed.toLocaleString() : 0}
          </span>
        </div>

        <div className="p-3 rounded-xl bg-dark-900 border border-dark-700">
          <span className="text-[11px] text-gray-400 block mb-0.5">Verification Result</span>
          <span className={`text-sm font-bold capitalize ${
            task.verification_status === 'passed' ? 'text-emerald-400' : 'text-amber-400'
          }`}>
            {task.verification_status || 'In Progress'}
          </span>
        </div>
      </div>

      {/* Live Timeline */}
      <div className="space-y-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-gray-300">
          <Layers className="w-4 h-4 text-brand-blue" />
          <span>Live Execution Stage Timeline</span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2">
          {STAGES.slice(0, 4).map((stg, idx) => {
            const isFinished = idx < activeStageIndex || isCompleted;
            const isCurrent = idx === activeStageIndex && isRunning;
            return (
              <div
                key={stg.id}
                className={`p-3 rounded-xl border transition-all ${
                  isFinished
                    ? 'bg-emerald-500/5 border-emerald-500/20 text-emerald-400'
                    : isCurrent
                    ? 'bg-brand-blue/10 border-brand-blue/40 text-brand-cyan ring-1 ring-brand-blue/30'
                    : 'bg-dark-900 border-dark-700 text-gray-500'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs font-semibold">{stg.label}</span>
                  {isFinished ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  ) : isCurrent ? (
                    <Activity className="w-3.5 h-3.5 text-brand-cyan animate-pulse" />
                  ) : (
                    <span className="w-2 h-2 rounded-full bg-gray-600"></span>
                  )}
                </div>
                <p className="text-[11px] text-gray-400 truncate">{stg.description}</p>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
