celo_price = 0.08                                                     # => 0.08
min_base_fee = 25G wei                                                # => 25,000,000,000
price_increase_per_gas = min_base_fee * celo_price / 10^18            # => 0.000000002

USDT tx price increase = (85_000 - 50_000) * price_increase_per_gas   # => 0.00007
USDC tx price increase = (128_000 - 50_000) * price_increase_per_gas  # => 0.000156
