/** Contract for GET VITE_DEFENSE_API_URL. Values are display-ready. */
export type Threat = {
  ip: string
  country: string
  port: number
  protocol: string
  reason: string
  severity: 'Critical' | 'High' | 'Medium'
  mac?: string
  target?: string
  ratePps?: number
  action?: string
  status?: 'ACTIVE DROP' | 'RETAINED' | 'EXPIRED' | string
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
  dropReasons: { reason: string; share: number }[]
}

// Use .env variable if it exists, otherwise fallback to your specific VM IP
const envUrl = import.meta.env.VITE_DEFENSE_API_URL as string | undefined
export const endpoint = envUrl || "http://192.168.8.147:5000/api/network-stats"

// Baseline legitimate traffic in thousands of PPS (~0.7 to 0.9k PPS = 700-900 packets/sec)
export const baseIngress = [
  0.72, 0.78, 0.81, 0.75, 0.84, 0.79, 0.82, 0.86, 0.80, 0.77, 
  0.83, 0.88, 0.82, 0.79, 0.85, 0.81, 0.84, 0.89, 0.83, 0.80,
  0.78, 0.85, 0.82, 0.87, 0.81, 0.79, 0.84, 0.88, 0.83, 0.81,
  0.85, 0.89, 0.82, 0.86, 0.84, 0.88, 0.83, 0.80, 0.85, 0.87,
  0.82, 0.88, 0.84, 0.81, 0.86, 0.89, 0.83, 0.85
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
    traffic: { ingress: [], dropped: [], threshold: 10 }, threats: [], dropReasons: [],
  }

  const ingress = customIngress && customIngress.length === 48 
    ? customIngress 
    : (attack ? baseIngress.map((n, i) => i > 28 ? Number((22.0 + (i % 3) * 0.7).toFixed(2)) : n) : baseIngress)

  const dropped = customDropped && customDropped.length === 48
    ? customDropped
    : ingress.map(n => (n > 10 ? Number((n * 0.95).toFixed(2)) : 0))

  const latestVal = ingress[ingress.length - 1] ?? 0.8
  const latestDropVal = dropped[dropped.length - 1] ?? 0
  const currentPps = Math.round(latestVal * 1000)
  const droppedPps = Math.round(latestDropVal * 1000)
  const forwardedPps = Math.max(0, currentPps - droppedPps)
  const isAttackActive = latestVal > 10 || attack
  const hasBlockedThreat = isAttackActive || blocked

  return {
    health: isAttackActive ? 'degraded' : 'operational',
    detectionMode: 'simulation',
    endpointsOnline: 1, // Demo models the switch telemetry link, not each host's reachability.
    endpointsTotal: 1,
    metrics: {
      currentPps,
      droppedPps,
      forwardedPps,
      uptimeSec: 420,
      activeRules: hasBlockedThreat ? 5 : 4,
      mlLatencyMs: isAttackActive ? 3.4 : 2.8
    },
    traffic: {
      ingress,
      dropped,
      threshold: 10 // 10.0k PPS fallback threshold
    },
    threats: hasBlockedThreat ? [
      {
        ip: '10.0.0.2',
        country: 'h2 (Attacker Host)',
        port: 80,
        protocol: 'UDP Flood',
        reason: isAttackActive ? 'High-rate UDP Flood (>10,000 pkts/s)' : 'OpenFlow DROP Rule Retained (300s Idle Timeout)',
        severity: 'Critical',
        mac: '00:00:00:00:00:02',
        target: '10.0.0.3:80 (h3 Server)',
        ratePps: isAttackActive ? currentPps : 0,
        action: 'DROP (Priority 65535)',
        status: isAttackActive ? 'ACTIVE DROP' : 'RETAINED',
      }
    ] : [],
    dropReasons: hasBlockedThreat ? [{ reason: 'Simulated DDoS detection (Threshold >10k PPS)', share: 100 }] : [],
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
    !value.threats.every((item: unknown) => record(item) && typeof item.ip === 'string' && typeof item.country === 'string' && finite(item.port) && typeof item.protocol === 'string' && typeof item.reason === 'string' && ['Critical', 'High', 'Medium'].includes(String(item.severity))) ||
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
