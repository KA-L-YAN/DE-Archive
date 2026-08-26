# Progress Log

| Date | Day | Topics | Verdict | Follow-up |
|---|---|---|---|---|
| 2026-08-25 | 1 | SQL: CTEs, window functions (ROW_NUMBER) intro; Python: collections, comprehensions | Joins/aggregation solid but sloppy on date-range logic + GROUP BY completeness. CTE concept present, chaining syntax broken. Window functions: real gap (never learned). Python: full rebuild needed (1yr away). | Redo Q3 (most-recent-row-per-customer) using ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...). Then Python basics before comprehensions. |
