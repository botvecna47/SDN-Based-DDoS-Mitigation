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
  metrics: { ingressTb: number; droppedTb: number; activeRules: number; mlLatencyMs: number }
  traffic: { ingress: number[]; dropped: number[]; threshold: number }
  threats: Threat[]
  dropReasons: { reason: string; share: number }[]
}

export const endpoint = "http://192.168.8.147:5000/api/network-stats"

const baseIngress = [30,35,32,38,35,42,36,39,44,40,43,48,42,47,45,51,48,54,50,46,52,55,49,57,54,58,53,60,56,63,58,65,62,69,66,73,64,68,62,70,66,72,68,75,70,74,71,78]

export function demoSnapshot(attack = false, empty = false): Snapshot {
  if (empty) return {
    health: 'operational', endpointsOnline: 0, endpointsTotal: 0,
    metrics: { ingressTb: 0, droppedTb: 0, activeRules: 0, mlLatencyMs: 0 },
    traffic: { ingress: [], dropped: [], threshold: 72 }, threats: [], dropReasons: [],
  }
  const ingress = baseIngress.map((n, i) => attack && i > 31 ? Math.min(96, n + (i % 4) * 5 + 13) : n)
  return {
    health: attack ? 'degraded' : 'operational', endpointsOnline: 24, endpointsTotal: 24,
    metrics: { ingressTb: attack ? 32.89 : 24.89, droppedTb: attack ? 3.81 : 1.21, activeRules: attack ? 1285 : 1284, mlLatencyMs: attack ? 14.8 : 12.4 },
    traffic: { ingress, dropped: ingress.map((n, i) => Math.round(n * (attack && i > 31 ? .59 : .30) + Math.sin(i * 1.7) * 4 + 5)), threshold: 72 },
    threats: [
      ...(attack ? [{ ip: '203.0.113.241', country: 'Unknown origin', port: 443, protocol: 'TCP', reason: 'Simulated DDoS attack', time: 'Just now', score: 99, severity: 'Critical' as const }] : []),
      { ip: '185.220.101.47', country: 'Russia', port: 443, protocol: 'TCP', reason: 'DDoS pattern detected', time: '2 mins ago', score: 98, severity: 'Critical' },
      { ip: '103.253.24.89', country: 'China', port: 22, protocol: 'SSH', reason: 'Brute force attempt', time: '8 mins ago', score: 94, severity: 'Critical' },
      { ip: '45.155.205.233', country: 'Netherlands', port: 8080, protocol: 'TCP', reason: 'Suspicious port scanning', time: '14 mins ago', score: 87, severity: 'High' },
      { ip: '91.240.118.172', country: 'Ukraine', port: 3389, protocol: 'RDP', reason: 'Unauthorized access attempt', time: '26 mins ago', score: 82, severity: 'High' },
      { ip: '198.51.100.42', country: 'United States', port: 80, protocol: 'HTTP', reason: 'Unusual traffic volume', time: '41 mins ago', score: 76, severity: 'Medium' },
    ] as Threat[],
    dropReasons: attack
      ? [{ reason: 'DDoS mitigation', share: 61 }, { reason: 'Threat signatures', share: 19 }, { reason: 'Brute force', share: 13 }, { reason: 'Policy rules', share: 7 }]
      : [{ reason: 'DDoS mitigation', share: 43 }, { reason: 'Threat signatures', share: 28 }, { reason: 'Brute force', share: 18 }, { reason: 'Policy rules', share: 11 }],
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
