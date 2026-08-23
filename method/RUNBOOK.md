# RUNBOOK — the vLLM serving-economics test (the ~$5 afternoon that prices the product)

*Prepared 2026-08-05. Purpose: replace the last estimate in the business math —
concurrency-per-card — with receipts. The instrument (kernel/loadtest.py) is built and
proven; this runbook is the exact procedure for the rented card.*

## WHAT WE'RE MEASURING
Subscribers-per-card. The chain: TTFT + tok/s at N concurrent → max N meeting the
presence bar (TTFT < ~3s, > ~8 tok/s/stream) → N × idle ratio (~1:20-1:50) = subscribers
per card → $/subscriber/month of GPU. That number goes under PRICING.md.

## THE CARD (verify prices at booking — they drift weekly)
- **First choice: 48GB class (A40 / RTX A6000 / L40S)** — Qwen3.6-35B-A3B fits at FP8/INT8
  with generous KV room. Roughly $0.40-0.90/hr on RunPod historically.
- 4090 24GB (~$0.69/hr) works only with 4-bit AWQ and thin KV — fine for a vLLM smoke,
  NOT for the pricing numbers. If both are available, take the 48GB.
- Pod: RunPod "Pods" (not serverless) so we control the engine; any region; no network
  volume needed (nothing persists — this is a measurement, not a home).

## SETUP (~15 min)
```bash
# on the pod (vLLM image or fresh CUDA image):
pip install vllm
# model: VERIFIED 2026-08-05 (web) — the OFFICIAL FP8 exists:
#   Qwen/Qwen3.6-35B-A3B-FP8   (Qwen's own; "nearly identical" quality; ~35GB on A40)
#   fallbacks: RedHatAI/Qwen3.6-35B-A3B-FP8-dynamic · QuantTrio/Qwen3.6-35B-A3B-AWQ
# needs vllm >= 0.19.0
vllm serve Qwen/Qwen3.6-35B-A3B-FP8 \
  --max-model-len 16384 \
  --enable-prefix-caching \
  --gpu-memory-utilization 0.92 \
  --port 8000
# reasoning OFF for companion serving (the 2026-08-05 finding: thinking tokens are
# invisible cost; warmth needs no CoT) — serve the base chat template, no reasoning flags.
```

## THE MATRIX (from the local machine or the pod itself; ~90 min total)
```bash
cd <repo>
EP="http://<POD_IP>:8000/v1/chat/completions"
for N in 5 10 20 40 60; do
  python3 -m kernel.loadtest --endpoint "$EP" --model <MODEL_ID> \
    --clients $N --turns 2 --soul-bytes 60000 --max-tokens 250 | tee receipts-N$N.json
done
# then the PREFIX-CACHE proof (the two-layer economics):
#   run N=20 twice back-to-back; second run's TTFT should CRATER (shared trunk cached).
```

## WHAT GOOD LOOKS LIKE (against the research doc's claims)
- Presence bar held at N=40-60 on a 48GB card → 1,000-2,000 subscribers/card at market
  idle ratios → infra ~5-10% of revenue → PRICING.md's math is CONFIRMED.
- Presence bar dies at N=10 → the math reshapes (more cards or a smaller model tier) —
  better to know for $5 than at subscriber 500.
- Prefix-cache second-run TTFT drop is the C.AI "95% from cache" effect made visible.

## RECORD
- All receipts-N*.json → kernel repo bench-reports/vllm-<date>/ + a one-page verdict
  in ventures/companion/ (numbers → the pricing page + the counsel/infra plan).
- Terminate the pod (Terminate, not Stop — kills storage billing too).

## LATER VARIANTS (same runbook, different model line)
- The bigger Qwen MoE (235B-A22B class) on 2×A100/H100 — the premium-tier audition.
  Same matrix, same bar, same math; the tier ladder can carry the model ladder.
- Any new serving candidate must ALSO pass the register bench (walk + P6/P7 flavors)
  before it serves anyone — economics AND soul, both gates, always.
