import React, { useState, useEffect } from 'react';
import { Shield, ShieldAlert, Cpu, Radio, RefreshCw, Zap } from 'lucide-react';

export default function Header({
  status,
  controllerOnline,
  dataSource,
  onToggleDataSource,
  onOpenDemoModal
}) {
  const [time, setTime] = useState(new Date().toLocaleTimeString());

  useEffect(() => {
    const timer = setInterval(() => {
      setTime(new Date().toLocaleTimeString());
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  const isUnderAttack = status === 'UNDER_ATTACK';
  const isMitigating = status === 'MITIGATING';

  return (
    <header className={`relative border-b transition-colors duration-500 ${
      isUnderAttack 
        ? 'border-red-500/50 bg-gradient-to-r from-red-950/60 via-slate-950 to-red-950/60' 
        : isMitigating
        ? 'border-amber-500/40 bg-gradient-to-r from-amber-950/40 via-slate-950 to-amber-950/40'
        : 'border-slate-800/80 bg-slate-950/80'
    } backdrop-blur-md sticky top-0 z-40`}>
      {/* Visual pulse glow when under attack */}
      {isUnderAttack && (
        <div className="absolute inset-0 bg-red-600/10 pointer-events-none animate-pulse-banner" />
      )}

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-4">
        {/* Left: Branding & Core SDN Info */}
        <div className="flex items-center gap-3.5">
          <div className={`p-2.5 rounded-xl border transition-all duration-300 ${
            isUnderAttack 
              ? 'bg-red-500/20 border-red-500 text-red-400 animate-pulse shadow-lg shadow-red-500/30' 
              : isMitigating
              ? 'bg-amber-500/20 border-amber-500 text-amber-400 shadow-lg shadow-amber-500/20'
              : 'bg-cyan-500/10 border-cyan-500/40 text-cyan-400 shadow-lg shadow-cyan-500/10'
          }`}>
            {isUnderAttack ? (
              <ShieldAlert className="w-7 h-7" />
            ) : (
              <Shield className="w-7 h-7" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg sm:text-xl font-bold tracking-tight text-white flex items-center gap-2">
                SDN DDoS Defense Center
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-full bg-cyan-950 border border-cyan-500/40 text-cyan-300">
                  OpenFlow 1.3
                </span>
              </h1>
            </div>
            <p className="text-xs text-slate-400 flex items-center gap-2 mt-0.5">
              <span>Telemetry & ML Real-Time Mitigation System</span>
              <span className="text-slate-600">•</span>
              <span className="font-mono text-slate-300">{time}</span>
            </p>
          </div>
        </div>

        {/* Right: Controller Status & Mode Selectors */}
        <div className="flex items-center flex-wrap gap-2.5 sm:gap-3">
          {/* Controller Status Indicator */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono font-medium ${
            controllerOnline
              ? 'bg-emerald-950/40 border-emerald-500/40 text-emerald-400'
              : 'bg-rose-950/60 border-rose-500/60 text-rose-400 animate-pulse'
          }`}>
            <span className={`w-2 h-2 rounded-full ${
              controllerOnline ? 'bg-emerald-400 animate-ping' : 'bg-rose-500'
            }`} />
            <Radio className="w-3.5 h-3.5" />
            <span>{controllerOnline ? 'RYU CONTROLLER ONLINE' : 'CONTROLLER OFFLINE'}</span>
          </div>

          {/* Mode Switcher: Mock vs Live API */}
          <div className="flex items-center bg-slate-900 border border-slate-700/80 rounded-lg p-0.5 text-xs font-medium">
            <button
              onClick={() => onToggleDataSource('MOCK')}
              className={`px-3 py-1 rounded-md transition-all ${
                dataSource === 'MOCK'
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Simulation Mode
            </button>
            <button
              onClick={() => onToggleDataSource('LIVE_API')}
              className={`px-3 py-1 rounded-md transition-all ${
                dataSource === 'LIVE_API'
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
              title="Connects to Flask REST API at http://localhost:5000"
            >
              Flask API
            </button>
          </div>

          {/* Quick Demo Controls Trigger */}
          <button
            onClick={onOpenDemoModal}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 hover:text-white rounded-lg transition-colors shadow-sm"
          >
            <Zap className="w-3.5 h-3.5 text-amber-400" />
            <span>Attack Scenarios</span>
          </button>
        </div>
      </div>
    </header>
  );
}
