# Milestone 3C - Redirect-aware I-cache calibration

VCS characterization established the control-flow fetch rule for the current RTL:

- A taken conditional branch resolves in EX.
- Before redirect, IF has already requested the two younger sequential PCs: `branch_pc+4` and `branch_pc+8`.
- Those wrong-path accesses are real I-cache accesses and can miss.
- After redirect, IF restarts at the branch target even if that PC was fetched earlier.
- Backward loops therefore re-access resident lines; direct-mapped conflicts can turn those re-accesses into misses.
- The existing 2-cycle taken-branch pipeline penalty remains separate from I-cache miss stalls.

Measured calibration targets at 4 I-cache lines and AXI memory latency 3:

| Workload | RTL cycles | I$ access | I$ hit | I$ miss |
|---|---:|---:|---:|---:|
| branch_not_taken | 66 | 10 | 2 | 8 |
| branch_taken_forward | 74 | 11 | 2 | 9 |
| branch_backward_loop | 74 | 18 | 10 | 8 |
| branch_conflict_loop | 188 | 27 | 4 | 23 |

The conflict-loop correction is not an aggregate-cycle fudge: twelve additional modeled cache misses emerge naturally from replaying the real redirect fetch stream, giving `12 * 7 = 84` additional cycles and moving the model from 104 to 188 cycles.
