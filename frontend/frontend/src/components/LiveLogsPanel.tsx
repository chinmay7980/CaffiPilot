import React, { useEffect, useRef, useState } from 'react';
import { Terminal, Trash2, ArrowDownCircle, Shield } from 'lucide-react';
import { LogEntry } from '../types/api';

interface LiveLogsPanelProps {
  logs: LogEntry[];
  onClearLogs: () => void;
  isRunning: boolean;
}

export const LiveLogsPanel: React.FC<LiveLogsPanelProps> = ({
  logs,
  onClearLogs,
  isRunning,
}) => {
  const logContainerRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  const sanitizeLogMessage = (msg: string): string => {
    let text = msg.replace(/(sk-[a-zA-Z0-9_-]{20,})/g, '[REDACTED_API_KEY]');
    if (text.trim().startsWith('{') && text.trim().endsWith('}')) {
      try {
        const obj = JSON.parse(text.trim());
        if (obj.name && obj.arguments) {
          return `Tool: ${obj.name}(${JSON.stringify(obj.arguments)})`;
        }
      } catch {
        // Not valid JSON
      }
    }
    return text;
  };

  const getEventBadge = (eventType: string) => {
    switch (eventType) {
      case 'TASK_STARTED':
        return <span className="px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 font-mono text-[10px]">INIT</span>;
      case 'STEP_COMPLETED':
        return <span className="px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-400 font-mono text-[10px]">STEP</span>;
      case 'TOOL_RESULT':
        return <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-400 font-mono text-[10px]">TOOL</span>;
      case 'TASK_COMPLETED':
        return <span className="px-1.5 py-0.5 rounded bg-emerald-500/30 text-emerald-300 font-mono text-[10px]">SUCCESS</span>;
      case 'TASK_FAILED':
        return <span className="px-1.5 py-0.5 rounded bg-rose-500/30 text-rose-300 font-mono text-[10px]">ERROR</span>;
      case 'RETRY':
        return <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 font-mono text-[10px]">RETRY</span>;
      default:
        return <span className="px-1.5 py-0.5 rounded bg-gray-700 text-gray-300 font-mono text-[10px]">{eventType}</span>;
    }
  };

  return (
    <div className="bg-dark-800 border border-dark-700 rounded-2xl p-5 shadow-xl space-y-3">
      {/* Panel Header */}
      <div className="flex items-center justify-between border-b border-dark-700 pb-3">
        <div className="flex items-center gap-2">
          <Terminal className="w-4 h-4 text-brand-cyan" />
          <h3 className="text-sm font-semibold text-white">Live Execution Terminal</h3>
          <span className="text-[11px] px-2 py-0.5 rounded-full bg-dark-900 border border-dark-700 text-gray-400 font-mono">
            {logs.length} entries
          </span>
          {isRunning && (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-500"></span>
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setAutoScroll(!autoScroll)}
            className={`p-1.5 rounded-lg border text-xs flex items-center gap-1 transition-colors ${
              autoScroll
                ? 'bg-brand-blue/20 border-brand-blue/30 text-brand-cyan'
                : 'bg-dark-900 border-dark-700 text-gray-400 hover:text-white'
            }`}
            title="Toggle Auto Scroll"
          >
            <ArrowDownCircle className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Auto-scroll</span>
          </button>

          <button
            onClick={onClearLogs}
            className="p-1.5 rounded-lg bg-dark-900 border border-dark-700 text-gray-400 hover:text-rose-400 hover:border-rose-500/30 transition-colors"
            title="Clear Log View"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Terminal Output Body */}
      <div
        ref={logContainerRef}
        className="h-64 sm:h-80 bg-[#070a11] border border-dark-700/80 rounded-xl p-4 font-mono text-xs overflow-y-auto space-y-2 select-text"
      >
        {logs.length === 0 ? (
          <div className="h-full flex items-center justify-center text-gray-500 space-x-2">
            <Shield className="w-4 h-4 text-gray-600" />
            <span>Terminal ready. Waiting for task execution logs...</span>
          </div>
        ) : (
          logs.map((log, index) => (
            <div key={index} className="flex items-start gap-2 hover:bg-dark-900/60 p-1 rounded transition-colors">
              <span className="text-gray-500 shrink-0 text-[11px]">
                {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : '--:--:--'}
              </span>
              <span className="shrink-0">{getEventBadge(log.event_type)}</span>
              <span className="text-gray-300 break-words leading-relaxed whitespace-pre-wrap flex-1">
                {sanitizeLogMessage(log.message)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
