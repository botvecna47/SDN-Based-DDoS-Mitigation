/** Contract for GET VITE_DEFENSE_API_URL. Values are display-ready. */

export type FlowDetail = {
  protocol: string
  dstPort: number
  dstIp: string
  pps: number
  packets: number
  attackType?: string
  reason?: string
  priority?: number
}

export type IpTrafficEntry = {
  ip: string
  hostLabel: string
  mac?: string
  forwardedPps: number
  droppedPps: number
  ingressPps: number
  allowedFlows: FlowDetail[]
  blockedFlows: FlowDetail[]
  status: 'MIXED' | 'ACTIVE DROP' | 'RULE RETAINED' | 'ALLOWED' | string
  primaryReason?: string
  severity?: 'Critical' | 'High' | 'Medium' | 'Low' | 'Benign'
}

export type Threat = {
  ip: string
  country: string
  port: number
  protocol: string
  reason: string
  severity: 'Critical' | 'High' | 'Medium' | 'Low' | 'Benign'
  mac?: string
  target?: string
  ratePps?: number
  forwardedPps?: number
  droppedPps?: number
  ingressPps?: number
  action?: string
  status?: 'ACTIVE DROP' | 'RULE RETAINED' | 'MIXED' | 'EXPIRED' | 'ALLOWED' | string
  flows?: FlowDetail[]
}

export type Snapshot = {
  health: 'operational' | 'degraded' | 'offline'
  detectionMode: 'machine_learning' | 'threshold_fallback' | 'simulation'
  endpointsOnline: number
  endpointsTotal: number
  metrics: {
    currentPps?: number
    droppedPps?: number
    forwardedPps?: number
    uptimeSec?: number
    activeRules: number
    mlLatencyMs: number
  }
  traffic: { ingress: number[]; dropped: number[]; threshold: number }
  threats: Threat[]
  ipTraffic?: IpTrafficEntry[]
  dropReasons: { reason: string; share: number }[]
}

// Automatically adapt backend endpoint to the current browser host or .env
const envUrl = import.meta.env.VITE_DEFENSE_API_URL as string | undefined

export function getEndpoint(): string {
  if (envUrl && envUrl.trim()) {
    return envUrl.trim()
  }
  if (typeof window !== 'undefined' && window.location?.hostname) {
    // If running in browser and no envUrl set, connect to port 5000 on the same machine/IP
    return `http://${window.location.hostname}:5000/api/network-stats`
  }
  return "http://localhost:5000/api/network-stats"
}

export const endpoint = getEndpoint()

// Baseline legitimate traffic in thousands of PPS (~1.315k PPS = 1,315 packets/sec)
export const baseIngress = [
  1.28, 1.32, 1.35, 1.29, 1.34, 1.30, 1.33, 1.36, 1.31, 1.28, 
  1.34, 1.37, 1.32, 1.29, 1.35, 1.31, 1.34, 1.38, 1.33, 1.30,
  1.28, 1.35, 1.32, 1.37, 1.31, 1.29, 1.34, 1.38, 1.33, 1.31,
  1.35, 1.39, 1.32, 1.36, 1.34, 1.38, 1.33, 1.30, 1.35, 1.37,
  1.32, 1.38, 1.34, 1.31, 1.36, 1.39, 1.33, 1.35
]

export function demoSnapshot(
  attack = false, 
  empty = false,
  customIngress?: number[],
  customDropped?: number[],
  blocked = false
): Snapshot {
  if (empty) return {
    health: 'operational', detectionMode: 'simulation', endpointsOnline: 0, endpointsTotal: 1,
    metrics: { currentPps: 0, droppedPps: 0, forwardedPps: 0, uptimeSec: 0, activeRules: 0, mlLatencyMs: 0 },
    traffic: { ingress: [], dropped: [], threshold: 10 }, threats: [], ipTraffic: [], dropReasons: [],
  }

  const isAttackActive = attack
  const hasBlockedThreat = isAttackActive || blocked

  // Realistic per-IP demo data showing distinct IPs and same-IP mixed traffic
  const ipTraffic: IpTrafficEntry[] = hasBlockedThreat ? [
    {
      ip: '10.0.0.1',
      hostLabel: 'h1 (Legitimate Streamer)',
      mac: '00:00:00:00:00:01',
      forwardedPps: 820,
      droppedPps: 0,
      ingressPps: 820,
      allowedFlows: [{ protocol: 'UDP', dstPort: 5001, dstIp: '10.0.0.3', pps: 820, packets: 51200 }],
      blockedFlows: [],
      status: 'ALLOWED',
      primaryReason: 'Clean legitimate UDP video stream',
      severity: 'Benign'
    },
    {
      ip: '10.0.0.2',
      hostLabel: 'h2 (Mixed / Volumetric Node)',
      mac: '00:00:00:00:00:02',
      forwardedPps: 440,
      droppedPps: isAttackActive ? 9500 : 0,
      ingressPps: 440 + (isAttackActive ? 9500 : 0),
      allowedFlows: [{ protocol: 'UDP', dstPort: 5001, dstIp: '10.0.0.3', pps: 440, packets: 14200 }],
      blockedFlows: isAttackActive ? [{
        protocol: 'UDP', dstPort: 80, dstIp: '10.0.0.3', pps: 9500, packets: 95000,
        attackType: 'Volumetric UDP Flood', reason: 'High-rate volumetric flood (9,500 pkts/s) on port 80 detected by CIC-DDoS2019 Decision Tree',
        priority: 65535
      }] : [{
        protocol: 'UDP', dstPort: 80, dstIp: '10.0.0.3', pps: 0, packets: 95000,
        attackType: 'Volumetric UDP Flood', reason: 'Priority 65535 DROP rule retained (idle timeout active)',
        priority: 65535
      }],
      status: isAttackActive ? 'MIXED' : 'RULE RETAINED',
      primaryReason: 'Volumetric UDP Flood on port 80 (Legitimate stream on port 5001 forwarded)',
      severity: 'Critical'
    },
    {
      ip: '10.0.0.4',
      hostLabel: 'h4 (Mixed / TCP SYN Node)',
      mac: '00:00:00:00:00:04',
      forwardedPps: 230,
      droppedPps: isAttackActive ? 6800 : 0,
      ingressPps: 230 + (isAttackActive ? 6800 : 0),
      allowedFlows: [{ protocol: 'UDP', dstPort: 53, dstIp: '10.0.0.3', pps: 230, packets: 7800 }],
      blockedFlows: isAttackActive ? [{
        protocol: 'TCP', dstPort: 80, dstIp: '10.0.0.3', pps: 6800, packets: 68000,
        attackType: 'TCP SYN Flood', reason: 'TCP SYN handshake flood (6,800 pkts/s) on port 80 detected by CIC-DDoS2019 Decision Tree',
        priority: 65535
      }] : [{
        protocol: 'TCP', dstPort: 80, dstIp: '10.0.0.3', pps: 0, packets: 68000,
        attackType: 'TCP SYN Flood', reason: 'Priority 65535 DROP rule retained',
        priority: 65535
      }],
      status: isAttackActive ? 'MIXED' : 'RULE RETAINED',
      primaryReason: 'TCP SYN Handshake Flood on port 80 (Legitimate DNS queries forwarded)',
      severity: 'Critical'
    },
    {
      ip: '10.0.0.5',
      hostLabel: 'h5 (Slowloris Node)',
      mac: '00:00:00:00:00:05',
      forwardedPps: 0,
      droppedPps: isAttackActive ? 48 : 0,
      ingressPps: isAttackActive ? 48 : 0,
      allowedFlows: [],
      blockedFlows: [{
        protocol: 'TCP', dstPort: 80, dstIp: '10.0.0.3', pps: isAttackActive ? 48 : 0, packets: 1440,
        attackType: 'Slowloris Starvation', reason: 'Slowloris connection starvation on port 80 detected by CIC-DDoS2019 Decision Tree',
        priority: 65535
      }],
      status: isAttackActive ? 'ACTIVE DROP' : 'RULE RETAINED',
      primaryReason: 'Slowloris HTTP connection starvation (low-and-slow socket exhaustion)',
      severity: 'High'
    },
    {
      ip: '10.0.0.6',
      hostLabel: 'h6 (ICMP Flood Node)',
      mac: '00:00:00:00:00:06',
      forwardedPps: 0,
      droppedPps: isAttackActive ? 5200 : 0,
      ingressPps: isAttackActive ? 5200 : 0,
      allowedFlows: [],
      blockedFlows: [{
        protocol: 'ICMP', dstPort: 0, dstIp: '10.0.0.3', pps: isAttackActive ? 5200 : 0, packets: 52000,
        attackType: 'ICMP Echo Flood', reason: 'High-rate ICMP echo flood (5,200 pkts/s) detected by CIC-DDoS2019 Decision Tree',
        priority: 65535
      }],
      status: isAttackActive ? 'ACTIVE DROP' : 'RULE RETAINED',
      primaryReason: 'High-Rate ICMP Echo Ping Flood',
      severity: 'Critical'
    },
    {
      ip: '10.0.0.7',
      hostLabel: 'h7 (High-Port UDP Node)',
      mac: '00:00:00:00:00:07',
      forwardedPps: 0,
      droppedPps: isAttackActive ? 11400 : 0,
      ingressPps: isAttackActive ? 11400 : 0,
      allowedFlows: [],
      blockedFlows: [{
        protocol: 'UDP', dstPort: 8080, dstIp: '10.0.0.3', pps: isAttackActive ? 11400 : 0, packets: 114000,
        attackType: 'High-Port UDP Flood', reason: 'High-port volumetric UDP flood (11,400 pkts/s) on port 8080 detected by CIC-DDoS2019 Decision Tree',
        priority: 65535
      }],
      status: isAttackActive ? 'ACTIVE DROP' : 'RULE RETAINED',
      primaryReason: 'High-Port / Amplification UDP Flood on port 8080',
      severity: 'Critical'
    },
    {
      ip: '10.0.0.8',
      hostLabel: 'h8 (Pulsing Wave Node)',
      mac: '00:00:00:00:00:08',
      forwardedPps: 0,
      droppedPps: isAttackActive ? 7600 : 0,
      ingressPps: isAttackActive ? 7600 : 0,
      allowedFlows: [],
      blockedFlows: [{
        protocol: 'UDP', dstPort: 53, dstIp: '10.0.0.3', pps: isAttackActive ? 7600 : 0, packets: 76000,
        attackType: 'Pulsing Wave DDoS', reason: 'Periodic pulsing wave burst attack (10s ON / 5s OFF on :53) detected by CIC-DDoS2019 Decision Tree',
        priority: 65535
      }],
      status: isAttackActive ? 'ACTIVE DROP' : 'RULE RETAINED',
      primaryReason: 'Dynamic Pulsing / Wave DDoS (10s ON / 5s OFF bursts on port 53)',
      severity: 'Critical'
    },
    {
      ip: '10.0.0.11',
      hostLabel: 'h11 (Legitimate Web Client)',
      mac: '00:00:00:00:00:11',
      forwardedPps: 310,
      droppedPps: 0,
      ingressPps: 310,
      allowedFlows: [{ protocol: 'TCP', dstPort: 80, dstIp: '10.0.0.3', pps: 310, packets: 9800 }],
      blockedFlows: [],
      status: 'ALLOWED',
      primaryReason: 'Legitimate HTTP web browsing sessions',
      severity: 'Benign'
    },
    {
      ip: '10.0.0.12',
      hostLabel: 'h12 (Legitimate DNS Client)',
      mac: '00:00:00:00:00:12',
      forwardedPps: 185,
      droppedPps: 0,
      ingressPps: 185,
      allowedFlows: [{ protocol: 'UDP', dstPort: 53, dstIp: '10.0.0.3', pps: 185, packets: 5600 }],
      blockedFlows: [],
      status: 'ALLOWED',
      primaryReason: 'Standard recursive DNS lookups',
      severity: 'Benign'
    }
  ] : [
    {
      ip: '10.0.0.1',
      hostLabel: 'h1 (Legitimate Streamer)',
      mac: '00:00:00:00:00:01',
      forwardedPps: 820,
      droppedPps: 0,
      ingressPps: 820,
      allowedFlows: [{ protocol: 'UDP', dstPort: 5001, dstIp: '10.0.0.3', pps: 820, packets: 51200 }],
      blockedFlows: [],
      status: 'ALLOWED',
      primaryReason: 'Clean legitimate UDP video stream',
      severity: 'Benign'
    },
    {
      ip: '10.0.0.11',
      hostLabel: 'h11 (Legitimate Web Client)',
      mac: '00:00:00:00:00:11',
      forwardedPps: 310,
      droppedPps: 0,
      ingressPps: 310,
      allowedFlows: [{ protocol: 'TCP', dstPort: 80, dstIp: '10.0.0.3', pps: 310, packets: 9800 }],
      blockedFlows: [],
      status: 'ALLOWED',
      primaryReason: 'Legitimate HTTP web browsing sessions',
      severity: 'Benign'
    },
    {
      ip: '10.0.0.12',
      hostLabel: 'h12 (Legitimate DNS Client)',
      mac: '00:00:00:00:00:12',
      forwardedPps: 185,
      droppedPps: 0,
      ingressPps: 185,
      allowedFlows: [{ protocol: 'UDP', dstPort: 53, dstIp: '10.0.0.3', pps: 185, packets: 5600 }],
      blockedFlows: [],
      status: 'ALLOWED',
      primaryReason: 'Standard recursive DNS lookups',
      severity: 'Benign'
    }
  ]

  // Calculate exact sums
  const forwardedPps = ipTraffic.reduce((sum, item) => sum + item.forwardedPps, 0)
  const droppedPps = ipTraffic.reduce((sum, item) => sum + item.droppedPps, 0)
  const currentPps = forwardedPps + droppedPps

  // Build chart history points matching sum
  const ingress = customIngress && customIngress.length === 48 
    ? customIngress 
    : (isAttackActive ? baseIngress.map((n, i) => i > 28 ? Number((currentPps / 1000.0 + (i % 3) * 0.4).toFixed(2)) : n) : baseIngress)

  const dropped = customDropped && customDropped.length === 48
    ? customDropped
    : (isAttackActive ? ingress.map((n, i) => i > 28 ? Number((droppedPps / 1000.0).toFixed(2)) : 0) : new Array(48).fill(0))

  // Threats array for table compatibility
  const threats: Threat[] = ipTraffic
    .filter(e => e.droppedPps > 0 || e.blockedFlows.length > 0)
    .map(e => {
      const bf = e.blockedFlows[0] || {}
      return {
        ip: e.ip,
        country: e.hostLabel,
        mac: e.mac,
        port: bf.dstPort || 80,
        protocol: bf.attackType || bf.protocol || 'Attack Flow',
        target: `10.0.0.3:${bf.dstPort || 80}`,
        reason: e.primaryReason || 'Mitigated Hostile Flow',
        severity: e.severity || 'Critical',
        ratePps: e.droppedPps,
        forwardedPps: e.forwardedPps,
        droppedPps: e.droppedPps,
        ingressPps: e.ingressPps,
        action: 'DROP (Priority 65535)',
        status: e.status,
        flows: [...e.blockedFlows, ...e.allowedFlows]
      }
    })

  const dropReasons = hasBlockedThreat ? [
    { reason: 'Volumetric UDP Flood (:80)', share: 24 },
    { reason: 'High-Port UDP Flood (:8080)', share: 28 },
    { reason: 'Pulsing Wave DDoS (:53)', share: 19 },
    { reason: 'TCP SYN Handshake Flood (:80)', share: 16 },
    { reason: 'ICMP Echo Flood', share: 13 },
  ] : []

  return {
    health: isAttackActive ? 'degraded' : 'operational',
    detectionMode: 'simulation',
    endpointsOnline: 1,
    endpointsTotal: 1,
    metrics: {
      currentPps,
      droppedPps,
      forwardedPps,
      uptimeSec: 420,
      activeRules: hasBlockedThreat ? 14 : 6,
      mlLatencyMs: isAttackActive ? 0.24 : 0.18
    },
    traffic: {
      ingress,
      dropped,
      threshold: 10
    },
    threats,
    ipTraffic,
    dropReasons
  }
}

const record = (value: unknown): value is Record<string, unknown> => typeof value === 'object' && value !== null && !Array.isArray(value)
const finite = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value) && value >= 0
const numberArray = (value: unknown): value is number[] => Array.isArray(value) && value.every(finite)

export function parseSnapshot(value: unknown): Snapshot {
  if (!record(value) || !record(value.metrics) || !record(value.traffic) || !Array.isArray(value.threats) || !Array.isArray(value.dropReasons)) {
    throw new Error('Invalid telemetry response. Check the dashboard API contract.')
  }
  const { metrics, traffic } = value
  if (!['operational', 'degraded', 'offline'].includes(String(value.health)) || !['machine_learning', 'threshold_fallback', 'simulation'].includes(String(value.detectionMode)) || !finite(value.endpointsOnline) || !finite(value.endpointsTotal) ||
    !finite(metrics.activeRules) || !finite(metrics.mlLatencyMs) ||
    !numberArray(traffic.ingress) || !numberArray(traffic.dropped) || traffic.ingress.length !== traffic.dropped.length || !finite(traffic.threshold) ||
    !value.threats.every((item: unknown) => record(item) && typeof item.ip === 'string' && typeof item.country === 'string' && finite(item.port) && typeof item.protocol === 'string' && typeof item.reason === 'string') ||
    !value.dropReasons.every((item: unknown) => record(item) && typeof item.reason === 'string' && finite(item.share) && item.share <= 100)) {
    throw new Error('Invalid telemetry values. Check the dashboard API contract.')
  }
  return value as Snapshot
}

export async function fetchSnapshot(signal: AbortSignal): Promise<Snapshot> {
  if (!endpoint) throw new Error('No backend endpoint configured. Set VITE_DEFENSE_API_URL to enable live mode.')
  const url = new URL(endpoint, window.location.href)
  const response = await fetch(url, { signal, headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`Telemetry request failed (${response.status}). Check your connection and try again.`)
  return parseSnapshot(await response.json())
}
