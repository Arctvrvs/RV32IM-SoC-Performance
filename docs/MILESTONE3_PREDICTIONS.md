# Frozen Milestone 3A Predictions

These predictions are generated before seeing the new VCS cache traces.

| Test | Mode | Model cycles | I$ misses | D$ misses | D$ writebacks |
|---|---:|---:|---:|---:|---:|
| dcache_repeat | validate | 17 | 0 | 1 | 0 |
| dcache_cache_test | validate | 48 | 0 | 3 | 2 |
| icache_linear | measure | 84 | 10 | 0 | 0 |
| split_cache | measure | 125 | 11 | 3 | 2 |

The D-cache cases test the RTL-FSM-derived miss penalties directly. The I-cache
cases intentionally remain `MEASURE` because architectural retired PCs do not
fully describe speculative/younger IF-stage requests.
