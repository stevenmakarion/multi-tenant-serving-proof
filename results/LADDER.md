# The Concurrency Ladder

**Measured 2026-08-05. One rented 48GB card. 300 requests. Zero errors.**

Hardware: RTX 6000 Ada, 48GB, RunPod, $0.84/hr.
Stack: vLLM 0.19.1, torch 2.10.0+cu128, a 35B-A3B mixture-of-experts model at FP8
(the vendor's own quantization), prefix caching on, reasoning off, 16K context.

Every row below came out of [`../method/loadtest.py`](../method/loadtest.py), which is
in this repository and re-runs against any endpoint in about an hour.

## Results

| N concurrent | TTFT median | TTFT p95 | tok/s per stream | aggregate tok/s |
|---:|---:|---:|---:|---:|
| 5  | 1.60s | 3.01s  | 63.2 | 224 |
| 10 | 0.59s | 7.32s  | 49.9 | 282 |
| 20 | 1.05s | 2.40s  | 38.8 | 649 |
| **40** | **2.27s** | **6.24s** | **28.3** | **870** |
| 60 | 4.61s | 10.54s | 20.3 | 865 |

**300 requests across the ladder. Zero errors.**

## The bar, and why it is that bar

A conversational assistant that you wait on stops feeling present. That is a product
property, not a latency budget, so it was set before the test rather than after:

> **TTFT under 3 seconds, and above 8 tokens per second per stream.**

**That bar holds through N=40 on one mid-tier card.**

Per-stream decode of 28 to 63 tokens per second is roughly three to five times adult
reading speed, which is the point at which text stops feeling like it is being typed at
you and starts feeling like it is already there.

## What the curve says

**Aggregate throughput saturates between N=40 and N=60** (870 then 865). The card is
fully utilized at 40. Past that you are buying queueing, not capacity.

**TTFT p95 at N=10 is worse than at N=20** (7.32s versus 2.40s). That inversion is real
and it is a scheduler artifact, not noise. It is reported rather than smoothed away
because a table that only goes the direction you expected is a table nobody should trust.

**Reasoning is off, deliberately.** Thinking tokens are invisible cost: paid for on every
turn, never seen by the user. Leaving them on triples the bill for a conversational
workload. This was confirmed three separate ways before it was made the default.

## Reproducing this

```bash
python3 -m loadtest \
  --endpoint http://HOST:8000/v1/chat/completions \
  --model YOUR_MODEL \
  --clients 40 --turns 2 --soul-bytes 60000
```

The `--soul-bytes` flag matters and it is the reason this instrument exists in this shape:
every simulated tenant is given an **identical large system prefix** plus a small unique
branch. That is the two-layer design a prefix cache is built for. The shared trunk is
computed once and reused; only the per-tenant branch costs anything. Testing with N
distinct full prompts measures a different and much worse system than the one you would
actually deploy.
