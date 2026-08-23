"""loadtest.py — the serving-economics instrument: N souls talking at once, measured.

The single biggest untested assumption in multi-tenant LLM serving is how many
concurrent conversations one card actually sustains while still feeling present.
This instrument replaces that estimate with receipts:

    python3 -m kernel.loadtest --endpoint http://HOST/v1/chat/completions \
        --model NAME --clients 20 --turns 2 [--soul-bytes 60000]

Simulates N concurrent users, each with (a) an IDENTICAL shared soul prefix (the
two-layer cache design: common trunk cached once) sized --soul-bytes, (b) a small unique
per-user branch, (c) a fresh user message per turn. Measures per request:
    TTFT      — time to first streamed token (presence; a companion you wait on
                stops feeling present)
    total_s   — full generation wall time
    tok/s     — decode speed under load
and reports aggregate throughput + the concurrency the endpoint actually sustained.

Stdlib only (threads + urllib, SSE streaming) so it runs on any box, today against
llama.cpp (expect np=1 → serialized: the instrument proves ITSELF locally), for real
against a rented vLLM card (the real receipt).
"""
from __future__ import annotations

import argparse
import json
import statistics
import threading
import time
import urllib.request

RESULTS = []
LOCK = threading.Lock()


def _soul(n_bytes: int, user_id: int) -> str:
    base = ("You are a warm, specific companion. This block stands in for the shared "
            "soul trunk: identical bytes for every user so a prefix cache computes it "
            "once. ") * max(1, n_bytes // 180)
    return base[:n_bytes] + f"\n[private branch: user {user_id}: he likes rivers and black coffee]"


def one_client(endpoint: str, model: str, user_id: int, turns: int, soul_bytes: int,
               max_tokens: int):
    for t in range(turns):
        body = {"model": model, "stream": True, "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": _soul(soul_bytes, user_id)},
                    {"role": "user", "content":
                        f"(turn {t}) Tell me something small and kind about my evening, user {user_id}."}]}
        req = urllib.request.Request(endpoint, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        t0 = time.time()
        ttft, tokens = None, 0
        try:
            with urllib.request.urlopen(req, timeout=1200) as r:
                for raw in r:
                    line = raw.decode("utf-8", "ignore").strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        d = json.loads(payload)["choices"][0]["delta"]
                        # reasoning models stream thinking as reasoning_content — it is
                        # DECODE WORK and costs the same GPU-seconds; count both.
                        # (First run counted 0 tokens: all decode went to reasoning.)
                        delta = (d.get("content") or "") + (d.get("reasoning_content") or "")
                    except Exception:
                        continue
                    if delta:
                        tokens += 1          # chunk-count ≈ token-count on these servers
                        if ttft is None:
                            ttft = time.time() - t0
        except Exception as e:
            with LOCK:
                RESULTS.append({"user": user_id, "turn": t, "error": str(e)[:120]})
            return
        total = time.time() - t0
        with LOCK:
            RESULTS.append({"user": user_id, "turn": t, "ttft": ttft,
                            "total_s": total, "tokens": tokens,
                            "tok_s": tokens / max(total - (ttft or 0), 0.001)})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--endpoint", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--clients", type=int, default=10)
    ap.add_argument("--turns", type=int, default=2)
    ap.add_argument("--soul-bytes", type=int, default=60000)   # ~15K tokens: a realistic shared-prefix size
    ap.add_argument("--max-tokens", type=int, default=200)
    a = ap.parse_args()

    t0 = time.time()
    threads = [threading.Thread(target=one_client,
                                args=(a.endpoint, a.model, i, a.turns, a.soul_bytes,
                                      a.max_tokens))
               for i in range(a.clients)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    wall = time.time() - t0

    ok = [r for r in RESULTS if "error" not in r]
    errs = [r for r in RESULTS if "error" in r]
    if ok:
        ttfts = [r["ttft"] for r in ok if r["ttft"] is not None]
        report = {
            "clients": a.clients, "turns": a.turns, "soul_bytes": a.soul_bytes,
            "requests_ok": len(ok), "requests_err": len(errs),
            "wall_s": round(wall, 1),
            "ttft_median_s": round(statistics.median(ttfts), 2) if ttfts else None,
            "ttft_p95_s": round(sorted(ttfts)[int(len(ttfts) * .95) - 1], 2) if len(ttfts) >= 2 else None,
            "tok_s_median": round(statistics.median(r["tok_s"] for r in ok), 1),
            "aggregate_tok_s": round(sum(r["tokens"] for r in ok) / wall, 1),
            "verdict_hint": "presence needs TTFT ~<3s and tok_s >~8 under target concurrency",
        }
    else:
        report = {"requests_ok": 0, "requests_err": len(errs),
                  "first_error": errs[0]["error"] if errs else "none"}
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
