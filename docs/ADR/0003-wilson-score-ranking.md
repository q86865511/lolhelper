# ADR 0003 — Wilson score lower bound as the primary ranking metric

**Date**: 2026-05-18
**Status**: Accepted

## Context

We need a way to rank augments (and items) within a (queue, patch, champion)
slice. Naive `wins / total` produces nonsense at small N:
- `5/5 = 100%` outranks `800/1000 = 80%`
- Even raising `min_games` to 50 leaves an unfair gap between `40/50 = 80%`
  and `400/500 = 80%`

## Decision

Sort by the Wilson score interval **lower bound** at 95% confidence.

```
denom = 1 + z²/n
center = p_hat + z²/(2n)
margin = z * sqrt(p_hat*(1-p_hat)/n + z²/(4n²))
lower = (center - margin) / denom
```

with `z = 1.96` (95% confidence) and `p_hat = wins/n`.

## Why not the alternatives

- **Bayesian (Beta) shrinkage**: needs a prior; picking a prior is contentious
  in a community-facing tool
- **Win rate + min sample threshold**: still has the 40/50 vs 400/500 problem
- **Raw win rate sorted desc**: see above; gives clickbait results
- **K-factor / Elo-like**: only meaningful between paired entities, augments
  don't oppose each other directly

Reddit's old ranking used this exact formula for the same reason (penalise
low-sample 100% upvote items vs high-sample 80% upvote items).

## Consequences

- ✅ Single number per row; trivial to ORDER BY
- ✅ Self-correcting as samples grow
- ⚠️ Not intuitive to read raw — UI displays "Wilson score: 0.624" and
  also `win_rate: 65% (N=823)` side-by-side
- ⚠️ For very rare augments (N<50) we display "insufficient sample" instead
  of the bound
