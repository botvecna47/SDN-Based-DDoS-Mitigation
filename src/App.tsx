import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { demoSnapshot, endpoint, fetchSnapshot } from './data'
import type { Snapshot, Threat } from './data'

type IconName = 'shield' | 'activity' | 'zap' | 'clock' | 'filter' | 'search' | 'download' | 'refresh' | 'alert' | 'check' | 'pause' | 'play' | 'close' | 'menu'

function Icon({ name, size = 16, className = '' }: { name: IconName; size?: number; className?: string }) {
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

const timelineLabels = ['-48s', '-40s', '-32s', '-24s', '-16s', '-8s', 'Now']

function smoothPath(values: number[], ceiling: number) {
  if (values.length < 2) return ''
  const points = values.map((value, i) => ({
    x: 45 + i * (935 / (values.length - 1)),
    y: 215 - Math.min(1, value / ceiling) * 185
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
  const y = activeHover === null ? 0 : 215 - Math.min(1, ingress[activeHover] / ceiling) * 185

  return (
    <div className="relative mt-5 select-none">
      <div 
        className="relative h-[250px] w-full" 
        onMouseMove={event => {
          const bounds = event.currentTarget.getBoundingClientRect()
          setHover(Math.max(0, Math.min(ingress.length - 1, Math.round(((event.clientX - bounds.left) / bounds.width - 0.045) / 0.935 * (ingress.length - 1)))))
        }} 
        onMouseLeave={() => setHover(null)}
      >
        <svg viewBox="0 0 1000 240" preserveAspectRatio="none" className="h-full w-full overflow-visible" role="img" aria-label="Traffic history chart">
          <defs>
            <linearGradient id="ingressFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#2563eb" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#2563eb" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="droppedFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#0d9488" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#0d9488" stopOpacity="0.0" />
            </linearGradient>
          </defs>
          
          {[0, 0.25, 0.5, 0.75, 1].map(fraction => (
            <g key={fraction}>
              <line x1="45" x2="980" y1={215 - fraction * 185} y2={215 - fraction * 185} stroke="#f1f5f9" strokeWidth="1" />
              <text x="0" y={219 - fraction * 185} fill="#94a3b8" fontSize="11" className="mono">{Math.round(fraction * ceiling)}k</text>
            </g>
          ))}

          {/* Threshold marker */}
          <line 
            x1="45" 
            x2="980" 
            y1={215 - traffic.threshold / ceiling * 185} 
            y2={215 - traffic.threshold / ceiling * 185} 
            stroke="#ef4444" 
            strokeWidth="1.5" 
            strokeDasharray="4 4" 
          />

          <path d={`${droppedPath} L 980 215 L 45 215 Z`} fill="url(#droppedFill)" />
          <path d={`${ingressPath} L 980 215 L 45 215 Z`} fill="url(#ingressFill)" />
          <path d={droppedPath} fill="none" stroke="#0d9488" strokeWidth="2" vectorEffect="non-scaling-stroke" />
          <path d={ingressPath} fill="none" stroke="#2563eb" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />

          {activeHover !== null && (
            <>
              <line x1={x} x2={x} y1="20" y2="215" stroke="#cbd5e1" strokeDasharray="3 3" />
              <circle cx={x} cy={y} r="4" fill="#2563eb" stroke="#ffffff" strokeWidth="2" />
            </>
          )}
        </svg>

        {activeHover !== null && (
          <div 
            className="pointer-events-none absolute rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-white shadow-md"
            style={{ left: `${Math.min(84, Math.max(10, x / 10))}%`, top: `${Math.max(8, y / 2.4 - 15)}%`, transform: 'translate(-50%, -100%)' }}
          >
            <div className="text-[10px] text-slate-400">{48 - activeHover}s ago</div>
            <div className="font-medium mono">{Math.round((ingress[activeHover] || 0) * 1000).toLocaleString()} incoming / sec</div>
            <div className="font-medium text-teal-400 mono">{Math.round((dropped[activeHover] || 0) * 1000).toLocaleString()} blocked / sec</div>
          </div>
        )}
      </div>

      <div className="ml-[4.5%] flex justify-between pt-2 text-[11px] text-slate-400 mono">
        {timelineLabels.map(label => <span key={label}>{label}</span>)}
      </div>
    </div>
  )
}

function MetricCard({ label, value, unit, detail }: { label: string; value: string; unit?: string; detail: string }) {
  return (
    <div className="panel-card p-5">
      <div className="text-xs font-medium text-slate-500">{label}</div>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span className="text-2xl font-bold tracking-tight text-slate-900 mono">{value}</span>
        {unit && <span className="text-xs font-medium text-slate-500">{unit}</span>}
      </div>
      <div className="mt-2 text-xs text-slate-500">{detail}</div>
    </div>
  )
}

function exportCsv(rows: Threat[]) {
  const fields = ['Source IP', 'Device Host', 'Port', 'Protocol', 'Reason', 'Confidence', 'Status']
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
      {/* Mobile Drawer Backdrop */}
      {mobileMenu && (
        <button 
          className="fixed inset-0 z-30 bg-slate-900/40 lg:hidden" 
          aria-label="Close menu" 
          onClick={() => setMobileMenu(false)}
        />
      )}

      {/* Clean Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-40 flex w-[240px] flex-col border-r border-slate-200 bg-white px-5 py-6 transition-transform duration-200 lg:translate-x-0 ${mobileMenu ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-md bg-slate-900 text-white">
              <Icon name="shield" size={15} />
            </span>
            <span className="text-base font-semibold tracking-tight text-slate-900">Network Defense</span>
          </div>
          <button className="text-slate-400 hover:text-slate-600 lg:hidden" onClick={() => setMobileMenu(false)} aria-label="Close menu">
            <Icon name="close" size={18} />
          </button>
        </div>

        <div className="mt-8 text-[11px] font-semibold uppercase tracking-wider text-slate-400">Navigation</div>
        <nav className="mt-3 space-y-1" aria-label="Main navigation">
          {navItems.map(item => (
            <a
              key={item.label}
              href={`#${item.target}`}
              onClick={() => { setActiveNav(item.label); setMobileMenu(false) }}
              className={`flex items-center justify-between rounded-lg px-3 py-2 text-sm font-medium transition-colors ${activeNav === item.label ? 'bg-slate-100 text-slate-900' : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'}`}
            >
              <span>{item.label}</span>
              {item.label === 'Blocked Devices' && data && data.threats.length > 0 && (
                <span className="rounded bg-red-100 px-1.5 py-0.5 text-xs font-semibold text-red-700">
                  {data.threats.length}
                </span>
              )}
            </a>
          ))}
        </nav>

        {/* Simple Connection Card */}
        <div className="mt-auto rounded-lg border border-slate-200 bg-slate-50/70 p-3.5">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-800">
            <span className={`h-2 w-2 rounded-full ${source === 'live' ? 'bg-emerald-500' : 'bg-blue-500'}`} />
            {source === 'live' ? 'Connected to Controller' : 'Demo Simulation'}
          </div>
          <div className="mt-1 text-[11px] text-slate-500">
            {source === 'live' ? 'Target: 192.168.8.147' : 'Simulating traffic'}
          </div>
        </div>
      </aside>

      {/* Main Container */}
      <div className="min-h-screen lg:pl-[240px]">
        {/* Simple Navbar */}
        <header className="sticky top-0 z-20 flex min-h-[60px] items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur-sm sm:px-8">
          <div className="flex items-center gap-3">
            <button className="rounded p-1 text-slate-600 lg:hidden" aria-label="Open menu" onClick={() => setMobileMenu(true)}>
              <Icon name="menu" size={20} />
            </button>
            <span className="text-xs font-medium text-slate-400">Mininet Virtual Network <span className="mx-1">/</span></span>
            <span className="text-xs font-semibold text-slate-700">Traffic Monitor</span>
          </div>

          <div className="flex items-center gap-2.5">
            <div className="flex items-center rounded-lg border border-slate-200 bg-slate-100/80 p-0.5 text-xs font-medium">
              <button 
                onClick={() => setSource('demo')} 
                className={`rounded-md px-2.5 py-1 transition-colors ${source === 'demo' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
              >
                Demo
              </button>
              <button 
                onClick={() => { setSource('live'); setStreaming(true) }} 
                disabled={!endpoint} 
                className={`rounded-md px-2.5 py-1 transition-colors ${source === 'live' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-800'}`}
              >
                Live
              </button>
            </div>

            <button
              onClick={() => setScenario(scenario === 'attack' ? 'normal' : 'attack')}
              disabled={source === 'live'}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                scenario === 'attack' && source === 'demo'
                  ? 'bg-red-600 text-white hover:bg-red-700'
                  : 'bg-slate-900 text-white hover:bg-slate-800'
              }`}
            >
              <Icon name={scenario === 'attack' && source === 'demo' ? 'pause' : 'play'} size={13} />
              {scenario === 'attack' && source === 'demo' ? 'Stop Attack' : 'Simulate Attack'}
            </button>
          </div>
        </header>

        {/* Content */}
        <main className="mx-auto max-w-7xl px-5 py-7 sm:px-8" id="overview">
          {/* Header Title */}
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
                Network Traffic &amp; DDoS Monitor
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                Live traffic monitoring and automatic attack defense for Mininet network.
              </p>
            </div>

            {source === 'demo' && (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span>Preset:</span>
                <select 
                  value={scenario} 
                  onChange={event => setScenario(event.target.value as typeof scenario)} 
                  className="rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-700 shadow-sm"
                >
                  <option value="normal">Normal Traffic (iperf)</option>
                  <option value="attack">Under Attack (hping3 Flood)</option>
                  <option value="empty">No Traffic</option>
                  <option value="loading">Loading Preview</option>
                  <option value="error">Error Preview</option>
                </select>
              </div>
            )}
          </div>

          {loading ? (
            <div className="mt-8 space-y-4">
              <div className="h-44 rounded-xl bg-slate-100 skeleton" />
              <div className="h-64 rounded-xl bg-slate-100 skeleton" />
            </div>
          ) : failed ? (
            <div className="panel-card mt-8 p-10 text-center">
              <div className="mx-auto flex h-10 w-10 items-center justify-center rounded-full bg-red-100 text-red-600">
                <Icon name="alert" size={20} />
              </div>
              <h2 className="mt-3 text-lg font-semibold text-slate-900">Could not connect to backend</h2>
              <p className="mx-auto mt-1 max-w-md text-xs text-slate-500">{error}</p>
              <div className="mt-5 flex justify-center gap-2">
                <button onClick={retryRequest} className="rounded-lg bg-slate-900 px-4 py-2 text-xs font-medium text-white hover:bg-slate-800">
                  Retry
                </button>
                {source === 'live' && (
                  <button onClick={() => setSource('demo')} className="rounded-lg border border-slate-200 bg-white px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50">
                    Switch to Demo
                  </button>
                )}
              </div>
            </div>
          ) : data && (
            <>
              {/* Status and Metric Cards */}
              <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {/* Status Indicator Card */}
                <div className={`rounded-xl border p-5 flex flex-col justify-between sm:col-span-2 lg:col-span-1 ${
                  data.health === 'degraded' 
                    ? 'border-red-200 bg-red-50/70 text-slate-900' 
                    : 'border-emerald-200 bg-emerald-50/60 text-slate-900'
                }`}>
                  <div>
                    <div className="flex items-center gap-2 text-xs font-semibold">
                      <span className={`h-2.5 w-2.5 rounded-full ${data.health === 'degraded' ? 'bg-red-500 animate-ping' : 'bg-emerald-500'}`} />
                      <span className={data.health === 'degraded' ? 'text-red-800' : 'text-emerald-800'}>
                        {data.health === 'degraded' ? 'Attack Detected' : 'Network Safe'}
                      </span>
                    </div>
                    <div className="mt-3 text-lg font-bold">
                      {empty ? 'No Flow Data' : data.health === 'degraded' ? 'DDoS Being Blocked' : 'Normal Operation'}
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-slate-600">
                      {empty 
                        ? 'Mininet is not yet sending traffic.' 
                        : data.health === 'degraded' 
                        ? 'High-speed flood from h2 is being dropped at the switch.' 
                        : 'User h1 traffic is flowing to server h3 normally.'}
                    </p>
                  </div>
                  <div className="mt-4 border-t border-slate-200/80 pt-3 text-xs text-slate-500 flex justify-between">
                    <span>Switch State</span>
                    <span className="font-semibold text-slate-700">
                      {data.health === 'degraded' ? 'DROP Rule Active' : 'Normal Forwarding'}
                    </span>
                  </div>
                </div>

                <MetricCard 
                  label="Current Traffic" 
                  value={currentPps.toLocaleString()} 
                  unit="pkts/s" 
                  detail="Live packets flowing through switch"
                />
                <MetricCard 
                  label="Highest Traffic (Peak)" 
                  value={peakPps.toLocaleString()} 
                  unit="pkts/s" 
                  detail="Peak spike recorded in this session"
                />
                <MetricCard 
                  label="Reaction Time" 
                  value={data.metrics.mlLatencyMs.toFixed(1)} 
                  unit="ms" 
                  detail="Time taken to detect and block"
                />
              </div>

              {/* Chart Section */}
              <section id="traffic" className="panel-card mt-6 p-6">
                <div className="flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-semibold text-slate-900">Live Network Traffic</h2>
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-2 py-0.5 text-[10px] font-semibold text-emerald-700 border border-emerald-200">
                        <span className={`h-1.5 w-1.5 rounded-full bg-emerald-500 ${streaming ? 'live-dot' : ''}`} />
                        {streaming ? 'Live Streaming' : 'Paused'}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-slate-500">
                      Comparing incoming traffic vs. blocked traffic over the last 48 seconds
                    </p>
                  </div>

                  <div className="flex items-center gap-4 text-xs font-medium text-slate-600">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-blue-600" /> Incoming Traffic
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2 w-2 rounded-full bg-teal-600" /> Blocked Traffic
                    </span>
                    <span className="flex items-center gap-1.5 text-slate-400">
                      <span className="h-0.5 w-3 bg-red-400" /> Limit (8,000 pkts/s)
                    </span>
                    <button 
                      onClick={() => setStreaming(!streaming)} 
                      aria-label={streaming ? 'Pause graph' : 'Resume graph'} 
                      className="rounded border border-slate-200 p-1 text-slate-500 hover:bg-slate-50 hover:text-slate-800"
                    >
                      <Icon name={streaming ? 'pause' : 'play'} size={14} />
                    </button>
                  </div>
                </div>

                {data.traffic.ingress.length > 1 ? (
                  <TrafficChart traffic={data.traffic} tick={source === 'demo' ? tick : 0} />
                ) : (
                  <div className="py-12 text-center text-xs text-slate-400">
                    Awaiting traffic packets from Mininet...
                  </div>
                )}
              </section>

              {/* How It Works & Mitigation Reason */}
              <div id="how-it-works" className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
                {/* How It Works Panel */}
                <div className="panel-card p-6">
                  <h3 className="text-sm font-semibold text-slate-900">How the Defense System Works</h3>
                  <p className="mt-1 text-xs text-slate-500">Automatic 3-step defense cycle</p>

                  <div className="mt-4 space-y-3.5 text-xs text-slate-600">
                    <div className="flex items-start gap-3">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-900 text-[10px] font-bold text-white">1</span>
                      <div>
                        <strong className="text-slate-900">Watch Traffic:</strong> The controller checks how many packets are moving through the switch every second.
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-900 text-[10px] font-bold text-white">2</span>
                      <div>
                        <strong className="text-slate-900">Spot Abnormal Spikes:</strong> If traffic suddenly jumps over 8,000 packets per second, it is flagged as an attack.
                      </div>
                    </div>
                    <div className="flex items-start gap-3">
                      <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-slate-900 text-[10px] font-bold text-white">3</span>
                      <div>
                        <strong className="text-slate-900">Block the Attacker:</strong> The switch immediately drops all packets from that device. Real users stay connected.
                      </div>
                    </div>
                  </div>
                </div>

                {/* Why Traffic Was Blocked */}
                <div className="panel-card p-6">
                  <h3 className="text-sm font-semibold text-slate-900">Why Traffic Was Blocked</h3>
                  <p className="mt-1 text-xs text-slate-500">Breakdown of rules triggered during an attack</p>

                  {data.dropReasons.length ? (
                    <div className="mt-4 space-y-3">
                      {data.dropReasons.map((reason) => (
                        <div key={reason.reason}>
                          <div className="flex justify-between text-xs font-medium text-slate-700">
                            <span>{reason.reason}</span>
                            <span className="mono">{reason.share}%</span>
                          </div>
                          <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-slate-100">
                            <div className="h-full rounded-full bg-slate-800" style={{ width: `${reason.share}%` }} />
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="py-8 text-center text-xs text-slate-400">
                      No traffic has been blocked yet.
                    </div>
                  )}
                </div>
              </div>

              {/* Blocked Devices Table */}
              <section id="threats" className="panel-card mt-6 overflow-hidden">
                <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 p-5">
                  <div>
                    <h2 className="text-base font-semibold text-slate-900">
                      Blocked Devices &amp; Attacks
                    </h2>
                    <p className="mt-0.5 text-xs text-slate-500">
                      Devices caught sending abnormal traffic and blocked at the switch
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <div className="flex h-8 items-center gap-2 rounded-lg border border-slate-200 bg-white px-2.5 text-slate-400">
                      <Icon name="search" size={14} />
                      <input 
                        value={search} 
                        onChange={event => setSearch(event.target.value)} 
                        placeholder="Search IP or host..." 
                        aria-label="Search blocked threats" 
                        className="w-32 bg-transparent text-xs text-slate-800 outline-none placeholder:text-slate-400"
                      />
                    </div>
                    <button 
                      disabled={!rows.length} 
                      onClick={() => exportCsv(rows)} 
                      className="flex h-8 items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 text-xs font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-50"
                    >
                      <Icon name="download" size={13} /> Export CSV
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50/70 font-semibold text-slate-500">
                        <th className="py-3 pl-5">Device &amp; IP</th>
                        <th className="py-3">Protocol</th>
                        <th className="py-3">Why It Was Blocked</th>
                        <th className="py-3">Confidence</th>
                        <th className="py-3 pr-5 text-right">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {rows.map((row, i) => (
                        <tr key={`${row.ip}-${i}`} className="hover:bg-slate-50/50">
                          <td className="py-3 pl-5">
                            <div className="font-semibold text-slate-900 mono">{row.ip}</div>
                            <div className="text-[11px] text-slate-500">{row.country}</div>
                          </td>
                          <td className="py-3 text-slate-700">
                            {row.protocol} (Port {row.port})
                          </td>
                          <td className="py-3 text-slate-600">
                            {row.reason}
                          </td>
                          <td className="py-3 font-medium text-slate-800 mono">
                            {row.score}%
                          </td>
                          <td className="py-3 pr-5 text-right">
                            <span className="inline-flex rounded-full bg-red-100 px-2 py-0.5 text-[11px] font-semibold text-red-700">
                              Blocked
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {!rows.length && (
                    <div className="py-10 text-center text-xs text-slate-400">
                      No devices are currently blocked. The network is clean.
                    </div>
                  )}
                </div>
              </section>
            </>
          )}

          {/* Simple Academic Footer */}
          <footer className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-6 text-xs text-slate-400">
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
