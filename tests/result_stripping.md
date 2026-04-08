Lines with existing results are re-evaluated, not trusted.

2 + 2                                   # =>   4
10 * 5                                  # =>  50

Lines with wrong results get corrected.

price = 100                             # => 100
qty = 3                                 # =>   3
price * qty                             # => 300

Trailing whitespace after stripping is harmless.

1 + 1                                   # =>   2

Results with various amounts of padding.

7 * 7                                   # =>  49
100 / 3                                 # =>  33.33333333
