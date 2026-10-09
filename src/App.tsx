import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { demoSnapshot, endpoint, fetchSnapshot } from './data'
import type { Snapshot, Threat } from './data'

type IconName = 'shield' | 'activity' | 'zap' | 'clock' | 'filter' | 'search' | 'download' | 'refresh' | 'alert' | 'check' | 'pause' | 'play' | 'close' | 'menu'

function Icon({ name, size = 18, className = '' }: { name: IconName; size?: number; className?: string }) {
  const paths: Record<IconName, ReactNode> = {
    shield: <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />,
    activity: <path d="M22 12h-4l-3 9L9 3l-3 9H2" />,
    zap: <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z" />,
    clock: <><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></>,
    filter: <path d="M22 3H2l8 9.46V19l4 2v-8.54L22 3z" />,
    search: <><circle cx="11" cy="11" r="8" /><path d="m21 21-4.3-4.3" /></>,
    download: <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4M7 10l5 5 5-5M12 15V3" />,
    refresh: <path d="M3 12a9 9 0 0 1 15-6.7L21 8M21 3v5h-5M21 12a9 9 0 0 1-15 6.7L3 16M3 21v-5h5" />,
    alert: <><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>,
    check: <polyline points="20 6 9 17 4 12" />,
    pause: <><rect x="6" y="4" width="4" height="16" rx="1" /><rect x="14" y="4" width="4" height="16" rx="1" /></>,
    play: <polygon points="5 3 19 12 5 21 5 3" />,
    close: <path d="M18 6 6 18M6 6l12 12" />,
    menu: <><line x1="4" y1="12" x2="20" y2="12" /><line x1="4" y1="6" x2="20" y2="6" /><line x1="4" y1="18" x2="20" y2="18" /></>,
  }

  return (
    <svg 
      className={className} 
      width={size} 
      height={size} 
      viewBox="0 0 24 24" 
      fill="none" 
      stroke="currentColor" 
      strokeWidth="2" 
      strokeLinecap="round" 
      strokeLinejoin="round" 
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  )
}

const timelineLabels = ['-48s', '-40s', '-32s', '-24s', '-16s', '-8s', 'Live (Now)']

function smoothPath(values: number[], ceiling: number) {
  if (values.length < 2) return ''
  const points = values.map((value, i) => ({
    x: 45 + i * (935 / (values.length - 1)),
    y: 220 - Math.min(1, value / ceiling) * 190
  }))
  return points.reduce((path, point, i) => {
    if (!i) return `M ${point.x} ${point.y}`
    const previous = points[i - 1]
    const middle = (previous.x + point.x) / 2
    return `${path} C ${middle} ${previous.y}, ${middle} ${point.y}, ${point.x} ${point.y}`
  }, '')
}

function TrafficChart({ traffic, tick }: { traffic: Snapshot['traffic']; tick: number }) {
  const [hover, setHover] = useState<number | null>(null)
  const ceiling = Math.max(12, traffic.threshold * 1.35, ...traffic.ingress, ...traffic.dropped)
  const ingress = traffic.ingress.map((n, i) => Math.max(0, n + (tick ? Math.sin(i * 0.7 + tick) * 0.08 : 0)))
  const dropped = traffic.dropped.map((n, i) => Math.max(0, n + (tick ? Math.sin(i * 0.8 + tick) * 0.08 : 0)))
  const ingressPath = smoothPath(ingress, ceiling)
  const droppedPath = smoothPath(dropped, ceiling)
  const activeHover = hover === null ? null : Math.min(hover, ingress.length - 1)
  const x = activeHover === null ? 0 : 45 + activeHover * (935 / (ingress.length - 1))
  const y = activeHover === null ? 0 : 220 - Math.min(1, ingress[activeHover] / ceiling) * 190

  return (
    <div className="relative mt-6 select-none">
      <div 
        className="relative h-[290px] w-full" 
        onMouseMove={event => {
          const bounds = event.currentTarget.getBoundingClientRect()
          setHover(Math.max(0, Math.min(ingress.length - 1, Math.round(((event.clientX - bounds.left) / bounds.width - 0.045) / 0.935 * (ingress.length - 1)))))
        }} 
        onMouseLeave={() => setHover(null)}
      >
        <svg viewBox="0 0 1000 250" preserveAspectRatio="none" className="h-full w-full overflow-visible" role="img" aria-label="Traffic history chart">
          <defs>
            <linearGradient id="ingressFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#2563eb" stopOpacity="0.14" />
              <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="droppedFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#0d9488" stopOpacity="0.14" />
              <stop offset="100%" stopColor="#0d9488" stopOpacity="0.0" />
            </linearGradient>
          </defs>
          
          {[0, 0.25, 0.5, 0.75, 1].map(fraction => (
            <g key={fraction}>
              <line x1="45" x2="980" y1={220 - fraction * 190} y2={220 - fraction * 190} stroke="#f1f5f9" strokeWidth="1.2" />
              <text x="0" y={224 - fraction * 190} fill="#94a3b8" fontSize="12" className="mono">{Math.round(fraction * ceiling)}k</text>
            </g>
          ))}

          {/* Anomaly Limit Line */}
          <line 
            x1="45" 
            x2="980" 
            y1={220 - traffic.threshold / ceiling * 190} 
            y2={220 - traffic.threshold / ceiling * 190} 
            stroke="#ef4444" 
            strokeWidth="1.5" 
            strokeDasharray="5 5" 
          />

          <path d={`${droppedPath} L 980 220 L 45 220 Z`} fill="url(#droppedFill)" />
          <path d={`${ingressPath} L 980 220 L 45 220 Z`} fill="url(#ingressFill)" />
          <path d={droppedPath} fill="none" stroke="#0d9488" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
          <path d={ingressPath} fill="none" stroke="#2563eb" strokeWidth="3" vectorEffect="non-scaling-stroke" />

          {activeHover !== null && (
            <>
              <line x1={x} x2={x} y1="20" y2="220" stroke="#cbd5e1" strokeDasharray="3 3" />
              <circle cx={x} cy={y} r="5" fill="#2563eb" stroke="#ffffff" strokeWidth="2.5" />
            </>
          )}
        </svg>

        {activeHover !== null && (
          <div 
            className="pointer-events-none absolute rounded-xl border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white shadow-xl"
            style={{ left: `${Math.min(84, Math.max(10, x / 10))}%`, top: `${Math.max(8, y / 2.5 - 20)}%`, transform: 'translate(-50%, -100%)' }}
          >
            <div className="text-xs text-slate-400">{48 - activeHover}s ago</div>
            <div className="font-semibold mono mt-0.5">{Math.round((ingress[activeHover] || 0) * 1000).toLocaleString()} incoming / sec</div>
            <div className="font-semibold text-teal-400 mono">{Math.round((dropped[activeHover] || 0) * 1000).toLocaleString()} blocked / sec</div>
          </div>
        )}
      </div>

      <div className="ml-[4.5%] flex justify-between pt-3 text-xs sm:text-sm font-medium text-slate-500 mono">
        {timelineLabels.map(label => <span key={label}>{label}</span>)}
      </div>
    </div>
  )
}

function MetricCard({ label, value, unit, detail }: { label: string; value: string; unit?: string; detail: string }) {
  return (
    <div className="panel-card p-6 sm:p-7 flex flex-col justify-between">
      <div className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500">{label}</div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 mono">{value}</span>
        {unit && <span className="text-sm font-semibold text-slate-500">{unit}</span>}
      </div>
      <div className="mt-3 text-xs sm:text-sm text-slate-500 leading-normal">{detail}</div>
    </div>
  )
}

function exportCsv(rows: Threat[]) {
  const fields = ['Source IP', 'Host node', 'Target port', 'Protocol', 'Reason', 'Confidence', 'Status']
  const csv = [fields, ...rows.map(row => [row.ip, row.country, row.port, row.protocol, row.reason, `${row.score}%`, 'Blocked'])].map(row => row.map(value => `"${String(value).replace(/"/g, '""')}"`).join(',')).join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = 'blocked-traffic-log.csv'
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

export default function App() {
  const [source, setSource] = useState<'demo' | 'live'>(endpoint ? 'live' : 'demo')
  const [scenario, setScenario] = useState<'normal' | 'attack' | 'empty' | 'loading' | 'error'>('normal')
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [loadState, setLoadState] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const [streaming, setStreaming] = useState(true)
  const [tick, setTick] = useState(0)
  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState('All severity')
  const [activeNav, setActiveNav] = useState('Overview')
  const [mobileMenu, setMobileMenu] = useState(false)

  useEffect(() => {
    if (source === 'demo') {
      setSnapshot(null)
      setLoadState('loading')
    }
  }, [source])

  useEffect(() => {
    if (source !== 'live' || !streaming) return
    const controller = new AbortController()
    setLoadState(current => current === 'ready' ? 'ready' : 'loading')
    fetchSnapshot('live', controller.signal).then(data => {
      setSnapshot(data)
      setLoadState('ready')
      setError('')
    }).catch((cause: unknown) => {
      if (controller.signal.aborted) return
      setError(cause instanceof Error ? cause.message : 'Could not connect to the backend server. Make sure your VM is running.')
      setLoadState('error')
    })
    return () => controller.abort()
  }, [source, retry, streaming])

  useEffect(() => {
    if (!streaming) return
    const interval = window.setInterval(() => {
      if (source === 'live') setRetry(value => value + 1)
      else setTick(value => value + 1)
    }, 1000)
    return () => window.clearInterval(interval)
  }, [source, streaming])

  const data = source === 'demo' ? demoSnapshot(scenario === 'attack', scenario === 'empty') : snapshot
  const loading = source === 'demo' ? scenario === 'loading' : loadState === 'loading'
  const failed = source === 'demo' ? scenario === 'error' : loadState === 'error'
  const empty = !!data && data.endpointsTotal === 0 && data.traffic.ingress.length === 0 && data.threats.length === 0
  const rows = (data?.threats || []).filter(row => (severity === 'All severity' || row.severity === severity) && `${row.ip} ${row.country} ${row.port} ${row.reason}`.toLowerCase().includes(search.toLowerCase()))

  const navItems = [
    { label: 'Overview', target: 'overview' },
    { label: 'Live Traffic', target: 'traffic' },
    { label: 'How It Works', target: 'how-it-works' },
    { label: 'Blocked Devices', target: 'threats' },
  ]

  const latestIngressK = data?.traffic.ingress.length ? data.traffic.ingress[data.traffic.ingress.length - 1] : 0
  const currentPps = data?.metrics.currentPps !== undefined ? data.metrics.currentPps : Math.round(latestIngressK * 1000)
  const peakIngressK = data?.traffic.ingress.length ? Math.max(...data.traffic.ingress) : 0
  const peakPps = Math.round(peakIngressK * 1000)

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      {/* Mobile Backdrop */}
      {mobileMenu && (
        <button 
          className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" 
          aria-label="Close menu" 
          onClick={() => setMobileMenu(false)}
        />
      )}

      {/* Spacious Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[265px] flex-col border-r border-slate-200 bg-white px-6 py-7 transition-transform duration-200 lg:translate-x-0 ${mobileMenu ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-slate-900 text-white">
              <Icon name="shield" size={17} />
            </span>
            <span className="text-lg font-bold tracking-tight text-slate-900">Network Defense</span>
          </div>
          <button className="text-slate-400 hover:text-slate-600 lg:hidden" onClick={() => setMobileMenu(false)} aria-label="Close menu">
            <Icon name="close" size={20} />
          </button>
        </div>

        <div className="mt-9 text-xs font-semibold uppercase tracking-wider text-slate-400">Navigation</div>
        <nav className="mt-3 space-y-1.5" aria-label="Main navigation">
          {navItems.map(item => (
            <a
              key={item.label}
              href={`#${item.target}`}
              onClick={() => { setActiveNav(item.label); setMobileMenu(false) }}
              className={`flex items-center justify-between rounded-xl px-4 py-3 text-sm sm:text-base font-medium transition-colors ${activeNav === item.label ? 'bg-slate-100 text-slate-900 font-semibold' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
            >
              <span>{item.label}</span>
              {item.label === 'Blocked Devices' && data && data.threats.length > 0 && (
                <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-bold text-red-700">
                  {data.threats.length}
                </span>
              )}
            </a>
          ))}
        </nav>

        {/* Clean Connection Status Card */}
        <div className="mt-auto rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <span className={`h-2.5 w-2.5 rounded-full ${source === 'live' ? 'bg-emerald-500' : 'bg-blue-500'}`} />
            {source === 'live' ? 'Connected to Controller' : 'Demo Simulation Mode'}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {source === 'live' ? 'Target: 192.168.8.147:5000' : 'Sample traffic loaded'}
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="min-h-screen lg:pl-[265px]">
        {/* Top Navbar */}
        <header className="sticky top-0 z-20 flex min-h-[70px] items-center justify-between border-b border-slate-200 bg-white/95 px-6 sm:px-10 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button className="rounded p-1.5 text-slate-600 lg:hidden" aria-label="Open menu" onClick={() => setMobileMenu(true)}>
              <Icon name="menu" size={22} />
            </button>
            <span className="text-sm font-medium text-slate-400">Mininet Network <span className="mx-1.5">/</span></span>
            <span className="text-sm font-semibold text-slate-800">Traffic &amp; DDoS Monitor</span>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center rounded-lg border border-slate-200 bg-slate-100/90 p-0.5 text-xs sm:text-sm font-medium">
              <button 
                onClick={() => setSource('demo')} 
                className={`rounded-md px-3 py-1.5 transition-colors ${source === 'demo' ? 'bg-white text-slate-900 shadow-sm font-semibold' : 'text-slate-500 hover:text-slate-800'}`}
              >
                Demo
              </button>
              <button 
                onClick={() => { setSource('live'); setStreaming(true) }} 
                disabled={!endpoint} 
                className={`rounded-md px-3 py-1.5 transition-colors ${source === 'live' ? 'bg-white text-slate-900 shadow-sm font-semibold' : 'text-slate-500 hover:text-slate-800'}`}
              >
                Live
              </button>
            </div>

            <button
              onClick={() => setScenario(scenario === 'attack' ? 'normal' : 'attack')}
              disabled={source === 'live'}
              className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs sm:text-sm font-semibold transition-colors ${
                scenario === 'attack' && source === 'demo'
                  ? 'bg-red-600 text-white hover:bg-red-700'
                  : 'bg-slate-900 text-white hover:bg-slate-800'
              }`}
            >
              <Icon name={scenario === 'attack' && source === 'demo' ? 'pause' : 'play'} size={14} />
              {scenario === 'attack' && source === 'demo' ? 'Stop Attack' : 'Simulate Attack'}
            </button>
          </div>
        </header>

        {/* Content Body */}
        <main className="mx-auto max-w-[1600px] px-6 sm:px-10 py-9 sm:py-10" id="overview">
          {/* Header Title & Subtitle */}
          <div className="flex flex-wrap items-end justify-between gap-5">
            <div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-slate-900">
                Network Traffic &amp; DDoS Monitor
              </h1>
              <p className="mt-2.5 text-base sm:text-lg text-slate-600 max-w-3xl leading-relaxed">
                Live packet flow monitoring and automatic DDoS attack defense for Mininet virtual network.
              </p>
            </div>

            {source === 'demo' && (
              <div className="flex items-center gap-2.5 text-sm text-slate-600">
                <span className="font-medium">Scenario Preset:</span>
                <select 
                  value={scenario} 
                  onChange={event => setScenario(event.target.value as typeof scenario)} 
                  className="rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-sm font-medium text-slate-800 shadow-sm"
                >
                  <option value="normal">Normal Baseline (iperf)</option>
                  <option value="attack">Under Attack (hping3 Flood)</option>
                  <option value="empty">No Traffic</option>
                  <option value="loading">Loading Preview</option>
                  <option value="error">Error Preview</option>
                </select>
              </div>
            )}
          </div>

          {loading ? (
            <div className="mt-8 space-y-5">
              <div className="h-32 rounded-xl bg-slate-100 skeleton" />
              <div className="h-64 rounded-xl bg-slate-100 skeleton" />
            </div>
          ) : failed ? (
            <div className="panel-card mt-8 p-12 text-center">
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600">
                <Icon name="alert" size={24} />
              </div>
              <h2 className="mt-4 text-xl font-bold text-slate-900">Could not connect to backend server</h2>
              <p className="mx-auto mt-2 max-w-lg text-sm text-slate-600 leading-relaxed">{error}</p>
              <div className="mt-6 flex justify-center gap-3">
                <button onClick={retryRequest} className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800">
                  Retry Connection
                </button>
                {source === 'live' && (
                  <button onClick={() => setSource('demo')} className="rounded-lg border border-slate-200 bg-white px-5 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50">
                    Switch to Demo Mode
                  </button>
                )}
              </div>
            </div>
          ) : data && (
            <>
              {/* TOP SECTION: Prominent Full-Width Status Banner (No more awkward narrow aspect ratio) */}
              <div className={`panel-card mt-8 sm:mt-10 p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 border-l-4 ${
                data.health === 'degraded' 
                  ? 'border-l-red-500 bg-red-50/50 border-red-200' 
                  : 'border-l-emerald-500 bg-emerald-50/40 border-emerald-200'
              }`}>
                <div>
                  <div className="flex items-center gap-2.5">
                    <span className={`h-3 w-3 rounded-full ${data.health === 'degraded' ? 'bg-red-500 animate-ping' : 'bg-emerald-500'}`} />
                    <span className={`text-xs sm:text-sm font-bold uppercase tracking-wider ${data.health === 'degraded' ? 'text-red-700' : 'text-emerald-700'}`}>
                      {data.health === 'degraded' ? 'DDoS Attack in Progress' : 'Network Operating Normally'}
                    </span>
                  </div>
                  <h2 className="mt-2 text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                    {empty ? 'Awaiting Traffic Telemetry' : data.health === 'degraded' ? 'Malicious Traffic Is Being Blocked' : 'All Network Flows Are Safe'}
                  </h2>
                  <p className="mt-2 max-w-3xl text-sm sm:text-base text-slate-600 leading-relaxed">
                    {empty 
                      ? 'Mininet is currently idle. Run legitimate traffic or an attack script to view live response.' 
                      : data.health === 'degraded' 
                      ? 'High-rate packet flood detected from host h2 (10.0.0.2). Attack packets are being dropped immediately at switch s1, while real user h1 continues communicating normally.' 
                      : 'Ryu controller is polling switch s1 every 1.5 seconds. Traffic from legitimate user host h1 is moving freely to server h3.'}
                  </p>
                </div>

                <div className="flex md:flex-col items-center md:items-end justify-between gap-2.5 border-t md:border-t-0 md:border-l border-slate-200 pt-4 md:pt-0 md:pl-8 shrink-0">
                  <div className="text-xs sm:text-sm font-medium text-slate-500">Switch Defense Policy</div>
                  <div className={`text-sm sm:text-base font-bold px-3.5 py-1.5 rounded-full ${
                    data.health === 'degraded' ? 'bg-red-100 text-red-800' : 'bg-emerald-100 text-emerald-800'
                  }`}>
                    {data.health === 'degraded' ? 'DROP Active (Priority 65535)' : 'Normal Forwarding'}
                  </div>
                  <div className="text-xs sm:text-sm text-slate-500 mt-0.5">
                    {data.endpointsOnline}/{data.endpointsTotal} Mininet Nodes Connected
                  </div>
                </div>
              </div>

              {/* BALANCED 4-CARD METRIC GRID (Equal shape, generous padding) */}
              <div className="mt-6 sm:mt-7 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard 
                  label="Current Traffic Rate" 
                  value={currentPps.toLocaleString()} 
                  unit="pkts/s" 
                  detail="Live packets moving across all switch ports"
                />
                <MetricCard 
                  label="Highest Traffic (Peak)" 
                  value={peakPps.toLocaleString()} 
                  unit="pkts/s" 
                  detail="Peak spike recorded in recent 48-second window"
                />
                <MetricCard 
                  label="Active Network Rules" 
                  value={data.metrics.activeRules.toLocaleString()} 
                  unit="Rules" 
                  detail="Active flow table rules installed on switch s1"
                />
                <MetricCard 
                  label="Defense Reaction Time" 
                  value={data.metrics.mlLatencyMs.toFixed(1)} 
                  unit="ms" 
                  detail="Average time to inspect traffic &amp; apply defense"
                />
              </div>

              {/* Live Traffic Chart Section */}
              <section id="traffic" className="panel-card mt-8 sm:mt-10 p-6 sm:p-8">
                <div className="flex flex-wrap items-center justify-between gap-5">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-lg sm:text-xl font-bold text-slate-900">Live Network Traffic</h2>
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
                        <span className={`h-2 w-2 rounded-full bg-emerald-500 ${streaming ? 'live-dot' : ''}`} />
                        {streaming ? 'Live Streaming' : 'Paused'}
                      </span>
                    </div>
                    <p className="mt-1.5 text-sm sm:text-base text-slate-500">
                      Comparing incoming traffic vs. blocked traffic over the last 48 seconds
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-5 text-sm font-medium text-slate-600">
                    <span className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-blue-600" /> Incoming Traffic
                    </span>
                    <span className="flex items-center gap-2">
                      <span className="h-3 w-3 rounded-full bg-teal-600" /> Blocked Traffic
                    </span>
                    <span className="flex items-center gap-2 text-slate-500">
                      <span className="h-0.5 w-4 bg-red-400" /> Limit (8,000 pkts/s)
                    </span>
                    <button 
                      onClick={() => setStreaming(!streaming)} 
                      aria-label={streaming ? 'Pause graph' : 'Resume graph'} 
                      className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    >
                      <Icon name={streaming ? 'pause' : 'play'} size={16} />
                    </button>
                  </div>
                </div>

                {data.traffic.ingress.length > 1 ? (
                  <TrafficChart traffic={data.traffic} tick={source === 'demo' ? tick : 0} />
                ) : (
                  <div className="py-16 text-center text-sm text-slate-400">
                    Awaiting traffic packets from Mininet...
                  </div>
                )}
              </section>

              {/* How It Works & Why Blocked Section */}
              <div id="how-it-works" className="mt-8 sm:mt-10 grid grid-cols-1 gap-6 sm:gap-8 lg:grid-cols-2">
                {/* How It Works */}
                <div className="panel-card p-7 sm:p-8">
                  <h3 className="text-lg sm:text-xl font-bold text-slate-900">How the Defense System Works</h3>
                  <p className="mt-1.5 text-sm text-slate-500">Automatic 3-step defense cycle</p>

                  <div className="mt-6 space-y-5 text-sm sm:text-base text-slate-700 leading-relaxed">
                    <div className="flex items-start gap-4">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white mt-0.5">1</span>
                      <div>
                        <strong className="text-slate-900">Watch Traffic:</strong> The controller checks how many packets are moving through the switch every second.
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white mt-0.5">2</span>
                      <div>
                        <strong className="text-slate-900">Spot Abnormal Spikes:</strong> If traffic suddenly jumps over 8,000 packets per second, it is flagged as an attack.
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white mt-0.5">3</span>
                      <div>
                        <strong className="text-slate-900">Block the Attacker:</strong> The switch immediately drops all packets from that device. Real users stay connected.
                      </div>
                    </div>
                  </div>
                </div>

                {/* Why Traffic Was Blocked */}
                <div className="panel-card p-7 sm:p-8">
                  <h3 className="text-lg sm:text-xl font-bold text-slate-900">Why Traffic Was Blocked</h3>
                  <p className="mt-1.5 text-sm text-slate-500">Breakdown of rules triggered during an attack</p>

                  {data.dropReasons.length ? (
                    <div className="mt-6 space-y-4">
                      {data.dropReasons.map((reason) => (
                        <div key={reason.reason}>
                          <div className="flex justify-between text-sm sm:text-base font-semibold text-slate-700">
                            <span>{reason.reason}</span>
                            <span className="mono">{reason.share}%</span>
                          </div>
                          <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-slate-100">
                            <div className="h-full rounded-full bg-slate-800" style={{ width: `${reason.share}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="py-12 text-center text-sm text-slate-400">
                      No traffic has been blocked yet. The network is clean.
                    </div>
                  )}
                </div>
              </div>

              {/* Blocked Devices Table */}
              <section id="threats" className="panel-card mt-8 sm:mt-10 overflow-hidden">
                <div className="flex flex-wrap items-center justify-between gap-5 border-b border-slate-200 p-6 sm:p-7">
                  <div>
                    <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                      Blocked Devices &amp; Attacks
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                      Devices caught sending abnormal traffic and blocked at the switch
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex h-10 items-center gap-2.5 rounded-lg border border-slate-200 bg-white px-3 text-slate-400">
                      <Icon name="search" size={16} />
                      <input 
                        value={search} 
                        onChange={event => setSearch(event.target.value)} 
                        placeholder="Search IP or host..." 
                        aria-label="Search blocked threats" 
                        className="w-36 sm:w-44 bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
                      />
                    </div>
                    <button 
                      disabled={!rows.length} 
                      onClick={() => exportCsv(rows)} 
                      className="flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      <Icon name="download" size={15} /> Export CSV
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-600">
                        <th className="py-4 px-6">Device &amp; IP</th>
                        <th className="py-4 px-6">Protocol</th>
                        <th className="py-4 px-6">Why It Was Blocked</th>
                        <th className="py-4 px-6">Confidence</th>
                        <th className="py-4 px-6 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {rows.map((row, i) => (
                        <tr key={`${row.ip}-${i}`} className="hover:bg-slate-50/70">
                          <td className="py-4.5 px-6">
                            <div className="font-bold text-slate-900 mono text-base">{row.ip}</div>
                            <div className="text-xs sm:text-sm text-slate-500 mt-0.5">{row.country}</div>
                          </td>
                          <td className="py-4.5 px-6 text-slate-700 font-medium">
                            {row.protocol} (Port {row.port})
                          </td>
                          <td className="py-4.5 px-6 text-slate-600">
                            {row.reason}
                          </td>
                          <td className="py-4.5 px-6 font-semibold text-slate-800 mono">
                            {row.score}%
                          </td>
                          <td className="py-4.5 px-6 text-right">
                            <span className="inline-flex rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-700">
                              Blocked
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {!rows.length && (
                    <div className="py-12 text-center text-sm text-slate-400">
                      No devices are currently blocked. The network is clean.
                    </div>
                  )}
                </div>
              </section>
            </>
          )}

          {/* Simple Academic Footer */}
          <footer className="mt-12 flex flex-wrap items-center justify-between gap-4 border-t border-slate-200 pt-7 text-sm text-slate-500">
            <div>
              SDN DDoS Mitigation Project · Built with Ryu Controller &amp; Mininet
            </div>
            <div>
              Academic Demo · {source === 'live' ? 'Connected to 192.168.8.147' : 'Simulation Mode'}
            </div>
          </footer>
        </main>
      </div>
    </div>
  )
}
