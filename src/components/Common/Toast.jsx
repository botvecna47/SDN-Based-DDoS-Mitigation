import React from 'react';
import { AlertTriangle, CheckCircle, Info, XCircle, X } from 'lucide-react';

export default function Toast({ toast, onClose }) {
  if (!toast) return null;

  const bgStyles = {
    danger: 'bg-rose-950/90 border-rose-500/80 text-rose-200 shadow-rose-950/50',
    warning: 'bg-amber-950/90 border-amber-500/80 text-amber-200 shadow-amber-950/50',
    success: 'bg-emerald-950/90 border-emerald-500/80 text-emerald-200 shadow-emerald-950/50',
    info: 'bg-slate-900/90 border-cyan-500/60 text-cyan-200 shadow-cyan-950/50'
  };

  const icons = {
    danger: <AlertTriangle className="w-5 h-5 text-rose-400 shrink-0 animate-pulse" />,
    warning: <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />,
    success: <CheckCircle className="w-5 h-5 text-emerald-400 shrink-0" />,
    info: <Info className="w-5 h-5 text-cyan-400 shrink-0" />
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 max-w-md transition-all duration-300 animate-in fade-in slide-in-from-bottom-5">
      <div className={`flex items-center gap-3 p-4 rounded-xl border backdrop-blur-md shadow-2xl ${bgStyles[toast.type] || bgStyles.info}`}>
        {icons[toast.type] || icons.info}
        <p className="text-sm font-medium tracking-wide flex-1">{toast.message}</p>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-white/10 text-white/60 hover:text-white transition-colors"
          title="Dismiss"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
