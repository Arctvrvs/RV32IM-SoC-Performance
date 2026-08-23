# Milestone 3B — Explicit IF-stage fetch-stream model

VCS fetch characterization showed that an instruction cache sees more requests
than the retirement stream.

For the current five-stage RTL and directed straight-line cache workloads:

- A D-cache miss freezes the pipeline with IF three instructions ahead
  (`memory_instruction_pc + 12`).
- The I-cache sees one hit request to that held PC per D-cache stall cycle.
- A terminating ECALL/EBREAK allows two younger sequential PCs to be fetched
  before halt commits in WB.
- The second younger PC is then requested for two additional hit cycles.

These rules reproduce the measured VCS streams:

- `icache_linear`: 14 accesses = 12 misses + 2 hits; 98 total cycles.
- `split_cache`: 48 accesses = 13 misses + 35 hits; 139 total cycles.

D-cache timing remains unchanged and cycle-exact from Milestone 3A.

Branch redirects/wrong-path I-cache requests are intentionally deferred to a
later front-end characterization workload; Milestone 3B validates the current
straight-line cache cases only.
