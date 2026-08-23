# Milestone 3D — calibrated JAL/JALR call-return I-cache model

VCS characterization established that JAL and JALR use the same EX-stage redirect timing family as taken conditional branches in this RTL.

Calibrated rules:

- every JAL/JALR contributes a 2-cycle redirect penalty;
- before redirect, IF issues two younger sequential requests (`PC+4`, `PC+8`);
- after redirect, IF restarts at the architectural target even if that target was fetched earlier;
- backward jumps and call/return traffic therefore create real direct-mapped cache refetch/conflict misses;
- cache miss cost remains the independently calibrated 7 cycles for memory `LATENCY=3`.

Measured/calibrated targets:

| Workload | Cycles | I$ access | I$ hit | I$ miss |
|---|---:|---:|---:|---:|
| `jal_forward_link` | 58 | 9 | 2 | 7 |
| `jal_backward_loop` | 78 | 15 | 6 | 9 |
| `jalr_forward` | 66 | 10 | 2 | 8 |
| `call_return` | 107 | 16 | 3 | 13 |

After preserving/extracting your real VCS results under `results/milestone3d/`, run:

```bash
python scripts/run_milestone3d.py --require-rtl
```

To validate both calibrated conditional branches and calibrated JAL/JALR together:

```bash
python scripts/run_controlflow_validation.py
```
