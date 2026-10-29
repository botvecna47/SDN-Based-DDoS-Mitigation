import { useEffect, useState, useRef } from 'react'
import type { ReactNode } from 'react'
import { demoSnapshot, endpoint, fetchSnapshot } from './data'
import type { Snapshot, Threat } from './data'

type IconName = 
  | 'shield' 
  | 'activity' 
  | 'zap' 
  | 'clock' 
  | 'filter' 
  | 'search' 
  | 'download' 
  | 'refresh' 
  | 'alert' 
  | 'check' 
  | 'pause' 
  | 'play' 
  | 'close' 
  | 'menu'
  | 'trash'

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
    trash: <><path d="M3 6h18" /><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" /><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" /></>,
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

const timelineLabels = ['-48s', '-40s', '-32s', '-24s', '-16s', '-8s']

function smoothPath(values: number[], ceiling: number) {
  if (values.length < 2) return ''
  const points = values.map((value, i) => ({
    x: 45 + i * (935 / (values.length - 1)),
    y: 220 - Math.min(1, Math.max(0, value) / ceiling) * 190
  }))
  return points.reduce((path, point, i) => {
    if (!i) return `M ${point.x} ${point.y}`
    const previous = points[i - 1]
    const middle = (previous.x + point.x) / 2
    return `${path} C ${middle} ${previous.y}, ${middle} ${point.y}, ${point.x} ${point.y}`
  }, '')
}

function TrafficChart({ 
  traffic, 
  source 
}: { 
  traffic: Snapshot['traffic']
  source: 'demo' | 'live' 
}) {
  const [hover, setHover] = useState<number | null>(null)
  const ingress = traffic.ingress || []
  const dropped = traffic.dropped || []
  // Clean forwarded traffic = Incoming minus Dropped (never negative)
  const forwarded = ingress.map((ing, i) => Math.max(0, Number((ing - (dropped[i] || 0)).toFixed(2))))

  if (ingress.length < 2) {
    return (
      <div className="py-20 text-center text-sm font-medium text-slate-400">
        Awaiting telemetry packets from switch...
      </div>
    )
  }

  const maxVal = Math.max(traffic.threshold, ...ingress, ...dropped)
  // Stepped, stable ceiling: locks at 12k during normal, steps stably to 28k during attack
  // Eliminates vertical bouncing and visual jitter
  const ceiling = maxVal > 9 ? 28 : 12
  const ingressPath = smoothPath(ingress, ceiling)
  const droppedPath = smoothPath(dropped, ceiling)
  const forwardedPath = smoothPath(forwarded, ceiling)

  const activeHover = hover === null ? null : Math.min(hover, ingress.length - 1)
  const x = activeHover === null ? 0 : 45 + activeHover * (935 / (ingress.length - 1))
  const y = activeHover === null ? 0 : 220 - Math.min(1, Math.max(0, ingress[activeHover] || 0) / ceiling) * 190

  const hoverIngressPps = activeHover !== null ? Math.round((ingress[activeHover] || 0) * 1000) : 0
  const hoverDroppedPps = activeHover !== null ? Math.round((dropped[activeHover] || 0) * 1000) : 0
  const hoverForwardedPps = activeHover !== null ? Math.round((forwarded[activeHover] || 0) * 1000) : 0
  const hoverDropPercent = hoverIngressPps > 0 ? ((hoverDroppedPps / hoverIngressPps) * 100).toFixed(1) : '0.0'

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
              <stop offset="0%" stopColor="#e11d48" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#e11d48" stopOpacity="0.0" />
            </linearGradient>
          </defs>
          
          {/* Background Grid Lines & Y-Axis Labels */}
          {[0, 0.25, 0.5, 0.75, 1].map(fraction => (
            <g key={fraction}>
              <line x1="45" x2="980" y1={220 - fraction * 190} y2={220 - fraction * 190} stroke="#f1f5f9" strokeWidth="1.2" />
              <text x="0" y={224 - fraction * 190} fill="#94a3b8" fontSize="12" className="mono">{Math.round(fraction * ceiling)}k</text>
            </g>
          ))}

          {/* Anomaly Limit Threshold Line */}
          <line 
            x1="45" 
            x2="980" 
            y1={220 - traffic.threshold / ceiling * 190} 
            y2={220 - traffic.threshold / ceiling * 190} 
            stroke="#f97316" 
            strokeWidth="1.5" 
            strokeDasharray="5 5" 
          />

          {/* 1. Dropped Area Fill & Line (Rose/Red) */}
          <path d={`${droppedPath} L 980 220 L 45 220 Z`} fill="url(#droppedFill)" />
          <path d={droppedPath} fill="none" stroke="#e11d48" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />

          {/* 2. Total Ingress Area Fill & Line (Blue) */}
          <path d={`${ingressPath} L 980 220 L 45 220 Z`} fill="url(#ingressFill)" />
          <path d={ingressPath} fill="none" stroke="#2563eb" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />

          {/* 3. Clean Forwarded Line (Green) */}
          <path d={forwardedPath} fill="none" stroke="#10b981" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />

          {/* Interactive Inspection Cursor */}
          {activeHover !== null && (
            <>
              <line x1={x} x2={x} y1="20" y2="220" stroke="#94a3b8" strokeDasharray="3 3" />
              <circle cx={x} cy={y} r="5" fill="#2563eb" stroke="#ffffff" strokeWidth="2.5" />
            </>
          )}
        </svg>

        {/* Enhanced Multi-Metric Tooltip */}
        {activeHover !== null && (
          <div 
            className="pointer-events-none absolute z-30 rounded-xl border border-slate-700 bg-slate-900/95 p-3.5 text-sm text-white shadow-2xl backdrop-blur-sm"
            style={{ 
              left: `${Math.min(80, Math.max(16, (x / 1000) * 100))}%`, 
              top: `${Math.max(8, Math.min(65, (y / 250) * 100))}%`, 
              transform: 'translate(-50%, -100%)' 
            }}
          >
            <div className="flex items-center justify-between border-b border-slate-700/80 pb-1.5 text-xs text-slate-400">
              <span className="mono">{ingress.length - 1 - activeHover}s ago</span>
              <span className="font-semibold text-slate-300">{source === 'demo' ? 'Simulation Step' : 'Switch s1 Telemetry'}</span>
            </div>
            <div className="mt-2.5 space-y-1.5 text-xs sm:text-sm">
              <div className="flex items-center justify-between gap-5">
                <span className="flex items-center gap-1.5 text-blue-400 font-medium">
                  <span className="h-2 w-2 rounded-full bg-blue-500" /> Total Incoming:
                </span>
                <span className="font-bold mono text-white">{hoverIngressPps.toLocaleString()} pkts/s</span>
              </div>
              <div className="flex items-center justify-between gap-5">
                <span className="flex items-center gap-1.5 text-rose-400 font-medium">
                  <span className="h-2 w-2 rounded-full bg-rose-500" /> Blocked / Dropped:
                </span>
                <span className="font-bold mono text-rose-300">{hoverDroppedPps.toLocaleString()} pkts/s</span>
              </div>
              <div className="flex items-center justify-between gap-5">
                <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                  <span className="h-2 w-2 rounded-full bg-emerald-500" /> Clean Forwarded:
                </span>
                <span className="font-bold mono text-emerald-300">{hoverForwardedPps.toLocaleString()} pkts/s</span>
              </div>
              {hoverDroppedPps > 0 && (
                <div className="mt-1.5 border-t border-slate-700/60 pt-1.5 flex items-center justify-between text-xs text-slate-300">
                  <span>Mitigation Efficiency:</span>
                  <span className="font-bold text-rose-400 mono">{hoverDropPercent}% dropped</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Timeline Labels */}
      <div className="ml-[4.5%] flex justify-between pt-3 text-xs sm:text-sm font-medium text-slate-500 mono">
        {timelineLabels.map((label, idx) => (
          <span key={label} className={idx % 2 === 1 ? 'hidden sm:inline' : ''}>{label}</span>
        ))}
        <span className="text-slate-700 font-bold">{source === 'demo' ? 'Preview (Now)' : 'Live Switch (Now)'}</span>
      </div>
    </div>
  )
}

function MetricCard({ 
  label, 
  value, 
  unit, 
  detail,
  badge,
  badgeType = 'neutral'
}: { 
  label: string
  value: string
  unit?: string
  detail: string
  badge?: string
  badgeType?: 'danger' | 'success' | 'warning' | 'neutral'
}) {
  const badgeStyles = {
    danger: 'bg-rose-100 text-rose-800 border-rose-200',
    success: 'bg-emerald-100 text-emerald-800 border-emerald-200',
    warning: 'bg-amber-100 text-amber-800 border-amber-200',
    neutral: 'bg-slate-100 text-slate-700 border-slate-200'
  }

  return (
    <div className="panel-card p-6 sm:p-7 flex flex-col justify-between">
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500">{label}</div>
        {badge && (
          <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold border ${badgeStyles[badgeType]}`}>
            {badge}
          </span>
        )}
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 mono">{value}</span>
        {unit && <span className="text-sm font-semibold text-slate-500">{unit}</span>}
      </div>
      <div className="mt-3 text-xs sm:text-sm text-slate-500 leading-normal">{detail}</div>
    </div>
  )
}

function exportCsv(rows: Threat[]) {
  const fields = ['Source IP', 'Host Node', 'Target', 'Protocol', 'Reason', 'Rule Priority', 'Status']
  const csv = [
    fields,
    ...rows.map(row => [
      row.ip,
      row.country,
      row.target || '10.0.0.3:80',
      row.protocol,
      row.reason,
      65535,
      row.status || 'Blocked'
    ])
  ].map(row => row.map(value => `"${String(value).replace(/"/g, '""')}"`).join(',')).join('\n')

  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `sdn-ddos-threat-log-${Date.now()}.csv`
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

type DemoMode = 'normal' | 'attack' | 'idle' | 'loading' | 'error'

export default function App() {
  const [source, setSource] = useState<'demo' | 'live'>('demo')
  const [demoMode, setDemoMode] = useState<DemoMode>('normal')
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [loadState, setLoadState] = useState<'loading' | 'ready' | 'error'>('ready')
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const [streaming, setStreaming] = useState(true)
  const [search, setSearch] = useState('')
  const [severity, setSeverity] = useState('All severity')
  const [activeNav, setActiveNav] = useState('Overview')
  const [mobileMenu, setMobileMenu] = useState(false)

  // Has an attack occurred that installed a retained drop rule?
  const [hasDemoRetainedThreat, setHasDemoRetainedThreat] = useState(false)
  
  // Continuous 48-entry sliding buffer - NEVER wiped on mode switch!
  const [demoTraffic, setDemoTraffic] = useState<{ ingress: number[]; dropped: number[] }>(() => {
    const init = Array.from({ length: 48 }, (_, i) => 
      Number((0.82 + Math.sin(i * 0.4) * 0.05).toFixed(2))
    )
    return { ingress: init, dropped: new Array(48).fill(0) }
  })

  // Ref to demoMode so the interval tick reads the latest mode without tearing down the timer
  const demoModeRef = useRef<DemoMode>(demoMode)
  useEffect(() => {
    demoModeRef.current = demoMode
  }, [demoMode])

  const isDemoAttacking = demoMode === 'attack'

  const targetHost = (() => {
    try {
      return new URL(endpoint).host
    } catch {
      return 'VM address not configured'
    }
  })()

  // 1-Second Continuous Live Streaming Loop
  useEffect(() => {
    if (!streaming) return

    const interval = window.setInterval(() => {
      if (source === 'live') {
        setRetry(value => value + 1)
      } else {
        const mode = demoModeRef.current
        if (mode === 'loading' || mode === 'error') return

        const now = Date.now() / 1000
        let nextIngress = 0
        let nextDropped = 0

        if (mode === 'idle') {
          nextIngress = 0
          nextDropped = 0
        } else if (mode === 'attack') {
          // Attack traffic surges in real time into ~22k-26k PPS
          const base = 23.4 + Math.sin(now * 0.8) * 1.6 + (Math.random() * 0.8 - 0.4)
          nextIngress = Number(Math.max(18.0, base).toFixed(2))
          // 96.5% of attack traffic dropped by OpenFlow 65535 rule; ~820 pkts/s clean traffic continues to pass
          nextDropped = Number((nextIngress * 0.965).toFixed(2))
        } else {
          // Normal traffic: steady ~750-900 pkts/s baseline
          const base = 0.82 + Math.sin(now * 0.4) * 0.06 + (Math.random() * 0.04 - 0.02)
          nextIngress = Number(Math.max(0.65, base).toFixed(2))
          nextDropped = 0
        }

        // Push new second to right, drop oldest from left (100% continuous, NO BUFFER RESETS!)
        setDemoTraffic(prev => ({
          ingress: [...prev.ingress.slice(1), nextIngress],
          dropped: [...prev.dropped.slice(1), nextDropped],
        }))
      }
    }, 1000)

    return () => window.clearInterval(interval)
  }, [source, streaming])

  // Fetch Live Snapshot from Flask API
  useEffect(() => {
    if (source !== 'live' || !streaming) return
    const controller = new AbortController()
    fetchSnapshot(controller.signal).then(data => {
      setSnapshot(data)
      setLoadState('ready')
      setError('')
    }).catch((cause: unknown) => {
      if (controller.signal.aborted) return
      setError(cause instanceof Error ? cause.message : 'Could not connect to Flask API. Ensure VM is running and VITE_DEFENSE_API_URL is configured.')
      setLoadState('error')
    })
    return () => controller.abort()
  }, [source, retry, streaming])

  // Toggle Attack in Demo Mode (Smoothly ramps without wiping the graph!)
  const toggleDemoAttack = () => {
    if (demoMode === 'attack') {
      // Stop Attack: traffic drops back to normal, but PAST ATTACK PEAK REMAINS on graph!
      setDemoMode('normal')
    } else {
      // Start Attack: traffic surges in from the right edge NOW!
      setDemoMode('attack')
      setHasDemoRetainedThreat(true)
    }
  }

  // Handle Demo Mode Changes (NEVER wipes history; adjusts live incoming stream)
  const handleDemoModeChange = (mode: string) => {
    if (mode === 'reset') {
      resetDemoSimulation()
      return
    }
    if (mode === 'attack') {
      setHasDemoRetainedThreat(true)
    }
    setDemoMode(mode as DemoMode)
  }

  // Explicit Reset for Demo Mode (Only when the user clicks "Clear History")
  const resetDemoSimulation = () => {
    setDemoMode('normal')
    setHasDemoRetainedThreat(false)
    setDemoTraffic({
      ingress: Array.from({ length: 48 }, (_, i) => Number((0.82 + Math.sin(i * 0.4) * 0.05).toFixed(2))),
      dropped: new Array(48).fill(0)
    })
  }

  // Construct Data Object (Live vs Demo)
  const isThreatBlocked = source === 'demo' ? (isDemoAttacking || hasDemoRetainedThreat) : Boolean(snapshot?.threats && snapshot.threats.length > 0)
  
  const data: Snapshot | null = source === 'demo'
    ? demoSnapshot(isDemoAttacking, demoMode === 'idle', demoTraffic.ingress, demoTraffic.dropped, isThreatBlocked)
    : snapshot

  const loading = source === 'demo' ? demoMode === 'loading' : loadState === 'loading'
  const failed = source === 'demo' ? demoMode === 'error' : loadState === 'error'
  const empty = !!data && data.endpointsTotal === 0 && data.traffic.ingress.length === 0 && data.threats.length === 0
  const offline = data?.health === 'offline'
  const underAttack = data?.health === 'degraded'

  // Calculations for current ingress, dropped, and forwarded rates
  const ingressArr = data?.traffic.ingress || []
  const droppedArr = data?.traffic.dropped || []
  const latestIngressK = ingressArr.length ? ingressArr[ingressArr.length - 1] : 0
  const latestDroppedK = droppedArr.length ? droppedArr[droppedArr.length - 1] : 0

  const currentIngressPps = data?.metrics.currentPps !== undefined ? data.metrics.currentPps : Math.round(latestIngressK * 1000)
  const currentDroppedPps = Math.round(latestDroppedK * 1000)
  const currentForwardedPps = Math.max(0, currentIngressPps - currentDroppedPps)
  const dropPercentage = currentIngressPps > 0 ? ((currentDroppedPps / currentIngressPps) * 100).toFixed(1) : '0.0'

  const peakIngressK = ingressArr.length ? Math.max(...ingressArr) : 0
  const peakPps = Math.round(peakIngressK * 1000)
  const noTraffic = source === 'live' && !offline && !underAttack && currentIngressPps === 0 && !data?.threats.length

  // Filtered threats
  const rows = (data?.threats || []).filter(row => 
    (severity === 'All severity' || row.severity === severity) && 
    `${row.ip} ${row.country} ${row.port} ${row.reason}`.toLowerCase().includes(search.toLowerCase())
  )

  const navItems = [
    { label: 'Overview', target: 'overview' },
    { label: 'Live Traffic', target: 'traffic' },
    { label: 'How It Works', target: 'how-it-works' },
    { label: 'Blocked Devices', target: 'threats' },
  ]

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

      {/* Spacious Left Navigation Sidebar */}
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
                <span className="rounded-full bg-rose-100 px-2.5 py-0.5 text-xs font-bold text-rose-700">
                  {data.threats.length}
                </span>
              )}
            </a>
          ))}
        </nav>

        {/* Connection Status Card */}
        <div className="mt-auto rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <span className={`h-2.5 w-2.5 rounded-full ${source === 'live' ? 'bg-emerald-500' : 'bg-blue-500'}`} />
            {source === 'live' ? 'Connected to Controller' : 'Interactive Demo Mode'}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {source === 'live' ? `Host: ${targetHost}` : 'Smooth Continuous Simulation'}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="min-h-screen lg:pl-[265px]">
        {/* Top Header Bar */}
        <header className="sticky top-0 z-20 flex min-h-[70px] items-center justify-between border-b border-slate-200 bg-white/95 px-6 sm:px-10 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button className="rounded p-1.5 text-slate-600 lg:hidden" aria-label="Open menu" onClick={() => setMobileMenu(true)}>
              <Icon name="menu" size={22} />
            </button>
            <span className="text-sm font-medium text-slate-400">Mininet Network <span className="mx-1.5">/</span></span>
            <span className="text-sm font-semibold text-slate-800">SDN Traffic &amp; DDoS Defense</span>
          </div>

          <div className="flex items-center gap-3">
            {/* Live vs Demo Toggle */}
            <div className="flex items-center rounded-lg border border-slate-200 bg-slate-100/90 p-0.5 text-xs sm:text-sm font-medium">
              <button 
                onClick={() => setSource('demo')} 
                className={`rounded-md px-3.5 py-1.5 transition-colors ${source === 'demo' ? 'bg-white text-slate-900 shadow-sm font-semibold' : 'text-slate-500 hover:text-slate-800'}`}
              >
                Demo
              </button>
              <button 
                onClick={() => { setLoadState('loading'); setSource('live'); setStreaming(true) }}
                disabled={!endpoint} 
                className={`rounded-md px-3.5 py-1.5 transition-colors ${source === 'live' ? 'bg-white text-slate-900 shadow-sm font-semibold' : 'text-slate-500 hover:text-slate-800'}`}
              >
                Live
              </button>
            </div>

            {/* Interactive Attack Simulator Button (Demo Mode) */}
            {source === 'demo' && (
              <>
                <button
                  onClick={toggleDemoAttack}
                  className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs sm:text-sm font-semibold shadow-sm transition-all ${
                    isDemoAttacking
                      ? 'bg-rose-600 text-white hover:bg-rose-700 shadow-rose-200'
                      : 'bg-slate-900 text-white hover:bg-slate-800'
                  }`}
                >
                  <Icon name={isDemoAttacking ? 'pause' : 'play'} size={14} />
                  {isDemoAttacking ? 'Stop Attack' : 'Simulate DDoS Attack'}
                </button>

                {hasDemoRetainedThreat && (
                  <button
                    onClick={resetDemoSimulation}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs sm:text-sm font-semibold text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                    title="Clear history and reset to calm baseline"
                  >
                    <Icon name="trash" size={14} />
                    <span>Clear</span>
                  </button>
                )}
              </>
            )}
          </div>
        </header>

        {/* Content Body */}
        <main className="mx-auto max-w-[1600px] px-6 sm:px-10 py-9 sm:py-10" id="overview">
          {/* Main Title Section */}
          <div className="flex flex-wrap items-end justify-between gap-5">
            <div>
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-slate-900">
                Network Traffic &amp; DDoS Defense
              </h1>
              <p className="mt-2.5 text-base sm:text-lg text-slate-600 max-w-3xl leading-relaxed">
                {source === 'demo' 
                  ? 'Interactive simulation of OpenFlow packet monitoring, automatic anomaly detection, and instant traffic mitigation.' 
                  : 'Live telemetry streamed directly from Ryu SDN controller and Open vSwitch switch s1 in Mininet.'}
              </p>
            </div>

            {/* Real-Time Traffic Mode Selector (Demo Mode) */}
            {source === 'demo' && (
              <div className="flex items-center gap-2.5 text-sm text-slate-600">
                <span className="font-medium text-slate-500">Traffic Mode:</span>
                <select 
                  value={demoMode} 
                  onChange={event => handleDemoModeChange(event.target.value)}
                  className="rounded-lg border border-slate-200 bg-white px-3.5 py-1.5 text-sm font-semibold text-slate-800 shadow-sm outline-none hover:bg-slate-50 cursor-pointer"
                >
                  <option value="normal">Normal Baseline (iperf Legitimate)</option>
                  <option value="attack">Under DDoS Attack (UDP Flood)</option>
                  <option value="idle">Network Idle (0 pkts/s)</option>
                  <option value="reset">Clear / Reset History</option>
                  <option value="loading">UI Preview: Loading State</option>
                  <option value="error">UI Preview: Connection Error</option>
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
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-rose-100 text-rose-600">
                <Icon name="alert" size={24} />
              </div>
              <h2 className="mt-4 text-xl font-bold text-slate-900">Could not connect to telemetry API</h2>
              <p className="mx-auto mt-2 max-w-lg text-sm text-slate-600 leading-relaxed">{error}</p>
              <div className="mt-6 flex justify-center gap-3">
                <button onClick={() => { setLoadState('loading'); setRetry(v => v + 1) }} className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-slate-800">
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
              {/* TOP SECTION: Prominent Full-Width Status Banner */}
              <div className={`panel-card mt-8 sm:mt-10 p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 border-l-4 ${
                underAttack
                  ? 'border-l-rose-500 bg-rose-50/50 border-rose-200'
                  : offline
                    ? 'border-l-slate-400 bg-slate-100/60 border-slate-200'
                    : isThreatBlocked
                      ? 'border-l-amber-500 bg-amber-50/50 border-amber-200'
                      : 'border-l-emerald-500 bg-emerald-50/40 border-emerald-200'
              }`}>
                <div>
                  <div className="flex items-center gap-2.5">
                    <span className={`h-3 w-3 rounded-full ${underAttack ? 'bg-rose-500 animate-ping' : offline ? 'bg-slate-400' : isThreatBlocked ? 'bg-amber-500' : 'bg-emerald-500'}`} />
                    <span className={`text-xs sm:text-sm font-bold uppercase tracking-wider ${underAttack ? 'text-rose-700' : offline ? 'text-slate-600' : isThreatBlocked ? 'text-amber-800' : 'text-emerald-700'}`}>
                      {underAttack 
                        ? 'DDoS Attack Detected · Autonomous Mitigation Active' 
                        : offline 
                          ? 'Mininet Switch Offline' 
                          : isThreatBlocked 
                            ? 'Attack Mitigated · OpenFlow Rule Retained' 
                            : noTraffic 
                              ? 'Switch Connected · Idle' 
                              : 'Network Operating Normally'}
                    </span>
                  </div>
                  <h2 className="mt-2 text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                    {underAttack 
                      ? 'Malicious Traffic Intercepted & Being Dropped' 
                      : offline 
                        ? 'Waiting for Ryu and Mininet Telemetry' 
                        : isThreatBlocked 
                          ? 'Attacker Dropped · Legitimate Users Uninterrupted' 
                          : empty || noTraffic 
                            ? 'Waiting for Network Traffic' 
                            : 'All Network Flows Safe & Verified'}
                  </h2>
                  <p className="mt-2 max-w-3xl text-sm sm:text-base text-slate-600 leading-relaxed">
                    {underAttack
                      ? 'High-volume packet flood detected from host h2 (10.0.0.2). Open vSwitch s1 has installed a Priority 65535 DROP rule. Malicious packets are discarded at the switch port while legitimate user h1 traffic continues unaffected.'
                      : isThreatBlocked
                        ? 'The flood has halted. The attacker remains blocked under OpenFlow idle timeout policy to protect the server from renewed bursts.'
                        : offline
                          ? 'The telemetry API is reachable, but no recent OpenFlow statistics are arriving from switch s1. Start Ryu and Mininet to connect live telemetry.'
                          : 'Ryu controller is monitoring switch s1 every second. Traffic from legitimate user host h1 is flowing smoothly to server h3.'}
                  </p>
                </div>

                <div className="flex md:flex-col items-center md:items-end justify-between gap-2.5 border-t md:border-t-0 md:border-l border-slate-200 pt-4 md:pt-0 md:pl-8 shrink-0">
                  <div className="text-xs sm:text-sm font-medium text-slate-500">Switch Defense Policy</div>
                  <div className={`text-sm sm:text-base font-bold px-3.5 py-1.5 rounded-full ${
                    underAttack 
                      ? 'bg-rose-100 text-rose-800' 
                      : offline 
                        ? 'bg-slate-200 text-slate-700' 
                        : isThreatBlocked 
                          ? 'bg-amber-100 text-amber-800' 
                          : 'bg-emerald-100 text-emerald-800'
                  }`}>
                    {underAttack 
                      ? 'ACTIVE DROP (Priority 65535)' 
                      : isThreatBlocked 
                        ? 'RULE RETAINED (Priority 65535)' 
                        : offline 
                          ? 'Waiting for Switch' 
                          : 'Normal Forwarding'}
                  </div>
                  <div className="text-xs sm:text-sm text-slate-500 mt-0.5">
                    {source === 'demo' ? 'Autonomous SDN Controller Simulation' : `${data.endpointsOnline}/${data.endpointsTotal} Switch Telemetry Link`}
                  </div>
                </div>
              </div>

              {/* 4 BALANCED METRIC CARDS: Incoming, Dropped, Clean Forwarded, Defense Engine */}
              <div className="mt-6 sm:mt-7 grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard 
                  label="Total Ingress Rate" 
                  value={currentIngressPps.toLocaleString()} 
                  unit="pkts/s" 
                  badge={underAttack ? 'Surge' : 'Normal'}
                  badgeType={underAttack ? 'danger' : 'success'}
                  detail="Total incoming packet volume reaching switch s1 per second"
                />
                <MetricCard 
                  label="Blocked / Dropped Rate" 
                  value={currentDroppedPps.toLocaleString()} 
                  unit="pkts/s" 
                  badge={currentDroppedPps > 0 ? `${dropPercentage}% Mitigated` : '0% Dropped'}
                  badgeType={currentDroppedPps > 0 ? 'danger' : 'neutral'}
                  detail={currentDroppedPps > 0 ? 'Malicious packets filtered at line-rate by Priority 65535 DROP rule' : 'No packets currently flagged for dropping'}
                />
                <MetricCard 
                  label="Clean Forwarded Traffic" 
                  value={currentForwardedPps.toLocaleString()} 
                  unit="pkts/s" 
                  badge="Protected"
                  badgeType="success"
                  detail="Legitimate packets allowed through switch s1 to destination server h3"
                />
                <MetricCard 
                  label="Defense Engine & Latency"
                  value={`${data.metrics.mlLatencyMs.toFixed(1)}`} 
                  unit="ms" 
                  badge={data.detectionMode === 'machine_learning' ? 'ML Active' : 'PPS Threshold'}
                  badgeType="neutral"
                  detail={data.detectionMode === 'machine_learning' ? 'Random Forest DDoS classifier loaded' : 'Per-flow threshold fallback (>10,000 pkts/s)'}
                />
              </div>

              {/* LIVE TRAFFIC CHART SECTION */}
              <section id="traffic" className="panel-card mt-8 sm:mt-10 p-6 sm:p-8">
                <div className="flex flex-wrap items-center justify-between gap-5 border-b border-slate-100 pb-6">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                        {source === 'demo' ? 'Real-Time Network Traffic Stream' : 'Live Network Traffic Stream'}
                      </h2>
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
                        <span className={`h-2 w-2 rounded-full bg-emerald-500 ${streaming ? 'live-dot' : ''}`} />
                        {streaming ? 'Live Stream Active' : 'Paused'}
                      </span>
                    </div>
                    <p className="mt-1.5 text-sm sm:text-base text-slate-500">
                      Comparing total incoming packets (Ingress) against malicious packets dropped (Blocked) and legitimate packets safely delivered (Clean Forwarded).
                    </p>
                  </div>

                  {/* Real-time Numeric Stat Pills */}
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-1.5 text-xs sm:text-sm font-semibold text-blue-800 border border-blue-200">
                      <span className="h-2.5 w-2.5 rounded-full bg-blue-600" />
                      <span>Incoming:</span>
                      <span className="mono font-bold">{currentIngressPps.toLocaleString()} pkts/s</span>
                    </div>

                    <div className="flex items-center gap-2 rounded-lg bg-rose-50 px-3 py-1.5 text-xs sm:text-sm font-semibold text-rose-800 border border-rose-200">
                      <span className="h-2.5 w-2.5 rounded-full bg-rose-600" />
                      <span>Blocked:</span>
                      <span className="mono font-bold">{currentDroppedPps.toLocaleString()} pkts/s</span>
                    </div>

                    <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3 py-1.5 text-xs sm:text-sm font-semibold text-emerald-800 border border-emerald-200">
                      <span className="h-2.5 w-2.5 rounded-full bg-emerald-600" />
                      <span>Clean Passed:</span>
                      <span className="mono font-bold">{currentForwardedPps.toLocaleString()} pkts/s</span>
                    </div>

                    <button 
                      onClick={() => setStreaming(!streaming)} 
                      aria-label={streaming ? 'Pause graph' : 'Resume graph'} 
                      className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
                      title={streaming ? 'Pause graph' : 'Resume graph'}
                    >
                      <Icon name={streaming ? 'pause' : 'play'} size={15} />
                    </button>
                  </div>
                </div>

                {/* Sub-Legend Row */}
                <div className="mt-4 flex flex-wrap items-center justify-between text-xs sm:text-sm text-slate-500">
                  <div className="flex flex-wrap items-center gap-4">
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-blue-600" /> Total Ingress (Blue)
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-rose-600" /> Blocked Traffic (Red)
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" /> Clean Throughput (Green)
                    </span>
                    <span className="flex items-center gap-1.5">
                      <span className="h-0.5 w-4 bg-orange-400" /> Anomaly Threshold ({Math.round(data.traffic.threshold * 1000).toLocaleString()} pkts/s)
                    </span>
                  </div>
                  <div className="mono font-medium text-slate-400">
                    Peak: {peakPps.toLocaleString()} pkts/s
                  </div>
                </div>

                {data.traffic.ingress.length > 1 ? (
                  <TrafficChart traffic={data.traffic} source={source} />
                ) : (
                  <div className="py-20 text-center text-sm text-slate-400">
                    Awaiting traffic packets from switch...
                  </div>
                )}
              </section>

              {/* HOW IT WORKS & WHY BLOCKED SECTION */}
              <div id="how-it-works" className="mt-8 sm:mt-10 grid grid-cols-1 gap-6 sm:gap-8 lg:grid-cols-2">
                {/* How It Works */}
                <div className="panel-card p-7 sm:p-8">
                  <h3 className="text-lg sm:text-xl font-bold text-slate-900">How Autonomous Defense Works</h3>
                  <p className="mt-1.5 text-sm text-slate-500">Autonomous closed-loop SDN defense lifecycle</p>

                  <div className="mt-6 space-y-5 text-sm sm:text-base text-slate-700 leading-relaxed">
                    <div className="flex items-start gap-4">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white mt-0.5">1</span>
                      <div>
                        <strong className="text-slate-900">Flow Statistics Polling:</strong> The Ryu controller queries OpenFlow 1.3 flow counters on switch s1 every second to calculate real-time packet-per-second (PPS) and byte-per-second (BPS) rates per flow.
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white mt-0.5">2</span>
                      <div>
                        <strong className="text-slate-900">Anomaly Classification:</strong> Observed flows are evaluated by the ML classification pipeline or the robust threshold fallback ({Math.round(data.traffic.threshold * 1000).toLocaleString()} pkts/s) to isolate malicious packet bursts.
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white mt-0.5">3</span>
                      <div>
                        <strong className="text-slate-900">Line-Rate Mitigation:</strong> The controller sends an OpenFlow `OFPFlowMod` message pushing a Priority 65535 DROP rule matching the attacker's source IP (`10.0.0.2`), dropping hostile traffic in hardware while legitimate traffic flows undisturbed.
                      </div>
                    </div>
                  </div>
                </div>

                {/* Why Traffic Was Blocked */}
                <div className="panel-card p-7 sm:p-8">
                  <h3 className="text-lg sm:text-xl font-bold text-slate-900">Detection Trigger Breakdown</h3>
                  <p className="mt-1.5 text-sm text-slate-500">Active rules and heuristics applied to mitigate the attack</p>

                  {data.dropReasons.length ? (
                    <div className="mt-6 space-y-5">
                      {data.dropReasons.map((reason) => (
                        <div key={reason.reason}>
                          <div className="flex justify-between text-sm sm:text-base font-semibold text-slate-700">
                            <span>{reason.reason}</span>
                            <span className="mono">{reason.share}%</span>
                          </div>
                          <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-slate-100">
                            <div className="h-full rounded-full bg-rose-600" style={{ width: `${reason.share}%` }} />
                          </div>
                        </div>
                      ))}
                      <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs sm:text-sm text-slate-600 leading-relaxed">
                        <strong>Policy Action:</strong> Attacking source IP <code>10.0.0.2</code> is blocked from flooding server <code>10.0.0.3</code>. Normal forwarding rule for legitimate host <code>10.0.0.1</code> remains active with Priority 1.
                      </div>
                    </div>
                  ) : (
                    <div className="py-16 text-center text-sm text-slate-400">
                      No malicious flows currently detected. The network is clean.
                    </div>
                  )}
                </div>
              </div>

              {/* BLOCKED DEVICES & ATTACKS TABLE */}
              <section id="threats" className="panel-card mt-8 sm:mt-10 overflow-hidden">
                <div className="flex flex-wrap items-center justify-between gap-5 border-b border-slate-200 p-6 sm:p-7">
                  <div>
                    <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                      Blocked Devices &amp; Security Events
                    </h2>
                    <p className="mt-1 text-sm text-slate-500">
                      Host devices identified sending malicious volumetric traffic and blocked at switch s1
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex h-10 items-center gap-2.5 rounded-lg border border-slate-200 bg-white px-3 text-slate-400">
                      <Icon name="search" size={16} />
                      <input 
                        value={search} 
                        onChange={event => setSearch(event.target.value)} 
                        placeholder="Search IP, host or reason..." 
                        aria-label="Search blocked threats" 
                        className="w-40 sm:w-52 bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
                      />
                    </div>
                    <select
                      value={severity}
                      onChange={event => setSeverity(event.target.value)}
                      aria-label="Filter by severity"
                      className="h-10 rounded-lg border border-slate-200 bg-white px-3 text-xs sm:text-sm font-semibold text-slate-700 outline-none hover:bg-slate-50"
                    >
                      <option value="All severity">All Severities</option>
                      <option value="Critical">Critical</option>
                      <option value="High">High</option>
                      <option value="Medium">Medium</option>
                    </select>
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
                      <tr className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                        <th className="py-4 px-6">Attacker Node &amp; IP</th>
                        <th className="py-4 px-6">Target Destination</th>
                        <th className="py-4 px-6">Blocked Traffic Volume</th>
                        <th className="py-4 px-6">Mitigation Reason</th>
                        <th className="py-4 px-6">Rule Priority</th>
                        <th className="py-4 px-6 text-right">Defense Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {rows.map((row, i) => (
                        <tr key={`${row.ip}-${i}`} className="hover:bg-slate-50/70 transition-colors">
                          <td className="py-4.5 px-6">
                            <div className="font-bold text-slate-900 mono text-base">{row.ip}</div>
                            <div className="text-xs text-slate-500 mt-0.5">{row.country} {row.mac ? `· ${row.mac}` : ''}</div>
                          </td>
                          <td className="py-4.5 px-6 text-slate-700 font-medium">
                            <div className="text-slate-900 font-semibold mono">{row.target || `10.0.0.3:${row.port}`}</div>
                            <div className="text-xs text-slate-500">{row.protocol} (Port {row.port})</div>
                          </td>
                          <td className="py-4.5 px-6">
                            <div className="font-bold mono text-rose-600">
                              {currentDroppedPps > 0 ? `${currentDroppedPps.toLocaleString()} pkts/s` : 'Rule Active (Idle)'}
                            </div>
                            <div className="text-xs text-slate-500 mt-0.5">Line-rate switch drop</div>
                          </td>
                          <td className="py-4.5 px-6 text-slate-700 max-w-xs">
                            <span className="font-medium text-slate-800">{row.reason}</span>
                          </td>
                          <td className="py-4.5 px-6 font-bold text-slate-900 mono">
                            65535
                          </td>
                          <td className="py-4.5 px-6 text-right">
                            {underAttack || isDemoAttacking ? (
                              <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-100 px-3 py-1 text-xs font-bold text-rose-700 border border-rose-200">
                                <span className="h-1.5 w-1.5 rounded-full bg-rose-600 animate-ping" />
                                ACTIVE DROP
                              </span>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 rounded-full bg-amber-100 px-3 py-1 text-xs font-bold text-amber-800 border border-amber-200">
                                RULE RETAINED
                              </span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>

                  {!rows.length && (
                    <div className="py-16 text-center text-sm text-slate-400">
                      {data.threats.length 
                        ? 'No blocked devices match the current search or severity filter.' 
                        : 'No devices are currently blocked. The network is clean.'}
                    </div>
                  )}
                </div>
              </section>
            </>
          )}

          {/* Academic Footer */}
          <footer className="mt-12 flex flex-wrap items-center justify-between gap-4 border-t border-slate-200 pt-7 text-sm text-slate-500">
            <div>
              SDN DDoS Mitigation System · Ryu OpenFlow 1.3 Controller &amp; Mininet Topology
            </div>
            <div>
              Academic Project · {source === 'live' ? `Connected to ${targetHost}` : 'Interactive Simulation Mode'}
            </div>
          </footer>
        </main>
      </div>
    </div>
  )
}
