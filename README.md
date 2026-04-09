<p align="center">
  <img src="logo.svg" alt="calced logo" width="128">
</p>

# calced

A notepad calculator that evaluates math expressions in plain text files. Available as a **CLI tool** and a **web app**.

## Why calced?

Spreadsheets are overkill for quick calculations. REPLs lose context once you close them. calced keeps your math in plain text files where results stay next to the expressions, files can be versioned and diffed, and you use whatever editor you want.

Compared to other notepad calculators:

- **Tiny, no dependencies** — the CLI is a single 47KB Python file (stdlib only), the web app is a single 52KB HTML file. No build step, no node_modules, no Electron.
- **Works offline** — both versions run entirely locally. Save the HTML file or install the CLI and you're set.
- **Both CLI and web** — same syntax, same test suite, but well adapted to each environment.
- **Stable results** — shared web URLs include the major version, so they won't break on updates. Files store results inline. All configuration is inside the documents.

## Web

[Open the web app](https://calced.karl.berlin) in a browser.

## CLI

```
calced <file>           # evaluate and update file in place
calced -s <file>        # print result to stdout (don't modify file)
calced -w <file>        # watch for changes and auto-update
calced -w -s <file>     # watch and print (clears screen on change)
calced -u <file>        # print shareable web URL
```

### Installation

Requires Python 3.9+. Any typical Python install method works (`pip install calced`, etc.).

```sh
# Install as a CLI tool
uv tool install calced

# Or run without installing
uvx calced <file>

# Or just grab the single-file script and run it directly
python calced.py <file>
```

## How it works

Write math anywhere in a plain text file. Results are appended inline as `# => result` comments. Non-math lines are left untouched.

<!-- [[[cog
import subprocess, tempfile, os

def run_calced(text):
    text = text.lstrip('\n')
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(text)
        fname = f.name
    env = {**os.environ, 'NO_COLOR': '1'}
    result = subprocess.run(
        ['python', 'python/calced.py', '-s', fname],
        capture_output=True, text=True, env=env
    )
    url_result = subprocess.run(
        ['python', 'python/calced.py', '--url', fname],
        capture_output=True, text=True, env=env
    )
    os.unlink(fname)
    url = url_result.stdout.strip()
    cog.out('```\n' + result.stdout + '```\n')
    cog.out(f'<sub>[Try in web app]({url})</sub>\n')

run_calced("""
rent 1500
groceries 200 + 150
utilities 80 + 45 + 30
total
""")
]]] -->
```
rent 1500                               # => 1_500 │
groceries 200 + 150                     # =>   350 │
utilities 80 + 45 + 30                  # =>   155 │
total                                   # => 2_005 ┘
```
<sub>[Try in web app](https://calced.karl.berlin/0/#K0rNK1EwNDUw4Eovyk9OLcpMLVYwMjBQ0AYJcpWWZOZkloDELEBCJqZAwtiAqyS_JDGHCwA)</sub>
<!-- [[[end]]] -->

Results are aligned and updated in place each time you run the CLI (or automatically in watch mode), or live as you type in the web app.

## Features

### Basic arithmetic

<!-- [[[cog
run_calced("""
2 + 3
10 * (4 + 6)
2 ^ 10
17 % 5
""")
]]] -->
```
2 + 3                                   # =>     5
10 * (4 + 6)                            # =>   100
2 ^ 10                                  # => 1_024
17 % 5                                  # =>     2
```
<sub>[Try in web app](https://calced.karl.berlin/0/#M1LQVjDmMjRQ0FLQMAGyzTS5jBTiFAwNuAzNFVQVTLkA)</sub>
<!-- [[[end]]] -->

### Variables

<!-- [[[cog
run_calced("""
income = 5000
tax_rate = 22%
tax = income * tax_rate
after_tax = income - tax
""")
]]] -->
```
income = 5000                           # => 5_000
tax_rate = 22%                          # =>     0.22
tax = income * tax_rate                 # => 1_100
after_tax = income - tax                # => 3_900
```
<sub>[Try in web app](https://calced.karl.berlin/0/#y8xLzs9NVbBVMDUwMOAqSayIL0osAfGNjFRBXCArE6JESwEmy5WYVpJaFI8iqwuS5QIA)</sub>
<!-- [[[end]]] -->

### Percentages

<!-- [[[cog
run_calced("""
50% of 300
200 + 15%
200 - 10%
10 as % of 50
""")
]]] -->
```
50% of 300                              # => 150
200 + 15%                               # => 230
200 - 10%                               # => 180
10 as % of 50                           # =>  20
```
<sub>[Try in web app](https://calced.karl.berlin/0/#MzVQVchPUzA2MOAyMjBQ0FYwNFUFs3QVDA1UuQwNFBKLFcBKTA24AA)</sub>
<!-- [[[end]]] -->

### SI prefixes

<!-- [[[cog
run_calced("""
1k
1M
1.5G
500n * 2
""")
]]] -->
```
1k                                      # =>         1_000
1M                                      # =>     1_000_000
1.5G                                    # => 1_500_000_000
500n * 2                                # =>             0.000001
```
<sub>[Try in web app](https://calced.karl.berlin/0/#M8zmMvTlMtQzdecyNTDIU9BSMOICAA)</sub>
<!-- [[[end]]] -->

Supported: `k`/`K` (kilo), `M` (mega), `G` (giga), `T` (tera), `P` (peta), `E` (exa), `m` (milli), `u`/`μ` (micro), `n` (nano), `p` (pico), `f` (femto), and more.

### Unit conversions

<!-- [[[cog
run_calced("""
5 km in miles
100 C in F
1 gib in mib
60 min in hr
1 gal in l
""")
]]] -->
```
5 km in miles                           # =>     3.106855961
100 C in F                              # =>   212
1 gib in mib                            # => 1_024
60 min in hr                            # =>     1
1 gal in l                              # =>     3.78541
```
<sub>[Try in web app](https://calced.karl.berlin/0/#M1XIzlXIzFPIzcxJLeYyNDBQcAZx3bgMFdIzkyAySVxmBkAqD8TLKALJJOaA2DlcAA)</sub>
<!-- [[[end]]] -->

Supported dimensions: length, mass, temperature, data, time, volume. Use `in` or `to`.

### Rate conversions

Define exchange rates (or any conversion rate) with `@rate`, then convert using `in`.

<!-- [[[cog
run_calced("""
@rate USD/EUR = 0.92
100 USD in EUR
50 EUR in USD
""")
]]] -->
```
@rate USD/EUR = 0.92
100 USD in EUR                          # => 92
50 EUR in USD                           # => 54.34782609
```
<sub>[Try in web app](https://calced.karl.berlin/0/#cyhKLElVCA120XcNDVKwVTDQszTiMjQwAAkpZOYpAEW5TA1AFIgHFOQCAA)</sub>
<!-- [[[end]]] -->

### Functions

<!-- [[[cog
run_calced("""
sqrt(16)
round(3.14159, 2)
min(5, 2, 8)
max(1, 9, 3)
log10(1000)
sin(0)
""")
]]] -->
```
sqrt(16)                                # => 4
round(3.14159, 2)                       # => 3.14
min(5, 2, 8)                            # => 2
max(1, 9, 3)                            # => 9
log10(1000)                             # => 3
sin(0)                                  # => 0
```
<sub>[Try in web app](https://calced.karl.berlin/0/#Ky4sKtEwNNPkKsovzUvRMNYzNDE0tdRRMNLkys3M0zAFsnQULICcxAoNQx0FoIyxJldOfrqhgYahgYGBJlcxUBWQAgA)</sub>
<!-- [[[end]]] -->

Available: `sqrt`, `abs`, `floor`, `ceil`, `round`, `log`, `log2`, `log10`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `exp`, `min`, `max`

### Constants

<!-- [[[cog
run_calced("""
pi * 2
e ^ 1
""")
]]] -->
```
pi * 2                                  # => 6.283185307
e ^ 1                                   # => 2.718281828
```
<sub>[Try in web app](https://calced.karl.berlin/0/#K8hU0FIw4kpViFMw5AIA)</sub>
<!-- [[[end]]] -->

### Date arithmetic

<!-- [[[cog
run_calced("""
2025-01-15 + 3 days
2025-01-31 + 1 month
2025-03-01 - 2025-01-01
""")
]]] -->
```
2025-01-15 + 3 days                     # => 2025-01-18
2025-01-31 + 1 month                    # => 2025-02-28
2025-03-01 - 2025-01-01                 # => 59
```
<sub>[Try in web app](https://calced.karl.berlin/0/#MzIwMtU1MNQ1NFXQVjBWSEmsLOYygooZGwLFDBVy8_NKMqCCxkBxBV0FmAoDQy4A)</sub>
<!-- [[[end]]] -->

Supports `days`, `weeks`, `months`, `years`. Subtracting two dates returns the difference in days. `today`, `tomorrow`, and `yesterday` work as keywords.

### Totals

The `total` (or `sum`) keyword sums all numeric results since the last `#` heading or start of file.

<!-- [[[cog
run_calced("""
rent 1500
groceries 350
utilities 155
total
""")
]]] -->
```
rent 1500                               # => 1_500 │
groceries 350                           # =>   350 │
utilities 155                           # =>   155 │
total                                   # => 2_005 ┘
```
<sub>[Try in web app](https://calced.karl.berlin/0/#K0rNK1EwNDUw4Eovyk9OLcpMLVYwNjXgKi3JzMksAfEMTU25SvJLEnO4AA)</sub>
<!-- [[[end]]] -->

Blank lines are ignored in the total; headings reset it.

### Number formats

Numbers can be written with commas or underscores as separators (`1,000` or `1_000`), in hex/binary/octal (`0xFF`, `0b1010`, `0o77`), or in scientific notation (`1.5e3`).

### Trailing annotations

Parenthetical notes after an expression are ignored:

<!-- [[[cog
run_calced("""
celo_price = 0.08 (see http://coinmarketcap.com)
""")
]]] -->
```
celo_price = 0.08 (see http://coinmarketcap.com)  # => 0.08
```
<sub>[Try in web app](https://calced.karl.berlin/0/#S07NyY8vKMpMTlWwVTDQM7BQ0ChOTVXIKCkpsNLXT87PzMtNLMpOLUlOLNBLzs_V5AIA)</sub>
<!-- [[[end]]] -->

### Format directives

Control output formatting with `@format` and `@separator` directives. These apply to all subsequent lines until changed.

<!-- [[[cog
run_calced("""
1000000
@format = fixed(2)
1000000
@format = scientific
1000000
@separator = comma
@format = minSig(3)
1000000
""")
]]] -->
```
1000000                                 # => 1_000_000
@format = fixed(2)
1000000                                 # => 1_000_000.00
@format = scientific
1000000                                 # => 1.00e+06
@separator = comma
@format = minSig(3)
1000000                                 # => 1,000,000
```
<sub>[Try in web app](https://calced.karl.berlin/0/#MzQAAy6HtPyi3MQSBVuFtMyK1BQNI00uQwyp4uTM1LySzLTMZIRkcWpBYlFiSX4RUD45Pzc3EUl9bmZecGa6hjHCLAA)</sub>
<!-- [[[end]]] -->
