import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend
} from 'recharts';
import { Activity, TrendingUp, AlertOctagon, CheckCircle2 } from 'lucide-react';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-slate-950/95 border border-slate-700/80 p-3 rounded-xl shadow-2xl backdrop-blur-md text-xs">
        <p className="font-mono text-slate-300 font-semibold mb-2 flex items-center gap-1.5">
          <Activity className="w-3.5 h-3.5 text-cyan-400" />
          Time: {label}
        </p>
        {payload.map((entry, index) => (
          <div key={`item-${index}`} className="flex items-center justify-between gap-4 py-0.5">
            <span style={{ color: entry.color }} className="font-medium flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: entry.color }} />
              {entry.name}:
            </span>
            <span className="font-mono font-bold text-white">
              {entry.value.toLocaleString()} <span className="text-[10px] text-slate-400 font-normal">pps</span>
            </span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function TrafficChart({ data = [], currentStats }) {
  const latestPps = currentStats ? currentStats.total_pps : (data[data.length - 1]?.total_pps || 0);
  const droppedPps = currentStats ? currentStats.dropped_pps : (data[data.length - 1]?.dropped_pps || 0);
  const isAttack = currentStats?.status === 'UNDER_ATTACK';
  const isMitigating = currentStats?.status === 'MITIGATING';

  // Compute peak PPS in current window
  const peakPps = data.reduce((max, pt) => Math.max(max, pt.total_pps || 0), 0);

  return (
    <div className={`p-6 rounded-2xl bg-slate-900/80 border transition-all duration-500 backdrop-blur-md shadow-2xl ${
      isAttack 
        ? 'border-red-500/60 shadow-red-950/40 animate-pulse-red' 
        : isMitigating
        ? 'border-amber-500/40 shadow-amber-950/30'
        : 'border-slate-800 shadow-slate-950/50'
    }`}>
      {/* Chart Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className={`p-2 rounded-lg ${isAttack ? 'bg-red-500/20 text-red-400' : 'bg-cyan-500/10 text-cyan-400'}`}>
              <Activity className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
                Global Traffic Monitor
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700">
                  Live Stream (1 Hz)
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Real-time OpenFlow port telemetry tracking packet throughput & anomaly spikes
              </p>
            </div>
          </div>
        </div>

        {/* Real-time Counters */}
        <div className="flex items-center gap-3">
          <div className="px-3.5 py-2 rounded-xl bg-slate-950/80 border border-slate-800 text-right">
            <span className="text-[10px] uppercase tracking-wider text-slate-400 block">Current Ingress</span>
            <span className={`text-lg font-mono font-bold ${
              isAttack ? 'text-red-400 animate-pulse' : 'text-cyan-400'
            }`}>
              {latestPps.toLocaleString()} <span className="text-xs font-normal text-slate-400">pps</span>
            </span>
          </div>

          <div className="px-3.5 py-2 rounded-xl bg-slate-950/80 border border-slate-800 text-right">
            <span className="text-[10px] uppercase tracking-wider text-slate-400 block">Peak Ingress</span>
            <span className="text-lg font-mono font-bold text-amber-400">
              {peakPps.toLocaleString()} <span className="text-xs font-normal text-slate-400">pps</span>
            </span>
          </div>

          {droppedPps > 0 && (
            <div className="px-3.5 py-2 rounded-xl bg-rose-950/40 border border-rose-500/40 text-right">
              <span className="text-[10px] uppercase tracking-wider text-rose-300 block">Mitigated Drop</span>
              <span className="text-lg font-mono font-bold text-rose-400">
                {droppedPps.toLocaleString()} <span className="text-xs font-normal text-rose-300">pps</span>
              </span>
            </div>
          )}
        </div>
      </div>

      {/* Main Chart Container */}
      <div className="w-full h-72 sm:h-80">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="totalPpsGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={isAttack ? '#ef4444' : '#06b6d4'} stopOpacity={0.4} />
                <stop offset="95%" stopColor={isAttack ? '#ef4444' : '#06b6d4'} stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="droppedPpsGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.6} />
                <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.05} />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
            <XAxis
              dataKey="time"
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
              dy={5}
            />
            <YAxis
              stroke="#64748b"
              fontSize={11}
              tickLine={false}
              axisLine={{ stroke: '#334155' }}
              tickFormatter={(v) => (v >= 1000 ? `${(v / 1000).toFixed(1)}k` : v)}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              verticalAlign="top"
              align="right"
              iconType="circle"
              wrapperStyle={{ paddingBottom: '12px', fontSize: '11px' }}
            />

            {/* Dropped malicious traffic when mitigating */}
            {(isMitigating || droppedPps > 0) && (
              <Area
                type="monotone"
                dataKey="dropped_pps"
                name="Dropped / Attack PPS"
                stroke="#f43f5e"
                strokeWidth={2}
                fillOpacity={1}
                fill="url(#droppedPpsGradient)"
                isAnimationActive={false}
              />
            )}

            {/* Normal/Total packets per second line */}
            <Area
              type="monotone"
              dataKey="total_pps"
              name={isAttack ? 'Total Ingress (DDoS Attack)' : 'Total Packets / Sec'}
              stroke={isAttack ? '#ef4444' : '#06b6d4'}
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#totalPpsGradient)"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Chart Footer Note */}
      <div className="mt-4 pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-xs text-slate-400">
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1.5">
            <span className={`w-2.5 h-2.5 rounded-full ${isAttack ? 'bg-red-500 animate-ping' : 'bg-cyan-400'}`} />
            Target: All OpenFlow Switches (s1-s4)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400" />
            Baseline Profile: ~850 pps
          </span>
        </div>
        <span className="font-mono text-[11px] text-slate-400">
          Threshold Alert Trigger: &gt; 5,000 pps
        </span>
      </div>
    </div>
  );
}
