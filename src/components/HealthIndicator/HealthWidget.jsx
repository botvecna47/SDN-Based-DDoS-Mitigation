import React from 'react';
import { ShieldCheck, ShieldAlert, Shield, Cpu, Activity, AlertTriangle, Radio } from 'lucide-react';

export default function HealthWidget({ currentStats, controllerOnline }) {
  const status = currentStats?.status || 'NORMAL';
  const isAttack = status === 'UNDER_ATTACK';
  const isMitigating = status === 'MITIGATING';
  const isNormal = status === 'NORMAL';

  const ml = currentStats?.ml_detection || {
    model: 'Random Forest + Entropy',
    attack_probability: 0.02,
    classification: 'Benign',
    entropy_score: 3.82,
    threshold: 0.75
  };

  const controller = currentStats?.controller_info || {
    name: 'Ryu Controller',
    protocol: 'OpenFlow 1.3',
    switches_online: 4,
    latency_ms: 1.4
  };

  return (
    <div className={`p-6 rounded-2xl bg-slate-900/80 border transition-all duration-500 backdrop-blur-md shadow-2xl ${
      !controllerOnline
        ? 'border-rose-700 bg-rose-950/20'
        : isAttack
        ? 'border-red-500/80 bg-red-950/25 shadow-red-950/50 animate-pulse-red'
        : isMitigating
        ? 'border-amber-500/80 bg-amber-950/20 shadow-amber-950/40'
        : 'border-emerald-500/40 bg-emerald-950/10 shadow-emerald-950/20'
    }`}>
      {/* Title */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-slate-300" />
          <h3 className="text-base font-bold text-white tracking-wide">
            System Health Indicator
          </h3>
        </div>
        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
          SDN State Engine
        </span>
      </div>

      {/* Main Status Hero Badge */}
      <div className={`p-6 rounded-2xl border text-center transition-all duration-500 relative overflow-hidden ${
        !controllerOnline
          ? 'bg-rose-950/40 border-rose-500/60 text-rose-300'
          : isAttack
          ? 'bg-red-900/40 border-red-500 text-red-200 shadow-xl shadow-red-950/60'
          : isMitigating
          ? 'bg-amber-900/30 border-amber-500 text-amber-200 shadow-lg shadow-amber-950/40'
          : 'bg-emerald-900/20 border-emerald-500/60 text-emerald-300 shadow-lg shadow-emerald-950/30'
      }`}>
        {/* Glow radar ripple */}
        <div className="flex justify-center mb-3">
          <div className={`relative p-4 rounded-full border ${
            !controllerOnline
              ? 'bg-rose-500/20 border-rose-500 text-rose-400'
              : isAttack
              ? 'bg-red-500/30 border-red-500 text-red-400 animate-bounce'
              : isMitigating
              ? 'bg-amber-500/20 border-amber-500 text-amber-400 animate-spin'
              : 'bg-emerald-500/20 border-emerald-500 text-emerald-400'
          }`}>
            {!controllerOnline ? (
              <AlertTriangle className="w-10 h-10" />
            ) : isAttack ? (
              <ShieldAlert className="w-10 h-10" />
            ) : isMitigating ? (
              <Shield className="w-10 h-10" />
            ) : (
              <ShieldCheck className="w-10 h-10" />
            )}
          </div>
        </div>

        <div className="space-y-1">
          <div className="text-[11px] font-mono tracking-widest uppercase opacity-80">
            Network Defense Posture
          </div>
          <div className="text-2xl sm:text-3xl font-black font-mono tracking-tight uppercase">
            {!controllerOnline
              ? 'CONTROLLER OFFLINE'
              : isAttack
              ? 'UNDER ATTACK'
              : isMitigating
              ? 'MITIGATION IN PROGRESS'
              : 'NORMAL'}
          </div>
          <p className="text-xs max-w-xs mx-auto opacity-90 pt-1">
            {!controllerOnline
              ? 'Cannot establish handshake with Ryu SDN Controller (REST API unreachable).'
              : isAttack
              ? 'Abnormal traffic detected! Ingress packets exceed anomaly baseline threshold.'
              : isMitigating
              ? 'Ryu OpenFlow drop actions installed. Filtering malicious flow entries.'
              : 'All SDN switches reporting healthy OpenFlow telemetry. Zero anomalies.'}
          </p>
        </div>
      </div>

      {/* Machine Learning Model Inference Metrics */}
      <div className="mt-5 space-y-3.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-slate-400 font-medium flex items-center gap-1.5">
            <Cpu className="w-3.5 h-3.5 text-cyan-400" />
            ML Threat Probability
          </span>
          <span className={`font-mono font-bold ${
            ml.attack_probability > 0.5 ? 'text-red-400' : 'text-emerald-400'
          }`}>
            {(ml.attack_probability * 100).toFixed(1)}%
          </span>
        </div>

        {/* Threat Level Progress Bar */}
        <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden border border-slate-700/60">
          <div
            className={`h-full transition-all duration-500 rounded-full ${
              ml.attack_probability > 0.7
                ? 'bg-gradient-to-r from-amber-500 to-red-500'
                : ml.attack_probability > 0.3
                ? 'bg-amber-400'
                : 'bg-gradient-to-r from-emerald-500 to-cyan-400'
            }`}
            style={{ width: `${Math.min(100, Math.max(5, ml.attack_probability * 100))}%` }}
          />
        </div>

        {/* Detailed telemetry metrics grid */}
        <div className="grid grid-cols-2 gap-2 pt-2 text-xs">
          <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[10px] text-slate-400 block uppercase">Classification</span>
            <span className={`font-semibold font-mono text-xs ${
              isAttack ? 'text-red-400' : 'text-slate-200'
            }`}>
              {ml.classification || 'Benign'}
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[10px] text-slate-400 block uppercase">Flow Entropy</span>
            <span className={`font-mono font-semibold text-xs ${
              ml.entropy_score < 2.0 ? 'text-red-400' : 'text-cyan-300'
            }`}>
              {ml.entropy_score} <span className="text-[10px] font-normal text-slate-400">/ 4.0</span>
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[10px] text-slate-400 block uppercase">OpenFlow Switches</span>
            <span className="font-mono text-slate-200 font-semibold text-xs">
              {controller.switches_online} Online
            </span>
          </div>

          <div className="p-2.5 rounded-xl bg-slate-950/60 border border-slate-800">
            <span className="text-[10px] text-slate-400 block uppercase">Controller Latency</span>
            <span className="font-mono text-emerald-400 font-semibold text-xs">
              {controller.latency_ms || 1.2} ms
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
