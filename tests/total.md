# Section A
100                                     # => 100 │
200                                     # => 200 │
300                                     # => 300 │
total                                   # => 600 ┘

# Section B
10                                      # => 10 │
20                                      # => 20 │
total                                   # => 30 ┘

# Two totals in one section
100                                     # => 100 │
200                                     # => 200 │
total                                   # => 300 ┘
400                                     # => 400 │
total                                   # => 400 ┘

# Total in expressions
100                                     # =>   100 │
200                                     # =>   200 │
300                                     # =>   300 │
total * 2                               # => 1_200 ┘

# Assign total to variable
10                                      # => 10 │
20                                      # => 20 │
gesamt = sum                            # => 30 ┘
gesamt / 2                              # => 15

# Assign total to variable and use in next section
100                                     # => 100 │
200                                     # => 200 │
first_half = total                      # => 300 ┘

# Next section uses the variable
first_half * 2                          # => 600

# Arithmetic with total
10                                      # =>  10 │
20                                      # =>  20 │
30                                      # =>  30 │
sum + first_half                        # => 360 ┘

# Total minus variable
100                                     # =>  100 │
200                                     # =>  200 │
gesamt = sum                            # =>  300 ┘
50                                      # =>   50 │
total - gesamt                          # => -250 ┘

# Assign total then use in later total expression
10                                      # => 10 │
20                                      # => 20 │
30                                      # => 30 │
subtotal = sum                          # => 60 ┘
40                                      # => 40 │
50                                      # => 50 │
total - subtotal                        # => 30 ┘
