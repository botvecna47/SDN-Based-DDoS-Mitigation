// Configuration for SDN DDoS Dashboard API
export const API_CONFIG = {
  // Flask REST API Base URL
  BASE_URL: import.meta.env.VITE_API_BASE_URL || "http://localhost:5000",

  // Endpoints specified in project architecture
  ENDPOINTS: {
    NETWORK_STATS: "/api/network-stats",
    BLOCKED_IPS: "/api/blocked-ips",
    SYSTEM_HEALTH: "/api/system-health",
    TRIGGER_MITIGATION: "/api/mitigate"
  },

  // Polling rate: 1000ms (1 second) per project specification
  POLL_INTERVAL_MS: 1000,

  // Sliding window buffer size: keep max 30 points to prevent memory leaks/browser freezing
  MAX_CHART_POINTS: 30,

  // Default mode: "MOCK" allows standalone execution without backend
  // Set to "LIVE_API" when the Flask server is running
  DEFAULT_DATA_SOURCE: "MOCK"
};
