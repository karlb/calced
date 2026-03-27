# Date Arithmetic

2025-01-15 + 3 days                     # => 2025-01-18
2025-01-15 - 7 days                     # => 2025-01-08
2025-01-01 + 2 weeks                    # => 2025-01-15
2025-01-31 + 1 month                    # => 2025-02-28
2025-02-28 + 1 year                     # => 2026-02-28
2025-12-31 + 1 day                      # => 2026-01-01
2025-06-15 + 3 months                   # => 2025-09-15

# Date Differences

2025-03-01 - 2025-01-01                 # => 59
2025-01-01 - 2024-01-01                 # => 366

# Label before bare date treated as plain text
rates from 2026-03-26
(info) 2025-06-15

# Date Variables

deadline = 2025-06-15 + 2 weeks         # => 2025-06-29
deadline - 2025-06-15                   # => 14

# Dates and Totals

2025-01-15 + 3 days                     # => 2025-01-18
100                                     # => 100
200                                     # => 200
total                                   # => 300
