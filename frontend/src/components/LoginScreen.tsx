import React, { useState } from 'react';
import { Github, Key, ArrowRight, ShieldCheck, Loader2, Sparkles, User, AlertCircle } from 'lucide-react';

interface LoginScreenProps {
  onLoginSuccess: (user: { username: string; name: string; avatar: string; token: string; reposCount: number }) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onLoginSuccess }) => {
  const [usernameInput, setUsernameInput] = useState<string>('');
  const [tokenInput, setTokenInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleOAuthLoginRedirect = () => {
    window.location.href = 'http://127.0.0.1:8000/api/v1/github/oauth/login';
  };

  const handleAuthenticate = async (e: React.FormEvent) => {
    e.preventDefault();
    const uname = usernameInput.trim();
    if (!uname && !tokenInput.trim()) {
      setErrorMsg('Please enter your GitHub Username or Personal Access Token.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    try {
      const url = tokenInput.trim()
        ? `http://127.0.0.1:8000/api/v1/github/user?token=${encodeURIComponent(tokenInput.trim())}`
        : `http://127.0.0.1:8000/api/v1/github/user?username=${encodeURIComponent(uname)}`;

      const res = await fetch(url);
      const data = await res.json();

      if (!res.ok || data.authenticated === false) {
        throw new Error(data.detail || data.error || data.message || 'Failed to verify GitHub account.');
      }

      onLoginSuccess({
        username: data.username,
        name: data.name || data.username,
        avatar: data.avatar_url || `https://github.com/${data.username}.png`,
        token: tokenInput.trim(),
        reposCount: data.public_repos || 0,
      });
    } catch (err: any) {
      setErrorMsg(err.message || 'Could not verify GitHub account. Please check your username or access token.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#07090e] px-4 py-12 text-gray-100 selection:bg-brand-blue selection:text-white relative overflow-hidden font-sans">
      {/* Dynamic Background Glow Effects */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-brand-blue/15 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-brand-purple/15 rounded-full blur-[120px] pointer-events-none" />

      <div className="w-full max-w-md space-y-6 relative z-10">
        {/* Brand Header */}
        <div className="text-center space-y-3">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-blue via-brand-purple to-cyan-400 p-0.5 shadow-2xl shadow-brand-blue/30 mx-auto transform hover:scale-105 transition-transform duration-300">
            <div className="w-full h-full bg-[#0d111c] rounded-[14px] flex items-center justify-center text-cyan-300">
              <Github className="w-8 h-8" />
            </div>
          </div>
          <div>
            <h1 className="text-2xl font-black text-white tracking-tight">GitHub Authentication</h1>
            <p className="text-xs text-gray-400 mt-1">
              Sign in with your GitHub Account to authorize repository access and launch autonomous AI coding agents.
            </p>
          </div>
        </div>

        {/* Premium Glassmorphic Card */}
        <div className="bg-[#0f1422]/80 backdrop-blur-xl border border-dark-600/60 rounded-3xl p-7 shadow-2xl space-y-6">
          {errorMsg && (
            <div className="p-3.5 rounded-2xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Official GitHub OAuth Button */}
          <div className="space-y-3">
            <button
              onClick={handleOAuthLoginRedirect}
              type="button"
              className="w-full py-3.5 px-4 bg-white hover:bg-gray-100 text-dark-900 font-extrabold text-xs rounded-2xl transition-all flex items-center justify-center gap-2.5 shadow-xl shadow-white/5 active:scale-[0.98]"
            >
              <Github className="w-5 h-5 text-dark-900" />
              <span>Sign in with GitHub Account</span>
              <ArrowRight className="w-4 h-4 opacity-70" />
            </button>

            <div className="relative flex py-1 items-center">
              <div className="flex-grow border-t border-dark-700"></div>
              <span className="flex-shrink mx-3 text-[10px] font-bold text-gray-500 uppercase tracking-widest">
                or verify via GitHub ID / PAT
              </span>
              <div className="flex-grow border-t border-dark-700"></div>
            </div>
          </div>

          <form onSubmit={handleAuthenticate} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                GitHub Username / Organization
              </label>
              <div className="relative">
                <User className="w-4 h-4 text-gray-400 absolute left-3.5 top-3.5" />
                <input
                  type="text"
                  value={usernameInput}
                  onChange={(e) => setUsernameInput(e.target.value)}
                  placeholder="Enter your GitHub username (e.g. octocat)..."
                  className="w-full bg-[#090c14] border border-dark-600 rounded-2xl pl-10 pr-3.5 py-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 mb-1.5">
                Personal Access Token <span className="text-gray-500 font-normal">(Optional for private repos)</span>
              </label>
              <div className="relative">
                <Key className="w-4 h-4 text-gray-400 absolute left-3.5 top-3.5" />
                <input
                  type="password"
                  value={tokenInput}
                  onChange={(e) => setTokenInput(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  className="w-full bg-[#090c14] border border-dark-600 rounded-2xl pl-10 pr-3.5 py-3 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue transition-all"
                />
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3.5 bg-gradient-to-r from-brand-blue via-brand-purple to-cyan-500 text-white font-extrabold text-xs rounded-2xl hover:opacity-95 transition-opacity flex items-center justify-center gap-2 shadow-xl shadow-brand-blue/25 disabled:opacity-50 active:scale-[0.98]"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Verifying Account with GitHub...
                </>
              ) : (
                <>
                  <ShieldCheck className="w-4 h-4" />
                  Verify & Access Repositories
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>

          <div className="pt-2 text-center text-[11px] text-gray-500 flex items-center justify-center gap-1.5 border-t border-dark-700/60">
            <Sparkles className="w-3.5 h-3.5 text-brand-purple" />
            <span>Zero Hardcoded Data &bull; Live GitHub Verification</span>
          </div>
        </div>
      </div>
    </div>
  );
};
