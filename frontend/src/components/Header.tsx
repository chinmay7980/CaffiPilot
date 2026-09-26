import React from 'react';
import { Cpu, RefreshCw, Settings, ShieldCheck, Wifi, WifiOff } from 'lucide-react';
import { HealthResponse } from '../types/api';

interface HeaderProps {
  health: HealthResponse | null;
  loadingHealth: boolean;
  onRefreshHealth: () => void;
  onOpenSettings: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  loadingHealth,
  onRefreshHealth,
  onOpenSettings,
}) => {
  const isOnline = !!health && health.status === 'ok';

  return (
    <header className="border-b border-dark-700 bg-dark-900/80 backdrop-blur sticky top-0 z-30 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
        {/* Title */}
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-brand-blue/20 to-brand-cyan/20 border border-brand-blue/30 text-brand-cyan shadow-lg shadow-brand-blue/5">
            <Cpu className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white tracking-tight">AI Coding Harness</h1>
              <span className="text-xs px-2 py-0.5 rounded-full bg-brand-blue/10 border border-brand-blue/20 text-brand-cyan font-mono">
                v{health?.version || '0.1.0'}
              </span>
            </div>
            <p className="text-xs text-gray-400">
              AI-powered repository task execution and testing dashboard
            </p>
          </div>
        </div>

        {/* Status Indicators & Settings */}
        <div className="flex items-center gap-3">
          {/* Model info badge */}
          {health && (
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-dark-800 border border-dark-700 text-xs font-mono text-gray-300">
              <ShieldCheck className="w-3.5 h-3.5 text-brand-emerald" />
              <span>Model: <strong className="text-white">{health.configured_model}</strong></span>
            </div>
          )}

          {/* Backend Status Indicator */}
          <button
            onClick={onRefreshHealth}
            disabled={loadingHealth}
            title="Click to check backend status"
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
              isOnline
                ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/20'
                : 'bg-rose-500/10 border-rose-500/30 text-rose-400 hover:bg-rose-500/20'
            }`}
          >
            {loadingHealth ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin text-gray-400" />
            ) : isOnline ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <Wifi className="w-3.5 h-3.5" />
                <span>Backend Online</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5" />
                <span>Backend Offline</span>
              </>
            )}
          </button>

          {/* Settings Trigger */}
          <button
            onClick={onOpenSettings}
            className="p-2 rounded-lg bg-dark-800 border border-dark-700 text-gray-300 hover:text-white hover:border-gray-600 transition-colors"
            title="Configure API Base URL"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>
      </div>
    </header>
  );
};
