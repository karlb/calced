# Result Column Alignment

## Current state

Decimal point alignment with no bloat cap (cap was removed as it produced
half-measures — partial padding that didn't achieve real alignment).

## The problem

With `minSig 10` (default), results can range from 2 chars (`92`) to 21 chars
(`1_125_899_906_842_624`). Uncapped decimal alignment produces excessive
left-padding on small results when paired with large integers:

    2 ^ 50    # => 1_125_899_906_842_624
    1 + 1     # =>                     2     <- 19 chars of padding

Similarly, different-magnitude numbers create ugly gaps:

    1/3       # =>             0.3333333333  <- 12 chars of padding
    1267M     # => 1_267_000_000

## Key insight: minSig normalizes total width

With `minSig 10`, most results are 10-13 chars total regardless of magnitude.
Large numbers grow via separators, small numbers grow via decimals. This means
**right-alignment** often needs very little padding even when decimal alignment
would need a lot:

    | Case                        | Decimal pad | Right pad |
    |-----------------------------|-------------|-----------|
    | `92` vs `54.34782609`       | 0           | 9         |
    | `0.333...` vs `1_267_000_000` | 12        | 1         |
    | `333.333...` vs `100`       | 2           | 8         |
    | `2` vs `2^50`               | 19          | 19        |

## Possible approach: pick the better alignment per section

For each section, compute both decimal-alignment and right-alignment padding.
Use whichever requires less max padding. Give up entirely (no padding) when
even the better option exceeds a threshold.

This naturally chooses:
- Decimal alignment for same-magnitude results (the common case)
- Right alignment for different-magnitude results
- No alignment for pathological cases (e.g., `2` next to `2^50`)

## Competitor behavior

No notepad calculator (Soulver, Numi, Calca, Parsify) does decimal alignment.
All use right-alignment in a result column. Calced's decimal alignment is a
unique feature.

Excel's "General" format adapts displayed precision to column width — reducing
decimal places when space is tight. This is the closest precedent for
display-adaptive formatting.

## Open questions

- What threshold for "give up"? Precision-based (e.g., `precision + N`)?
- Should the choice between decimal/right alignment be per-section or global?
- Should sections split at blank lines or `@rate` directives, not just `#` headers?
- Is display-adaptive precision (reducing decimals to fit alignment) acceptable,
  or is it "silently discarding accuracy"?
