import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { demoSnapshot, endpoint, fetchSnapshot } from './data'
import type { Snapshot, Threat } from './data'

type IconName = 'grid' | 'activity' | 'shield' | 'layers' | 'settings' | 'help' | 'chevron' | 'bell' | 'search' | 'arrowUp' | 'arrowDown' | 'download' | 'filter' | 'play' | 'pulse' | 'check' | 'globe' | 'zap' | 'clock' | 'pause' | 'crosshair' | 'close' | 'refresh' | 'alert'
function Icon({ name, size = 18, className = '' }: { name: IconName; size?: number; className?: string }) {
  const paths: Record<IconName, ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
    activity: <path d="M3 12h4l3-7 4 14 3-7h4"/>,
    shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/></>,
    layers: <><path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M19 5l-1.5 1.5m-11 11L5 19"/></>,
    help: <><circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.6 2.6 0 0 1 5 .9c0 1.8-2.5 2.2-2.5 4M12 17h.01"/></>,
    chevron: <path d="m6 9 6 6 6-6"/>, bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>, arrowUp: <path d="m7 17 10-10M8 7h9v9"/>, arrowDown: <path d="m7 7 10 10M17 8v9H8"/>,
    download: <path d="M12 3v12m-4-4 4 4 4-4M4 17v3h16v-3"/>, filter: <path d="M4 7h16M7 12h10m-7 5h4"/>,
    play: <path d="m9 6 9 6-9 6V6Z" fill="currentColor" stroke="none"/>, pulse: <path d="M3 12h4l3-7 4 14 3-7h4"/>, check: <path d="m5 12 4 4L19 6"/>,
    globe: <><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 4 5.5 4 9s-1.5 6.5-4 9c-2.5-2.5-4-5.5-4-9s1.5-6.5 4-9Z"/></>,
    zap: <path d="m13 2-9 11h7l-1 9 10-12h-7l1-8Z"/>, clock: <><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>, pause: <path d="M9 6v12M15 6v12"/>,
    crosshair: <><circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="3"/><path d="M12 2v3m0 14v3M2 12h3m14 0h3"/></>, close: <path d="M5 5l14 14M19 5 5 19"/>,
    refresh: <><path d="M20 11a8 8 0 1 0-2 6M20 4v7h-7"/></>, alert: <><path d="m12 3 10 18H2L12 3Z"/><path d="M12 9v5m0 3h.01"/></>,
  }
  return <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>
}

const timelineLabels = ['-48s', '-40s', '-32s', '-24s', '-16s', '-8s', 'Live (Now)']

function smoothPath(values: number[], ceiling: number) {
  if (values.length < 2) return ''
  const points = values.map((value, i) => ({ x: 50 + i * (930 / (values.length - 1)), y: 218 - Math.min(1, value / ceiling) * 190 }))
  return points.reduce((path, point, i) => {
    if (!i) return `M ${point.x} ${point.y}`
    const previous = points[i - 1]
    const middle = (previous.x + point.x) / 2
    return `${path} C ${middle} ${previous.y}, ${middle} ${point.y}, ${point.x} ${point.y}`
  }, '')
}

function TrafficChart({ traffic, tick }: { traffic: Snapshot['traffic']; tick: number }) {
  const [hover, setHover] = useState<number | null>(null)
  // Dynamic ceiling with safe floor of 12k PPS so baseline (~0.8k) is clearly visible under the 8k threshold line
  const ceiling = Math.max(12, traffic.threshold * 1.35, ...traffic.ingress, ...traffic.dropped)
  const ingress = traffic.ingress.map((n, i) => Math.max(0, n + (tick ? Math.sin(i * .7 + tick) * 0.1 : 0)))
  const dropped = traffic.dropped.map((n, i) => Math.max(0, n + (tick ? Math.sin(i * .8 + tick) * 0.1 : 0)))
  const ingressPath = smoothPath(ingress, ceiling)
  const droppedPath = smoothPath(dropped, ceiling)
  const activeHover = hover === null ? null : Math.min(hover, ingress.length - 1)
  const x = activeHover === null ? 0 : 50 + activeHover * (930 / (ingress.length - 1))
  const y = activeHover === null ? 0 : 218 - Math.min(1, ingress[activeHover] / ceiling) * 190

  return <div className="relative mt-7 select-none">
    <div className="relative h-[274px] w-full" onMouseMove={event => {
      const bounds = event.currentTarget.getBoundingClientRect()
      setHover(Math.max(0, Math.min(ingress.length - 1, Math.round(((event.clientX - bounds.left) / bounds.width - .05) / .93 * (ingress.length - 1)))))
    }} onMouseLeave={() => setHover(null)}>
      <svg viewBox="0 0 1000 250" preserveAspectRatio="none" className="h-full w-full overflow-visible" role="img" aria-label="Area chart of ingress and dropped traffic over time">
        <defs>
          <linearGradient id="ingressFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#5367ed" stopOpacity=".23"/><stop offset="100%" stopColor="#5367ed" stopOpacity="0"/></linearGradient>
          <linearGradient id="droppedFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#2bc6b4" stopOpacity=".22"/><stop offset="100%" stopColor="#2bc6b4" stopOpacity="0"/></linearGradient>
        </defs>
        {[0, .25, .5, .75, 1].map(fraction => (
          <g key={fraction}>
            <line x1="50" x2="980" y1={218 - fraction * 190} y2={218 - fraction * 190} stroke="#e8edf5" strokeDasharray="4 6"/>
            <text x="0" y={222 - fraction * 190} fill="#9aa6b8" fontSize="12" fontFamily="inherit">{Math.round(fraction * ceiling)}k</text>
          </g>
        ))}
        {/* Anomaly Detection Threshold Line */}
        <line x1="50" x2="980" y1={218 - traffic.threshold / ceiling * 190} y2={218 - traffic.threshold / ceiling * 190} stroke="#e69289" strokeWidth="1.5" strokeDasharray="6 6"/>
        <path d={`${droppedPath} L 980 218 L 50 218 Z`} fill="url(#droppedFill)"/>
        <path d={`${ingressPath} L 980 218 L 50 218 Z`} fill="url(#ingressFill)"/>
        <path d={droppedPath} fill="none" stroke="#30bda9" strokeWidth="2.5" vectorEffect="non-scaling-stroke"/>
        <path d={ingressPath} fill="none" stroke="#5b6cf0" strokeWidth="3" vectorEffect="non-scaling-stroke"/>
        {activeHover !== null && (
          <>
            <line x1={x} x2={x} y1="20" y2="218" stroke="#a7b0ca" strokeDasharray="4 5"/>
            <circle cx={x} cy={y} r="5" fill="#5b6cf0" stroke="white" strokeWidth="2"/>
          </>
        )}
      </svg>
      {activeHover !== null && (
        <div className="elevation-dropdown pointer-events-none absolute rounded-xl bg-[#172348] px-3.5 py-2 text-xs font-semibold text-white shadow-lg" style={{ left: `${Math.min(82, Math.max(12, x / 10))}%`, top: `${Math.max(4, y / 2.5 - 20)}%`, transform: 'translate(-50%, -100%)' }}>
          <div className="text-[10px] text-[#9bb0db]">t = -{48 - activeHover}s</div>
          <div>{Math.round((ingress[activeHover] || 0) * 1000).toLocaleString()} PPS ingress</div>
          <div className="text-[#45decb]">{Math.round((dropped[activeHover] || 0) * 1000).toLocaleString()} PPS dropped</div>
        </div>
      )}
    </div>
    <div className="ml-[5%] flex justify-between text-[11px] font-semibold text-[#8a98af]">
      {timelineLabels.map(label => <span key={label}>{label}</span>)}
    </div>
  </div>
}

function MetricCard({ icon, label, value, unit, detail, accent }: { icon: IconName; label: string; value: string; unit?: string; detail: string; accent: string }) {
  return <div className="glass-panel elevation-card metric-card min-w-0 rounded-[20px] p-5 xl:p-6">
    <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${accent}`}><Icon name={icon} size={19}/></div>
    <div className="mt-4 text-xs font-bold uppercase tracking-wide text-[#7d8ba1]">{label}</div>
    <div className="mt-2 flex items-baseline gap-1.5">
      <span className="text-[28px] font-extrabold leading-none tracking-[-.05em] text-[#17213d] xl:text-[32px]">{value}</span>
      {unit && <span className="text-xs font-bold text-[#7f8da4]">{unit}</span>}
    </div>
    <div className="mt-3 text-[11px] font-medium text-[#929fb2]">{detail}</div>
  </div>
}

function Skeleton({ className = '' }: { className?: string }) { return <div className={`skeleton rounded-lg ${className}`} aria-hidden="true"/> }
function LoadingDashboard() {
  return <div role="status" aria-label="Loading network telemetry" className="mt-8 space-y-5">
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
      <div className="glass-panel elevation-card min-h-[344px] rounded-[22px] p-7 md:col-span-2 xl:col-span-1 xl:row-span-2">
        <Skeleton className="h-4 w-28"/><Skeleton className="mt-28 h-12 w-2/3"/><Skeleton className="mt-4 h-4 w-4/5"/>
      </div>
      {[0,1,2,3].map(i => (
        <div className="glass-panel elevation-card min-h-[164px] rounded-[20px] p-6" key={i}>
          <Skeleton className="h-10 w-10"/><Skeleton className="mt-5 h-3 w-24"/><Skeleton className="mt-3 h-8 w-32"/>
        </div>
      ))}
    </div>
    <div className="glass-panel elevation-card rounded-[22px] p-7"><Skeleton className="h-5 w-40"/><Skeleton className="mt-7 h-[235px] w-full"/></div>
    <span className="sr-only">Loading telemetry…</span>
  </div>
}

function EmptyPanel({ title, description, icon = 'activity' }: { title: string; description: string; icon?: IconName }) {
  return <div className="flex min-h-[235px] flex-col items-center justify-center px-5 py-10 text-center">
    <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-[#dce5f3] bg-[#f1f5fb] text-[#697deb]"><Icon name={icon} size={22}/></div>
    <h3 className="text-sm font-bold text-[#30405e]">{title}</h3>
    <p className="mt-2 max-w-[310px] text-xs leading-relaxed text-[#929fb1]">{description}</p>
  </div>
}

function exportCsv(rows: Threat[]) {
  const fields = ['Source IP', 'Host node', 'Target port', 'Protocol', 'Mitigation trigger', 'Confidence', 'Severity', 'Rule status']
  const csv = [fields, ...rows.map(row => [row.ip, row.country, row.port, row.protocol, row.reason, `${row.score}%`, row.severity, 'Active DROP (Priority 65535)'])].map(row => row.map(value => `"${String(value).replace(/"/g, '""')}"`).join(',')).join('\n')
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a'); link.href = url; link.download = 'sdn-mitigation-log.csv'; link.click()
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
    fetchSnapshot('live', controller.signal).then(data => { setSnapshot(data); setLoadState('ready'); setError('') }).catch((cause: unknown) => {
      if (controller.signal.aborted) return
      setError(cause instanceof Error ? cause.message : 'Could not reach Ryu/Flask backend. Please verify VM is running.')
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
  
  const nav: { label: string; icon: IconName; target: string }[] = [
    { label: 'Overview', icon: 'grid', target: 'overview' },
    { label: 'Live telemetry', icon: 'activity', target: 'traffic' },
    { label: 'Mitigation pipeline', icon: 'layers', target: 'pipeline' },
    { label: 'Blocked threats', icon: 'shield', target: 'threats' }
  ]
  const retryRequest = () => { if (source === 'demo') setScenario('normal'); else setRetry(value => value + 1) }

  // Extract authentic, realistic packet metrics
  const latestIngressK = data?.traffic.ingress.length ? data.traffic.ingress[data.traffic.ingress.length - 1] : 0
  const currentPps = data?.metrics.currentPps !== undefined ? data.metrics.currentPps : Math.round(latestIngressK * 1000)
  const peakIngressK = data?.traffic.ingress.length ? Math.max(...data.traffic.ingress) : 0
  const peakPps = Math.round(peakIngressK * 1000)

  return (
    <div className="app-bg elevation-base min-h-screen text-[#202b46]">
      <div className="ambient ambient-one"/>
      <div className="ambient ambient-two"/>
      {mobileMenu && <button className="elevation-modal fixed inset-0 bg-[#122044]/30 lg:hidden" aria-label="Close menu" onClick={() => setMobileMenu(false)}/>}
      
      {/* Sidebar */}
      <aside className={`sidebar-glass elevation-dropdown fixed inset-y-0 left-0 flex w-[250px] flex-col border-r border-white/80 px-4 py-6 transition-transform duration-300 lg:translate-x-0 ${mobileMenu ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex items-center gap-2.5 px-3">
          <div className="logo-mark flex h-9 w-9 items-center justify-center rounded-[11px] text-white">
            <Icon name="shield" size={21}/>
          </div>
          <div>
            <div className="text-[17px] font-extrabold tracking-[-.04em] text-[#182344]">SDN Defense<span className="text-[#6474ee]">.</span></div>
            <div className="text-[10px] font-semibold text-[#8492a8]">OpenFlow 1.3 Console</div>
          </div>
          <button className="ml-auto text-[#71809c] lg:hidden" onClick={() => setMobileMenu(false)} aria-label="Close menu">
            <Icon name="close"/>
          </button>
        </div>

        <div className="mt-8 px-3 text-[10px] font-bold uppercase tracking-[.17em] text-[#a3aec0]">Topology Environment</div>
        <div className="mt-3 flex items-center gap-2.5 rounded-xl border border-[#e8ecf5] bg-white/80 px-2.5 py-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-[#e9edff] text-[#586ae1]">
            <Icon name="globe" size={17}/>
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-xs font-bold text-[#27314c]">Mininet s1 (OVS)</div>
            <div className="text-[10px] font-medium text-[#7a889b]">Hosts: h1, h2, h3</div>
          </div>
        </div>

        <div className="mt-8 px-3 text-[10px] font-bold uppercase tracking-[.17em] text-[#a3aec0]">Navigation</div>
        <nav className="mt-3 space-y-1" aria-label="Main navigation">
          {nav.map(item => (
            <a 
              key={item.label} 
              href={`#${item.target}`} 
              onClick={() => { setActiveNav(item.label); setMobileMenu(false) }} 
              className={`nav-link flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-semibold ${activeNav === item.label ? 'nav-active text-[#5365e5]' : 'text-[#7c889d] hover:bg-white/65 hover:text-[#344262]'}`}
            >
              <Icon name={item.icon} size={18}/>
              {item.label}
              {item.label === 'Blocked threats' && data && (
                <span className="ml-auto rounded-md bg-[#fff0ed] px-1.5 py-0.5 text-[10px] font-bold text-[#e27667]">
                  {data.threats.length}
                </span>
              )}
            </a>
          ))}
        </nav>

        {/* Controller Status card */}
        <div className="mt-auto px-1">
          <div className="relative overflow-hidden rounded-[18px] border border-[#e1e7ff] bg-gradient-to-br from-[#edf0ff] to-[#f7f8ff] p-4">
            <div className="relative flex h-8 w-8 items-center justify-center rounded-lg bg-white text-[#6574e9]">
              <Icon name="layers" size={17}/>
            </div>
            <div className="mt-3 text-[12px] font-bold text-[#293555]">Ryu SDN Controller</div>
            <p className="mt-1 text-[10px] leading-relaxed text-[#7c8a9e]">
              Connected to OpenFlow switch at port 6653. Flow polling active every 1.5 seconds.
            </p>
            <div className="mt-3 flex items-center gap-1.5 text-[10px] font-bold text-[#35ad87]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#45c397]"/>
              {source === 'live' ? 'Connected: 192.168.8.147' : 'Simulation Mode'}
            </div>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="relative min-h-screen lg:pl-[250px]">
        {/* Header */}
        <header className="topbar-glass elevation-dropdown sticky top-0 flex min-h-[76px] flex-wrap items-center justify-between gap-3 border-b border-white/75 px-5 py-3 sm:px-8 xl:px-10">
          <div className="flex items-center gap-3">
            <button className="rounded-lg p-1 text-[#364260] lg:hidden" aria-label="Open menu" onClick={() => setMobileMenu(true)}>
              <Icon name="grid" size={21}/>
            </button>
            <span className="hidden text-xs font-semibold text-[#8c98ac] sm:inline">Controller Telemetry <span className="mx-2 text-[#cbd3df]">/</span></span>
            <span className="text-xs font-bold text-[#2b3754]">Mininet Flow Monitor</span>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <span className="hidden rounded-full border border-[#e1e6f0] bg-white/70 px-3 py-1.5 text-[10px] font-bold uppercase tracking-[.1em] text-[#7d8b9f] sm:inline">
              Read-Only
            </span>
            <div className="flex items-center rounded-lg border border-[#e1e6f0] bg-white/75 p-0.5 text-[11px] font-bold">
              <button onClick={() => setSource('demo')} aria-pressed={source === 'demo'} className={`rounded-md px-2.5 py-1.5 ${source === 'demo' ? 'bg-[#e9edff] text-[#5365d8]' : 'text-[#8995a9]'}`}>
                Demo
              </button>
              <button onClick={() => { setSource('live'); setStreaming(true) }} disabled={!endpoint} title={!endpoint ? 'Configure VITE_DEFENSE_API_URL in .env to connect' : 'Connect to live Ryu/Flask backend'} aria-pressed={source === 'live'} className={`rounded-md px-2.5 py-1.5 ${source === 'live' ? 'bg-[#e9edff] text-[#5365d8]' : 'text-[#8995a9]'}`}>
                Live
              </button>
            </div>
            <button 
              onClick={() => setScenario(scenario === 'attack' ? 'normal' : 'attack')} 
              disabled={source === 'live'} 
              title={source === 'live' ? 'In Live mode, run attack_traffic.sh in Mininet' : undefined} 
              className={`flex items-center gap-1.5 rounded-lg px-3 py-2 text-[11px] font-bold text-white ${scenario === 'attack' && source === 'demo' ? 'bg-[#d96f69]' : 'bg-[#5b6de9]'}`}
            >
              <Icon name={scenario === 'attack' && source === 'demo' ? 'pause' : 'play'} size={14}/>
              {scenario === 'attack' && source === 'demo' ? 'End simulation' : 'Simulate attack'}
            </button>
          </div>
        </header>

        {/* Main Body */}
        <main className="mx-auto max-w-[1740px] px-5 pb-12 pt-8 sm:px-8 xl:px-10" id="overview">
          {/* Hero Section */}
          <div className="flex flex-wrap items-end justify-between gap-5">
            <div>
              <div className="mb-2.5 flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.2em] text-[#6e7ea0]">
                <span className="h-1.5 w-1.5 rounded-full bg-[#6575ec]"/> Software-Defined Networking Defense
              </div>
              <h1 className="max-w-[740px] text-[clamp(2.4rem,4vw,4.2rem)] font-extrabold leading-[1.04] tracking-[-.065em] text-[#192440]">
                SDN Volumetric <span className="text-[#6475e9]">Defense Console.</span>
              </h1>
              <p className="mt-3 max-w-[580px] text-xs font-medium leading-relaxed tracking-[-.01em] text-[#7c889c]">
                Real-time OpenFlow 1.3 flow rate telemetry, automated rate anomaly classification, and line-rate OVS switch mitigation.
              </p>
            </div>

            <div className="flex flex-col items-end gap-2">
              <span className="flex items-center gap-2 rounded-full border border-[#e1e6f0] bg-white/70 px-3 py-2 text-[11px] font-bold text-[#62718a]">
                <span className={`h-1.5 w-1.5 rounded-full ${source === 'demo' ? 'bg-[#6c7dea]' : 'bg-[#35bd8b]'}`}/>
                {source === 'demo' ? 'SIMULATED TELEMETRY' : 'LIVE BACKEND TELEMETRY'}
              </span>
              {source === 'demo' && (
                <label className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[.12em] text-[#8c99ae]">
                  State Preset: 
                  <select value={scenario} onChange={event => setScenario(event.target.value as typeof scenario)} className="rounded-lg border border-[#e0e5ef] bg-white/80 px-2 py-1 text-[11px] font-bold normal-case tracking-normal text-[#53617c]">
                    <option value="normal">Normal Baseline (iperf)</option>
                    <option value="attack">DDoS Flood (hping3)</option>
                    <option value="empty">Day Zero</option>
                    <option value="loading">Loading State</option>
                    <option value="error">Error State</option>
                  </select>
                </label>
              )}
            </div>
          </div>

          {loading ? (
            <LoadingDashboard/>
          ) : failed ? (
            <div role="alert" className="glass-panel elevation-card mt-8 flex min-h-[360px] flex-col items-center justify-center rounded-[22px] p-8 text-center">
              <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#fff0ed] text-[#d97870]">
                <Icon name="alert" size={26}/>
              </div>
              <h2 className="text-2xl font-extrabold tracking-[-.05em] text-[#25304a]">Unable to connect to controller.</h2>
              <p className="mt-3 max-w-[430px] text-xs leading-relaxed text-[#7c899e]">{error}</p>
              <div className="mt-6 flex gap-2">
                <button onClick={retryRequest} className="flex items-center gap-2 rounded-lg bg-[#5b6de9] px-4 py-2.5 text-xs font-bold text-white">
                  <Icon name="refresh" size={15}/>Retry Connection
                </button>
                {source === 'live' && (
                  <button onClick={() => setSource('demo')} className="rounded-lg border border-[#dce3ef] bg-white px-4 py-2.5 text-xs font-bold text-[#63718b]">
                    View Demo Simulation
                  </button>
                )}
              </div>
            </div>
          ) : data && (
            <>
              {/* Metrics Grid */}
              <section id="metrics" className="mt-9 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-[1.04fr_1fr_1fr] xl:grid-rows-2">
                {/* System Health Card */}
                <div className="health-card elevation-card relative flex min-h-[260px] flex-col rounded-[22px] p-6 text-white md:col-span-2 xl:col-span-1 xl:row-span-2 xl:p-7">
                  <div className="health-orb"/>
                  <div className="relative z-10 flex items-center justify-between">
                    <span className="text-[10px] font-bold tracking-[.16em] text-white/60">CONTROLLER HEALTH & STATE</span>
                    <Icon name="shield" size={19}/>
                  </div>
                  <div className="relative z-10 mt-auto pt-10">
                    <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl border border-white/20 bg-white/10 backdrop-blur-md">
                      <Icon name={data.health === 'degraded' ? 'alert' : 'check'} size={29}/>
                    </div>
                    <div className="text-[26px] font-extrabold leading-tight tracking-[-.05em]">
                      {empty ? 'Awaiting Flow Data' : data.health === 'degraded' ? 'Volumetric DDoS Detected' : 'OVS s1 Operating Normally'}
                    </div>
                    <p className="mt-2 max-w-[280px] text-xs leading-relaxed text-[#b8c5e0]">
                      {empty 
                        ? 'Mininet network is not yet sending flow packets.' 
                        : data.health === 'degraded' 
                        ? 'High-rate flood detected. Priority 65535 DROP rule installed on switch s1.' 
                        : 'Switch s1 connected to Ryu (TCP :6653). Flow stats polled every 1.5 seconds.'}
                    </p>
                    <div className="mt-6 flex items-center justify-between border-t border-white/15 pt-4 text-[11px]">
                      <span className="flex items-center gap-2 font-semibold">
                        <span className={`h-2 w-2 rounded-full ${data.health === 'degraded' ? 'bg-[#ff7b6b] animate-ping' : 'bg-[#64e0b5]'}`}/>
                        {data.health === 'degraded' ? 'Mitigation Active (DROP)' : 'Forwarding Normal'}
                      </span>
                      <span className="font-medium text-white/70">{data.endpointsOnline}/{data.endpointsTotal} Mininet Nodes</span>
                    </div>
                  </div>
                </div>

                {/* Real Packet Rate Metrics */}
                <MetricCard 
                  icon="activity" 
                  accent="bg-[#e9edff] text-[#6978ed]" 
                  label="Current Traffic Rate" 
                  value={currentPps.toLocaleString()} 
                  unit="PPS" 
                  detail="Aggregate packets/second across all switch ports"
                />
                <MetricCard 
                  icon="zap" 
                  accent="bg-[#fff0ed] text-[#ee8a76]" 
                  label="Peak Rate (Window)" 
                  value={peakPps.toLocaleString()} 
                  unit="PPS" 
                  detail="Highest volume spike in recent telemetry window"
                />
                <MetricCard 
                  icon="layers" 
                  accent="bg-[#e7f8f3] text-[#3cbd9b]" 
                  label="Active OpenFlow Rules" 
                  value={data.metrics.activeRules.toLocaleString()} 
                  unit="Rules" 
                  detail="Flow entries in OVS s1 (Forwarding + Mitigation DROP)"
                />
                <MetricCard 
                  icon="clock" 
                  accent="bg-[#fff3e5] text-[#e9ad5e]" 
                  label="Inference Latency" 
                  value={data.metrics.mlLatencyMs.toFixed(1)} 
                  unit="ms" 
                  detail="Average feature extraction & classification cycle"
                />
              </section>

              {/* Chart Section */}
              <section id="traffic" className="glass-panel elevation-card mt-5 rounded-[22px] px-5 pb-6 pt-6 sm:px-7">
                <div className="flex flex-wrap items-start justify-between gap-5">
                  <div>
                    <div className="flex items-center gap-2.5">
                      <h2 className="text-lg font-bold tracking-[-.04em] text-[#25304a]">Real-Time Traffic Telemetry</h2>
                      <span className="flex items-center gap-1.5 rounded-md bg-[#eaf8f2] px-2 py-1 text-[10px] font-bold text-[#35ae83]">
                        <span className={`h-1.5 w-1.5 rounded-full bg-[#3bc38d] ${streaming ? 'live-dot' : ''}`}/>
                        {streaming ? 'LIVE STREAMING' : 'PAUSED'}
                      </span>
                    </div>
                    <p className="mt-1.5 text-[11px] text-[#8694a7]">
                      Ingress vs. Dropped packets on OVS s1 · 48-second sliding window
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-3 text-[11px] font-semibold text-[#738096]">
                      <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-[#6575ea]"/>Ingress Rate</span>
                      <span className="flex items-center gap-1.5"><i className="h-2 w-2 rounded-full bg-[#35c0aa]"/>Dropped Packets</span>
                    </div>
                    <span className="rounded-lg border border-[#e5e9f1] bg-[#f5f7fb] px-2.5 py-1 text-[10px] font-bold text-[#6a7a92]">
                      Window: 48s @ 1.5s Ryu Polling
                    </span>
                    <button 
                      onClick={() => setStreaming(!streaming)} 
                      aria-label={streaming ? 'Pause live stream' : 'Resume live stream'} 
                      className="flex h-8 w-8 items-center justify-center rounded-lg border border-[#e3e8f0] bg-white/80 text-[#7f8aa0]"
                    >
                      <Icon name={streaming ? 'pause' : 'play'} size={14}/>
                    </button>
                  </div>
                </div>

                {data.traffic.ingress.length > 1 ? (
                  <TrafficChart traffic={data.traffic} tick={source === 'demo' ? tick : 0}/>
                ) : (
                  <EmptyPanel title="No traffic telemetry yet" description="Traffic will graph as packets flow between Mininet hosts."/>
                )}

                <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-[#edf0f5] pt-5">
                  <span className="flex items-center gap-2 text-[11px] text-[#7e8ca1]">
                    <Icon name="crosshair" size={15} className="text-[#e29b85]"/>
                    Volumetric anomaly threshold: <strong className="text-[#40506c]">{data.traffic.threshold}.0k PPS</strong> (breach triggers automated drop)
                  </span>
                  <span className="text-[11px] font-medium text-[#9aa6b7]">
                    {streaming ? 'Refreshes every second via Flask REST API' : 'Updates paused'}
                  </span>
                </div>
              </section>

              {/* Defense Pipeline & Mitigation Policy */}
              <div id="pipeline" className="mt-5 grid gap-5 xl:grid-cols-[1.3fr_1fr]">
                {/* Autonomous Defense Loop Panel */}
                <div className="relative flex min-h-[220px] flex-col justify-between overflow-hidden rounded-[22px] border border-[#dce4f9] bg-[#eef3fe] p-6 sm:p-7">
                  <div className="relative">
                    <div className="flex items-center gap-2 text-[10px] font-extrabold uppercase tracking-[.18em] text-[#5569a2]">
                      <Icon name="layers" size={14}/> Autonomous Mitigation Loop
                    </div>
                    <div className="mt-2.5 text-[18px] font-extrabold tracking-[-.04em] text-[#22335f]">
                      SDN Closed-Loop Control Architecture
                    </div>
                    <div className="mt-4 space-y-2.5 text-[11px] text-[#4d5f8a]">
                      <div className="flex items-start gap-2.5">
                        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#5b6de9] text-[9px] font-bold text-white">1</span>
                        <span><strong>Telemetry Collection:</strong> Ryu polls switch <code>s1</code> every 1.5s using <code>OFPFlowStatsRequest</code>.</span>
                      </div>
                      <div className="flex items-start gap-2.5">
                        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#5b6de9] text-[9px] font-bold text-white">2</span>
                        <span><strong>Rate Anomaly Classifier:</strong> Ingress rates &gt; 8,000 PPS are flagged as volumetric DDoS attack.</span>
                      </div>
                      <div className="flex items-start gap-2.5">
                        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#5b6de9] text-[9px] font-bold text-white">3</span>
                        <span><strong>Line-Rate Mitigation:</strong> Installs high-priority (65535) <code>OFPFlowMod</code> DROP rule on <code>s1</code>.</span>
                      </div>
                      <div className="flex items-start gap-2.5">
                        <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[#5b6de9] text-[9px] font-bold text-white">4</span>
                        <span><strong>Traffic Preservation:</strong> Legitimate packets from <code>h1</code> (10.0.0.1) continue forwarding uninterrupted.</span>
                      </div>
                    </div>
                  </div>
                  <div className="mt-4 border-t border-[#d8e2f8] pt-3 text-[10px] font-semibold text-[#6e80ad]">
                    Enforced at Open vSwitch Datapath Level (s1)
                  </div>
                </div>

                {/* Mitigation Policy Breakdown */}
                <section className="glass-panel elevation-card rounded-[22px] p-6 sm:p-7" aria-label="Mitigation Policy Breakdown">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <div className="text-[10px] font-extrabold uppercase tracking-[.18em] text-[#7e8ca1]">Policy Distribution</div>
                      <h2 className="mt-2 text-xl font-extrabold tracking-[-.04em] text-[#25304a]">Mitigation Criteria</h2>
                      <p className="mt-1 text-[11px] leading-relaxed text-[#8795a7]">
                        Enforcement breakdown reported by Ryu controller
                      </p>
                    </div>
                    <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#fff0ed] text-[#e78a7a]">
                      <Icon name="shield" size={19}/>
                    </div>
                  </div>

                  {data.dropReasons.length ? (
                    <div className="mt-7 grid gap-4 sm:grid-cols-3">
                      {data.dropReasons.map((reason, i) => (
                        <div key={reason.reason} className="min-w-0">
                          <div className="text-[26px] font-extrabold tracking-[-.07em] text-[#25304a]">
                            {reason.share}<span className="text-sm text-[#9ca8ba]">%</span>
                          </div>
                          <div className="mt-2 h-1 overflow-hidden rounded-full bg-[#edf0f6]">
                            <div className={`h-full rounded-full ${['bg-[#6475ec]','bg-[#36bda9]','bg-[#ecaa76]'][i % 3]}`} style={{ width: `${reason.share}%` }}/>
                          </div>
                          <div className="mt-2 text-[10px] font-semibold leading-tight text-[#748297]">
                            {reason.reason}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <EmptyPanel title="No mitigation active" description="When attack traffic is blocked, enforcement criteria will appear here." icon="shield"/>
                  )}
                </section>
              </div>

              {/* Blocked Threats Table */}
              <section id="threats" className="glass-panel elevation-card mt-5 overflow-hidden rounded-[22px]">
                <div className="flex flex-wrap items-center justify-between gap-4 px-5 py-6 sm:px-7">
                  <div>
                    <h2 className="text-lg font-bold tracking-[-.04em] text-[#25304a]">
                      Blocked Attack Sources 
                      <span className="ml-1.5 rounded-md bg-[#fff0ed] px-2 py-1 align-middle text-[10px] font-bold text-[#e47b70]">
                        {data.threats.length} Active DROP Rule{data.threats.length === 1 ? '' : 's'}
                      </span>
                    </h2>
                    <p className="mt-1.5 text-[11px] text-[#8694a7]">
                      Proactive line-rate DROP rules installed on switch s1 via Ryu OpenFlow controller
                    </p>
                  </div>

                  <div className="flex w-full flex-wrap gap-2 sm:w-auto">
                    <div className="flex h-9 min-w-[175px] flex-1 items-center gap-2 rounded-lg border border-[#e4e9f0] bg-white/75 px-3 text-[#9aa6b6] sm:flex-none">
                      <Icon name="search" size={15}/>
                      <input 
                        value={search} 
                        onChange={event => setSearch(event.target.value)} 
                        placeholder="Search IP or node..." 
                        aria-label="Search blocked threats" 
                        className="w-full bg-transparent text-[11px] text-[#3b4967] outline-none placeholder:text-[#a9b3c1] sm:w-[130px]"
                      />
                    </div>
                    <div className="relative flex h-9 items-center rounded-lg border border-[#e4e9f0] bg-white/75 px-2.5 text-[#8793a7]">
                      <Icon name="filter" size={15}/>
                      <select 
                        aria-label="Filter by severity" 
                        value={severity} 
                        onChange={event => setSeverity(event.target.value)} 
                        className="max-w-[95px] cursor-pointer appearance-none bg-transparent pl-1.5 pr-3 text-[11px] font-semibold text-[#64718a] outline-none"
                      >
                        <option>All severity</option>
                        <option>Critical</option>
                        <option>High</option>
                        <option>Medium</option>
                      </select>
                      <Icon name="chevron" size={12} className="pointer-events-none absolute right-2"/>
                    </div>
                    <button 
                      disabled={!rows.length} 
                      onClick={() => exportCsv(rows)} 
                      className="flex h-9 items-center gap-1.5 rounded-lg border border-[#e4e9f0] bg-white/75 px-3 text-[11px] font-bold text-[#556480] hover:bg-white"
                    >
                      <Icon name="download" size={14}/>Export CSV
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full min-w-[800px] border-collapse text-left">
                    <thead>
                      <tr className="border-y border-[#eef1f6] bg-[#f8f9fc]/60 text-[10px] font-bold uppercase tracking-[.08em] text-[#8694a8]">
                        <th className="py-3.5 pl-7">Source IP & Node</th>
                        <th className="py-3.5">Target Port / Protocol</th>
                        <th className="py-3.5">Mitigation Trigger</th>
                        <th className="py-3.5">ML Score</th>
                        <th className="py-3.5">Severity</th>
                        <th className="py-3.5 pr-7 text-right">Rule Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((row, i) => (
                        <tr key={`${row.ip}-${i}`} className="border-b border-[#f0f2f6] text-[11px] hover:bg-white/65 last:border-0">
                          <td className="py-3.5 pl-7">
                            <div className="font-bold text-[#2d3a54]">{row.ip}</div>
                            <div className="mt-0.5 text-[10px] font-medium text-[#7d8c9e]">{row.country}</div>
                          </td>
                          <td className="py-3.5">
                            <span className="font-bold text-[#45526c]">{row.port}</span>
                            <span className="ml-2 rounded bg-[#f0f3f8] px-1.5 py-0.5 text-[9px] font-bold text-[#768499]">{row.protocol}</span>
                          </td>
                          <td className="py-3.5 font-medium text-[#5f6d84]">{row.reason}</td>
                          <td className="py-3.5">
                            <div className="flex items-center gap-2">
                              <span className="w-7 font-bold text-[#2d3a54]">{row.score}%</span>
                              <span className="h-1.5 w-16 overflow-hidden rounded-full bg-[#edf0f5]">
                                <span className={`block h-full rounded-full ${row.score >= 90 ? 'bg-[#ef8b7c]' : 'bg-[#eeb66a]'}`} style={{ width: `${row.score}%` }}/>
                              </span>
                            </div>
                          </td>
                          <td className="py-3.5">
                            <span className={`inline-flex rounded-md px-2 py-0.5 text-[10px] font-bold ${row.severity === 'Critical' ? 'bg-[#fff0ee] text-[#e6746b]' : 'bg-[#fff5e7] text-[#dc9a50]'}`}>
                              {row.severity}
                            </span>
                          </td>
                          <td className="py-3.5 pr-7 text-right">
                            <span className="inline-flex items-center gap-1.5 rounded-md bg-[#edf8f3] px-2 py-0.5 text-[10px] font-bold text-[#27986f]">
                              <span className="h-1.5 w-1.5 rounded-full bg-[#32ba88]"/>
                              DROP Active (Priority 65535)
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!rows.length && (
                    <EmptyPanel 
                      title={data.threats.length ? 'No matching records' : 'No flow DROP rules active'} 
                      description={data.threats.length ? 'Adjust your search or filter.' : 'When Ryu identifies a DDoS flood, attacker IPs will be listed here with active DROP rules.'} 
                      icon="shield"
                    />
                  )}
                </div>

                <div className="flex items-center justify-between border-t border-[#eef1f6] px-7 py-4 text-[11px] text-[#8e9aa9]">
                  <span>Showing {rows.length} of {data.threats.length} enforced rules</span>
                  <span>{source === 'demo' ? 'Simulation Environment' : 'Live OVS Telemetry'}</span>
                </div>
              </section>
            </>
          )}

          {/* Academic Footer */}
          <footer className="mt-8 flex flex-wrap items-center justify-between gap-3 border-t border-[#e2e7f0] px-1 pt-6 text-[11px] text-[#7d8c9e]">
            <div>
              <strong>SDN-Based DDoS Detection & Mitigation System</strong> · Ryu Controller & Open vSwitch
            </div>
            <div>
              Academic Demonstration Console · {source === 'demo' ? 'Simulated Preset' : 'Ubuntu VM Live: 192.168.8.147'}
            </div>
          </footer>
        </main>
      </div>
    </div>
  )
}
