import React, { useState } from 'react';
import { Check, X } from 'lucide-react';
import { getApiBaseUrl, setApiBaseUrl } from '../services/api';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaved: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  onSaved,
}) => {
  const [url, setUrl] = useState(getApiBaseUrl());
  const [savedSuccess, setSavedSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setApiBaseUrl(url);
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onSaved();
      onClose();
    }, 600);
  };

  const handleReset = () => {
    setApiBaseUrl('http://localhost:8000');
    setUrl('http://localhost:8000');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="bg-dark-800 border border-dark-700 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-5">
        <div className="flex items-center justify-between border-b border-dark-700 pb-3">
          <h3 className="text-lg font-semibold text-white">Backend Connection Settings</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-dark-700 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-gray-300 mb-1.5">
              Backend API Base URL
            </label>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="http://localhost:8000"
              className="w-full px-3.5 py-2 bg-dark-900 border border-dark-700 rounded-xl text-sm font-mono text-white placeholder-gray-500 focus:outline-none focus:border-brand-blue focus:ring-1 focus:ring-brand-blue"
            />
            <p className="text-xs text-gray-400 mt-1.5">
              Set the URL of the running FastAPI server backend (`http://localhost:8000`).
            </p>
          </div>

          <div className="flex items-center justify-between pt-2">
            <button
              type="button"
              onClick={handleReset}
              className="text-xs text-gray-400 hover:text-white underline transition-colors"
            >
              Reset to Default
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-medium text-gray-300 hover:text-white rounded-xl bg-dark-700 hover:bg-dark-600 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="flex items-center gap-1.5 px-4 py-2 text-xs font-medium text-white rounded-xl bg-brand-blue hover:bg-blue-600 transition-colors shadow-lg shadow-blue-500/20"
              >
                {savedSuccess ? <Check className="w-3.5 h-3.5" /> : null}
                <span>{savedSuccess ? 'Saved!' : 'Save Connection'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
