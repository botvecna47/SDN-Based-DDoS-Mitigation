import React from 'react';

export default function MetricCard({
  title,
  value,
  unit = '',
  subtitle,
  icon: Icon,
  colorScheme = 'cyan', // 'cyan' | 'red' | 'emerald' | 'amber' | 'purple'
  badgeText = null,
  isAlert = false
}) {
  const schemeStyles = {
    cyan: {
      border: 'border-cyan-500/20 hover:border-cyan-500/40',
      bgIcon: 'bg-cyan-500/10 text-cyan-400',
      valText: 'text-cyan-300'
    },
    red: {
      border: 'border-red-500/30 hover:border-red-500/60',
      bgIcon: 'bg-red-500/15 text-red-400',
      valText: 'text-red-400'
    },
    emerald: {
      border: 'border-emerald-500/20 hover:border-emerald-500/40',
      bgIcon: 'bg-emerald-500/10 text-emerald-400',
      valText: 'text-emerald-300'
    },
    amber: {
      border: 'border-amber-500/20 hover:border-amber-500/40',
      bgIcon: 'bg-amber-500/10 text-amber-400',
      valText: 'text-amber-300'
    },
    purple: {
      border: 'border-purple-500/20 hover:border-purple-500/40',
      bgIcon: 'bg-purple-500/10 text-purple-400',
      valText: 'text-purple-300'
    }
  };

  const style = schemeStyles[colorScheme] || schemeStyles.cyan;

  return (
    <div className={`relative p-5 rounded-2xl bg-slate-900/70 border ${style.border} backdrop-blur-md shadow-xl transition-all duration-300 ${
      isAlert ? 'ring-2 ring-red-500/50 bg-red-950/20' : ''
    }`}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs uppercase tracking-wider font-semibold text-slate-400">{title}</span>
        {Icon && (
          <div className={`p-2 rounded-xl ${style.bgIcon}`}>
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-1.5">
        <span className={`text-2xl sm:text-3xl font-extrabold font-mono tracking-tight ${style.valText}`}>
          {value}
        </span>
        {unit && <span className="text-xs font-medium text-slate-400">{unit}</span>}
      </div>

      <div className="mt-2.5 flex items-center justify-between text-xs text-slate-400">
        <span>{subtitle}</span>
        {badgeText && (
          <span className="px-2 py-0.5 rounded-full font-mono text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
            {badgeText}
          </span>
        )}
      </div>
    </div>
  );
}
