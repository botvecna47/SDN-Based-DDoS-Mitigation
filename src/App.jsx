import React, { useState, useEffect, useMemo, useRef } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Activity,
  Server,
  Info,
  HelpCircle,
  Play,
  RotateCcw,
  Zap,
  Check,
  Copy,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Filter,
  Download,
  Terminal,
  Cpu,
  RefreshCw,
  Search,
  Trash2,
  Sliders,
  CheckCircle,
  AlertTriangle,
  Flame,
  ArrowUpRight,
  Database,
  Radio,
  X
} from 'lucide-react';

const ANOMALY_PPS_THRESHOLD = 8000;
const CHART_HISTORY_POINTS = 30;

const DEFAULT_BLOCKED_ENTRIES = [
  {
    id: 'rule-701',
    ip: '192.168.1.105',
    vector: 'TCP SYN Flood',
    port: '80 (HTTP)',
    switchId: 's1-eth1',
    confidence: '99.4%',
    ruleAction: 'DROP (Priority 65535, timeout 180s)',
    packetsDropped: '148,220',
    timestamp: 'Just now',
    severity: 'High'
  },
  {
    id: 'rule-702',
    ip: '10.0.0.45',
    vector: 'UDP Reflection',
    port: '53 (DNS)',
    switchId: 's3-eth2',
    confidence: '97.8%',
    ruleAction: 'DROP (Priority 65535, timeout 180s)',
    packetsDropped: '92,410',
    timestamp: '2 mins ago',
    severity: 'High'
  },
  {
    id: 'rule-703',
    ip: '172.16.2.89',
    vector: 'ICMP Echo Flood',
    port: 'ICMP (Type 8)',
    switchId: 's2-eth1',
    confidence: '95.1%',
    ruleAction: 'DROP (Priority 65535, timeout 120s)',
    packetsDropped: '34,180',
    timestamp: '5 mins ago',
    severity: 'Medium'
  }
];

export default function App() {
  // Operating Mode
  const [useLiveApi, setUseLiveApi] = useState(false);
  const [apiUrl, setApiUrl] = useState('http://localhost:5000/api/network-stats');
  const [controllerConnected, setControllerConnected] = useState(true);
  const [apiError, setApiError] = useState(null);

  // Attack & Mitigation State
  const [attackActive, setAttackActive] = useState(null); // null | 'SYN_FLOOD' | 'UDP_STORM'
  const [autoMitigationEnabled, setAutoMitigationEnabled] = useState(true);

  // UI state
  const [showHowItWorks, setShowHowItWorks] = useState(false);
  const [showApiModal, setShowApiModal] = useState(false);
  const [activeInfoTooltip, setActiveInfoTooltip] = useState(null);
  const [filterQuery, setFilterQuery] = useState('');
  const [copiedCode, setCopiedCode] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // Metrics Data State
  const [metrics, setMetrics] = useState({
    ingressPps: 1420,
    mitigatedPps: 0,
    activeFlowRules: 38,
    inferenceLatency: 3.2,
    bandwidthMbps: 14.8,
    blockedCount: 3,
    status: 'NORMAL' // 'NORMAL' | 'UNDER_ATTACK'
  });

  // Table Logs State
  const [blockedEntries, setBlockedEntries] = useState(DEFAULT_BLOCKED_ENTRIES);

  // Helper to trigger toast
  const showToast = (text, type = 'info') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Chart time series data
  const [chartData, setChartData] = useState(() => {
    const list = [];
    const now = Date.now();
    for (let i = CHART_HISTORY_POINTS; i >= 0; i--) {
      const timeLabel = new Date(now - i * 1000).toLocaleTimeString([], { hour12: false, minute: '2-digit', second: '2-digit' });
      list.push({
        time: timeLabel,
        ingress: 1200 + Math.floor(Math.random() * 300),
        mitigated: 0
      });
    }
    return list;
  });

  // Polling Effect
  useEffect(() => {
    if (!controllerConnected) return;

    const timer = setInterval(async () => {
      // Branch 1: Live Flask backend polling
      if (useLiveApi) {
        try {
          const res = await fetch(apiUrl);
          if (!res.ok) throw new Error(`Controller Offline (HTTP ${res.status})`);
          const data = await res.json();
          setApiError(null);
          
          setMetrics({
            ingressPps: data.ingress_pps || 0,
            mitigatedPps: data.mitigated_pps || 0,
            activeFlowRules: data.active_flow_rules || 24,
            inferenceLatency: data.ml_inference_latency_ms || 3.1,
            bandwidthMbps: data.bandwidth_mbps || 0,
            blockedCount: data.blocked_ips_count || blockedEntries.length,
            status: data.system_state || 'NORMAL'
          });

          setChartData(prev => [
            ...prev.slice(1),
            {
              time: new Date().toLocaleTimeString([], { hour12: false, minute: '2-digit', second: '2-digit' }),
              ingress: data.ingress_pps || 0,
              mitigated: data.mitigated_pps || 0
            }
          ]);
        } catch (err) {
          setApiError(err.message || 'Cannot connect to Flask API server at ' + apiUrl);
        }
        return;
      }

      // Branch 2: Realistic Client-Side Traffic Simulation
      setApiError(null);
      let newIngress = 1200 + Math.floor(Math.random() * 400);
      let newMitigated = 0;
      let newRules = 38;
      let sysStatus = 'NORMAL';

      if (attackActive === 'SYN_FLOOD') {
        newIngress = 18500 + Math.floor(Math.random() * 3200);
        sysStatus = 'UNDER_ATTACK';
        if (autoMitigationEnabled) {
          newMitigated = Math.floor(newIngress * 0.95);
          newRules += 6;
        }
      } else if (attackActive === 'UDP_STORM') {
        newIngress = 24200 + Math.floor(Math.random() * 4100);
        sysStatus = 'UNDER_ATTACK';
        if (autoMitigationEnabled) {
          newMitigated = Math.floor(newIngress * 0.94);
          newRules += 8;
        }
      }

      // Periodically add realistic entry if under active attack
      if (attackActive && autoMitigationEnabled && Math.random() > 0.7) {
        const randHost = Math.floor(Math.random() * 250) + 2;
        const newIp = `10.0.0.${randHost}`;
        if (!blockedEntries.some(b => b.ip === newIp)) {
          const entry = {
            id: `rule-${Math.floor(100 + Math.random() * 900)}`,
            ip: newIp,
            vector: attackActive === 'SYN_FLOOD' ? 'TCP SYN Flood' : 'UDP Amplification',
            port: attackActive === 'SYN_FLOOD' ? '80 (HTTP)' : '53 (DNS)',
            switchId: `s${Math.floor(Math.random() * 3) + 1}-eth1`,
            confidence: (98.0 + Math.random() * 1.8).toFixed(1) + '%',
            ruleAction: 'DROP (Priority 65535, timeout 180s)',
            packetsDropped: (Math.floor(Math.random() * 40000) + 10000).toLocaleString(),
            timestamp: 'Just now',
            severity: 'High'
          };
          setBlockedEntries(prev => [entry, ...prev.slice(0, 14)]);
        }
      }

      setMetrics({
        ingressPps: newIngress,
        mitigatedPps: newMitigated,
        activeFlowRules: newRules,
        inferenceLatency: (2.8 + Math.random() * 0.8).toFixed(1),
        bandwidthMbps: ((newIngress * 1100 * 8) / (1024 * 1024)).toFixed(1),
        blockedCount: blockedEntries.length,
        status: sysStatus
      });

      setChartData(prev => [
        ...prev.slice(1),
        {
          time: new Date().toLocaleTimeString([], { hour12: false, minute: '2-digit', second: '2-digit' }),
          ingress: newIngress,
          mitigated: newMitigated
        }
      ]);
    }, 1000);

    return () => clearInterval(timer);
  }, [controllerConnected, useLiveApi, apiUrl, attackActive, autoMitigationEnabled, blockedEntries]);

  // Chart coordinate and geometry generation
  const chartProps = useMemo(() => {
    const width = 900;
    const height = 250;
    const margin = { top: 20, right: 25, bottom: 30, left: 60 };
    const plotW = width - margin.left - margin.right;
    const plotH = height - margin.top - margin.bottom;

    const maxVal = Math.max(30000, ...chartData.map(d => d.ingress));

    const getX = (idx) => margin.left + (idx / (chartData.length - 1)) * plotW;
    const getY = (val) => margin.top + plotH - (val / maxVal) * plotH;

    let ingressLine = '';
    let ingressArea = '';
    let mitigatedLine = '';

    chartData.forEach((d, i) => {
      const x = getX(i);
      const yIngress = getY(d.ingress);
      const yMit = getY(d.mitigated);

      if (i === 0) {
        ingressLine += `M ${x} ${yIngress}`;
        ingressArea += `M ${x} ${margin.top + plotH} L ${x} ${yIngress}`;
        mitigatedLine += `M ${x} ${yMit}`;
      } else {
        ingressLine += ` L ${x} ${yIngress}`;
        ingressArea += ` L ${x} ${yIngress}`;
        mitigatedLine += ` L ${x} ${yMit}`;
      }
    });

    const lastX = getX(chartData.length - 1);
    const bottomY = margin.top + plotH;
    ingressArea += ` L ${lastX} ${bottomY} Z`;

    const thresholdY = getY(ANOMALY_PPS_THRESHOLD);

    return {
      width,
      height,
      margin,
      plotW,
      plotH,
      maxVal,
      ingressLine,
      ingressArea,
      mitigatedLine,
      thresholdY,
      getX,
      getY
    };
  }, [chartData]);

  // Search filtering
  const filteredList = useMemo(() => {
    if (!filterQuery) return blockedEntries;
    const q = filterQuery.toLowerCase();
    return blockedEntries.filter(
      item => item.ip.toLowerCase().includes(q) || item.vector.toLowerCase().includes(q) || item.switchId.toLowerCase().includes(q)
    );
  }, [blockedEntries, filterQuery]);

  const handleUnblock = (id) => {
    const entry = blockedEntries.find(e => e.id === id);
    setBlockedEntries(prev => prev.filter(e => e.id !== id));
    showToast(`Removed OpenFlow DROP rule for ${entry ? entry.ip : id}`, 'info');
  };

  const handleExportCsv = () => {
    const headers = 'RuleID,SourceIP,AttackVector,TargetPort,Switch,Confidence,Action,PacketsDropped,Timestamp\n';
    const rows = blockedEntries.map(e => `${e.id},${e.ip},"${e.vector}",${e.port},${e.switchId},${e.confidence},"${e.ruleAction}",${e.packetsDropped},${e.timestamp}`);
    const blob = new Blob([headers + rows.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sdn-firewall-rules-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Exported active OpenFlow mitigation table to CSV', 'success');
  };

  const sampleFlaskCode = `# app.py - Flask Bridge for Mininet & Ryu Controller
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin requests for the React dashboard

@app.route('/api/network-stats', methods=['GET'])
def get_network_stats():
    # In production, query Ryu REST API (e.g., http://localhost:8080/stats/flow/1)
    return jsonify({
        "system_state": "UNDER_ATTACK",  # "NORMAL" or "UNDER_ATTACK"
        "ingress_pps": 18450,
        "mitigated_pps": 17500,
        "bandwidth_mbps": 162.3,
        "active_flow_rules": 44,
        "blocked_ips_count": 3,
        "ml_inference_latency_ms": 3.12,
        "packet_drop_rate_pct": 94.8
    })

@app.route('/api/blocked-ips', methods=['GET'])
def get_blocked_ips():
    return jsonify([
        {
            "id": "rule-701",
            "ip": "10.0.0.1",
            "vector": "TCP SYN Flood",
            "port": "80 (HTTP)",
            "switchId": "s1-eth1",
            "confidence": "99.4%",
            "ruleAction": "DROP (Priority 65535)",
            "packetsDropped": "148,220",
            "timestamp": "Just now",
            "severity": "High"
        }
    ])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)`;

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 font-sans selection:bg-blue-100 selection:text-blue-900 flex flex-col">
      
      {/* Top Application Bar */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-30 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            
            {/* Title & Brand */}
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-slate-900 flex items-center justify-center text-white shadow-sm">
                <ShieldCheck className="w-5 h-5 text-emerald-400" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-base font-semibold text-slate-900 tracking-tight">SDN Defense Console</h1>
                  <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded-md font-mono border border-slate-200">
                    OpenFlow 1.3
                  </span>
                </div>
                <p className="text-xs text-slate-500">Mininet Fat-Tree Network • Ryu Controller • Random Forest Classifier</p>
              </div>
            </div>

            {/* Top Toolbar Actions */}
            <div className="flex items-center space-x-3">
              
              {/* Educational 'How it works' trigger button */}
              <button
                onClick={() => setShowHowItWorks(!showHowItWorks)}
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                  showHowItWorks 
                    ? 'bg-blue-50 border-blue-200 text-blue-700' 
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                <HelpCircle className="w-4 h-4 text-blue-600" />
                <span>How This Works</span>
                {showHowItWorks ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>

              {/* Mode Selector */}
              <div className="flex items-center bg-slate-100 p-0.5 rounded-lg border border-slate-200 text-xs">
                <button
                  onClick={() => {
                    setUseLiveApi(false);
                    showToast('Switched to Demo Simulation Mode', 'info');
                  }}
                  className={`px-3 py-1 rounded-md font-medium transition-all ${
                    !useLiveApi ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Demo Mode
                </button>
                <button
                  onClick={() => {
                    setUseLiveApi(true);
                    showToast('Connecting to Live Flask API at ' + apiUrl, 'info');
                  }}
                  className={`px-3 py-1 rounded-md font-medium transition-all ${
                    useLiveApi ? 'bg-emerald-600 text-white shadow-xs' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Live Flask API
                </button>
              </div>

              {/* API Contract Drawer Trigger */}
              <button
                onClick={() => setShowApiModal(true)}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-900 text-white hover:bg-slate-800 transition-colors shadow-xs"
              >
                <Terminal className="w-3.5 h-3.5 text-slate-300" />
                <span>Flask Schema</span>
              </button>

            </div>
          </div>
        </div>

        {/* Interactive Demo Simulation Ribbon */}
        <div className="bg-slate-100/90 border-t border-slate-200 px-4 sm:px-6 lg:px-8 py-2.5">
          <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2 text-slate-600 font-medium">
              <Sliders className="w-3.5 h-3.5 text-slate-500" />
              <span>Interactive Demonstration Controls:</span>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                onClick={() => {
                  setAttackActive(null);
                  showToast('Baseline normal network traffic restored', 'success');
                }}
                className={`px-2.5 py-1 rounded-md font-medium border transition-all ${
                  attackActive === null
                    ? 'bg-emerald-50 border-emerald-300 text-emerald-800 shadow-xs'
                    : 'bg-white border-slate-200 text-slate-600 hover:bg-slate-50'
                }`}
              >
                Normal Traffic Baseline
              </button>

              <button
                onClick={() => {
                  setAttackActive('SYN_FLOOD');
                  showToast('Injected simulated hping3 TCP SYN Flood on Port 80', 'danger');
                }}
                className={`px-2.5 py-1 rounded-md font-medium border flex items-center gap-1.5 transition-all ${
                  attackActive === 'SYN_FLOOD'
                    ? 'bg-rose-600 border-rose-700 text-white shadow-xs font-semibold'
                    : 'bg-white border-rose-200 text-rose-700 hover:bg-rose-50'
                }`}
              >
                <Flame className="w-3.5 h-3.5" />
                Trigger hping3 SYN Flood
              </button>

              <button
                onClick={() => {
                  setAttackActive('UDP_STORM');
                  showToast('Injected simulated high-volume UDP Amplification Storm', 'warning');
                }}
                className={`px-2.5 py-1 rounded-md font-medium border flex items-center gap-1.5 transition-all ${
                  attackActive === 'UDP_STORM'
                    ? 'bg-amber-600 border-amber-700 text-white shadow-xs font-semibold'
                    : 'bg-white border-amber-200 text-amber-800 hover:bg-amber-50'
                }`}
              >
                <Zap className="w-3.5 h-3.5" />
                Trigger UDP Storm
              </button>

              <div className="h-4 w-px bg-slate-300 mx-1"></div>

              <button
                onClick={() => {
                  setAutoMitigationEnabled(!autoMitigationEnabled);
                  showToast(
                    !autoMitigationEnabled 
                      ? 'Auto-Mitigation enabled: Controller writing OpenFlow drop rules' 
                      : 'Auto-Mitigation disabled: Ingress drops bypassed', 
                    'info'
                  );
                }}
                className={`px-2.5 py-1 rounded-md font-medium border transition-all ${
                  autoMitigationEnabled
                    ? 'bg-blue-50 border-blue-300 text-blue-800 font-medium'
                    : 'bg-slate-200 border-slate-300 text-slate-500 line-through'
                }`}
                title="Toggle automatic OpenFlow FlowMod drop injection"
              >
                Auto-Mitigation: {autoMitigationEnabled ? 'Active' : 'Bypassed'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Live API Error Notice if polling fails */}
      {useLiveApi && apiError && (
        <div className="bg-amber-50 border-b border-amber-200 px-4 py-2.5 text-xs text-amber-800 flex items-center justify-between">
          <div className="max-w-7xl mx-auto w-full flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0" />
              <span>
                <strong>Flask API Notice:</strong> {apiError}. Ensure <code className="bg-amber-100 px-1 rounded">python app.py</code> is running on port 5000.
              </span>
            </div>
            <button
              onClick={() => setShowApiModal(true)}
              className="text-amber-900 underline font-medium hover:text-black shrink-0 ml-4"
            >
              View API Code
            </button>
          </div>
        </div>
      )}

      {/* Main Content Viewport */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6 flex-1 w-full">
        
        {/* Educational 'How This Works' Drawer */}
        {showHowItWorks && (
          <div className="bg-white border border-blue-200 rounded-2xl p-5 shadow-xs transition-all">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-sm font-semibold text-slate-900 flex items-center gap-2">
                  <Info className="w-4 h-4 text-blue-600" />
                  How this SDN Defense Architecture Works
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Understand how your Mininet virtual hosts, OpenFlow switches, ML model, and Ryu controller work together:
                </p>
              </div>
              <button 
                onClick={() => setShowHowItWorks(false)}
                className="text-slate-400 hover:text-slate-600 text-xs font-medium"
              >
                Dismiss
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
              {/* Step 1 */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                <div className="w-6 h-6 rounded-full bg-blue-100 text-blue-700 font-bold text-xs flex items-center justify-center mb-2">1</div>
                <h3 className="text-xs font-semibold text-slate-900">Telemetry Extraction</h3>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  OpenFlow switches (OVS in Mininet) stream statistical counters (packet count, byte count, duration) via OpenFlow 1.3 to the Ryu Controller every 1 second.
                </p>
              </div>

              {/* Step 2 */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                <div className="w-6 h-6 rounded-full bg-indigo-100 text-indigo-700 font-bold text-xs flex items-center justify-center mb-2">2</div>
                <h3 className="text-xs font-semibold text-slate-900">Machine Learning Detection</h3>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  The Ryu application feeds rolling flow statistical vectors into a trained Random Forest classifier. If packets exceed threshold ratios, an anomaly is flagged.
                </p>
              </div>

              {/* Step 3 */}
              <div className="bg-slate-50 border border-slate-200 rounded-xl p-3.5">
                <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 font-bold text-xs flex items-center justify-center mb-2">3</div>
                <h3 className="text-xs font-semibold text-slate-900">OpenFlow FlowMod Drop</h3>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                  Ryu immediately issues an <code className="text-slate-800 bg-white px-1 py-0.5 rounded border border-slate-200 font-mono text-[10px]">OFPFC_ADD</code> message with high priority (65535) instructing switches to discard hostile packets at the port boundary.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* System Health + KPI Metrics */}
        <section className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          
          {/* Main System Health Widget */}
          <div className="lg:col-span-4 bg-white border border-slate-200 rounded-2xl p-5 shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-slate-500 uppercase tracking-wider">System Defense Status</span>
                <span className="relative flex h-2.5 w-2.5">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                    metrics.status === 'UNDER_ATTACK' ? 'bg-rose-400' : 'bg-emerald-400'
                  }`}></span>
                  <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                    metrics.status === 'UNDER_ATTACK' ? 'bg-rose-500' : 'bg-emerald-500'
                  }`}></span>
                </span>
              </div>

              <div className="mt-3 flex items-center gap-3">
                <div className={`p-2.5 rounded-xl border ${
                  metrics.status === 'UNDER_ATTACK'
                    ? 'bg-rose-50 border-rose-200 text-rose-600'
                    : 'bg-emerald-50 border-emerald-200 text-emerald-600'
                }`}>
                  {metrics.status === 'UNDER_ATTACK' ? (
                    <ShieldAlert className="w-6 h-6" />
                  ) : (
                    <ShieldCheck className="w-6 h-6" />
                  )}
                </div>
                <div>
                  <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                    {metrics.status === 'UNDER_ATTACK' ? 'Under DDoS Attack' : 'Normal Operation'}
                  </h2>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {metrics.status === 'UNDER_ATTACK' 
                      ? 'Automated OpenFlow rules currently suppressing hostile flow' 
                      : 'Network traffic within standard baseline tolerances'}
                  </p>
                </div>
              </div>
            </div>

            {/* Diagnostic Context Note */}
            <div className="mt-5 pt-4 border-t border-slate-100 text-xs text-slate-600">
              <span className="font-medium text-slate-800">Operational Summary:</span>{' '}
              {metrics.status === 'UNDER_ATTACK' ? (
                <span className="text-rose-700 font-medium">
                  High-frequency volumetric packet surge detected. {metrics.mitigatedPps.toLocaleString()} pps intercepted before hitting server hosts.
                </span>
              ) : (
                <span>
                  All switches reporting normal ping &amp; iperf load. ML classifier variance score is 0.02 (healthy).
                </span>
              )}
            </div>
          </div>

          {/* KPI Data Grid */}
          <div className="lg:col-span-8 grid grid-cols-2 sm:grid-cols-4 gap-4">
            
            {/* KPI 1: Ingress PPS */}
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="font-medium">Total Ingress</span>
                  <button 
                    onClick={() => setActiveInfoTooltip(activeInfoTooltip === 'ingress' ? null : 'ingress')}
                    className="text-slate-400 hover:text-slate-600"
                    title="Explain this metric"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="mt-2 text-2xl font-bold text-slate-900 tracking-tight">
                  {metrics.ingressPps.toLocaleString()}
                  <span className="text-xs font-normal text-slate-500 ml-1">pps</span>
                </div>
              </div>
              <div className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100 flex items-center justify-between">
                <span>Anomaly Cap</span>
                <span className="font-mono font-medium text-slate-700">8.0k pps</span>
              </div>
            </div>

            {/* KPI 2: Mitigated Packets */}
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="font-medium">Dropped Traffic</span>
                  <button 
                    onClick={() => setActiveInfoTooltip(activeInfoTooltip === 'mitigated' ? null : 'mitigated')}
                    className="text-slate-400 hover:text-slate-600"
                    title="Explain this metric"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="mt-2 text-2xl font-bold text-rose-600 tracking-tight">
                  {metrics.mitigatedPps.toLocaleString()}
                  <span className="text-xs font-normal text-slate-500 ml-1">pps</span>
                </div>
              </div>
              <div className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100 flex items-center justify-between">
                <span>Filter Rate</span>
                <span className="font-medium text-emerald-600">
                  {metrics.ingressPps > 0 ? ((metrics.mitigatedPps / metrics.ingressPps) * 100).toFixed(1) : 0}%
                </span>
              </div>
            </div>

            {/* KPI 3: Flow Table Entries */}
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="font-medium">Active Flow Rules</span>
                  <button 
                    onClick={() => setActiveInfoTooltip(activeInfoTooltip === 'flows' ? null : 'flows')}
                    className="text-slate-400 hover:text-slate-600"
                    title="Explain this metric"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="mt-2 text-2xl font-bold text-slate-900 tracking-tight">
                  {metrics.activeFlowRules}
                  <span className="text-xs font-normal text-slate-500 ml-1">rules</span>
                </div>
              </div>
              <div className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100 flex items-center justify-between">
                <span>Protocol</span>
                <span className="text-slate-700">OpenFlow 1.3</span>
              </div>
            </div>

            {/* KPI 4: ML Inference Latency */}
            <div className="bg-white border border-slate-200 rounded-2xl p-4 shadow-xs flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between text-xs text-slate-500">
                  <span className="font-medium">ML Decision Delay</span>
                  <button 
                    onClick={() => setActiveInfoTooltip(activeInfoTooltip === 'latency' ? null : 'latency')}
                    className="text-slate-400 hover:text-slate-600"
                    title="Explain this metric"
                  >
                    <HelpCircle className="w-3.5 h-3.5" />
                  </button>
                </div>
                <div className="mt-2 text-2xl font-bold text-slate-900 tracking-tight">
                  {metrics.inferenceLatency}
                  <span className="text-xs font-normal text-slate-500 ml-1">ms</span>
                </div>
              </div>
              <div className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100 flex items-center justify-between">
                <span>Model Engine</span>
                <span className="text-slate-700">Random Forest</span>
              </div>
            </div>

          </div>
        </section>

        {/* Explainability Helper Banners */}
        {activeInfoTooltip && (
          <div className="bg-slate-100 border border-slate-300 rounded-xl p-3.5 text-xs text-slate-700 flex items-start justify-between">
            <div>
              {activeInfoTooltip === 'ingress' && (
                <p>
                  <strong>Total Ingress (pps):</strong> The raw number of network packets reaching the OpenFlow switch ports every second. In normal Mininet operations, legitimate ping/iperf traffic sits around 1,000 to 2,000 pps. An <code>hping3</code> attack triggers spikes over 15,000 pps.
                </p>
              )}
              {activeInfoTooltip === 'mitigated' && (
                <p>
                  <strong>Dropped Traffic (pps):</strong> The number of malicious packets actively thrown away per second by the switches before they reach victim hosts. This shows your mitigation rules are functioning.
                </p>
              )}
              {activeInfoTooltip === 'flows' && (
                <p>
                  <strong>Active Flow Rules:</strong> The count of forwarding and dropping instructions stored directly inside the switch's Open vSwitch flow table. When an attack is detected, the controller writes temporary high-priority drop rules.
                </p>
              )}
              {activeInfoTooltip === 'latency' && (
                <p>
                  <strong>ML Decision Delay:</strong> The time required for the scikit-learn Random Forest model to ingest flow feature vectors (packet rate, byte entropy, duration) and output a classification verdict.
                </p>
              )}
            </div>
            <button 
              onClick={() => setActiveInfoTooltip(null)}
              className="text-slate-500 hover:text-slate-800 font-bold ml-4"
            >
              ✕
            </button>
          </div>
        )}

        {/* The Global Traffic Monitor Chart Section */}
        <section className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-xs space-y-4">
          
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-slate-100 gap-3">
            <div>
              <div className="flex items-center gap-2">
                <Activity className="w-5 h-5 text-blue-600" />
                <h3 className="text-sm font-semibold text-slate-900">The Global Traffic Monitor</h3>
                <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                  30s Rolling Window
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Real-time ingress rate plotted against controller-instructed drops
              </p>
            </div>

            {/* Clean Legend */}
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-blue-600 inline-block"></span>
                <span className="text-slate-700">Ingress Packets (pps)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-rose-600 inline-block"></span>
                <span className="text-slate-700">Mitigated Dropped (pps)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-amber-500 inline-block border-t border-dashed border-amber-500"></span>
                <span className="text-amber-700 font-medium">DDoS Detection Threshold (8k)</span>
              </div>
            </div>
          </div>

          {/* Traffic Monitor SVG Chart */}
          <div className="w-full overflow-x-auto">
            <div className="min-w-[650px]">
              <svg 
                viewBox={`0 0 ${chartProps.width} ${chartProps.height}`} 
                className="w-full h-64 overflow-visible"
              >
                <defs>
                  <linearGradient id="humanIngressGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2563eb" stopOpacity="0.12" />
                    <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
                  </linearGradient>
                </defs>

                {/* Horizontal Scale Lines */}
                {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
                  const y = chartProps.margin.top + chartProps.plotH * (1 - ratio);
                  const labelVal = Math.round(chartProps.maxVal * ratio);
                  return (
                    <g key={i}>
                      <line 
                        x1={chartProps.margin.left} 
                        y1={y} 
                        x2={chartProps.width - chartProps.margin.right} 
                        y2={y} 
                        stroke="#f1f5f9" 
                        strokeWidth="1"
                      />
                      <text 
                        x={chartProps.margin.left - 10} 
                        y={y + 3.5} 
                        fill="#94a3b8" 
                        fontSize="10" 
                        fontFamily="monospace"
                        textAnchor="end"
                      >
                        {labelVal >= 1000 ? `${(labelVal / 1000).toFixed(0)}k` : labelVal}
                      </text>
                    </g>
                  );
                })}

                {/* DDoS Detection Threshold Line */}
                <line 
                  x1={chartProps.margin.left} 
                  y1={chartProps.thresholdY} 
                  x2={chartProps.width - chartProps.margin.right} 
                  y2={chartProps.thresholdY} 
                  stroke="#f59e0b" 
                  strokeWidth="1.5" 
                  strokeDasharray="4 4"
                />
                <text 
                  x={chartProps.width - chartProps.margin.right - 8} 
                  y={chartProps.thresholdY - 5} 
                  fill="#d97706" 
                  fontSize="10" 
                  fontFamily="sans-serif"
                  fontWeight="600"
                  textAnchor="end"
                >
                  DDoS Detection Threshold (8,000 pps)
                </text>

                {/* Ingress traffic filled area */}
                <path d={chartProps.ingressArea} fill="url(#humanIngressGrad)" />

                {/* Ingress traffic line */}
                <path 
                  d={chartProps.ingressLine} 
                  fill="none" 
                  stroke="#2563eb" 
                  strokeWidth="2" 
                  strokeLinecap="round" 
                />

                {/* Mitigated traffic dashed line */}
                {metrics.mitigatedPps > 0 && (
                  <path 
                    d={chartProps.mitigatedLine} 
                    fill="none" 
                    stroke="#e11d48" 
                    strokeWidth="2" 
                    strokeDasharray="3 3"
                    strokeLinecap="round" 
                  />
                )}

                {/* Active Pulse Dot on Latest Reading */}
                {chartData.length > 0 && (() => {
                  const lastIdx = chartData.length - 1;
                  const lx = chartProps.getX(lastIdx);
                  const ly = chartProps.getY(chartData[lastIdx].ingress);
                  return (
                    <circle 
                      cx={lx} 
                      cy={ly} 
                      r="4" 
                      fill={metrics.status === 'UNDER_ATTACK' ? '#e11d48' : '#2563eb'} 
                      stroke="#ffffff" 
                      strokeWidth="2" 
                    />
                  );
                })()}

                {/* X-axis time marks */}
                {chartData.filter((_, idx) => idx % 6 === 0).map((pt, idx) => {
                  const realIdx = idx * 6;
                  const x = chartProps.getX(realIdx);
                  return (
                    <text 
                      key={realIdx} 
                      x={x} 
                      y={chartProps.height - 10} 
                      fill="#94a3b8" 
                      fontSize="10" 
                      fontFamily="monospace"
                      textAnchor="middle"
                    >
                      {pt.time}
                    </text>
                  );
                })}
              </svg>
            </div>
          </div>

          {/* Educational Note about Live Demonstration */}
          <div className="bg-slate-50 border border-slate-200 rounded-xl p-3 flex items-center justify-between text-xs text-slate-600">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-800">What to look for during testing:</span>
              <span>
                When you execute <code>hping3 -S --flood -V 10.0.0.4</code> in Mininet, you will see the blue line spike past 8,000 pps. Within 1 second, the red dashed line catches up to represent packets being dropped at the switch.
              </span>
            </div>
          </div>
        </section>

        {/* The Mitigation Log Table Section */}
        <section className="bg-white border border-slate-200 rounded-2xl p-5 sm:p-6 shadow-xs space-y-4">
          
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 pb-3 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-2">
                <Server className="w-5 h-5 text-indigo-600" />
                <h3 className="text-sm font-semibold text-slate-900">The Mitigation Log</h3>
                <span className="text-xs bg-slate-100 text-slate-600 px-2 py-0.5 rounded font-mono">
                  Active OpenFlow DROP Table
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Hostile endpoints quarantined by Ryu controller rule installations (Priority 65535)
              </p>
            </div>

            {/* Search and Table Actions */}
            <div className="flex flex-wrap items-center gap-2">
              <div className="relative">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
                <input 
                  type="text" 
                  value={filterQuery}
                  onChange={(e) => setFilterQuery(e.target.value)}
                  placeholder="Filter by IP or vector..." 
                  className="pl-8 pr-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-blue-500 text-slate-800 placeholder-slate-400 w-48"
                />
              </div>

              <button
                onClick={handleExportCsv}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-700 transition-colors"
              >
                <Download className="w-3.5 h-3.5 text-slate-500" />
                Export CSV
              </button>

              <button
                onClick={() => {
                  setBlockedEntries([]);
                  showToast('Flushed all active flow table entries', 'info');
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white border border-slate-200 hover:bg-slate-50 rounded-lg text-slate-500 hover:text-slate-800 transition-colors"
                title="Flush flow tables in memory"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Flush
              </button>
            </div>
          </div>

          {/* Clean Enterprise Data Table */}
          <div className="overflow-x-auto border border-slate-200 rounded-xl">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 uppercase tracking-wider font-semibold text-[11px] border-b border-slate-200">
                <tr>
                  <th className="py-3 px-3.5">Rule ID</th>
                  <th className="py-3 px-3.5">Source Host IP</th>
                  <th className="py-3 px-3.5">Attack Signature</th>
                  <th className="py-3 px-3.5">Switch Port</th>
                  <th className="py-3 px-3.5">ML Confidence</th>
                  <th className="py-3 px-3.5">Packets Intercepted</th>
                  <th className="py-3 px-3.5">OpenFlow Action</th>
                  <th className="py-3 px-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {filteredList.length === 0 ? (
                  <tr>
                    <td colSpan="8" className="py-8 text-center text-slate-400">
                      No blocked flow rules currently recorded. Everything clean.
                    </td>
                  </tr>
                ) : (
                  filteredList.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-3 px-3.5 font-mono text-slate-500">{entry.id}</td>
                      <td className="py-3 px-3.5 font-mono font-semibold text-slate-900">{entry.ip}</td>
                      <td className="py-3 px-3.5">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium ${
                          entry.vector.includes('TCP')
                            ? 'bg-rose-50 text-rose-700 border border-rose-200'
                            : 'bg-amber-50 text-amber-800 border border-amber-200'
                        }`}>
                          {entry.vector}
                        </span>
                      </td>
                      <td className="py-3 px-3.5 text-slate-600 font-mono">{entry.switchId}</td>
                      <td className="py-3 px-3.5 text-emerald-600 font-medium">{entry.confidence}</td>
                      <td className="py-3 px-3.5 text-slate-700 font-mono">{entry.packetsDropped}</td>
                      <td className="py-3 px-3.5 font-mono text-[11px] text-slate-600">
                        <code>{entry.ruleAction}</code>
                      </td>
                      <td className="py-3 px-3.5 text-right">
                        <button
                          onClick={() => handleUnblock(entry.id)}
                          className="text-xs text-slate-500 hover:text-rose-600 font-medium px-2 py-1 rounded hover:bg-rose-50 transition-colors"
                          title="Withdraw OpenFlow DROP rule"
                        >
                          Unblock
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

        </section>

      </main>

      {/* Flask Schema Modal */}
      {showApiModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-3xl shadow-xl overflow-hidden flex flex-col max-h-[90vh]">
            
            <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2">
                <Terminal className="w-4 h-4 text-blue-600" />
                <h3 className="font-semibold text-slate-900 text-sm">Flask REST API Schema &amp; Code</h3>
              </div>
              <button 
                onClick={() => setShowApiModal(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-semibold"
              >
                ✕
              </button>
            </div>

            <div className="p-5 overflow-y-auto space-y-4 text-xs">
              <p className="text-slate-600">
                Give this exact blueprint to the teammate managing Flask and Mininet. They can run this snippet right alongside the Ryu controller:
              </p>

              {/* Code Box */}
              <div className="relative">
                <button
                  onClick={() => {
                    navigator.clipboard.writeText(sampleFlaskCode);
                    setCopiedCode(true);
                    setTimeout(() => setCopiedCode(false), 2000);
                  }}
                  className="absolute right-3 top-3 px-2 py-1 rounded bg-slate-800 text-slate-200 hover:bg-slate-700 text-[11px] flex items-center gap-1 shadow-xs cursor-pointer"
                >
                  {copiedCode ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  {copiedCode ? 'Copied!' : 'Copy Code'}
                </button>
                <pre className="bg-slate-900 text-slate-200 p-4 rounded-xl font-mono text-[11px] overflow-x-auto leading-relaxed">
                  {sampleFlaskCode}
                </pre>
              </div>

              {/* Custom API URL Connect Bar */}
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-200 space-y-2">
                <span className="font-semibold text-slate-800">Target Flask Bridge URL:</span>
                <div className="flex gap-2">
                  <input 
                    type="text" 
                    value={apiUrl}
                    onChange={(e) => setApiUrl(e.target.value)}
                    className="flex-1 bg-white border border-slate-300 rounded-lg px-3 py-1.5 font-mono text-slate-800 focus:outline-none focus:border-blue-500"
                    placeholder="http://localhost:5000/api/network-stats"
                  />
                  <button
                    onClick={() => {
                      setUseLiveApi(true);
                      setShowApiModal(false);
                      showToast(`Attempting connection to ${apiUrl}`, 'info');
                    }}
                    className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium cursor-pointer"
                  >
                    Connect
                  </button>
                </div>
              </div>
            </div>

            <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 flex justify-end">
              <button 
                onClick={() => setShowApiModal(false)}
                className="px-4 py-1.5 text-xs font-medium rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 cursor-pointer"
              >
                Close
              </button>
            </div>

          </div>
        </div>
      )}

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 animate-bounce duration-300">
          <div className={`px-4 py-2.5 rounded-xl shadow-lg border text-xs font-medium flex items-center gap-2 ${
            toastMessage.type === 'danger'
              ? 'bg-rose-900 text-white border-rose-700'
              : toastMessage.type === 'warning'
              ? 'bg-amber-900 text-white border-amber-700'
              : toastMessage.type === 'success'
              ? 'bg-emerald-900 text-white border-emerald-700'
              : 'bg-slate-900 text-white border-slate-700'
          }`}>
            {toastMessage.type === 'danger' ? (
              <AlertTriangle className="w-4 h-4 text-rose-400" />
            ) : toastMessage.type === 'success' ? (
              <CheckCircle className="w-4 h-4 text-emerald-400" />
            ) : (
              <Info className="w-4 h-4 text-blue-400" />
            )}
            <span>{toastMessage.text}</span>
          </div>
        </div>
      )}

      {/* Footer */}
      <footer className="bg-white border-t border-slate-200 px-4 py-3 text-center text-xs text-slate-500">
        SDN-Based DDoS Detection &amp; Mitigation System • Developed for Mininet + Ryu OpenFlow Controller Evaluation
      </footer>

    </div>
  );
}
