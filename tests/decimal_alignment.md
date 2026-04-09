# Mixed Decimal and Integer Widths

100                                     # => 100
round(pi, 2)                            # =>   3.14
5                                       # =>   5

# Equal Integer Widths (no padding needed)

round(pi, 2)                            # => 3.14
5                                       # => 5
3                                       # => 3

# All Integers Align

10                                      # =>  10
200                                     # => 200
5                                       # =>   5

# Single Result (no alignment)

42                                      # => 42

# Dates Excluded From Alignment

2025-01-01 + 1 days                     # => 2025-01-02
42                                      # => 42

# Negative Numbers Align

0 - 5                                   # => -5
round(pi, 2)                            # =>  3.14

# Bloat Cap Limits Padding (max 3 chars per result)

1M                                      # => 1_000_000
5                                       # =>         5

# Sections Are Independent

1000                                    # => 1_000
5                                       # =>     5

# Scientific Notation Excluded (only 1 alignable → no padding)

@format = scientific
1234.5678                               # => 1.23e+03
@format = minSig
5                                       # => 5

# Second Section Resets

round(pi, 2)                            # => 3.14
7                                       # => 7
