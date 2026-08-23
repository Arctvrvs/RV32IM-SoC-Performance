# Milestone 4B - Cache Concurrency

The Milestone 4A full Dhrystone run reduced the remaining model/RTL difference
to a concurrency effect rather than a latency or functional mismatch.

Measured RTL:

- 193,203 retirements, architectural PASS
- 1,365,926 trace cycles
- 996,933 IF stall cycles
- 110,914 MEM stall cycles
- 12 cycles with IF and MEM stalled simultaneously
- I$ 368,993 accesses / 226,574 hits / 142,419 misses
- D$ 79,394 accesses / 68,740 hits / 10,654 misses / 6,056 writebacks

The analytical model independently predicts the two individual cache stall
streams exactly, but currently sums them. Therefore the next rule must model the
union of overlapping waits rather than changing either miss penalty.

The RTL also gates `dmem_valid` with `!if_stall`. A D-cache transaction already
in progress can therefore finish while IF remains stalled; when IF recovers the
held MEM request can be presented again to the now-filled D-cache and appear as
an additional hit access. Milestone 4B probes this directly.
