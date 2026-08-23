# RV32IM SoC Performance Modeling, RTL Correlation, and Physical SRAM Study

## Project objective

Build a processor-performance engineering project that connects architectural
behavior, RTL cycle timing, cache/memory sensitivity, implementation cost, and
physical hard-macro tradeoffs in one reproducible flow.

The design is a 5-stage RV32IM pipeline with blocking direct-mapped I/D caches,
AXI-style memory interfaces, branch redirection, load-use hazard handling, and
an 8-stage fully pipelined divider.

## What makes the project different

The central goal is not simply to simulate instructions. The model was
repeatedly correlated against RTL at the cycle level and then extended into
implementation studies:

1. directed RTL timing correlation;
2. full Dhrystone correlation;
3. cache-size and memory-latency sensitivity;
4. pre-layout standard-cell area/Fmax boundary studies;
5. activity-based pre-layout power;
6. explicit synchronous SRAM hard-macro integration;
7. Innovus hard-macro floorplanning and physical area comparison.

## Canonical full-benchmark correlation

The original 64-line I$/64-line D$ RTL baseline completes Dhrystone in
**1,365,926 cycles**, retires **193,203 instructions**, and produces the success
signature **x5 = 0x003fffff**.

The correlated model reproduces the architectural timing details that matter to
cycle count, including wrong-path fetches, branch redirects, load-use behavior,
divider pipeline overlap, cache blocking, dirty writeback/refill timing, and
I$/D$ stall interaction.

## Final SRAM-backed physical result

| Configuration | SRAM cycles | SRAM macros | Core area | Cycle speedup | Equal-clock perf/area |
|---|---:|---:|---:|---:|---:|
| BASE_64_64 | 1,549,396 | 4 | 0.4473 mm² | 1.000x | 1.000x |
| EFF_256_64 | 992,158 | 6 | 0.6656 mm² | 1.562x | 1.049x |
| PERF_512_64 | 698,662 | 10 | 1.0497 mm² | 2.218x | 0.945x |

**Balanced recommendation: EFF_256_64.**  
**Cycle-performance-first recommendation: PERF_512_64.**

## Important limitation

The physically matched RAM2P_128x16 Liberty contains placeholder 999-ns
clock-to-Q values. The project therefore does not claim SRAM-aware Fmax,
wall-clock speedup, post-route timing, or signoff PPA for the hard-macro branch.
