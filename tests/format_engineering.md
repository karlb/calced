@format = eng
1234567                                 # => 1.23M
1000000                                 # => 1M
4700                                    # => 4.7k
42                                      # => 42
0.0012                                  # => 1.2m
0.5                                     # => 500m
0.0000001234                            # => 123n
-4700                                   # => -4.7k
0                                       # =>  0
123456789                               # => 123M
2.5k * 400                              # => 1M

# precision argument = significant digits
@format = eng(1)
1234567                                 # => 1M
@format = eng(5)
1234567                                 # => 1.2346M
0.0012                                  # => 1.2m

# edge cases
@format = eng
999999                                  # => 1M
1e30                                    # => 1Q
1e-24                                   # => 1y
1.5e40                                  # => 1.50e+40
1.23M + 0                               # => 1.23M

# back to the default mode
@format = minSig
1234567                                 # => 1_234_567
