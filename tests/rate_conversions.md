@rate USD/EUR = 0.92

100 USD in EUR                          # => 92
50 EUR in USD                           # => 54.34782609

@rate BTC/USD = 97500

0.5 BTC in USD                          # => 48_750

# Variables with rate conversion
budget = 1000 USD in EUR                # => 920
budget                                  # => 920

# Expressions with rate conversion
(500 + 500) USD in EUR                  # => 920

# Cross-currency conversion via shared intermediate
@rate CELO/USD = 0.083
@rate ETH/USD = 2068

1 ETH in CELO                           # => 24_915.66265
0.5 BTC in EUR                          # => 44_850

# Trailing text with hyphenated word (orphaned operator stripping)
Other non-CELO (converted, approx) 437  # => 437

# Inline conversion with trailing arithmetic
earn_USD = 100                          # => 100
earn_CELO = 500                         # => 500
earn_USD USD in CELO + earn_CELO        # => 1_704.819277
