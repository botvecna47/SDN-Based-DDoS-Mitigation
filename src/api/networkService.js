import { API_CONFIG } from './config';
import { generateNetworkTick, getBlockedIpsSnapshot } from '../data/mockDataGenerator';

/**
 * Service to fetch live telemetry from Flask REST API or mock generator
 */
export const networkService = {
  /**
   * Fetch network traffic statistics
   * @param {string} dataSource - 'MOCK' | 'LIVE_API'
   * @param {string} mockScenario - 'NORMAL' | 'UNDER_ATTACK' | 'MITIGATING' | 'OFFLINE'
   */
  async fetchNetworkStats(dataSource = 'MOCK', mockScenario = 'NORMAL') {
    if (dataSource === 'MOCK') {
      if (mockScenario === 'OFFLINE') {
        throw new Error('SDN Controller unreachable (Simulated Offline)');
      }
      return generateNetworkTick(mockScenario);
    }

    // Live API mode (Flask endpoint)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000); // 2s timeout

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.NETWORK_STATS}`, {
        signal: controller.signal,
        headers: {
          'Accept': 'application/json'
        }
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`API error HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      return {
        ...data,
        displayTime: new Date(data.timestamp || Date.now()).toTimeString().split(' ')[0]
      };
    } catch (err) {
      clearTimeout(timeoutId);
      throw err;
    }
  },

  /**
   * Fetch list of blocked IPs from the controller
   * @param {string} dataSource - 'MOCK' | 'LIVE_API'
   */
  async fetchBlockedIps(dataSource = 'MOCK') {
    if (dataSource === 'MOCK') {
      return getBlockedIpsSnapshot();
    }

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000);

    try {
      const response = await fetch(`${API_CONFIG.BASE_URL}${API_CONFIG.ENDPOINTS.BLOCKED_IPS}`, {
        signal: controller.signal,
        headers: {
          'Accept': 'application/json'
        }
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        throw new Error(`API error HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      // Handle both { blocked_list: [...] } and direct array [...]
      return Array.isArray(data) ? data : (data.blocked_list || []);
    } catch (err) {
      clearTimeout(timeoutId);
      throw err;
    }
  }
};
