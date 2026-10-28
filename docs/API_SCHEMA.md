# API Schema

This document outlines the API contract between the Flask backend and the React frontend.

## 1. Purpose
The backend exposes a consolidated set of endpoints. Notably, a single endpoint (`/api/network-stats`) drives the entire dashboard's visual state, metrics, chart data, and blocked IPs. There is no separate blocked IPs endpoint.

## 2. Base Configuration

| Property | Value |
|---|---|
| **Base URL** | `http://192.168.8.147:5000` (configurable via `.env`) |
| **CORS** | `*` (All origins allowed) |
| **Polling Interval** | 1 second via `setInterval` in React |
| **HTTP Client** | Native `fetch` API (No Axios) |

## 3. Endpoint 1: `GET /api/network-stats`

Returns the full `Snapshot` object representing the immediate state of the network. The backend calculates a rolling 48-tick history for chart rendering.

**Response Schema:**
```json
{
  "health": "operational", 
  "detectionMode": "threshold_fallback",
  "endpointsOnline": 1,
  "endpointsTotal": 1,
  "metrics": {
    "currentPps": 850,
    "uptimeSec": 120,
    "activeRules": 3,
    "mlLatencyMs": 3.1
  },
  "traffic": {
    "ingress": [0.0, 0.0, 0.8, 0.7, 0.9],
    "dropped": [0.0, 0.0, 0.0, 0.0, 0.0],
    "threshold": 10
  },
  "threats": [
    {
      "ip": "10.0.0.2",
      "country": "Local Mininet",
      "port": 80,
      "protocol": "UDP",
      "reason": "DDoS detected by PPS threshold fallback",
      "severity": "Critical"
    }
  ],
  "dropReasons": [
    {"reason": "PPS threshold fallback", "share": 100}
  ]
}
```
*   `health`: `"operational"`, `"degraded"`, or `"offline"` when the switch has stopped sending fresh statistics.
*   `endpointsOnline` and `endpointsTotal`: These count the switch telemetry link (0/1); they do not verify each Mininet host's reachability.
*   `detectionMode`: `"machine_learning"` when the model is loaded, otherwise `"threshold_fallback"`; demo snapshots use `"simulation"`.
*   `traffic.ingress[]` and `dropped[]`: Arrays of PPS values in thousands; dropped values come from OVS DROP-flow counters.
*   `traffic.threshold`: The per-flow fallback trigger point, in thousands of packets per second. The dashboard obtains this value from the shared controller configuration through the API.
*   `threats[]`: Structured objects if blocked IPs exist; empty otherwise.
*   `dropReasons[]`: Populated during attacks; empty normally.

## 4. Endpoint 2: `GET /api/flow-table`

Fetches a snapshot of OpenFlow rules currently installed on the switch.

**Response Schema:**
```json
{
  "summary": {
    "description": "Latest OpenFlow 1.3 flow-stat snapshot reported by OVS Switch s1",
    "connected": true,
    "snapshotAgeSeconds": 0.4,
    "allowed_flows": [
      {
        "match": {"ipv4_src": "10.0.0.1", "ipv4_dst": "10.0.0.3"},
        "action": "FORWARD",
        "priority": 1,
        "packets": 1200,
        "bytes": 84000,
        "status": "ALLOWED"
      }
    ],
    "blocked_flows": [
      {
        "match": {"ipv4_src": "10.0.0.2"},
        "action": "DROP",
        "priority": 65535,
        "packets": 85000,
        "bytes": 5100000,
        "status": "BLOCKED"
      }
    ],
    "table_miss": {
      "match": {},
      "action": "SEND_TO_CONTROLLER",
      "priority": 0,
      "packets": 0,
      "bytes": 0,
      "status": "CONTROLLER"
    },
    "other_flows": []
  }
}
```

## 5. Endpoint 3: `GET /api/health`

Basic liveness probe.

**Response Schema:**
```json
{
  "status": "ok"
}
```

## 6. Frontend Fetch Pattern

The React frontend handles fetching data using the native `fetch` API:

```typescript
export async function fetchSnapshot(url: string): Promise<Snapshot> {
  const response = await fetch(url);
  if (!response.ok) throw new Error('Network response was not ok');
  const data = await response.json();
  return parseSnapshot(data);
}
```

## 7. `parseSnapshot()` Validation Rules
The UI checks health and detection-mode enums, non-negative numeric metrics, equal-length ingress/drop arrays, threshold value, and threat/drop-reason fields. Invalid payloads are rejected and shown as a connection/contract error.

## 8. Configuration
To override the default endpoint in local development, create a `.env` file at the root of the React project:
```env
VITE_DEFENSE_API_URL=http://192.168.8.147:5000/api/network-stats
```

*Last Updated: 2026-10-28*
