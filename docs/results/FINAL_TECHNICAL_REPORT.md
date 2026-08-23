# Final Technical Report

## 1. Processor architecture

The processor is a 5-stage RV32IM implementation with IF, ID, EX, MEM, and WB
stages. Conditional branches and JAL/JALR redirect in EX and incur a two-cycle
redirect penalty. Normal load-use dependencies incur one cycle. Store data is
treated separately from the store address so `lw xN,...; sw xN,...` does not
require the same decode stall as a true EX-stage consumer.

The divider is an 8-stage fully pipelined unit. The first operation in a
contiguous DIV/REM burst pays seven startup cycles; back-to-back divider
operations thereafter complete at one result per cycle.

## 2. Cache and memory system

The original cache model uses blocking direct-mapped caches with one 32-bit
word per line. The D-cache is write-back/write-allocate and the I-cache is
read-only. The baseline has 64 lines in each cache, which is 256 bytes per
cache.

The cycle model reproduces clean refill, dirty eviction plus refill, instruction
fetch stalls, data-memory stalls, and the CPU's exact arbitration behavior.

## 3. RTL correlation

Directed tests established exact timing rules before full-benchmark work.
Full Dhrystone correlation then matched:

- 1,365,926 cycles;
- 193,203 retired instructions;
- x5 = 0x003fffff;
- 142,419 I-cache misses;
- 10,654 D-cache misses;
- 6,056 D-cache writebacks.

A key correlation fix was recognizing that store rs2 data is consumed in MEM,
not EX, eliminating false decode load-use stalls.

## 4. Sensitivity studies

Cache capacity and memory latency were swept against RTL. Representative exact
results included:

- I64/D64/L1: 1,047,672 cycles;
- I64/D64/L5: 1,684,180 cycles;
- I256/D64/L2: 649,561 cycles;
- I256/D256/L5: 748,359 cycles.

This separated architectural cache-capacity gains from external-memory-latency
effects.

## 5. Pre-layout implementation study

Genus synthesis with standard-cell cache arrays established implementation-cost
proxies and adaptive target-period boundaries. These are explicitly
pre-layout—not silicon Fmax.

Representative M7B results:

| Config | Target-period boundary | Frequency proxy | Liberty area |
|---|---:|---:|---:|
| BASE | 6.7188 ns | 148.8 MHz | 140,299.7 |
| EFF | 6.8750 ns | 145.5 MHz | 242,419.9 |
| PERF | 6.7188 ns | 148.8 MHz | 375,494.4 |

Activity-based M8B estimates gave total power of 5.868, 8.832, and 13.699 mW
for BASE/EFF/PERF respectively, with benchmark energy falling from 53,848.9 nJ
to 43,464.4 nJ to 34,369.1 nJ. These are pre-layout same-flow estimates.

## 6. Hard-SRAM integration

The project then replaced abstract cache arrays with explicit banked
RAM2P_128x16 hard macros. Because this SRAM has synchronous reads, the cache
architecture was changed so completed I$/D$ responses are held until consumed.
That avoided response-pulse loss when I$ and D$ stalls interact.

Exact SRAM-backed benchmark cycles became:

- BASE: 1,549,396;
- EFF: 992,158;
- PERF: 698,662.

Explicit macro counts are 4, 6, and 10.

## 7. Timing-collateral audit

The exact physical SRAM Liberty was found to contain literal 999-ns clock-to-Q
tables. A separate exact-voltage/temperature SRAM timing library with realistic
delay existed, but it represented a different macro and had no paired LEF.
Rather than substitute incompatible collateral, SRAM-aware Fmax was formally
closed as unavailable.

## 8. Innovus physical study

The mapped CPU + explicit SRAM cache netlists imported into Innovus with exact
macro counts. A deterministic two-column macro floorplan with margins, gaps,
and halos was generated, followed by non-timing-driven standard-cell placement
so the invalid SRAM timing model could not bias the physical comparison.

Measured core areas:

- BASE: 0.4473 mm²;
- EFF: 0.6656 mm²;
- PERF: 1.0497 mm².

The resulting equal-clock performance/area metric selects EFF_256_64 as the
balanced architecture.

## 9. Final conclusion

The project demonstrates a complete reasoning chain from processor timing and
RTL correlation to architectural sensitivity, implementation proxies, SRAM
integration, physical floorplanning, and evidence-based architecture selection.

It also demonstrates an important engineering boundary: when implementation
collateral cannot support a requested metric, the correct outcome is to
document and isolate the limitation rather than manufacture a number.
