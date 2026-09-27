// Dynamic Mock Generator for live SDN simulation
// Simulates live Ryu SDN Controller telemetry and ML classification

let attackCounter = 0;
let blockedList = [
  {
    id: "blk-901",
    ip: "10.0.0.9",
    timestamp: "23:55:12",
    reason: "TCP SYN Flood (PPS > 6,500)",
    flow_rule: "OFPFC_ADD: table=0, priority=65535, ip, nw_src=10.0.0.9, actions=drop",
    status: "DROPPED",
    packets_mitigated: 184520,
    switch_id: "s1-eth2",
    duration_sec: 300
  },
  {
    id: "blk-902",
    ip: "10.0.0.14",
    timestamp: "23:52:40",
    reason: "UDP Amplification Reflection",
    flow_rule: "OFPFC_ADD: table=0, priority=65535, ip, nw_src=10.0.0.14, actions=drop",
    status: "DROPPED",
    packets_mitigated: 95400,
    switch_id: "s2-eth1",
    duration_sec: 450
  },
  {
    id: "blk-903",
    ip: "192.168.1.185",
    timestamp: "23:48:19",
    reason: "ICMP Smurf Anomaly",
    flow_rule: "OFPFC_ADD: table=0, priority=65535, ip, nw_src=192.168.1.185, actions=drop",
    status: "DROPPED",
    packets_mitigated: 63210,
    switch_id: "s3-eth3",
    duration_sec: 600
  }
];

export const getBlockedIpsSnapshot = () => [...blockedList];

export const addBlockedIpFromAttack = (ip, reason = "ML High-Confidence SYN Flood") => {
  const now = new Date();
  const timeStr = now.toTimeString().split(" ")[0];
  const newEntry = {
    id: `blk-${Date.now().toString().slice(-4)}`,
    ip: ip || `10.0.0.${Math.floor(Math.random() * 20) + 2}`,
    timestamp: timeStr,
    reason: reason,
    flow_rule: `OFPFC_ADD: table=0, priority=65535, ip, nw_src=${ip}, actions=drop`,
    status: "DROPPED",
    packets_mitigated: Math.floor(Math.random() * 50000) + 12000,
    switch_id: `s${Math.floor(Math.random() * 4) + 1}-eth${Math.floor(Math.random() * 3) + 1}`,
    duration_sec: 300
  };
  blockedList = [newEntry, ...blockedList];
  return newEntry;
};

export const clearBlockedList = () => {
  blockedList = [];
  return blockedList;
};

export const generateNetworkTick = (scenario = "NORMAL") => {
  const now = new Date();
  const timeLabel = now.toTimeString().split(" ")[0];

  let total_pps = 0;
  let normal_pps = 0;
  let dropped_pps = 0;
  let bandwidth_mbps = 0;
  let active_flows = 0;
  let attack_probability = 0.02;
  let classification = "Benign";
  let entropy_score = 3.82;
  let status = scenario;

  const jitter = (Math.random() - 0.5) * 60;

  if (scenario === "UNDER_ATTACK") {
    attackCounter++;
    // Violent spike in traffic
    normal_pps = Math.round(900 + jitter);
    const attack_pps = Math.round(8500 + Math.random() * 4000);
    total_pps = normal_pps + attack_pps;
    dropped_pps = Math.round(attack_pps * 0.15); // Partial drop before full mitigation rule
    bandwidth_mbps = +(75.4 + Math.random() * 35).toFixed(1);
    active_flows = Math.round(1450 + Math.random() * 300);
    attack_probability = +(0.94 + Math.random() * 0.05).toFixed(3);
    classification = "MALICIOUS: TCP SYN Flood";
    entropy_score = +(1.18 + Math.random() * 0.2).toFixed(2); // Entropy collapse indicates DDoS
  } else if (scenario === "MITIGATING") {
    // SDN Controller actively pushing OpenFlow rules to drop malicious flows
    normal_pps = Math.round(920 + jitter);
    const residual_attack = Math.round(4200 + Math.random() * 1500);
    dropped_pps = residual_attack; // Controller dropping all attack packets
    total_pps = normal_pps + dropped_pps;
    bandwidth_mbps = +(14.2 + Math.random() * 4).toFixed(1);
    active_flows = Math.round(310 + Math.random() * 50);
    attack_probability = +(0.72 - Math.random() * 0.1).toFixed(3);
    classification = "Mitigating (Drop Rules Active)";
    entropy_score = +(2.95 + Math.random() * 0.4).toFixed(2);
  } else {
    // NORMAL state
    normal_pps = Math.max(200, Math.round(850 + jitter));
    total_pps = normal_pps;
    dropped_pps = 0;
    bandwidth_mbps = +(7.5 + (Math.random() * 2.5)).toFixed(1);
    active_flows = Math.round(110 + Math.random() * 25);
    attack_probability = +(0.01 + Math.random() * 0.04).toFixed(3);
    classification = "Benign Normal Flow";
    entropy_score = +(3.75 + Math.random() * 0.35).toFixed(2);
    status = "NORMAL";
  }

  return {
    timestamp: now.toISOString(),
    displayTime: timeLabel,
    status: status,
    total_pps,
    normal_pps,
    dropped_pps,
    bandwidth_mbps,
    active_flows,
    cpu_load_percent: scenario === "UNDER_ATTACK" ? Math.floor(75 + Math.random() * 20) : Math.floor(18 + Math.random() * 8),
    ml_detection: {
      model: "Random Forest + Flow Entropy Classifier",
      attack_probability,
      classification,
      entropy_score,
      threshold: 0.75
    },
    controller_info: {
      name: "Ryu SDN Controller",
      protocol: "OpenFlow 1.3",
      switches_online: 4,
      latency_ms: +(1.2 + Math.random() * 0.6).toFixed(1),
      online: scenario !== "OFFLINE"
    }
  };
};
