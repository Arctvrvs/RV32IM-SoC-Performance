# Project milestones

## Milestone 1 — architectural correlation (this ZIP)

Goal: execute the exact same RV32IM program in the reference model and RTL and compare the retirement stream.

- [x] RV32IM functional CPU model in C++17
- [x] Optional SystemC clock wrapper
- [x] `.hex` loader
- [x] retirement CSV
- [x] RTL trace-collector template
- [x] Python architectural trace comparator
- [x] basic instruction-mix analyzer
- [x] connect the collector to your actual RTL testbench
- [x] run one of your existing RTL regression programs through both models
- [x] fix semantic mismatches until the retirement streams are identical

## Milestone 2 — cycle-aware performance model

- load-use stalls
- EX-stage branch redirects/flushes
- forwarding behavior
- 8-stage DIV/REM latency/dependencies
- instruction-side stalls
- data-side stalls

## Milestone 3 — cache + AXI performance model

- I-cache accesses/hits/misses
- D-cache accesses/hits/misses/writebacks
- AXI-Lite read/write transactions
- configurable AXI latency
- memory-stall attribution

## Milestone 4 — Apple-style performance correlation

Produce a report per workload containing:

- total retired instructions
- total cycles and CPI
- model-vs-RTL cycle error
- cache hit/miss rates
- branch/load-use/divider/memory stall cycles
- top bottleneck

## Milestone 5 — model-guided optimization

Use the model to predict one change (for example I-cache capacity or line size), implement that change in RTL, and compare:

1. model-predicted speedup
2. RTL-measured speedup
3. prediction error

