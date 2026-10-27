1234.5678                               # => 1_234.5678
@format = fixed(2)
1234.5678                               # => 1_234.57
@format = scientific
1234.5678                               # => 1.23e+03
@format = scientific(5)
1234.5678                               # => 1.2346e+03
@format = auto(4)
1234.5678                               # =>  1235
@format = minSig(5)
1234.5678                               # => 1_234.6
@format = minSig
1234.5678                               # => 1_234.5678

# Exact digits beyond float precision
@format = minSig
3^40                                    # =>    12_157_665_459_056_928_801
@format = fixed(2)
3^40                                    # =>    12_157_665_459_056_928_801.00
1e21                                    # => 1_000_000_000_000_000_000_000.00
@format = minSig(20)
1/3                                     # =>                             0.33333333333333333333
0.1                                     # =>                             0.1

# Half-up rounding
@format = fixed(2)
0.125                                   # => 0.13
@format = fixed(0)
2.5                                     # => 3
@format = auto(4)
12345                                   # => 1.235e+04

# auto trims zeros like Python's "g"
1                                       # => 1
0.00001                                 # => 1e-05
@format = scientific(3)
0                                       # => 0.00e+00
