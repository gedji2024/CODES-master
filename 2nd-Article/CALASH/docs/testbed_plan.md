# CALASH Testbed Validation Plan
## Hardware Testbed for Future Experimental Verification

### Overview
This document describes a practical testbed deployment plan for validating
CALASH simulation results with real hardware.  The testbed is designed to
be reproducible with commercially available components.

### 1. Hardware Components

| Component | Model | Qty | Role | Cost (est.) |
|-----------|-------|-----|------|-------------|
| MCU + Radio | ESP32-S3 + SX1276 LoRa | 20 | Sensor nodes | $15 × 20 = $300 |
| Sensors | BME280 (temp/humidity/pressure) | 20 | Environmental sensing | $5 × 20 = $100 |
| Gateway | Raspberry Pi 4B + LoRa HAT | 1 | Base station | $80 |
| RIS Panel | Custom 8×8 varactor-based reflectarray (2.4 GHz) | 1 | RIS demonstration | $200 |
| Power meters | INA219 current sensor modules | 20 | Energy measurement | $3 × 20 = $60 |
| Battery | LiPo 3.7V 1000mAh | 20 | Node power supply | $5 × 20 = $100 |
| **Total** | | | | **~$840** |

### 2. Network Topology

```
┌──────────────────────────────────────────────────────────┐
│                  20m × 20m Indoor Area                   │
│                                                          │
│    [N1]  [N2]  [N3]  [N4]  [N5]     ┌─────────┐        │
│                                       │ RIS     │        │
│    [N6]  [N7]  [N8]  [N9]  [N10]    │ Panel   │        │
│                                       └─────────┘        │
│    [N11] [N12] [N13] [N14] [N15]                        │
│                                            [GW/BS]       │
│    [N16] [N17] [N18] [N19] [N20]                        │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

- 20 nodes in 4×5 grid, 4m spacing (matches density of simulation)
- 1 gateway (Raspberry Pi) at edge of deployment
- 1 RIS panel mounted on wall (demonstrating reflection path)

### 3. Protocol Implementation

#### 3.1 CALASH Components on ESP32
- **CADR**: Compressive sensing on MCU (CS encoding uses sparse measurement matrix, lightweight)
  - Signal dimension n=100 → m=30-80 measurements (compression ratio ρ=0.3-0.8)
  - OMP reconstruction at gateway only
- **CARE**: Lyapunov routing + simplified DQN (quantized weights, INT8 inference)
  - DQN: 8→32→16→1 architecture (reduced for MCU, ~900 parameters)
  - Lyapunov: virtual carbon queue Z(t) with real CI from gateway beacon
- **SHDR**: Heartbeat-based MAPE-K self-healing
  - Each node broadcasts heartbeat beacon every 10 seconds
  - Missing 3 consecutive heartbeats → node declared dead
- **LSE**: Lifecycle penalty in routing cost function
  - Embodied carbon stored per-node, EOL weight in cost

#### 3.2 CI Data Source
- Real-time carbon intensity from UK National Grid API
  - https://api.carbonintensity.org.uk/intensity
  - Gateway polls every 30 minutes and broadcasts to nodes via beacon

#### 3.3 Disaster Simulation
- Physical obstruction: place RF-absorbing material around target nodes
  - Simulates building collapse / rubble blocking line-of-sight
- Node removal: disconnect battery from 5-8 nodes simultaneously
- Test self-healing recovery: measure time-to-reorganize

### 4. Measurement Plan

| Metric | Measurement Method | Expected Accuracy |
|--------|-------------------|-------------------|
| Energy per packet (Tx) | INA219 current × voltage × time | ±2% |
| Energy per packet (Rx) | INA219 during receive window | ±2% |
| PDR | Gateway counts received vs. expected | Exact |
| Latency | Timestamp at source and gateway (NTP sync) | ±1ms |
| RSSI / SNR | LoRa radio registers (SX1276) | ±1 dB |
| Lifetime | Monitor battery voltage via ADC | ±5% |
| Carbon | CI(t) × measured energy | ±5% |

### 5. Experimental Protocol

| Phase | Duration | Activity |
|-------|----------|----------|
| Calibration | 1 hour | Measure baseline energy per Tx/Rx, path loss characterization |
| Normal ops | 4 hours | Run all protocols, collect steady-state metrics |
| Disaster | 10 min | Introduce physical obstruction, disconnect nodes |
| Recovery | 2 hours | Monitor self-healing, topology restructuring |
| Post-disaster | 2 hours | Continue operation with degraded network |

### 6. Baselines to Implement

1. **LEACH**: ESP32 implementation (well-documented reference implementations exist)
2. **EE-LEACH**: LEACH + energy-weighted CH threshold
3. **RIS-DRL**: DRL routing with RIS but no carbon/lifecycle awareness
4. **CALASH**: Full framework

### 7. Expected Outcomes

Based on simulation results, the testbed should validate:
1. CALASH extends network lifetime by 15-25% vs LEACH
2. CALASH reduces carbon emissions by 20-35% vs energy-optimal baselines
3. Self-healing restores >80% coverage within 5 minutes post-disaster
4. RIS panel provides 3-6 dB link budget improvement for obstructed paths
5. DQN converges within 200 rounds (~30 minutes real-time)

### 8. Limitations and Mitigations

| Limitation | Mitigation |
|-----------|-----------|
| No THz hardware | Use 2.4 GHz LoRa as proxy; scale results using THz channel model |
| Small scale (20 nodes) | Validate per-node energy model; extrapolate using simulation |
| Indoor only | Controlled environment ensures reproducibility; outdoor planned for Phase 2 |
| RIS at 2.4 GHz (not THz) | Demonstrates principle; THz RIS testbeds exist at UC Davis, KAUST |

### 9. Timeline

| Week | Activity |
|------|----------|
| 1-2 | Hardware procurement and assembly |
| 3 | Firmware development (ESP32 CALASH implementation) |
| 4 | Calibration and baseline measurements |
| 5-6 | Full experimental campaign |
| 7 | Data analysis and comparison with simulation |
| 8 | Paper revision with testbed results |

### 10. References

- [ESP32-S3 Datasheet](https://www.espressif.com/en/products/socs/esp32-s3)
- [SX1276 LoRa Transceiver](https://www.semtech.com/products/wireless-rf/lora-connect/sx1276)
- [BME280 Environmental Sensor](https://www.bosch-sensortec.com/products/environmental-sensors/humidity-sensors-bme280/)
- [INA219 Current/Power Monitor](https://www.ti.com/product/INA219)
- UK Carbon Intensity API: https://carbonintensity.org.uk/
