import { useState, useEffect, useRef, useCallback } from 'react';
import { networkService } from '../api/networkService';
import { API_CONFIG } from '../api/config';
import { addBlockedIpFromAttack } from '../data/mockDataGenerator';

export function useNetworkData() {
  const [dataSource, setDataSource] = useState(API_CONFIG.DEFAULT_DATA_SOURCE);
  const [mockScenario, setMockScenario] = useState('NORMAL'); // 'NORMAL' | 'UNDER_ATTACK' | 'MITIGATING' | 'OFFLINE'
  const [trafficHistory, setTrafficHistory] = useState(() => {
    // Generate initial 20 points of history for immediate visual impact
    const initial = [];
    const now = Date.now();
    for (let i = 20; i >= 1; i--) {
      const time = new Date(now - i * 1000).toTimeString().split(' ')[0];
      const pps = Math.round(820 + (Math.random() - 0.5) * 50);
      initial.push({
        time,
        total_pps: pps,
        normal_pps: pps,
        dropped_pps: 0,
        bandwidth_mbps: 7.8,
        status: 'NORMAL'
      });
    }
    return initial;
  });

  const [currentStats, setCurrentStats] = useState(null);
  const [blockedIps, setBlockedIps] = useState([]);
  const [controllerOnline, setControllerOnline] = useState(true);
  const [toast, setToast] = useState(null);
  const [lastAttackIp, setLastAttackIp] = useState(null);

  const prevStatusRef = useRef('NORMAL');
  const attackTickCountRef = useRef(0);

  // Helper to show transient toast alerts
  const showToast = useCallback((message, type = 'info', duration = 4000) => {
    setToast({ message, type, id: Date.now() });
    setTimeout(() => {
      setToast(curr => (curr && curr.message === message ? null : curr));
    }, duration);
  }, []);

  // Poll cycle every 1000ms
  useEffect(() => {
    let isMounted = true;

    const poll = async () => {
      try {
        // 1. Fetch latest stats
        const stats = await networkService.fetchNetworkStats(dataSource, mockScenario);
        if (!isMounted) return;

        setControllerOnline(true);
        setCurrentStats(stats);

        // Append to sliding window chart history (capped at MAX_CHART_POINTS)
        setTrafficHistory(prev => {
          const newPoint = {
            time: stats.displayTime || new Date().toTimeString().split(' ')[0],
            total_pps: stats.total_pps,
            normal_pps: stats.normal_pps,
            dropped_pps: stats.dropped_pps,
            bandwidth_mbps: stats.bandwidth_mbps,
            status: stats.status
          };
          const updated = [...prev, newPoint];
          if (updated.length > API_CONFIG.MAX_CHART_POINTS) {
            return updated.slice(updated.length - API_CONFIG.MAX_CHART_POINTS);
          }
          return updated;
        });

        // 2. State transition detection & automatic alert toasts
        if (prevStatusRef.current !== stats.status) {
          if (stats.status === 'UNDER_ATTACK') {
            showToast('⚠️ CRITICAL: High-rate DDoS attack detected! ML classification triggered.', 'danger', 5000);
          } else if (stats.status === 'MITIGATING') {
            showToast('🛡️ MITIGATION ACTIVE: SDN Controller installing OpenFlow DROP rules.', 'warning', 4000);
          } else if (stats.status === 'NORMAL' && prevStatusRef.current !== 'NORMAL') {
            showToast('✅ ATTACK NEUTRALIZED: Network traffic stabilized to normal levels.', 'success', 4000);
          }
          prevStatusRef.current = stats.status;
        }

        // In Mock mode, when under attack for a few seconds, auto-generate a blocked IP event
        if (dataSource === 'MOCK' && mockScenario === 'UNDER_ATTACK') {
          attackTickCountRef.current++;
          if (attackTickCountRef.current % 4 === 0) {
            const attackIps = ['10.0.0.7', '10.0.0.18', '192.168.1.105', '172.16.0.44'];
            const targetIp = attackIps[Math.floor(Math.random() * attackIps.length)];
            const newBlock = addBlockedIpFromAttack(targetIp, 'ML Threshold Exceeded (PPS > 8,000)');
            setLastAttackIp(targetIp);
            showToast(`🛑 OpenFlow Rule Pushed: Blocked attacker IP ${targetIp}`, 'danger', 4000);
          }
        }

        // 3. Fetch blocked IPs list
        const ips = await networkService.fetchBlockedIps(dataSource);
        if (isMounted) {
          setBlockedIps(ips);
        }
      } catch (err) {
        if (!isMounted) return;
        setControllerOnline(false);
        showToast(`Controller Offline: ${err.message || 'Connection refused'}`, 'danger', 3000);
      }
    };

    // Initial immediate tick
    poll();

    // 1-second polling interval
    const intervalId = setInterval(poll, API_CONFIG.POLL_INTERVAL_MS);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, [dataSource, mockScenario, showToast]);

  // Actions for manual presentation demo
  const triggerAttack = useCallback((type = 'SYN_FLOOD') => {
    setMockScenario('UNDER_ATTACK');
    showToast(`🚨 hping3 Attack Injected (${type})! Traffic spiking...`, 'danger');
  }, [showToast]);

  const triggerMitigation = useCallback(() => {
    setMockScenario('MITIGATING');
    showToast('🛡️ Automated Mitigation invoked: Controller pushing drop rules', 'warning');
    setTimeout(() => {
      setMockScenario('NORMAL');
    }, 6000);
  }, [showToast]);

  const resetToNormal = useCallback(() => {
    setMockScenario('NORMAL');
    attackTickCountRef.current = 0;
    showToast('Network restored to benign traffic profile', 'info');
  }, [showToast]);

  const toggleOffline = useCallback(() => {
    setMockScenario(prev => (prev === 'OFFLINE' ? 'NORMAL' : 'OFFLINE'));
  }, []);

  return {
    trafficHistory,
    currentStats,
    blockedIps,
    controllerOnline,
    dataSource,
    setDataSource,
    mockScenario,
    setMockScenario,
    toast,
    setToast,
    triggerAttack,
    triggerMitigation,
    resetToNormal,
    toggleOffline,
    lastAttackIp
  };
}
