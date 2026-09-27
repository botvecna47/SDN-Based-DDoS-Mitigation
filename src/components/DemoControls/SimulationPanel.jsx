import React, { useState } from 'react';
import { Play, Shield, RefreshCw, AlertTriangle, WifiOff, Terminal, X, ChevronDown, ChevronUp } from 'lucide-react';

export default function SimulationPanel({
  isOpen,
  onClose,
  onTriggerAttack,
  onTriggerMitigation,
  onResetNormal,
  onToggleOffline,
  currentScenario,
  controllerOnline
}) {
  const [showCliHint, setShowCliHint] = useState(false);

  return (
    <div className={`fixed bottom-4 left-1/2 -translate-x-1/2 z-40 w-11/12 max-w-4xl transition-all duration-300 ${
      isOpen ? 'translate-y-0 opacity-100' : 'translate-y-24 opacity-0 pointer-events-none'
    }`}>
      <div className="bg-slate-950/95 border border-cyan-500/40 rounded-2xl p-4 sm:p-5 shadow-2xl backdrop-blur-xl shadow-cyan-950/40">
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-cyan-400 animate-pulse" />
            <h4 className="text-xs sm:text-sm font-bold uppercase tracking-wider text-cyan-300">
              Project Presentation & Attack Simulation Panel
            </h4>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
              Active: {currentScenario}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowCliHint(!showCliHint)}
              className="text-xs text-slate-400 hover:text-slate-200 flex items-center gap-1 px-2.5 py-1 rounded bg-slate-900 border border-slate-800"
            >
              <Terminal className="w-3.5 h-3.5 text-cyan-400" />
              <span>Backend hping3 Command</span>
              {showCliHint ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
            <button
              onClick={onClose}
              className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* CLI Hint dropdown for College Defense */}
        {showCliHint && (
          <div className="mb-4 p-3 rounded-xl bg-slate-900 border border-slate-800 text-xs font-mono text-slate-300">
            <div className="text-[11px] text-cyan-400 font-bold mb-1">
              Mininet Terminal hping3 Attack Command:
            </div>
            <code className="text-rose-300 bg-black/50 p-1.5 rounded block select-all">
              mininet&gt; h2 hping3 -S -p 80 --flood --rand-source 10.0.0.1
            </code>
            <p className="text-[10px] text-slate-400 mt-1.5">
              Running this in the Mininet VM floods switch s1 with SYN packets. The Ryu controller detects the anomaly and flags status as UNDER_ATTACK.
            </p>
          </div>
        )}

        {/* Action Buttons */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
          {/* 1. Attack Trigger */}
          <button
            onClick={() => onTriggerAttack('TCP SYN Flood')}
            className={`flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl font-bold text-xs transition-all ${
              currentScenario === 'UNDER_ATTACK'
                ? 'bg-red-600 text-white shadow-lg shadow-red-600/50 ring-2 ring-red-400'
                : 'bg-red-950/60 hover:bg-red-900/80 text-red-200 border border-red-500/50'
            }`}
          >
            <AlertTriangle className="w-4 h-4 text-red-400" />
            <span>Inject SYN Flood</span>
          </button>

          {/* 2. Automated Mitigation Trigger */}
          <button
            onClick={onTriggerMitigation}
            className={`flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl font-bold text-xs transition-all ${
              currentScenario === 'MITIGATING'
                ? 'bg-amber-600 text-white shadow-lg shadow-amber-600/50'
                : 'bg-amber-950/60 hover:bg-amber-900/80 text-amber-200 border border-amber-500/50'
            }`}
          >
            <Shield className="w-4 h-4 text-amber-400" />
            <span>Trigger Mitigation</span>
          </button>

          {/* 3. Reset to Normal */}
          <button
            onClick={onResetNormal}
            className={`flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl font-bold text-xs transition-all ${
              currentScenario === 'NORMAL'
                ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-600/50'
                : 'bg-emerald-950/60 hover:bg-emerald-900/80 text-emerald-200 border border-emerald-500/50'
            }`}
          >
            <RefreshCw className="w-4 h-4 text-emerald-400" />
            <span>Normal Traffic</span>
          </button>

          {/* 4. Resilience Test (Offline) */}
          <button
            onClick={onToggleOffline}
            className={`flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl font-bold text-xs transition-all ${
              !controllerOnline
                ? 'bg-rose-700 text-white'
                : 'bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700'
            }`}
          >
            <WifiOff className="w-4 h-4 text-slate-400" />
            <span>{controllerOnline ? 'Simulate Offline' : 'Reconnect Controller'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
