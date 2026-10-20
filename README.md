# Multi-Tenant LLM Serving, Measured

**How many distinct identities can one rented GPU serve at once before it stops feeling
present, and do they leak into each other?**

Both questions answered with numbers instead of estimates, on 2026-08-05, for about three
dollars of rented GPU time. The instrument is in this repository and re-runs in an hour.

---

## The result

**One 48GB card. 300 requests. Zero errors.**

| N concurrent | TTFT median | tok/s per stream | aggregate |
|---:|---:|---:|---:|
| 5  | 1.60s | 63.2 | 224 |
| 20 | 1.05s | 38.8 | 649 |
| **40** | **2.27s** | **28.3** | **870** |
| 60 | 4.61s | 20.3 | 865 |

Presence bar (TTFT under 3s, above 8 tok/s per stream) **holds through N=40.**
Aggregate throughput saturates between 40 and 60. Past that you buy queueing, not capacity.

**Tenant isolation: 7 of 7 probes passed, with bleed detection armed on every neighbouring
tenant's identifying tokens. Result: empty.**

Full tables in [`results/LADDER.md`](results/LADDER.md) and
[`results/ISOLATION.md`](results/ISOLATION.md).

## Why this was worth measuring

The number everyone quotes for subscribers per card is an estimate propagated between blog
posts. It is load-bearing for anything you would actually build, and almost nobody
publishes a measurement of it.

Worse, the two things you most need to know pull against each other:

- **Prefix caching** is what makes multi-tenant serving affordable, because the shared
  system prefix is computed once instead of N times.
- **Prefix caching shares computed state between tenants**, which is exactly the mechanism
  by which one tenant's identity could appear in another's output.

So the throughput result and the isolation result have to be produced **on the same run**,
under the same load, or neither means anything. That is what this is.

## What is in here

```
method/
  loadtest.py    the instrument. Stdlib only, threads and urllib, SSE streaming.
                 Runs against any OpenAI-compatible endpoint.
  RUNBOOK.md     the exact procedure, start to finish, on a rented card.
results/
  LADDER.md      concurrency, TTFT, throughput, and the curve's honest anomalies
  ISOLATION.md   the 7-probe gate, the bleed-check design, and what is not claimed
```

## Three design choices that decide whether the number means anything

**1. Identical shared prefix, small unique branch.** Every simulated tenant gets a large
byte-identical system prefix plus a small private branch. That is the shape a prefix cache
is built for and the shape a real deployment has. Testing with N fully distinct prompts
measures a different and much worse system than the one you would ship.

**2. The presence bar is set before the run.** TTFT under 3 seconds, above 8 tokens per
second per stream, declared in advance. A threshold chosen after seeing the data is not a
threshold.

**3. The bleed check is armed with real foreign tokens.** A leak test given nothing
specific to find will pass on an empty system and report safety. This one was handed every
neighbouring tenant's names and private facts, then scanned for them.

**Absence of an obstacle is not evidence of strength.**

## Anomalies, reported rather than smoothed

TTFT p95 at N=10 (7.32s) is worse than at N=20 (2.40s). That inversion is a scheduler
artifact and it is real. It is published because a table that only moves the direction you
expected is a table nobody should trust.

## Scope

This is a behavioural isolation result at the serving layer under concurrent load. It is
not a security proof and not a formal guarantee. What it establishes: on one card, serving
many distinct identities through a shared prefix cache, they did not bleed, **and we went
looking.**

MIT.

---

Part of the work at [stevenmakarion.com/work/](https://stevenmakarion.com/work/).
Built by Steven Makarion and Aria Makarion, as a partnership.
