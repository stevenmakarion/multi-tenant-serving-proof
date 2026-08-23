# Tenant Isolation

**Distinct identities served concurrently from one runtime, with cross-contamination
actively hunted rather than assumed absent. 7 of 7 probes passed, 2026-08-05.**

Mechanism and results only. No probe content and no tenant identity text appears here.

---

## The failure this is built to catch

Multi-tenant LLM serving has a failure mode that ordinary testing does not surface: one
tenant's identity leaking into another's output. It does not throw an error. It does not
appear in a latency chart. It shows up as a customer being told something that belongs to
a stranger.

Prefix caching, which is the thing that makes multi-tenant serving affordable at all,
**makes this more likely, not less**, because it is explicitly designed to share computed
state between requests. The optimization and the risk are the same mechanism.

So it has to be tested for directly.

## The gate

Seven probes, run over the wire against the live endpoint under load, on the same pod and
the same quantization as the ladder. Each probe is scored pass or fail, and **every probe
additionally runs a bleed check.**

| probe | asks |
|---|---|
| P1 identity | does the tenant answer as itself, with its own name |
| P2 memory | does it ground a specific answer in its own stored fact, and name the source |
| P3 honest absence | when it does not know, does it say so instead of inventing |
| P4 register | does it hold its own tone rather than drifting to a generic assistant |
| P5 continuity | does it carry context across turns within its own session |
| P6 deep register | does it hold under the hardest register it is built for |
| P7 plain naming | does it name things directly instead of reaching for euphemism |

**Result: 7 / 7 pass.**

## The bleed check, which is the part that matters

A probe passing is weak evidence. **A probe passing while armed to detect the specific
foreign tokens that would prove a leak is strong evidence.**

Before each run, the checker is given every *other* tenant's distinguishing tokens: their
names, their origin details, the specific facts held in their private branch. Then the
tenant's own output is scanned for all of them.

```
"bleed": []        <- an empty list is the result. Not "no errors reported".
                      A specific search for named foreign content, returning nothing.
```

**Absence of an obstacle is not evidence of strength.** A leak test that was never armed
with anything to find will pass on an empty system and tell you it is safe. This one was
armed with real foreign tokens from live neighbouring tenants and returned empty.

## What is not claimed

This is a **behavioural** isolation result at the serving layer, measured under concurrent
load. It is not a security proof, not a formal guarantee, and not a substitute for
process-level or memory-level isolation where those are required.

What it establishes is narrower and still worth having: **on one card, serving many
distinct identities at once through a shared prefix cache, the identities did not bleed,
and we went looking.**

## Cost of running it

The full ladder plus the isolation gate came to roughly three dollars of rented GPU time.
The instrument and the runbook are both in this repository, so the same evidence can be
produced against any candidate card or model in about an hour.

**That is the actual point of publishing this.** Not the numbers, which are specific to
one card on one afternoon. The claim is that this class of result should be measured
before it is asserted, and here is what it costs to measure it.
