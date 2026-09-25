# API Contract & Schema
## Backend ↔ Frontend Interface Agreement

> **Document Version:** 1.0  
> **Last Updated:** 2026-09-24  
> **Status:** Active — This is the binding contract between backend and frontend.

---

## Purpose

This document is the **formal contract** between the **Backend Developer (Lead)** and the **Frontend Developer (Friend 2)**.

- **Phase 1 (Frontend builds UI):** The frontend must build mock data matching these schemas *exactly* using `mockData.json` and simulate polling with `setInterval`. The backend is not needed yet.
- **Phase 2 (Integration):** The frontend swaps the mock data source for real Axios calls to the Flask API. **Zero schema changes should be needed** if both sides follow this contract.

> ⚠️ **Critical rule:** Never change a field name, type, or structure without updating this document AND notifying the other developer first.

---

## Base Configuration

| Property | Value |
|----------|-------|
| **Base URL** | `http://localhost:5000` |
| **Frontend URL** | `http://localhost:5173` |
| **CORS** | Enabled for `http://localhost:5173` only |
| **Polling Interval** | `1000ms` (1 second) |
| **Content-Type** | `application/json` |
| **Auth** | None (local dev only) |

---

## Endpoint 1: `GET /api/network-stats`

### Description

Returns the current real-time state of the SDN network. This is the **primary polling endpoint** that drives the dashboard's live chart, status badge, and PPS counter.

### Request

| Property | Value |
|----------|-------|
| Method | `GET` |
| Path | `/api/network-stats` |
| Parameters | None |
| Body | None |
| Headers | None required |

### Response — 200 OK

```json
{
  "status": "NORMAL",
  "current_pps": 245,
  "normal_baseline_pps": 280,
  "active_flows": 3,
  "blocked_count": 0,
  "timestamp": "2026-09-24T15:30:45.123Z",
  "controller_uptime_sec": 3600
}
```

### Field Descriptions

| Field | Type | Possible Values | Description |
|-------|------|-----------------|-------------|
| `status` | `string` | `"NORMAL"`, `"UNDER_ATTACK"`, `"MITIGATING"` | Current system state. Controls the colour of the status badge and whether the alert banner is shown. |
| `current_pps` | `integer` | `0` – `999999` | Packets per second observed across all flows in the last polling interval. |
| `normal_baseline_pps` | `integer` | `100` – `1000` | The rolling average PPS during non-attack periods. Used by the frontend to draw a reference line on the chart. |
| `active_flows` | `integer` | `0` – `999` | Number of active OpenFlow entries currently installed on the switch. |
| `blocked_count` | `integer` | `0` – `999` | Number of IPs currently blocked by DROP rules. Should match the length of the `/api/blocked-ips` array. |
| `timestamp` | `string` | ISO 8601 UTC | Server-side timestamp of when this snapshot was taken. Use for the X-axis of the live chart. |
| `controller_uptime_sec` | `integer` | `0` – `∞` | Seconds since the Ryu controller started. Used in the dashboard footer. |

### Status Codes

| Code | Meaning | Frontend Action |
|------|---------|-----------------|
| `200 OK` | Controller running, data valid | Update state and re-render |
| `503 Service Unavailable` | Controller is offline or restarting | Show "Controller Offline" toast, stop chart updates, keep last data visible, retry in 5s |

---

## Endpoint 2: `GET /api/blocked-ips`

### Description

Returns an array of all IP addresses currently blocked by the Ryu controller via DROP flow rules. Returns an **empty array `[]`** when no IPs are blocked — never returns `null`.

### Request

| Property | Value |
|----------|-------|
| Method | `GET` |
| Path | `/api/blocked-ips` |
| Parameters | None |
| Body | None |

### Response — 200 OK

```json
[
  {
    "ip": "10.0.0.2",
    "blocked_at": "2026-09-24T15:31:02.456Z",
    "reason": "DDoS - ML Classification",
    "packets_dropped": 45231,
    "pps_at_detection": 23450
  }
]
```

**When nothing is blocked:**

```json
[]
```

### Field Descriptions

| Field | Type | Possible Values | Description |
|-------|------|-----------------|-------------|
| `ip` | `string` | Valid IPv4 address | The source IP that was blocked. Display in the blocked-IPs table. |
| `blocked_at` | `string` | ISO 8601 UTC | Timestamp when the DROP rule was installed. Display as human-readable time (e.g., "3:31:02 PM"). |
| `reason` | `string` | `"DDoS - ML Classification"` | Human-readable reason for the block. Shown in the table's Reason column. |
| `packets_dropped` | `integer` | `0` – `999999999` | Running count of packets dropped by the DROP rule since it was installed. Update this value on each poll. |
| `pps_at_detection` | `integer` | `0` – `999999` | PPS rate at the moment the ML model triggered the detection. Shown in the alert details panel. |

---

## Axios Polling Example

This is the **reference implementation** for the frontend. Use this exact pattern in `useNetworkStats.js` (or equivalent):

```jsx
// frontend/src/hooks/useNetworkStats.js
import { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const BASE_URL = 'http://localhost:5000';
const POLL_INTERVAL_MS = 1000;
const RETRY_INTERVAL_MS = 5000;
const CHART_MAX_POINTS = 60; // Keep last 60 seconds of data

export function useNetworkStats() {
  const [networkStats, setNetworkStats] = useState(null);
  const [blockedIps, setBlockedIps]     = useState([]);
  const [timeSeriesData, setTimeSeriesData] = useState([]);
  const [isOffline, setIsOffline]       = useState(false);
  const [error, setError]               = useState(null);
  const intervalRef = useRef(null);

  const fetchData = async () => {
    try {
      const [statsRes, blockedRes] = await Promise.all([
        axios.get(`${BASE_URL}/api/network-stats`, { timeout: 3000 }),
        axios.get(`${BASE_URL}/api/blocked-ips`,   { timeout: 3000 }),
      ]);

      const stats = statsRes.data;
      const blocked = blockedRes.data;

      setNetworkStats(stats);
      setBlockedIps(blocked);
      setIsOffline(false);
      setError(null);

      // Append new point to time series, keep last N points
      setTimeSeriesData(prev => {
        const newPoint = {
          timestamp: stats.timestamp,
          pps:       stats.current_pps,
          baseline:  stats.normal_baseline_pps,
          status:    stats.status,
        };
        const updated = [...prev, newPoint];
        return updated.slice(-CHART_MAX_POINTS);
      });

      // Reset to fast polling if we were in retry mode
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = setInterval(fetchData, POLL_INTERVAL_MS);
      }

    } catch (err) {
      console.error('[useNetworkStats] Fetch failed:', err.message);
      setIsOffline(true);
      setError(err.message);

      // Switch to slower retry polling on error
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = setInterval(fetchData, RETRY_INTERVAL_MS);
      }
    }
  };

  useEffect(() => {
    // Fetch immediately on mount
    fetchData();

    // Start polling
    intervalRef.current = setInterval(fetchData, POLL_INTERVAL_MS);

    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { networkStats, blockedIps, timeSeriesData, isOffline, error };
}
```

**Usage in a component:**

```jsx
// frontend/src/components/Dashboard.jsx
import { useNetworkStats } from '../hooks/useNetworkStats';

export default function Dashboard() {
  const { networkStats, blockedIps, timeSeriesData, isOffline } = useNetworkStats();

  if (isOffline) {
    return <div className="toast-error">Controller Offline — retrying in 5s...</div>;
  }

  if (!networkStats) {
    return <div>Connecting to controller...</div>;
  }

  return (
    <div>
      <StatusBadge status={networkStats.status} />
      <PPSCounter current={networkStats.current_pps} />
      <LiveChart data={timeSeriesData} baseline={networkStats.normal_baseline_pps} />
      <BlockedIPsTable ips={blockedIps} />
    </div>
  );
}
```

---

## Error Handling

| Scenario | HTTP Code | Frontend Behaviour |
|----------|-----------|--------------------|
| Controller offline | `503` or network error | Show "Controller Offline" toast (red, persistent). Stop updating chart values but **keep last data visible** — do not blank out the chart. Auto-retry every **5 seconds**. When connection restores, dismiss toast and resume 1s polling. |
| Unexpected JSON shape | `200` but malformed | Log error to console. Do not update state with broken data. Show "Data Error" warning badge. |
| Request timeout (>3s) | Axios `ECONNABORTED` | Treat same as 503 — offline mode. |
| CORS error | Browser blocks request | This means the backend CORS config is wrong. Backend must allow `http://localhost:5173`. Check Flask-CORS config. |

---

## Mock Data File

> **Phase 1 instruction for Frontend Dev:** Copy the JSON below into `frontend/src/mockData.json`. In Phase 1, import this file instead of calling Axios. Use `setInterval` to cycle through `time_series_data` to simulate live polling.

```json
{
  "network_stats": {
    "normal_scenario": {
      "status": "NORMAL",
      "current_pps": 245,
      "normal_baseline_pps": 280,
      "active_flows": 3,
      "blocked_count": 0,
      "timestamp": "2026-09-24T15:30:45.123Z",
      "controller_uptime_sec": 3600
    },
    "attack_scenario": {
      "status": "UNDER_ATTACK",
      "current_pps": 24873,
      "normal_baseline_pps": 280,
      "active_flows": 3,
      "blocked_count": 0,
      "timestamp": "2026-09-24T15:31:01.456Z",
      "controller_uptime_sec": 3617
    },
    "mitigation_scenario": {
      "status": "MITIGATING",
      "current_pps": 18432,
      "normal_baseline_pps": 280,
      "active_flows": 4,
      "blocked_count": 1,
      "timestamp": "2026-09-24T15:31:07.789Z",
      "controller_uptime_sec": 3623
    }
  },
  "blocked_ips": [
    {
      "ip": "10.0.0.2",
      "blocked_at": "2026-09-24T15:31:02.456Z",
      "reason": "DDoS - ML Classification",
      "packets_dropped": 45231,
      "pps_at_detection": 23450
    },
    {
      "ip": "10.0.0.5",
      "blocked_at": "2026-09-24T15:31:45.112Z",
      "reason": "DDoS - ML Classification",
      "packets_dropped": 12874,
      "pps_at_detection": 19800
    },
    {
      "ip": "10.0.0.7",
      "blocked_at": "2026-09-24T15:32:10.334Z",
      "reason": "DDoS - ML Classification",
      "packets_dropped": 8934,
      "pps_at_detection": 15620
    }
  ],
  "time_series_data": [
    { "timestamp": "2026-09-24T15:30:00.000Z", "pps": 231, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:01.000Z", "pps": 248, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:02.000Z", "pps": 263, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:03.000Z", "pps": 271, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:04.000Z", "pps": 245, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:05.000Z", "pps": 259, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:06.000Z", "pps": 238, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:07.000Z", "pps": 276, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:08.000Z", "pps": 291, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:09.000Z", "pps": 254, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:10.000Z", "pps": 268, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:11.000Z", "pps": 243, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:12.000Z", "pps": 287, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:13.000Z", "pps": 261, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:14.000Z", "pps": 255, "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:15.000Z", "pps": 8420,  "baseline": 280, "status": "UNDER_ATTACK" },
    { "timestamp": "2026-09-24T15:30:16.000Z", "pps": 16340, "baseline": 280, "status": "UNDER_ATTACK" },
    { "timestamp": "2026-09-24T15:30:17.000Z", "pps": 23780, "baseline": 280, "status": "UNDER_ATTACK" },
    { "timestamp": "2026-09-24T15:30:18.000Z", "pps": 24873, "baseline": 280, "status": "UNDER_ATTACK" },
    { "timestamp": "2026-09-24T15:30:19.000Z", "pps": 24512, "baseline": 280, "status": "UNDER_ATTACK" },
    { "timestamp": "2026-09-24T15:30:20.000Z", "pps": 18432, "baseline": 280, "status": "MITIGATING" },
    { "timestamp": "2026-09-24T15:30:21.000Z", "pps": 12100, "baseline": 280, "status": "MITIGATING" },
    { "timestamp": "2026-09-24T15:30:22.000Z", "pps": 6540,  "baseline": 280, "status": "MITIGATING" },
    { "timestamp": "2026-09-24T15:30:23.000Z", "pps": 2103,  "baseline": 280, "status": "MITIGATING" },
    { "timestamp": "2026-09-24T15:30:24.000Z", "pps": 842,   "baseline": 280, "status": "MITIGATING" },
    { "timestamp": "2026-09-24T15:30:25.000Z", "pps": 314,   "baseline": 280, "status": "MITIGATING" },
    { "timestamp": "2026-09-24T15:30:26.000Z", "pps": 271,   "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:27.000Z", "pps": 258,   "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:28.000Z", "pps": 249,   "baseline": 280, "status": "NORMAL" },
    { "timestamp": "2026-09-24T15:30:29.000Z", "pps": 266,   "baseline": 280, "status": "NORMAL" }
  ]
}
```
