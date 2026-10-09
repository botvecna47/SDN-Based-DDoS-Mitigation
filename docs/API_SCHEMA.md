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
  "endpointsOnline": 4,
  "endpointsTotal": 4,
  "metrics": {
    "ingressTb": 0.03,
    "droppedTb": 0.0,
    "activeRules": 3,
    "mlLatencyMs": 3.1
  },
  "traffic": {
    "ingress": [0.0, 0.0, 0.8, 0.7, 0.9],
    "dropped": [0.0, 0.0, 0.0],
    "threshold": 8
  },
  "threats": [
    {
      "ip": "10.0.0.2",
      "country": "Local Mininet",
      "port": 80,
      "protocol": "UDP",
      "reason": "DDoS Signature Detected by ML",
      "score": 98,
      "severity": "Critical",
      "time": "Just now"
    }
  ],
  "dropReasons": [
    {"reason": "ML DDoS Classification", "share": 72},
    {"reason": "PPS Threshold Breach", "share": 18},
    {"reason": "OpenFlow DROP Rule", "share": 10}
  ]
}
```
*   `health`: `"operational"` or `"degraded"`.
*   `traffic.ingress[]` and `dropped[]`: Arrays of PPS values in thousands.
*   `traffic.threshold`: The trigger point (e.g., 8 = 8,000 PPS).
*   `threats[]`: Structured objects if blocked IPs exist; empty otherwise.
*   `dropReasons[]`: Populated during attacks; empty normally.

## 4. Endpoint 2: `GET /api/flow-table`

Fetches a snapshot of OpenFlow rules currently installed on the switch.

**Response Schema:**
```json
{
  "summary": {
    "description": "OpenFlow 1.3 flow rules currently installed on OVS Switch s1",
    "allowed_flows": [
      {
        "match": "h1 (10.0.0.1) to h3 (10.0.0.3)",
        "action": "FORWARD",
        "priority": 1,
        "reason": "Legitimate user traffic",
        "status": "ALLOWED"
      }
    ],
    "blocked_flows": [
      {
        "match": "src=10.0.0.2 to any",
        "action": "DROP",
        "priority": 65535,
        "reason": "DDoS detected",
        "status": "BLOCKED"
      }
    ],
    "table_miss": {
      "match": "*",
      "action": "SEND_TO_CONTROLLER",
      "priority": 0,
      "reason": "Unknown flows sent to Ryu for MAC learning",
      "status": "CONTROLLER"
    }
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
The UI rigorously checks runtime typing:
- Ensures `health` is strictly `"operational"` or `"degraded"`.
- Validates arrays (`traffic.ingress`, `threats`) and assigns fallbacks.
- Drops invalid payloads to prevent UI crashes.

## 8. Configuration
To override the default endpoint in local development, create a `.env` file at the root of the React project:
```env
VITE_DEFENSE_API_URL=http://192.168.8.147:5000/api/network-stats
```

*Last Updated: 2026-10-09*
