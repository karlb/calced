# Nested Functions

sqrt(abs(-16))                          # => 4
max(sqrt(4), sqrt(9))                   # => 3
round(pi, 2)                            # => 3.14
sqrt(3^2 + 4^2)                         # => 5
ceil(sqrt(8))                           # => 3
floor(sqrt(8))                          # => 2

# Functions with Conversions

sqrt(4) km in miles                     # => 1.242742384
(sqrt(4) + 1) lb in kg                  # => 1.360776

# Percentages in Expressions

(200 + 10%) * 2                         # => 440
200 + 10% + 50                          # => 270
200 + 10% - 50                          # => 170
200 + 10% + 5%                          # => 231
50% of (200 + 300)                      # => 250
200 * 10%                               # =>  20

# SI Prefixes in Expressions

1k + 500                                # =>     1_500
2k * 3k                                 # => 6_000_000
sqrt(1M)                                # =>     1_000
1k + 10%                                # =>     1_100

# Variables with Conversions

dist = 100                              # => 100
dist km in miles                        # =>  62.13711922

# Variables with Percentages

price = 200                             # => 200
price + 15%                             # => 230

# Variables with Functions

val = 16                                # => 16
sqrt(val)                               # =>  4

# Variable Chains

a = 10                                  # => 10
b = a + 5                               # => 15
c = b * 2                               # => 30
a + b + c                               # => 55

# Text Labels with Expressions

monthly 10 + yearly 5                   # =>  15
distance 100 km in miles                # =>  62.13711922
fee 200 + 15%                           # => 230
answer sqrt(16)                         # =>   4

# Text with Trailing Annotations

1500 (monthly rent)                     # => 1_500
100 (plus tax)                          # =>   100

# Parenthesized Text Labels

(just) 100                              # =>   100
(note) 100 + 50                         # =>   150
rent (monthly) 1500                     # => 1_500
(tax) 200 + 10%                         # =>   220
(weight) 150 lb in kg                   # =>    68.0388
(area) sqrt(144)                        # =>    12
(note) 1k + 500                         # => 1_500
(first) 10 + (second) 20                # =>    30
((deep)) 100                            # =>   100
(foo) (bar) 100                         # =>   100

# Date Arithmetic with Expressions

2025-01-01 + (2 * 7) days               # => 2025-01-15
2025-01-01 + 0 days                     # => 2025-01-01
2025-01-01 - 2025-03-01                 # => -59

# Compound Date Durations

2025-01-01 + 1 week + 3 days                    # => 2025-01-11
2025-01-01 + 1 month + 15 days                  # => 2025-02-16
2025-01-15 - 1 week - 3 days                    # => 2025-01-05
2025-01-01 + 1 day + 1 week + 1 month + 1 year  # => 2026-02-09
2025-01-01 + 1 week + 1 week                    # => 2025-01-15
2025-01-01 + 1 week + 2 * 3 days                # => 2025-01-14

# Labels Before Date Arithmetic

note 2025-06-15 + 3 days                # => 2025-06-18
(deadline) 2025-06-15 + 3 days          # => 2025-06-18
(info) 2025-06-15                       # => 2025-06-15
(plan) 2025-01-01 + 1 week + 3 days     # => 2025-01-11
gap 2025-03-01 - 2025-01-01             # => 59

# Leap Year Dates

2024-02-29 + 1 year                     # => 2025-02-28
2024-02-29 + 4 years                    # => 2028-02-29
2024-03-01 - 2024-02-28                 # => 2

# Date Difference in Expressions

(2025-03-01 - 2025-01-01) * 24          # => 1_416
(2025-03-01 - 2025-01-01) + 10          # =>    69
(2025-03-01 - 2025-01-01) days in hr    # => 1_416

# Constants in Expressions

sin(pi / 2)                             # => 1
e ^ 2                                   # => 7.389056099
