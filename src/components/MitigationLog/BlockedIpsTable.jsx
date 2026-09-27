import React, { useState } from 'react';
import { ShieldX, Search, Filter, Terminal, Copy, Check } from 'lucide-react';

export default function BlockedIpsTable({ blockedIps = [], lastAttackIp }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [copiedId, setCopiedId] = useState(null);

  const filteredIps = blockedIps.filter(item => {
    const q = searchTerm.toLowerCase();
    return (
      item.ip?.toLowerCase().includes(q) ||
      item.reason?.toLowerCase().includes(q) ||
      item.switch_id?.toLowerCase().includes(q)
    );
  });

  const handleCopyRule = (rule, id) => {
    navigator.clipboard.writeText(rule);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-md shadow-2xl">
      {/* Header and Filter */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-rose-500/10 text-rose-400">
            <ShieldX className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base sm:text-lg font-bold text-white flex items-center gap-2">
              Mitigation Log & Blocked Attacker IPs
              <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-rose-950 border border-rose-500/40 text-rose-300">
                {blockedIps.length} Blocked
              </span>
            </h2>
            <p className="text-xs text-slate-400">
              Live OpenFlow mitigation table pushed by the SDN Controller
            </p>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search IP, Reason, Switch..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-4 py-2 bg-slate-950/80 border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-500/80 transition-colors"
          />
        </div>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-950/90 text-slate-400 uppercase font-mono tracking-wider border-b border-slate-800">
            <tr>
              <th className="py-3 px-4">Blocked IP</th>
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4">Trigger Reason</th>
              <th className="py-3 px-4">OpenFlow Rule</th>
              <th className="py-3 px-4">Switch / Port</th>
              <th className="py-3 px-4 text-right">Packets Mitigated</th>
              <th className="py-3 px-4 text-center">Enforcement</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {filteredIps.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-slate-500 font-sans">
                  No blocked IPs match the search criteria.
                </td>
              </tr>
            ) : (
              filteredIps.map((entry, idx) => {
                const isNewest = idx === 0 && entry.ip === lastAttackIp;

                return (
                  <tr
                    key={entry.id || idx}
                    className={`transition-colors duration-300 ${
                      isNewest
                        ? 'bg-rose-950/40 animate-pulse'
                        : 'hover:bg-slate-800/40'
                    }`}
                  >
                    {/* Attacker IP */}
                    <td className="py-3.5 px-4 font-bold text-slate-100 flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
                      <span className="font-mono text-cyan-300">{entry.ip}</span>
                    </td>

                    {/* Timestamp */}
                    <td className="py-3.5 px-4 text-slate-400">
                      {entry.timestamp}
                    </td>

                    {/* Trigger Reason */}
                    <td className="py-3.5 px-4 font-sans text-slate-300 font-medium max-w-xs">
                      {entry.reason}
                    </td>

                    {/* OpenFlow Rule snippet with copy */}
                    <td className="py-3.5 px-4 text-slate-400 max-w-xs truncate">
                      <div className="flex items-center gap-1.5 group">
                        <span className="truncate text-[11px] text-slate-400 group-hover:text-slate-200">
                          {entry.flow_rule || 'OFPFC_ADD: actions=drop'}
                        </span>
                        <button
                          onClick={() => handleCopyRule(entry.flow_rule, entry.id)}
                          className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-slate-700 text-slate-300 transition-opacity"
                          title="Copy OpenFlow Rule"
                        >
                          {copiedId === entry.id ? (
                            <Check className="w-3 h-3 text-emerald-400" />
                          ) : (
                            <Copy className="w-3 h-3" />
                          )}
                        </button>
                      </div>
                    </td>

                    {/* Switch / Port */}
                    <td className="py-3.5 px-4 text-slate-400">
                      <span className="px-2 py-0.5 rounded bg-slate-800/80 border border-slate-700 text-[11px] text-slate-300">
                        {entry.switch_id || 's1-eth1'}
                      </span>
                    </td>

                    {/* Packets Mitigated */}
                    <td className="py-3.5 px-4 text-right font-bold text-amber-400">
                      {(entry.packets_mitigated || 0).toLocaleString()}
                    </td>

                    {/* Status Badge */}
                    <td className="py-3.5 px-4 text-center">
                      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold tracking-wider uppercase bg-rose-950/80 text-rose-400 border border-rose-500/60 shadow-sm shadow-rose-950/40">
                        <ShieldX className="w-3 h-3" />
                        {entry.status || 'DROPPED'}
                      </span>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex flex-wrap items-center justify-between text-xs text-slate-400">
        <span>Showing {filteredIps.length} blocked OpenFlow rule entries</span>
        <span className="font-mono text-slate-400 flex items-center gap-1">
          <Terminal className="w-3.5 h-3.5 text-cyan-400" />
          Ryu REST API: /api/blocked-ips
        </span>
      </div>
    </div>
  );
}
