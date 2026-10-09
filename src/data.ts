/** Contract for GET VITE_DEFENSE_API_URL?range=24h|7d|30d. Values are display-ready. */
export type Threat = {
  ip: string
  country: string
  port: number
  protocol: string
  reason: string
  score: number
  severity: 'Critical' | 'High' | 'Medium'
  time: string
}

export type Snapshot = {
  health: 'operational' | 'degraded'
  endpointsOnline: number
  endpointsTotal: number
  metrics: {
    currentPps?: number
    uptimeSec?: number
    ingressTb: number
    droppedTb: number
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
const baseIngress = [
  0.72, 0.78, 0.81, 0.75, 0.84, 0.79, 0.82, 0.86, 0.80, 0.77, 
  0.83, 0.88, 0.82, 0.79, 0.85, 0.81, 0.84, 0.89, 0.83, 0.80,
  0.78, 0.85, 0.82, 0.87, 0.81, 0.79, 0.84, 0.88, 0.83, 0.81,
  0.85, 0.89, 0.82, 0.86, 0.84, 0.88, 0.83, 0.80, 0.85, 0.87,
  0.82, 0.88, 0.84, 0.81, 0.86, 0.89, 0.83, 0.85
]

export function demoSnapshot(attack = false, empty = false): Snapshot {
  if (empty) return {
    health: 'operational', endpointsOnline: 0, endpointsTotal: 0,
    metrics: { currentPps: 0, uptimeSec: 0, ingressTb: 0, droppedTb: 0, activeRules: 0, mlLatencyMs: 0 },
    traffic: { ingress: [], dropped: [], threshold: 8 }, threats: [], dropReasons: [],
  }
  // If attack simulated, last 16 ticks surge to 20-25k PPS (flood)
  const ingress = baseIngress.map((n, i) => attack && i > 31 ? 21.5 + (i % 4) * 0.8 : n)
  const dropped = ingress.map((n, i) => (attack && i > 31 ? Number((n * 0.95).toFixed(2)) : 0))

  return {
    health: attack ? 'degraded' : 'operational',
    endpointsOnline: 4, // h1, h2, h3, s1
    endpointsTotal: 4,
    metrics: {
      currentPps: attack ? 22400 : 850,
      uptimeSec: 360,
      ingressTb: attack ? 0.08 : 0.04,
      droppedTb: attack ? 0.07 : 0.00,
      activeRules: attack ? 5 : 4,
      mlLatencyMs: attack ? 3.4 : 2.9
    },
    traffic: {
      ingress,
      dropped,
      threshold: 8 // 8.0k PPS threshold
    },
    threats: [
      ...(attack ? [{
        ip: '10.0.0.2',
        country: 'h2 (Attacker Host)',
        port: 80,
        protocol: 'UDP',
        reason: 'hping3 UDP Flood (>20k PPS)',
        time: 'Active',
        score: 99,
        severity: 'Critical' as const
      }] : []),
      {
        ip: '10.0.0.2',
        country: 'h2 (Attacker Host)',
        port: 80,
        protocol: 'UDP',
        reason: 'Volumetric Rate Spike Anomaly',
        time: '1 min ago',
        score: 98,
        severity: 'Critical'
      }
    ] as Threat[],
    dropReasons: attack
      ? [
          { reason: 'ML DDoS Model', share: 72 },
          { reason: 'PPS Threshold Spike', share: 18 },
          { reason: 'OpenFlow L3/L4 Match', share: 10 }
        ]
      : [
          { reason: 'ML DDoS Model', share: 72 },
          { reason: 'PPS Threshold Spike', share: 18 },
          { reason: 'OpenFlow L3/L4 Match', share: 10 }
        ],
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
  if ((value.health !== 'operational' && value.health !== 'degraded') || !finite(value.endpointsOnline) || !finite(value.endpointsTotal) ||
    !finite(metrics.ingressTb) || !finite(metrics.droppedTb) || !finite(metrics.activeRules) || !finite(metrics.mlLatencyMs) ||
    !numberArray(traffic.ingress) || !numberArray(traffic.dropped) || traffic.ingress.length !== traffic.dropped.length || !finite(traffic.threshold) ||
    !value.threats.every((item: unknown) => record(item) && typeof item.ip === 'string' && typeof item.country === 'string' && finite(item.port) && typeof item.protocol === 'string' && typeof item.reason === 'string' && finite(item.score) && item.score <= 100 && ['Critical', 'High', 'Medium'].includes(String(item.severity)) && typeof item.time === 'string') ||
    !value.dropReasons.every((item: unknown) => record(item) && typeof item.reason === 'string' && finite(item.share) && item.share <= 100)) {
    throw new Error('Invalid telemetry values. Check the dashboard API contract.')
  }
  return value as Snapshot
}

export async function fetchSnapshot(range: string, signal: AbortSignal): Promise<Snapshot> {
  if (!endpoint) throw new Error('No backend endpoint configured. Set VITE_DEFENSE_API_URL to enable live mode.')
  const url = new URL(endpoint, window.location.href)
  url.searchParams.set('range', range)
  const response = await fetch(url, { signal, headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`Telemetry request failed (${response.status}). Check your connection and try again.`)
  return parseSnapshot(await response.json())
}
