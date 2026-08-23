# Milestone 3A - Cache / Memory Hierarchy Performance Model

This milestone adds an analytical model of the exact cache organization used by Project 2:

- split I-cache / D-cache
- direct mapped
- one 32-bit word per line
- blocking
- I-cache read-only
- D-cache write-back + write-allocate
- AXI-Lite backing memory
- configurable backing-memory `LATENCY`

For backing-memory latency `L`, the current RTL FSM implies:

- clean refill stall = `L + 4`
- dirty-victim D-cache miss stall = `2*L + 7`

At the RTL default `LATENCY=3`, those are 7 and 13 cycles.

## Accuracy boundary

D-cache accesses come from architecturally executed loads/stores, so directed D-cache tests can be correlated directly.

The current I-cache model uses architecturally executed PCs as a fetch proxy. The RTL IF stage can fetch younger/wrong-path instructions. I-cache timing is therefore marked *characterization* until an explicit IF-stage fetch-stream model is added.
