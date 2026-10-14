---
name: ponytail-gain
description: >
  Show ponytail's measured savings (code, cost, speed) from the benchmark.
  One-shot display. Use for /ponytail-gain, "what does ponytail save",
  "ponytail impact".
---

# Ponytail Gain

Display this scoreboard when invoked. One-shot: do NOT change mode, write flag
files, or persist anything.

## Scoreboard

```
  ponytail gain           benchmark
  no-skill        ████████████████████  100%
  Lines of code   █████████░░░░░░░░░░░   47%   − 53%
  Output tokens   ███████████░░░░░░░░░   55%   − 45%
  Cost            ███████████████░░░░░   74%   − 26%
  Time            ████████████░░░░░░░░   59%   − 41%
  Hidden checks passed   97%  (no-skill 96%)
  Tests where the logic needs one   98%  (no-skill 68%)

  This repo:  /ponytail-debt  (shortcuts you deferred)
              /ponytail-audit (what's still cuttable)
```

## Boundaries

One-shot display. Edits nothing, changes no mode.
"stop ponytail" or "normal mode": revert.
