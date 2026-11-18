import { useEffect, useState, useRef } from 'react'
import type { ReactNode } from 'react'
import { demoSnapshot, endpoint, fetchSnapshot } from './data'
import type { Snapshot, IpTrafficEntry } from './data'

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
  // Stepped, stable dynamic ceiling: locks smoothly at 12k during normal (~1.3k PPS),
  // and dynamically steps through [12, 20, 30, 45, 60, 80, 100, 150, 200, 300, 500]
  // to ensure multi-IP summed traffic NEVER clips or flatlines while remaining jitter-free.
  const stepCeilings = [12, 20, 30, 45, 60, 80, 100, 150, 200, 300, 500]
  const targetCeiling = maxVal * 1.15
  const ceiling = stepCeilings.find(c => c >= targetCeiling) || Math.ceil(targetCeiling / 50) * 50
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
              <stop offset="0%" stopColor="#334155" stopOpacity="0.10" />
              <stop offset="100%" stopColor="#334155" stopOpacity="0.0" />
            </linearGradient>
            <linearGradient id="droppedFill" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stopColor="#dc2626" stopOpacity="0.18" />
              <stop offset="100%" stopColor="#dc2626" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Background Grid Lines & Y-Axis Labels */}
          {[0, 0.25, 0.5, 0.75, 1].map(fraction => (
            <g key={fraction}>
              <line x1="45" x2="980" y1={220 - fraction * 190} y2={220 - fraction * 190} stroke="#f1f5f9" strokeWidth="1.2" />
              <text x="0" y={224 - fraction * 190} fill="#94a3b8" fontSize="12" className="mono tabular-nums">{Math.round(fraction * ceiling)}k</text>
            </g>
          ))}

          {/* Traffic Baseline & Anomaly Limit Line (Neutral Slate Dashed) */}
          <line
            x1="45"
            x2="980"
            y1={220 - traffic.threshold / ceiling * 190}
            y2={220 - traffic.threshold / ceiling * 190}
            stroke="#64748b"
            strokeWidth="1.5"
            strokeDasharray="4 4"
          />

          {/* 1. Dropped Hostile Traffic Area & Line (Crimson Red) */}
          <path d={`${droppedPath} L 980 220 L 45 220 Z`} fill="url(#droppedFill)" />
          <path d={droppedPath} fill="none" stroke="#dc2626" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />

          {/* 2. Total Ingress Volume Area & Line (Slate Charcoal) */}
          <path d={`${ingressPath} L 980 220 L 45 220 Z`} fill="url(#ingressFill)" />
          <path d={ingressPath} fill="none" stroke="#334155" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />

          {/* 3. Clean Verified Throughput Line (Emerald Green) */}
          <path d={forwardedPath} fill="none" stroke="#059669" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />

          {/* Interactive Inspection Cursor */}
          {activeHover !== null && (
            <>
              <line x1={x} x2={x} y1="20" y2="220" stroke="#94a3b8" strokeDasharray="3 3" />
              <circle cx={x} cy={y} r="5" fill="#0f172a" stroke="#ffffff" strokeWidth="2.5" />
            </>
          )}
        </svg>

        {/* Enhanced Multi-Metric Tooltip (Strict 3 Colors) */}
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
              <span className="mono tabular-nums">{ingress.length - 1 - activeHover}s ago</span>
              <span className="font-semibold text-slate-300">{source === 'demo' ? 'Simulation Time' : 'Switch Telemetry'}</span>
            </div>
            <div className="mt-2.5 space-y-1.5 text-xs sm:text-sm">
              <div className="flex items-center justify-between gap-5">
                <span className="flex items-center gap-1.5 text-slate-300 font-medium">
                  <span className="size-2 rounded-full bg-slate-400" /> Total Incoming Traffic:
                </span>
                <span className="font-bold mono tabular-nums text-white">{hoverIngressPps.toLocaleString()} pkts/s</span>
              </div>
              <div className="flex items-center justify-between gap-5">
                <span className="flex items-center gap-1.5 text-red-400 font-medium">
                  <span className="size-2 rounded-full bg-red-500" /> Malicious Blocked:
                </span>
                <span className="font-bold mono tabular-nums text-red-300">{hoverDroppedPps.toLocaleString()} pkts/s</span>
              </div>
              <div className="flex items-center justify-between gap-5">
                <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                  <span className="size-2 rounded-full bg-emerald-500" /> Clean Delivered:
                </span>
                <span className="font-bold mono tabular-nums text-emerald-300">{hoverForwardedPps.toLocaleString()} pkts/s</span>
              </div>
              <div className="mt-2 border-t border-slate-700/60 pt-1.5 text-[11px] text-slate-400 mono tabular-nums text-center">
                Total ({hoverIngressPps.toLocaleString()}) = Blocked ({hoverDroppedPps.toLocaleString()}) + Clean ({hoverForwardedPps.toLocaleString()})
              </div>
              {hoverDroppedPps > 0 && (
                <div className="flex items-center justify-between text-xs text-slate-300">
                  <span>Attack Block Efficiency:</span>
                  <span className="font-bold text-red-400 mono tabular-nums">{hoverDropPercent}% neutralized</span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Timeline Labels */}
      <div className="ml-[4.5%] flex justify-between pt-3 text-xs sm:text-sm font-medium text-slate-500 mono tabular-nums">
        {timelineLabels.map((label, idx) => (
          <span key={label} className={idx % 2 === 1 ? 'hidden sm:inline' : ''}>{label}</span>
        ))}
        <span className="text-slate-700 font-bold">{source === 'demo' ? 'Preview (Now)' : 'Live Switch (Now)'}</span>
      </div>
    </div>
  )
}

function exportCsv(rows: IpTrafficEntry[]) {
  const fields = ['Source IP', 'Device Identity', 'Status', 'Passed (pkts/s)', 'Blocked (pkts/s)', 'Total Ingress (pkts/s)', 'Allowed Flow Vectors', 'Blocked Flow Vectors', 'Autonomous Mitigation Reason']
  const csv = [
    fields,
    ...rows.map(row => [
      row.ip,
      row.hostLabel,
      row.status,
      row.forwardedPps,
      row.droppedPps,
      row.ingressPps,
      row.allowedFlows.map(f => `${f.protocol} :${f.dstPort} (${f.pps} pps)`).join('; '),
      row.blockedFlows.map(f => `${f.attackType || f.protocol} :${f.dstPort} (${f.pps} pps)`).join('; '),
      row.primaryReason || 'Clean Traffic'
    ])
  ].map(row => row.map(value => `"${String(value).replace(/"/g, '""')}"`).join(',')).join('\n')

  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `sdn-ddos-traffic-analysis-${Date.now()}.csv`
  link.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}

function formatFlowVector(protocol: string, dstPort: number, isAttack: boolean, attackType?: string): string {
  const p = (protocol || 'IP').toUpperCase()
  if (!isAttack) {
    if (p === 'UDP' && dstPort === 5001) return 'Live Video Stream (UDP :5001)'
    if (p === 'TCP' && (dstPort === 80 || dstPort === 8080)) return 'Standard Web Traffic (TCP :80)'
    if (p === 'UDP' && dstPort === 53) return 'Standard DNS Queries (UDP :53)'
    if (p === 'ICMP') return 'Ping Echo Check (ICMP)'
    return `Legitimate Flow (${p} :${dstPort})`
  }

  // Attack vectors
  if (attackType) {
    const a = attackType.toLowerCase()
    if (a.includes('slow')) return 'Slow Socket Starvation (Slowloris :80)'
    if (a.includes('syn')) return 'Connection Flood (TCP SYN :80)'
    if (a.includes('icmp')) return 'Ping Echo Flood (ICMP)'
    if (a.includes('high port') || dstPort === 8080) return 'High-Port Flood (UDP :8080)'
    if (a.includes('pulse') || a.includes('wave')) return 'Pulsing Wave Attack (UDP :53)'
  }
  if (p === 'UDP' && dstPort === 80) return 'Fake Web Flood (UDP :80)'
  if (p === 'TCP' && dstPort === 80) return 'Connection Overload (TCP SYN :80)'
  if (p === 'ICMP') return 'Ping Echo Flood (ICMP Echo)'
  if (p === 'UDP' && dstPort === 53) return 'DNS Query Overload (UDP :53)'
  if (p === 'UDP' && dstPort === 8080) return 'High-Port Amplification (UDP :8080)'

  return `${attackType || 'Malicious Flood'} (${p} :${dstPort})`
}

type DemoMode = 'normal' | 'attack' | 'idle' | 'loading' | 'error'

export default function App() {
  const [source, setSource] = useState<'demo' | 'live'>(() => {
    try {
      const params = new URLSearchParams(window.location.search)
      if (params.get('source') === 'demo') return 'demo'
    } catch {
      // Fallback
    }
    return 'live'
  })
  const [demoMode, setDemoMode] = useState<DemoMode>('normal')
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [loadState, setLoadState] = useState<'loading' | 'ready' | 'error'>('ready')
  const [error, setError] = useState('')
  const [retry, setRetry] = useState(0)
  const [streaming, setStreaming] = useState(true)
  const [search, setSearch] = useState('')
  const [tableFilter, setTableFilter] = useState<'all' | 'blocked_mixed' | 'legit'>('all')
  const [activeNav, setActiveNav] = useState('Overview')
  const [mobileMenu, setMobileMenu] = useState(false)

  // Has an attack occurred that installed a retained drop rule?
  const [hasDemoRetainedThreat, setHasDemoRetainedThreat] = useState(false)

  // Continuous 48-entry sliding buffer - NEVER wiped on mode switch!
  const [demoTraffic, setDemoTraffic] = useState<{ ingress: number[]; dropped: number[] }>(() => {
    const init = Array.from({ length: 48 }, (_, i) =>
      Number((1.32 + Math.sin(i * 0.4) * 0.05).toFixed(2))
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

  // Demo Mode Continuous 1-Second Sliding Buffer
  useEffect(() => {
    if (source !== 'demo' || !streaming) return

    const interval = window.setInterval(() => {
      const mode = demoModeRef.current
      if (mode === 'loading' || mode === 'error') return

      const now = Date.now() / 1000
      let nextIngress = 0
      let nextDropped = 0

      if (mode === 'idle') {
        nextIngress = 0
        nextDropped = 0
      } else if (mode === 'attack') {
        // Multi-IP botnet attack traffic sums to ~40.5k PPS dropped + ~1.98k PPS clean forwarded = ~42.5k PPS
        const base = 42.5 + Math.sin(now * 0.8) * 1.2 + (Math.random() * 0.6 - 0.3)
        nextIngress = Number(base.toFixed(2))
        nextDropped = Number((base - 1.98).toFixed(2))
      } else {
        // Normal traffic: steady ~1.315k PPS baseline across pure legit users
        const base = 1.32 + Math.sin(now * 0.4) * 0.05 + (Math.random() * 0.02 - 0.01)
        nextIngress = Number(base.toFixed(2))
        nextDropped = 0
      }

      // Push new second to right, drop oldest from left (100% continuous, NO BUFFER RESETS!)
      setDemoTraffic(prev => ({
        ingress: [...prev.ingress.slice(1), nextIngress],
        dropped: [...prev.dropped.slice(1), nextDropped],
      }))
    }, 1000)

    return () => window.clearInterval(interval)
  }, [source, streaming])

  // Live Mode Sequential Polling Loop
  // Sequential polling ensures in-flight requests are never prematurely canceled by a rigid interval timer.
  useEffect(() => {
    if (source !== 'live' || !streaming) return

    let cancelled = false
    let timerId: number | undefined

    const poll = async () => {
      const controller = new AbortController()
      // Generous 4s request timeout prevents stuck TCP sockets without killing normal responses
      const timeoutId = window.setTimeout(() => controller.abort(), 4000)

      try {
        const data = await fetchSnapshot(controller.signal)
        window.clearTimeout(timeoutId)
        if (!cancelled) {
          setSnapshot(data)
          setLoadState('ready')
          setError('')
        }
      } catch (cause: unknown) {
        window.clearTimeout(timeoutId)
        if (!cancelled && !controller.signal.aborted) {
          setError(
            cause instanceof Error
              ? cause.message
              : 'Could not connect to Flask API. Ensure VM is running and VITE_DEFENSE_API_URL is configured.'
          )
          setLoadState('error')
        }
      } finally {
        if (!cancelled) {
          // Schedule next poll 1000ms after response finishes
          timerId = window.setTimeout(poll, 1000)
        }
      }
    }

    poll()

    return () => {
      cancelled = true
      if (timerId !== undefined) {
        window.clearTimeout(timerId)
      }
    }
  }, [source, streaming, retry])

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
  const currentDroppedPps = data?.metrics.droppedPps !== undefined ? data.metrics.droppedPps : Math.round(latestDroppedK * 1000)
  const currentForwardedPps = data?.metrics.forwardedPps !== undefined ? data.metrics.forwardedPps : Math.max(0, currentIngressPps - currentDroppedPps)
  const dropPercentage = currentIngressPps > 0 ? ((currentDroppedPps / currentIngressPps) * 100).toFixed(1) : '0.0'

  const peakIngressK = ingressArr.length ? Math.max(...ingressArr) : 0
  const peakPps = Math.round(peakIngressK * 1000)
  const noTraffic = source === 'live' && !offline && !underAttack && currentIngressPps === 0 && !data?.threats.length

  // Source IP entries from data.ipTraffic or fallback
  const ipTrafficList: IpTrafficEntry[] = (data?.ipTraffic && data.ipTraffic.length > 0)
    ? data.ipTraffic
    : (data?.threats || []).map(t => ({
        ip: t.ip,
        hostLabel: t.country || `Host (${t.ip})`,
        mac: t.mac,
        forwardedPps: t.forwardedPps || 0,
        droppedPps: t.droppedPps !== undefined ? t.droppedPps : (t.ratePps || 0),
        ingressPps: t.ingressPps !== undefined ? t.ingressPps : ((t.forwardedPps || 0) + (t.droppedPps !== undefined ? t.droppedPps : (t.ratePps || 0))),
        allowedFlows: (t.flows || []).filter(f => !f.attackType && (f.priority === 10 || !f.priority)),
        blockedFlows: (t.flows || []).filter(f => f.attackType || f.priority === 65535),
        status: t.status || (t.ratePps ? 'ACTIVE DROP' : 'RULE RETAINED'),
        primaryReason: t.reason,
        severity: t.severity
      }))

  // Filtered IP entries for the table
  const filteredIpEntries = ipTrafficList.filter(row => {
    if (tableFilter === 'blocked_mixed') {
      const isBlockedOrMixed = row.droppedPps > 0 || row.blockedFlows.length > 0 || row.status === 'MIXED' || row.status === 'ACTIVE DROP' || row.status === 'RULE RETAINED'
      if (!isBlockedOrMixed) return false
    } else if (tableFilter === 'legit') {
      const isPureLegit = row.droppedPps === 0 && row.blockedFlows.length === 0 && (row.status === 'ALLOWED' || row.forwardedPps > 0) && row.status !== 'MIXED' && row.status !== 'ACTIVE DROP'
      if (!isPureLegit) return false
    }

    if (search.trim()) {
      const q = search.toLowerCase()
      const searchStr = `${row.ip} ${row.hostLabel} ${row.mac || ''} ${row.primaryReason || ''} ${row.status} ${row.allowedFlows.map(f => `${f.protocol} ${f.dstPort}`).join(' ')} ${row.blockedFlows.map(f => `${f.protocol} ${f.dstPort} ${f.attackType || ''}`).join(' ')}`.toLowerCase()
      if (!searchStr.includes(q)) return false
    }

    return true
  })

  const maxRowIngress = Math.max(1, ...filteredIpEntries.map(r => r.ingressPps))
  const totalVisiblePassed = filteredIpEntries.reduce((acc, r) => acc + r.forwardedPps, 0)
  const totalVisibleBlocked = filteredIpEntries.reduce((acc, r) => acc + r.droppedPps, 0)
  const totalVisibleIngress = filteredIpEntries.reduce((acc, r) => acc + r.ingressPps, 0)

  const navItems = [
    { label: 'Overview', target: 'overview' },
    { label: 'Live Traffic', target: 'traffic' },
    { label: 'Terms Decoded', target: 'glossary' },
    { label: 'How Defense Works', target: 'how-it-works' },
    { label: 'Host Traffic & Defense', target: 'threats' },
  ]

  return (
    <div className="min-h-dvh bg-slate-50 text-slate-800">
      {/* Skip to Main Content Link for Keyboard Accessibility */}
      <a
        href="#overview"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-50 focus:rounded-lg focus:bg-slate-900 focus:px-4 focus:py-2.5 focus:text-sm focus:font-semibold focus:text-white focus:shadow-xl focus:outline-none focus:ring-2 focus:ring-slate-900 focus:ring-offset-2"
      >
        Skip to main content
      </a>

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
            <span className="flex size-8 items-center justify-center rounded-lg bg-slate-900 text-white">
              <Icon name="shield" size={17} />
            </span>
            <span className="text-lg font-bold tracking-tight text-slate-900">Network Defense</span>
          </div>
          <button className="flex size-8 items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 lg:hidden" onClick={() => setMobileMenu(false)} aria-label="Close menu">
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
              {item.label === 'Host Traffic & Defense' && data && data.threats.length > 0 && (
                <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-bold text-red-700 tabular-nums">
                  <span className="sr-only">Active threats: </span>
                  {data.threats.length}
                </span>
              )}
            </a>
          ))}
        </nav>

        {/* Connection Status Card */}
        <div className="mt-auto rounded-xl border border-slate-200 bg-slate-50 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-slate-800">
            <span className={`size-2.5 rounded-full ${source === 'live' ? 'bg-emerald-500' : 'bg-slate-700'}`} />
            {source === 'live' ? 'Connected to Controller' : 'Interactive Demo Mode'}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {source === 'live' ? `Host: ${targetHost}` : 'Smooth Continuous Simulation'}
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="min-h-dvh lg:pl-[265px]">
        {/* Top Header Bar */}
        <header className="sticky top-0 z-20 flex min-h-[70px] items-center justify-between border-b border-slate-200 bg-white/95 px-6 sm:px-10 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <button className="flex size-9 items-center justify-center rounded-lg p-1.5 text-slate-600 hover:bg-slate-100 lg:hidden" aria-label="Open menu" onClick={() => setMobileMenu(true)}>
              <Icon name="menu" size={22} />
            </button>
            <span className="text-sm font-medium text-slate-400">Campus Network <span className="mx-1.5">/</span></span>
            <span className="text-sm font-semibold text-slate-800">SDN Traffic &amp; Autonomous Defense</span>
          </div>

          <div className="flex items-center gap-3">
            {/* Live vs Demo Toggle */}
            <div className="flex items-center rounded-lg border border-slate-200 bg-slate-100/90 p-0.5 text-xs sm:text-sm font-medium">
              <button
                onClick={() => setSource('demo')}
                className={`rounded-md px-3.5 py-1.5 transition-all enabled:active:scale-[0.97] motion-reduce:enabled:active:scale-100 ${source === 'demo' ? 'bg-white text-slate-900 shadow-sm font-semibold' : 'text-slate-500 hover:text-slate-800'}`}
              >
                Demo
              </button>
              <button
                onClick={() => { setLoadState('loading'); setSource('live'); setStreaming(true) }}
                disabled={!endpoint}
                className={`rounded-md px-3.5 py-1.5 transition-all enabled:active:scale-[0.97] motion-reduce:enabled:active:scale-100 ${source === 'live' ? 'bg-white text-slate-900 shadow-sm font-semibold' : 'text-slate-500 hover:text-slate-800'}`}
              >
                Live
              </button>
            </div>

            {/* Interactive Attack Simulator Button (Demo Mode) */}
            {source === 'demo' && (
              <>
                <button
                  onClick={toggleDemoAttack}
                  className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs sm:text-sm font-semibold shadow-sm transition-all enabled:active:scale-[0.97] motion-reduce:enabled:active:scale-100 ${
                    isDemoAttacking
                      ? 'bg-red-600 text-white hover:bg-red-700 shadow-red-200'
                      : 'bg-slate-900 text-white hover:bg-slate-800'
                  }`}
                >
                  <Icon name={isDemoAttacking ? 'pause' : 'play'} size={14} />
                  {isDemoAttacking ? 'Halt Attack Simulation' : 'Simulate DDoS Attack'}
                </button>

                {hasDemoRetainedThreat && (
                  <button
                    onClick={resetDemoSimulation}
                    className="flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-2 text-xs sm:text-sm font-semibold text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-all enabled:active:scale-[0.97] motion-reduce:enabled:active:scale-100"
                    title="Clear history and reset to calm baseline"
                    aria-label="Clear attack history and reset to calm baseline"
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
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-slate-900 text-balance">
                Network Traffic &amp; DDoS Defense
              </h1>
              <p className="mt-2.5 text-base sm:text-lg text-slate-600 max-w-3xl leading-relaxed text-pretty">
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
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-red-100 text-red-600">
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
              {/* TOP SECTION: Prominent Operational Posture Banner */}
              <div className={`panel-card mt-8 sm:mt-10 p-6 sm:p-8 flex flex-col md:flex-row md:items-center justify-between gap-6 border-l-4 ${
                underAttack
                  ? 'border-l-red-600 bg-red-50/70 border-red-200'
                  : offline
                    ? 'border-l-slate-400 bg-slate-100/70 border-slate-200'
                    : isThreatBlocked
                      ? 'border-l-slate-500 bg-slate-50/90 border-slate-200'
                      : 'border-l-emerald-600 bg-emerald-50/60 border-emerald-200'
              }`}>
                <div>
                  <div className="flex items-center gap-2.5">
                    <span className={`size-3 rounded-full ${underAttack ? 'bg-red-600 animate-ping' : offline ? 'bg-slate-400' : isThreatBlocked ? 'bg-slate-600' : 'bg-emerald-600'}`} />
                    <span className={`text-xs sm:text-sm font-bold uppercase tracking-wider ${underAttack ? 'text-red-700' : offline ? 'text-slate-600' : isThreatBlocked ? 'text-slate-700' : 'text-emerald-700'}`}>
                      {underAttack
                        ? 'DDoS Attack In Progress · Line-Rate Mitigation Active'
                        : offline
                          ? 'Mininet Virtual Switch Offline'
                          : isThreatBlocked
                            ? 'Attack Mitigated · Hardware Protective Rule Retained'
                            : noTraffic
                              ? 'Switch Connected · Idle'
                              : 'All Network Flows Verified · Normal Operation'}
                    </span>
                  </div>
                  <h2 className="mt-2 text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 text-balance">
                    {underAttack
                      ? 'Malicious Traffic Intercepted & Being Filtered At Switch'
                      : offline
                        ? 'Waiting for Telemetry from Controller & Switch'
                        : isThreatBlocked
                          ? 'Attacker Blocked · Legitimate User Traffic Protected'
                          : empty || noTraffic
                            ? 'Waiting for Network Traffic'
                            : 'Protected & Operational · Clean User Traffic Passing'}
                  </h2>
                  <p className="mt-2 max-w-3xl text-sm sm:text-base text-slate-600 leading-relaxed text-pretty">
                    {underAttack
                      ? 'Hostile packet flood detected from infected devices targeting the protected server (10.0.0.3). Open vSwitch s1 has installed Priority 65535 DROP rules to discard junk packets at line rate on the switch port. Genuine video streams and web requests continue flowing without lag.'
                      : isThreatBlocked
                        ? 'The flood burst has stopped. The hardware drop rule is retained during the idle timeout period to protect the server from renewed wave bursts.'
                        : offline
                          ? 'The telemetry API is reachable, but no statistics are arriving from switch s1. Start Ryu controller and Mininet to connect live telemetry.'
                          : 'The SDN controller is monitoring switch flow tables every second. Legitimate video streams, web visits, and DNS queries are flowing freely to the protected server.'}
                  </p>
                </div>

                <div className="flex md:flex-col items-center md:items-end justify-between gap-2.5 border-t md:border-t-0 md:border-l border-slate-200 pt-4 md:pt-0 md:pl-8 shrink-0">
                  <div className="text-xs sm:text-sm font-medium text-slate-500">Switch Defense Rule</div>
                  <div className={`text-sm sm:text-base font-bold px-3.5 py-1.5 rounded-full border ${
                    underAttack
                      ? 'bg-red-100 text-red-800 border-red-200'
                      : offline
                        ? 'bg-slate-200 text-slate-700 border-slate-300'
                        : isThreatBlocked
                          ? 'bg-slate-100 text-slate-800 border-slate-300'
                          : 'bg-emerald-100 text-emerald-800 border-emerald-200'
                  }`}>
                    {underAttack
                      ? 'ACTIVE HARDWARE DROP'
                      : isThreatBlocked
                        ? 'PROTECTIVE RULE RETAINED'
                        : offline
                          ? 'Waiting for Switch'
                          : 'CLEAN FORWARDING'}
                  </div>
                  <div className="text-xs sm:text-sm text-slate-500 mt-0.5">
                    {source === 'demo' ? 'Autonomous OpenFlow Controller Simulation' : `${data.endpointsOnline}/${data.endpointsTotal} Switch Telemetry Link`}
                  </div>
                </div>
              </div>

              {/* OPERATIONAL TELEMETRY COCKPIT (Asymmetric 3-Segment Bento Layout) */}
              <div className="mt-7 grid grid-cols-1 gap-5 lg:grid-cols-12">
                {/* Segment 1: Main Traffic Split (Spans 6 cols on large screens) */}
                <div className="panel-card p-6 sm:p-7 lg:col-span-6 flex flex-col justify-between">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500">
                      Total Network Ingress Volume
                    </div>
                    <span className="rounded-full px-2.5 py-0.5 text-xs font-bold border border-slate-200 bg-slate-100 text-slate-700 tabular-nums">
                      {underAttack ? 'Surge Ingress' : 'Calm Baseline'}
                    </span>
                  </div>
                  <div className="mt-3 flex items-baseline gap-2.5">
                    <span className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 mono tabular-nums">
                      {currentIngressPps.toLocaleString()}
                    </span>
                    <span className="text-sm font-semibold text-slate-500">pkts/s (packets per second)</span>
                  </div>

                  {/* Dual Traffic Allocation Bar (Delivered vs Blocked) */}
                  <div className="mt-5 pt-4 border-t border-slate-100">
                    <div className="flex items-center justify-between text-xs text-slate-600 mb-2 font-medium">
                      <span className="flex items-center gap-1.5 text-emerald-700">
                        <span className="size-2 rounded-full bg-emerald-600" />
                        Clean Delivered: <strong className="mono tabular-nums text-slate-900">{currentForwardedPps.toLocaleString()}</strong> pkts/s
                      </span>
                      <span className="flex items-center gap-1.5 text-red-700">
                        <span className="size-2 rounded-full bg-red-600" />
                        Blocked Flood: <strong className="mono tabular-nums text-slate-900">{currentDroppedPps.toLocaleString()}</strong> pkts/s
                      </span>
                    </div>
                    <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-100 flex">
                      <div
                        className="h-full bg-emerald-500 transition-all duration-300"
                        style={{ width: `${currentIngressPps > 0 ? (currentForwardedPps / currentIngressPps) * 100 : 100}%` }}
                        title={`Clean Delivered: ${currentForwardedPps} pkts/s`}
                      />
                      <div
                        className="h-full bg-red-600 transition-all duration-300"
                        style={{ width: `${currentIngressPps > 0 ? (currentDroppedPps / currentIngressPps) * 100 : 0}%` }}
                        title={`Blocked Flood: ${currentDroppedPps} pkts/s`}
                      />
                    </div>
                  </div>
                </div>

                {/* Segment 2: Protection Line-Rate Efficiency (Spans 3 cols) */}
                <div className="panel-card p-6 sm:p-7 lg:col-span-3 flex flex-col justify-between">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500">
                      Mitigation Efficiency
                    </div>
                    <span className={`rounded-full px-2.5 py-0.5 text-xs font-bold border tabular-nums ${currentDroppedPps > 0 ? 'bg-red-50 text-red-700 border-red-200' : 'bg-slate-100 text-slate-700 border-slate-200'}`}>
                      {currentDroppedPps > 0 ? `${dropPercentage}% Blocked` : '0% Filtered'}
                    </span>
                  </div>
                  <div className="mt-3 flex items-baseline gap-2">
                    <span className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 mono tabular-nums">
                      {currentDroppedPps > 0 ? `${dropPercentage}%` : '100%'}
                    </span>
                    <span className="text-sm font-semibold text-slate-500">{currentDroppedPps > 0 ? 'filtered' : 'clean'}</span>
                  </div>
                  <div className="mt-3 text-xs sm:text-sm text-slate-500 leading-normal text-pretty">
                    {currentDroppedPps > 0
                      ? 'Malicious packets discarded in hardware on switch port before touching server CPU.'
                      : 'All flows verified benign. No packets flagged for dropping.'}
                  </div>
                </div>

                {/* Segment 3: AI Classification SLA & Latency (Spans 3 cols) */}
                <div className="panel-card p-6 sm:p-7 lg:col-span-3 flex flex-col justify-between">
                  <div className="flex items-center justify-between gap-2">
                    <div className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500">
                      AI Decision Speed
                    </div>
                    <span className="rounded-full px-2.5 py-0.5 text-xs font-bold border tabular-nums bg-emerald-50 text-emerald-700 border-emerald-200">
                      &lt; 1.0 ms SLA
                    </span>
                  </div>
                  <div className="mt-3 flex items-baseline gap-2">
                    <span className="text-3xl sm:text-4xl font-bold tracking-tight text-slate-900 mono tabular-nums">
                      {data.metrics.mlLatencyMs < 1.0 ? data.metrics.mlLatencyMs.toFixed(2) : data.metrics.mlLatencyMs.toFixed(1)}
                    </span>
                    <span className="text-sm font-semibold text-slate-500">ms</span>
                  </div>
                  <div className="mt-3 text-xs sm:text-sm text-slate-500 leading-normal text-pretty">
                    CIC-DDoS2019 ML classification engine evaluates every flow under 0.5 ms without packet buffering lag.
                  </div>
                </div>
              </div>

              {/* LIVE TRAFFIC CHART SECTION (Strict 3 Colors) */}
              <section id="traffic" className="panel-card mt-8 sm:mt-10 p-6 sm:p-8 scroll-mt-24">
                <div className="flex flex-wrap items-center justify-between gap-5 border-b border-slate-100 pb-6">
                  <div>
                    <div className="flex items-center gap-3">
                      <h2 className="text-lg sm:text-xl font-bold text-slate-900 text-balance">
                        {source === 'demo' ? 'Real-Time Network Traffic Stream' : 'Live Network Traffic Stream'}
                      </h2>
                      <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 border border-emerald-200">
                        <span className={`size-2 rounded-full bg-emerald-500 ${streaming ? 'live-dot' : ''}`} />
                        {streaming ? 'Live Stream Active' : 'Paused'}
                      </span>
                    </div>
                    <p className="mt-1.5 text-sm sm:text-base text-slate-500 text-pretty">
                      Comparing total incoming packets (Ingress) against malicious packets dropped (Blocked) and legitimate packets safely delivered (Clean Forwarded).
                    </p>
                  </div>

                  {/* Real-time Numeric Stat Pills (Strict 3 Colors) */}
                  <div className="flex flex-wrap items-center gap-3">
                    <div className="flex items-center gap-2 rounded-lg bg-slate-100 px-3.5 py-1.5 text-xs sm:text-sm font-semibold text-slate-800 border border-slate-200">
                      <span className="size-2.5 rounded-full bg-slate-700" />
                      <span>Total Incoming:</span>
                      <span className="mono tabular-nums font-bold text-slate-900">{currentIngressPps.toLocaleString()} pkts/s</span>
                    </div>

                    <div className="flex items-center gap-2 rounded-lg bg-red-50 px-3.5 py-1.5 text-xs sm:text-sm font-semibold text-red-800 border border-red-200">
                      <span className="size-2.5 rounded-full bg-red-600" />
                      <span>Blocked Flood:</span>
                      <span className="mono tabular-nums font-bold text-red-700">{currentDroppedPps.toLocaleString()} pkts/s</span>
                    </div>

                    <div className="flex items-center gap-2 rounded-lg bg-emerald-50 px-3.5 py-1.5 text-xs sm:text-sm font-semibold text-emerald-800 border border-emerald-200">
                      <span className="size-2.5 rounded-full bg-emerald-600" />
                      <span>Clean Delivered:</span>
                      <span className="mono tabular-nums font-bold text-emerald-700">{currentForwardedPps.toLocaleString()} pkts/s</span>
                    </div>

                    <button
                      onClick={() => setStreaming(!streaming)}
                      aria-label={streaming ? 'Pause graph streaming' : 'Resume graph streaming'}
                      className="rounded-lg border border-slate-200 p-2 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-all enabled:active:scale-[0.97] motion-reduce:enabled:active:scale-100"
                      title={streaming ? 'Pause graph' : 'Resume graph'}
                    >
                      <Icon name={streaming ? 'pause' : 'play'} size={15} />
                    </button>
                  </div>
                </div>

                {/* Sub-Legend Row (Strict 3 Colors) */}
                <div className="mt-4 flex flex-wrap items-center justify-between text-xs sm:text-sm text-slate-500">
                  <div className="flex flex-wrap items-center gap-5">
                    <span className="flex items-center gap-1.5 font-medium text-slate-700">
                      <span className="size-2.5 rounded-full bg-slate-700" /> Total Network Volume (Slate)
                    </span>
                    <span className="flex items-center gap-1.5 font-medium text-red-700">
                      <span className="size-2.5 rounded-full bg-red-600" /> Blocked Attack Flood (Red)
                    </span>
                    <span className="flex items-center gap-1.5 font-medium text-emerald-700">
                      <span className="size-2.5 rounded-full bg-emerald-600" /> Clean User Traffic (Green)
                    </span>
                    <span className="flex items-center gap-1.5 text-slate-500">
                      <span className="h-0.5 w-4 bg-slate-400" /> Normal Traffic Baseline ({Math.round(data.traffic.threshold * 1000).toLocaleString()} pkts/s)
                    </span>
                  </div>
                  <div className="mono tabular-nums font-medium text-slate-500">
                    Recorded Peak: <strong className="text-slate-800">{peakPps.toLocaleString()}</strong> pkts/s
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

              {/* NETWORK TERMS DECODED (GLOSSARY) */}
              <section id="glossary" className="mt-8 sm:mt-10 scroll-mt-24">
                <div className="panel-card p-7 sm:p-8">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200 pb-5">
                    <div>
                      <h2 className="text-lg sm:text-xl font-bold text-slate-900 text-balance">
                        Network Terms Decoded · Understand Every Concept
                      </h2>
                      <p className="mt-1 text-sm text-slate-500 text-pretty">
                        Plain-English explanations of key network terminology, protocols, and autonomous defense principles
                      </p>
                    </div>
                    <span className="self-start sm:self-auto rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 border border-slate-200 shrink-0">
                      Educational Reference
                    </span>
                  </div>

                  <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Concept 1: Packets & Rates */}
                    <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-5 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-2">
                          <h3 className="font-bold text-slate-900 text-base">Packets &amp; Traffic Speed (pkts/s)</h3>
                          <span className="rounded bg-slate-200 px-2 py-0.5 text-[11px] font-bold text-slate-700 uppercase">Speed</span>
                        </div>
                        <p className="mt-2 text-sm text-slate-600 leading-relaxed text-pretty">
                          All Internet communication travels in small envelopes called <strong className="text-slate-900">packets</strong>. Traffic speed is measured in <strong className="text-slate-900">pkts/s</strong> (packets per second).
                        </p>
                        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-3 text-xs text-slate-600 space-y-1.5">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-emerald-700">Legitimate Users:</span>
                            <span className="mono tabular-nums text-slate-700 font-medium">100 – 1,500 pkts/s</span>
                          </div>
                          <div className="flex items-center justify-between">
                            <span className="font-semibold text-red-700">DDoS Attacks:</span>
                            <span className="mono tabular-nums text-slate-700 font-medium">5,000 – 50,000+ pkts/s</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Concept 2: UDP vs TCP */}
                    <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-5 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-2">
                          <h3 className="font-bold text-slate-900 text-base">UDP vs. TCP Streams</h3>
                          <span className="rounded bg-slate-200 px-2 py-0.5 text-[11px] font-bold text-slate-700 uppercase">Protocols</span>
                        </div>
                        <p className="mt-2 text-sm text-slate-600 leading-relaxed text-pretty">
                          <strong className="text-slate-900">TCP:</strong> Requires a two-way handshake before sending data (like a confirmed phone call). Used for websites and secure logins.<br />
                          <strong className="text-slate-900">UDP:</strong> Shoots packets with no handshake or confirmation (like a live radio broadcast). Used for video streaming and DNS lookups.
                        </p>
                        <div className="mt-3 rounded-lg border border-red-100 bg-red-50/50 p-2.5 text-xs text-red-800 leading-relaxed">
                          <strong>Why UDP is abused:</strong> Attackers can flood millions of fake UDP packets with zero handshake, quickly overwhelming target servers.
                        </div>
                      </div>
                    </div>

                    {/* Concept 3: Same-IP Mixed Traffic */}
                    <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-5 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-2">
                          <h3 className="font-bold text-slate-900 text-base">Same-IP Mixed Traffic</h3>
                          <span className="inline-flex items-center gap-1 rounded bg-slate-200 px-2 py-0.5 text-[11px] font-bold text-slate-700 uppercase">
                            <span className="size-1.5 rounded-full bg-emerald-600" />
                            <span className="size-1.5 rounded-full bg-red-600" />
                            Dual-Stream
                          </span>
                        </div>
                        <p className="mt-2 text-sm text-slate-600 leading-relaxed text-pretty">
                          A single device (IP address) can simultaneously run a <strong className="text-emerald-700">safe application</strong> (e.g. video streaming on port 5001) while infected background malware launches a <strong className="text-red-700">malicious flood</strong> on port 80.
                        </p>
                        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-2.5 text-xs text-slate-600 leading-relaxed">
                          <strong>Selective Mitigation:</strong> Older firewalls block the entire IP, punishing innocent traffic. Our SDN controller inspects individual ports and protocols to drop only the attack while letting good traffic through.
                        </div>
                      </div>
                    </div>

                    {/* Concept 4: SDN Hardware Line-Rate Drop */}
                    <div className="rounded-xl border border-slate-200 bg-slate-50/50 p-5 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between gap-2">
                          <h3 className="font-bold text-slate-900 text-base">Line-Rate Switch Drop Rules</h3>
                          <span className="rounded bg-red-100 px-2 py-0.5 text-[11px] font-bold text-red-700 uppercase">Hardware</span>
                        </div>
                        <p className="mt-2 text-sm text-slate-600 leading-relaxed text-pretty">
                          Traditional software firewalls inspect traffic on a CPU, which burns 100% compute and drops packets indiscriminately under a flood.
                        </p>
                        <div className="mt-3 rounded-lg border border-slate-200 bg-white p-2.5 text-xs text-slate-600 leading-relaxed">
                          <strong>Microsecond Wire Speed:</strong> Our Ryu controller pushes an <strong className="text-slate-900">OpenFlow Priority 65535 DROP rule</strong> directly into Open vSwitch hardware. Hostile packets are discarded at the switch port before they ever reach the server.
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </section>

              {/* HOW IT WORKS & WHY BLOCKED SECTION */}
              <div id="how-it-works" className="mt-8 sm:mt-10 grid grid-cols-1 gap-6 sm:gap-8 lg:grid-cols-2 scroll-mt-24">
                {/* How It Works */}
                <div className="panel-card p-7 sm:p-8">
                  <h3 className="text-lg sm:text-xl font-bold text-slate-900 text-balance">How Autonomous Defense Works</h3>
                  <p className="mt-1.5 text-sm text-slate-500 text-pretty">Autonomous closed-loop SDN defense lifecycle</p>

                  <div className="mt-6 space-y-5 text-sm sm:text-base text-slate-700 leading-relaxed">
                    <div className="flex items-start gap-4">
                      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white mt-0.5">1</span>
                      <div className="text-pretty">
                        <strong className="text-slate-900">Flow Statistics Polling:</strong> The Ryu controller queries OpenFlow 1.3 flow counters on switch s1 every second to calculate real-time packet-per-second (PPS) and byte-per-second (BPS) rates per flow.
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white mt-0.5">2</span>
                      <div className="text-pretty">
                        <strong className="text-slate-900">Anomaly Classification:</strong> Observed flows are evaluated by the ML classification pipeline or the robust threshold fallback ({Math.round(data.traffic.threshold * 1000).toLocaleString()} pkts/s) to isolate malicious packet bursts.
                      </div>
                    </div>
                    <div className="flex items-start gap-4">
                      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-slate-900 text-xs font-bold text-white mt-0.5">3</span>
                      <div className="text-pretty">
                        <strong className="text-slate-900">Line-Rate Mitigation:</strong> The controller sends an OpenFlow `OFPFlowMod` message pushing a Priority 65535 DROP rule matching the exact hostile flow tuple, dropping attack traffic at line rate in hardware while concurrent legitimate streams continue passing without packet loss.
                      </div>
                    </div>
                  </div>
                </div>

                {/* Why Traffic Was Blocked */}
                <div className="panel-card p-7 sm:p-8">
                  <h3 className="text-lg sm:text-xl font-bold text-slate-900 text-balance">Detection Trigger Breakdown</h3>
                  <p className="mt-1.5 text-sm text-slate-500 text-pretty">Active rules and heuristics applied to mitigate the attack</p>

                  {data.dropReasons.length ? (
                    <div className="mt-6 space-y-5">
                      {data.dropReasons.map((reason) => (
                        <div key={reason.reason}>
                          <div className="flex justify-between text-sm sm:text-base font-semibold text-slate-700">
                            <span>{reason.reason}</span>
                            <span className="mono tabular-nums">{reason.share}%</span>
                          </div>
                          <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-slate-100">
                            <div className="h-full rounded-full bg-red-600" style={{ width: `${reason.share}%` }} />
                          </div>
                        </div>
                      ))}
                      <div className="mt-6 rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs sm:text-sm text-slate-600 leading-relaxed text-pretty">
                        <strong>Policy Action:</strong> Attacking packet flows are isolated at the switch and dropped at hardware line-rate (Priority 65535). Safe forwarding rules (Priority 10) remain active, allowing clean user traffic and concurrent benign streams to pass undisturbed.
                      </div>
                    </div>
                  ) : (
                    <div className="py-16 text-center text-sm text-slate-400 text-pretty">
                      No malicious flows currently detected. The network is clean.
                    </div>
                  )}
                </div>
              </div>

              {/* PER-IP MITIGATION & TRAFFIC TELEMETRY TABLE GRAPH */}
              <section id="threats" className="panel-card mt-8 sm:mt-10 overflow-hidden scroll-mt-24">
                <div className="flex flex-wrap items-center justify-between gap-5 border-b border-slate-200 p-6 sm:p-7">
                  <div>
                    <h2 className="text-lg sm:text-xl font-bold text-slate-900 text-balance">
                      Per-IP Traffic Breakdown &amp; Mitigation Table
                    </h2>
                    <p className="mt-1 text-sm text-slate-500 text-pretty">
                      Flow-level OpenFlow 1.3 telemetry per host: Passed vs. Blocked packets with line-rate switch rules
                    </p>
                  </div>

                  {/* Filter Pills + Search + Export CSV */}
                  <div className="flex flex-wrap items-center gap-3">
                    {/* Filter Pills */}
                    <div className="inline-flex rounded-lg border border-slate-200 bg-slate-100 p-1 text-xs font-semibold">
                      <button
                        onClick={() => setTableFilter('all')}
                        className={`rounded-md px-3 py-1.5 transition-all enabled:active:scale-[0.97] motion-reduce:enabled:active:scale-100 tabular-nums ${
                          tableFilter === 'all'
                            ? 'bg-white text-slate-900 shadow-sm font-bold'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        All IPs ({ipTrafficList.length})
                      </button>
                      <button
                        onClick={() => setTableFilter('blocked_mixed')}
                        className={`rounded-md px-3 py-1.5 transition-all enabled:active:scale-[0.97] motion-reduce:enabled:active:scale-100 tabular-nums ${
                          tableFilter === 'blocked_mixed'
                            ? 'bg-white text-red-700 shadow-sm font-bold'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Blocked / Mixed ({ipTrafficList.filter(r => r.droppedPps > 0 || r.blockedFlows.length > 0 || r.status === 'MIXED').length})
                      </button>
                      <button
                        onClick={() => setTableFilter('legit')}
                        className={`rounded-md px-3 py-1.5 transition-all enabled:active:scale-[0.97] motion-reduce:enabled:active:scale-100 tabular-nums ${
                          tableFilter === 'legit'
                            ? 'bg-white text-emerald-700 shadow-sm font-bold'
                            : 'text-slate-600 hover:text-slate-900'
                        }`}
                      >
                        Legit Only ({ipTrafficList.filter(r => r.droppedPps === 0 && r.blockedFlows.length === 0 && r.status !== 'MIXED').length})
                      </button>
                    </div>

                    {/* Search with accessible label and clear button */}
                    <div className="relative flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3 text-slate-400 focus-within:border-slate-400 transition-colors">
                      <label htmlFor="ip-table-search" className="sr-only">Search IP traffic entries</label>
                      <Icon name="search" size={15} />
                      <input
                        id="ip-table-search"
                        value={search}
                        onChange={event => setSearch(event.target.value)}
                        placeholder="Search IP, host, vector..."
                        className="w-36 sm:w-48 bg-transparent text-xs sm:text-sm text-slate-800 outline-none placeholder:text-slate-400"
                      />
                      {search && (
                        <button
                          type="button"
                          onClick={() => setSearch('')}
                          aria-label="Clear search input"
                          className="flex size-5 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                        >
                          <Icon name="close" size={12} />
                        </button>
                      )}
                    </div>

                    {/* Export CSV */}
                    <button
                      disabled={!filteredIpEntries.length}
                      onClick={() => exportCsv(filteredIpEntries)}
                      className="flex h-10 items-center gap-2 rounded-lg border border-slate-200 bg-white px-3.5 text-xs sm:text-sm font-semibold text-slate-700 hover:bg-slate-50 disabled:opacity-50 transition-all enabled:active:scale-[0.97] motion-reduce:enabled:active:scale-100"
                    >
                      <Icon name="download" size={15} /> Export CSV
                    </button>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-slate-200 bg-slate-50 font-semibold text-slate-600 text-xs uppercase tracking-wider">
                        <th className="py-4 px-6">Source IP &amp; Device Identity</th>
                        <th className="py-4 px-6">Traffic Streams &amp; Application Vectors</th>
                        <th className="py-4 px-6 min-w-[240px]">Passed vs. Blocked Traffic</th>
                        <th className="py-4 px-6 max-w-xs">Autonomous Decision &amp; Behavior</th>
                        <th className="py-4 px-6">Rule Priority</th>
                        <th className="py-4 px-6 text-right">Defense Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-100">
                      {filteredIpEntries.map((row) => {
                        const widthPercent = Math.max(8, Math.min(100, (row.ingressPps / maxRowIngress) * 100))
                        const passPercent = row.ingressPps > 0 ? (row.forwardedPps / row.ingressPps) * 100 : 0
                        const dropPercent = row.ingressPps > 0 ? (row.droppedPps / row.ingressPps) * 100 : 0
                        const isMixed = row.status === 'MIXED' || (row.forwardedPps > 0 && row.droppedPps > 0)

                        return (
                          <tr key={row.ip} className="hover:bg-slate-50/70 transition-colors">
                            {/* Source IP & Device Identity */}
                            <td className="py-4.5 px-6">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-slate-900 mono tabular-nums text-base">{row.ip}</span>
                                {isMixed && (
                                  <span className="inline-flex items-center gap-1 rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-800 border border-slate-300">
                                    <span className="size-1.5 rounded-full bg-emerald-600" />
                                    <span className="size-1.5 rounded-full bg-red-600" />
                                    DUAL-STREAM
                                  </span>
                                )}
                              </div>
                              <div className="text-xs text-slate-600 mt-0.5 font-semibold">{row.hostLabel}</div>
                              {row.mac && <div className="text-[11px] text-slate-400 mono tabular-nums">{row.mac}</div>}
                            </td>

                            {/* Traffic Streams & Application Vectors */}
                            <td className="py-4.5 px-6">
                              <div className="flex flex-col gap-1.5">
                                {row.allowedFlows.map((f, fi) => (
                                  <span key={`af-${fi}`} className="inline-flex items-center gap-1.5 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-800 border border-emerald-200 w-fit">
                                    <span className="size-1.5 rounded-full bg-emerald-600 shrink-0" />
                                    <span>{formatFlowVector(f.protocol, f.dstPort, false)}</span>
                                    <span className="mono tabular-nums text-emerald-700 font-bold ml-0.5">({f.pps.toLocaleString()} pkts/s)</span>
                                  </span>
                                ))}
                                {row.blockedFlows.map((f, fi) => (
                                  <span key={`bf-${fi}`} className="inline-flex items-center gap-1.5 rounded-md bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-800 border border-red-200 w-fit">
                                    <span className="size-1.5 rounded-full bg-red-600 shrink-0" />
                                    <span>{formatFlowVector(f.protocol, f.dstPort, true, f.attackType)}</span>
                                    <span className="mono tabular-nums text-red-700 font-bold ml-0.5">({f.pps.toLocaleString()} pkts/s)</span>
                                  </span>
                                ))}
                                {!row.allowedFlows.length && !row.blockedFlows.length && (
                                  <span className="text-xs text-slate-400">Idle / No active packets</span>
                                )}
                              </div>
                            </td>

                            {/* Passed vs Blocked Traffic (Table Graph) */}
                            <td className="py-4.5 px-6">
                              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                                <div>
                                  <span className="text-slate-500 font-medium">Passed: </span>
                                  <span className="mono tabular-nums font-bold text-emerald-700">{row.forwardedPps.toLocaleString()}</span>
                                  <span className="text-[10px] text-slate-400"> pkts/s</span>
                                </div>
                                <div>
                                  <span className="text-slate-500 font-medium">Blocked: </span>
                                  <span className="mono tabular-nums font-bold text-red-700">{row.droppedPps.toLocaleString()}</span>
                                  <span className="text-[10px] text-slate-400"> pkts/s</span>
                                </div>
                                <div>
                                  <span className="text-slate-500 font-medium">Total: </span>
                                  <span className="mono tabular-nums font-bold text-slate-900">{row.ingressPps.toLocaleString()}</span>
                                  <span className="text-[10px] text-slate-400"> pkts/s</span>
                                </div>
                              </div>

                              {/* Stacked Bar Graph */}
                              <div className="mt-2 flex items-center gap-2">
                                <div className="h-2.5 overflow-hidden rounded-full bg-slate-100 flex border border-slate-200" style={{ width: `${widthPercent}%`, minWidth: '48px' }}>
                                  {passPercent > 0 && (
                                    <div
                                      className="h-full bg-emerald-600 transition-all duration-300"
                                      style={{ width: `${passPercent}%` }}
                                      title={`Passed: ${row.forwardedPps.toLocaleString()} pkts/s (${passPercent.toFixed(1)}%)`}
                                    />
                                  )}
                                  {dropPercent > 0 && (
                                    <div
                                      className="h-full bg-red-600 transition-all duration-300"
                                      style={{ width: `${dropPercent}%` }}
                                      title={`Blocked: ${row.droppedPps.toLocaleString()} pkts/s (${dropPercent.toFixed(1)}%)`}
                                    />
                                  )}
                                </div>
                                <span className="mono tabular-nums text-[10px] text-slate-500 shrink-0 font-medium">
                                  {dropPercent > 0 && passPercent > 0
                                    ? `${dropPercent.toFixed(0)}% drop`
                                    : dropPercent > 0
                                      ? '100% drop'
                                      : '100% pass'}
                                </span>
                              </div>
                            </td>

                            {/* Mitigation Reason */}
                            <td className="py-4.5 px-6 max-w-xs">
                              <div className="text-xs sm:text-sm text-slate-800 font-medium leading-snug text-pretty">
                                {row.primaryReason || 'Clean Legitimate Traffic'}
                              </div>
                              {isMixed && (
                                <div className="text-[11px] text-slate-600 font-medium mt-1 text-pretty">
                                  Hostile stream blocked at switch hardware; genuine stream forwarded without interference.
                                </div>
                              )}
                            </td>

                            {/* Rule Priority */}
                            <td className="py-4.5 px-6">
                              {isMixed ? (
                                <div>
                                  <div className="mono tabular-nums font-bold text-slate-900 text-xs">P10 (Pass) / P65535 (Drop)</div>
                                  <div className="text-[10px] text-slate-500 font-semibold mt-0.5">Selective Flow Isolation</div>
                                </div>
                              ) : row.droppedPps > 0 || row.status === 'ACTIVE DROP' || row.status === 'RULE RETAINED' ? (
                                <div>
                                  <div className="mono tabular-nums font-bold text-red-700 text-sm">Priority 65535</div>
                                  <div className="text-[10px] text-red-600 font-medium">Hardware Drop Rule</div>
                                </div>
                              ) : (
                                <div>
                                  <div className="mono tabular-nums font-semibold text-emerald-700 text-sm">Priority 10</div>
                                  <div className="text-[10px] text-emerald-600 font-medium">Safe Forward Rule</div>
                                </div>
                              )}
                            </td>

                            {/* Defense Status */}
                            <td className="py-4.5 px-6 text-right">
                              {row.status === 'MIXED' ? (
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-800 border border-slate-300">
                                  <span className="flex items-center gap-1">
                                    <span className="size-1.5 rounded-full bg-emerald-600" />
                                    <span className="size-1.5 rounded-full bg-red-600" />
                                  </span>
                                  DUAL-STREAM · PARTIAL DROP
                                </span>
                              ) : row.status === 'ACTIVE DROP' ? (
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-800 border border-red-200">
                                  <span className="size-1.5 rounded-full bg-red-600 animate-ping" />
                                  ACTIVE DROP
                                </span>
                              ) : row.status === 'RULE RETAINED' ? (
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700 border border-slate-300">
                                  <span className="size-1.5 rounded-full bg-slate-500" />
                                  RULE RETAINED
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-100 px-3 py-1 text-xs font-bold text-emerald-800 border border-emerald-200">
                                  <span className="size-1.5 rounded-full bg-emerald-600" />
                                  CLEAN ALLOWED
                                </span>
                              )}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>

                    {/* Table Totals Footer Row */}
                    <tfoot className="border-t-2 border-slate-200 bg-slate-50/90 font-semibold text-slate-700 text-xs sm:text-sm">
                      <tr>
                        <td className="py-4 px-6" colSpan={2}>
                          <div className="flex items-center gap-2">
                            <span className="font-bold text-slate-900 uppercase tracking-wider text-xs">Switch s1 Sum</span>
                            <span className="text-xs text-slate-500 font-normal tabular-nums">({filteredIpEntries.length} hosts shown)</span>
                          </div>
                        </td>
                        <td className="py-4 px-6" colSpan={2}>
                          <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                            <div>
                              <span className="text-slate-500 text-xs font-medium">Passed: </span>
                              <span className="mono tabular-nums font-bold text-emerald-700">{totalVisiblePassed.toLocaleString()}</span>
                              <span className="text-[11px] text-slate-400"> pkts/s</span>
                            </div>
                            <div>
                              <span className="text-slate-500 text-xs font-medium">Blocked: </span>
                              <span className="mono tabular-nums font-bold text-red-700">{totalVisibleBlocked.toLocaleString()}</span>
                              <span className="text-[11px] text-slate-400"> pkts/s</span>
                            </div>
                            <div>
                              <span className="text-slate-500 text-xs font-medium">Total Ingress: </span>
                              <span className="mono tabular-nums font-bold text-slate-900">{totalVisibleIngress.toLocaleString()}</span>
                              <span className="text-[11px] text-slate-400"> pkts/s</span>
                            </div>
                          </div>
                        </td>
                        <td className="py-4 px-6 text-right" colSpan={2}>
                          {tableFilter === 'all' && !search.trim() ? (
                            <span className="inline-flex items-center gap-1.5 rounded-md bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700 border border-emerald-200">
                              <Icon name="check" size={13} />
                              100% KPI MATCH
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1.5 rounded-md bg-slate-100 px-2.5 py-1 text-xs font-semibold text-slate-600 tabular-nums">
                              Filtered View ({totalVisibleIngress.toLocaleString()} pkts/s)
                            </span>
                          )}
                        </td>
                      </tr>
                    </tfoot>
                  </table>

                  {!filteredIpEntries.length && (
                    <div className="py-16 text-center">
                      <div className="mx-auto flex size-12 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                        <Icon name="search" size={20} />
                      </div>
                      <p className="mt-3 text-sm font-medium text-slate-600 text-pretty">
                        {ipTrafficList.length
                          ? 'No host entries match the current search or filter criteria.'
                          : 'No host devices detected on switch s1. Network is idle.'}
                      </p>
                      {ipTrafficList.length > 0 && (tableFilter !== 'all' || search.trim()) && (
                        <button
                          onClick={() => {
                            setTableFilter('all')
                            setSearch('')
                          }}
                          className="mt-4 inline-flex items-center gap-1.5 rounded-lg bg-slate-900 px-4 py-2 text-xs font-semibold text-white hover:bg-slate-800 transition-all enabled:active:scale-[0.97] motion-reduce:enabled:active:scale-100"
                        >
                          <Icon name="refresh" size={13} />
                          Reset Filters &amp; Search
                        </button>
                      )}
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
