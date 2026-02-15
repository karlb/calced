#!/usr/bin/env python3
"""calced - a notepad calculator that updates files with results."""

import argparse
import math
import os
import re
import sys
import time

RESULT_RE = re.compile(r"\s{2,}# => .*$")
DIRECTIVE_RE = re.compile(r"^@(format|separator)\s*=\s*(.+)$", re.IGNORECASE)
FORMAT_RE = re.compile(r"^(minSig|fixed|scientific|auto)(?:\((\d+)\))?$", re.IGNORECASE)

# SI prefixes (case-sensitive: M=mega, m=milli)
SI_PREFIX = {
    "Q": 1e30,  # quetta
    "R": 1e27,  # ronna
    "Y": 1e24,  # yotta
    "Z": 1e21,  # zetta
    "E": 1e18,  # exa
    "P": 1e15,  # peta
    "T": 1e12,  # tera
    "G": 1e9,  # giga
    "M": 1e6,  # mega
    "K": 1e3,  # kilo (unofficial but common)
    "k": 1e3,  # kilo
    "m": 1e-3,  # milli
    "u": 1e-6,  # micro (ASCII)
    "μ": 1e-6,  # micro
    "n": 1e-9,  # nano
    "p": 1e-12,  # pico
    "f": 1e-15,  # femto
    "a": 1e-18,  # atto
    "z": 1e-21,  # zepto
    "y": 1e-24,  # yocto
}
SI_SUFFIX_RE = "[" + re.escape("".join(SI_PREFIX.keys())) + "]"

BUILTIN_FUNCS_1 = {
    "sqrt": math.sqrt,
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "exp": math.exp,
}
BUILTIN_FUNCS_N = {
    "round": lambda args: round(args[0])
    if len(args) == 1
    else round(args[0], int(args[1])),
    "min": lambda args: min(args),
    "max": lambda args: max(args),
}
BUILTIN_FUNC_NAMES = set(BUILTIN_FUNCS_1) | set(BUILTIN_FUNCS_N)

BUILTIN_CONSTS = {"pi": math.pi, "e": math.e, "tau": math.tau}

# --- Unit conversion tables ---
UNIT_TABLE = {
    "length": {
        "_base": "meter",
        "mm": 0.001,
        "millimeter": 0.001,
        "millimeters": 0.001,
        "cm": 0.01,
        "centimeter": 0.01,
        "centimeters": 0.01,
        "m": 1,
        "meter": 1,
        "meters": 1,
        "km": 1000,
        "kilometer": 1000,
        "kilometers": 1000,
        "in": 0.0254,
        "inch": 0.0254,
        "inches": 0.0254,
        "ft": 0.3048,
        "foot": 0.3048,
        "feet": 0.3048,
        "yd": 0.9144,
        "yard": 0.9144,
        "yards": 0.9144,
        "mi": 1609.344,
        "mile": 1609.344,
        "miles": 1609.344,
    },
    "mass": {
        "_base": "gram",
        "mg": 0.001,
        "milligram": 0.001,
        "milligrams": 0.001,
        "g": 1,
        "gram": 1,
        "grams": 1,
        "kg": 1000,
        "kilogram": 1000,
        "kilograms": 1000,
        "oz": 28.3495,
        "ounce": 28.3495,
        "ounces": 28.3495,
        "lb": 453.592,
        "lbs": 453.592,
        "pound": 453.592,
        "pounds": 453.592,
    },
    "temperature": {
        "_base": "special",
        "c": "c",
        "celsius": "c",
        "f": "f",
        "fahrenheit": "f",
        "k": "k",
        "kelvin": "k",
    },
    "data": {
        "_base": "byte",
        "b": 1,
        "byte": 1,
        "bytes": 1,
        "kb": 1000,
        "kilobyte": 1000,
        "kilobytes": 1000,
        "mb": 1e6,
        "megabyte": 1e6,
        "megabytes": 1e6,
        "gb": 1e9,
        "gigabyte": 1e9,
        "gigabytes": 1e9,
        "tb": 1e12,
        "terabyte": 1e12,
        "terabytes": 1e12,
        "kib": 1024,
        "kibibyte": 1024,
        "kibibytes": 1024,
        "mib": 1048576,
        "mebibyte": 1048576,
        "mebibytes": 1048576,
        "gib": 1073741824,
        "gibibyte": 1073741824,
        "gibibytes": 1073741824,
        "tib": 1099511627776,
        "tebibyte": 1099511627776,
        "tebibytes": 1099511627776,
    },
    "time": {
        "_base": "second",
        "ms": 0.001,
        "millisecond": 0.001,
        "milliseconds": 0.001,
        "s": 1,
        "sec": 1,
        "second": 1,
        "seconds": 1,
        "min": 60,
        "minute": 60,
        "minutes": 60,
        "hr": 3600,
        "hour": 3600,
        "hours": 3600,
        "day": 86400,
        "days": 86400,
        "week": 604800,
        "weeks": 604800,
    },
    "volume": {
        "_base": "ml",
        "ml": 1,
        "milliliter": 1,
        "milliliters": 1,
        "l": 1000,
        "liter": 1000,
        "liters": 1000,
        "tsp": 4.929,
        "teaspoon": 4.929,
        "teaspoons": 4.929,
        "tbsp": 14.787,
        "tablespoon": 14.787,
        "tablespoons": 14.787,
        "floz": 29.574,
        "cup": 236.588,
        "cups": 236.588,
        "pt": 473.176,
        "pint": 473.176,
        "pints": 473.176,
        "qt": 946.353,
        "quart": 946.353,
        "quarts": 946.353,
        "gal": 3785.41,
        "gallon": 3785.41,
        "gallons": 3785.41,
    },
}

# Flat lookup: lowercase name → (dimension, factor_or_key)
UNIT_LOOKUP = {}
for _dim, _units in UNIT_TABLE.items():
    for _name, _factor in _units.items():
        if _name.startswith("_"):
            continue
        UNIT_LOOKUP[_name] = (_dim, _factor)


def convert_temperature(value, from_key, to_key):
    """Convert temperature via Kelvin as intermediate."""
    # To Kelvin
    if from_key == "c":
        k = value + 273.15
    elif from_key == "f":
        k = (value - 32) * 5 / 9 + 273.15
    else:
        k = value
    # From Kelvin
    if to_key == "c":
        return k - 273.15
    elif to_key == "f":
        return (k - 273.15) * 9 / 5 + 32
    else:
        return k


class ParseError(Exception):
    pass


def tokenize(text):
    """Tokenize text into math-relevant tokens, preserving words."""
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        if text[i].isspace():
            i += 1
            continue

        start = i

        # Hex/binary/octal: 0xFF, 0b1010, 0o77
        if text[i] == "0" and i + 1 < n and text[i + 1] in "xXbBoO":
            m = re.match(r"0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+", text[i:])
            if m:
                val = float(int(m.group(), 0))
                end = i + m.end()
                tokens.append(("NUM", val, start, end))
                i = end
                continue

        # Numbers: 1,000 or 1_000 or 1.5 or .5 or 1.5e3 with optional SI suffix
        m = re.match(
            r"(\d(?:\d|_|,(?=\d))*\.?\d*|\.\d+)(?:([eE][+-]?\d+)|("
            + SI_SUFFIX_RE
            + r"))?",
            text[i:],
        )
        if m and m.group(1):
            raw = m.group(1).replace(",", "").replace("_", "")
            exp = m.group(2)
            if exp:
                val = float(raw + exp)
            else:
                val = float(raw)
            suffix = m.group(3)
            if suffix:
                val *= SI_PREFIX[suffix]
            end = i + m.end()
            if end < n and text[end] == "%":
                tokens.append(("PCT", val, start, end + 1))
                i = end + 1
            else:
                tokens.append(("NUM", val, start, end))
                i = end
            continue

        if text[i] in "+-":
            tokens.append(("ADDOP", text[i], start, i + 1))
            i += 1
            continue
        if text[i] in "*/":
            tokens.append(("MULOP", text[i], start, i + 1))
            i += 1
            continue
        if text[i] == "^":
            tokens.append(("POW", "^", start, i + 1))
            i += 1
            continue
        if text[i] == "%":
            tokens.append(("MULOP", "%", start, i + 1))  # modulo when standalone
            i += 1
            continue
        if text[i] == "(":
            tokens.append(("LPAREN", "(", start, i + 1))
            i += 1
            continue
        if text[i] == ")":
            tokens.append(("RPAREN", ")", start, i + 1))
            i += 1
            continue
        if text[i] == ",":
            tokens.append(("COMMA", ",", start, i + 1))
            i += 1
            continue
        if text[i] == "=":
            tokens.append(("EQ", "=", start, i + 1))
            i += 1
            continue

        # Words/identifiers
        m = re.match(r"[a-zA-Z_]\w*", text[i:])
        if m:
            word = m.group()
            wl = word.lower()
            end = i + m.end()
            if wl == "of":
                tokens.append(("OF", "of", start, end))
            elif wl in ("total", "sum"):
                tokens.append(("TOTAL", wl, start, end))
            elif wl in BUILTIN_FUNC_NAMES:
                tokens.append(("FUNC", wl, start, end))
            else:
                tokens.append(("WORD", word, start, end))
            i = end
            continue

        i += 1  # skip unknown chars

    tokens.append(("EOF", None, n, n))
    return tokens


DIM = "\033[2m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RESET = "\033[0m"


def classify_line(text, variables):
    """Classify tokens in a line for syntax highlighting.

    Returns "blank", "comment", "directive", or list of [start, end, dim] tuples.
    """
    stripped = text.strip()
    if not stripped:
        return "blank"
    if stripped.startswith("#"):
        return "comment"
    if DIRECTIVE_RE.match(stripped):
        return "directive"

    tokens = tokenize(text)
    all_names = set(BUILTIN_CONSTS) | set(variables or {})

    has_math = any(
        t[0] in ("NUM", "PCT", "FUNC", "TOTAL")
        or (t[0] == "WORD" and t[1].lower() in all_names)
        for t in tokens
        if t[0] != "EOF"
    )

    active = set()

    if has_math:
        if any(t[0] == "TOTAL" for t in tokens if t[0] != "EOF"):
            for idx, t in enumerate(tokens):
                if t[0] == "TOTAL":
                    active.add(idx)
        else:
            math_start = 0
            if len(tokens) >= 3 and tokens[0][0] == "WORD" and tokens[1][0] == "EQ":
                active.add(0)
                active.add(1)
                math_start = 2

            conversion, conv_start = _detect_conversion(tokens)
            eof_idx = len(tokens) - 1
            if conversion is not None:
                active.update({conv_start, conv_start + 1, conv_start + 2})

            all_vars = {**BUILTIN_CONSTS, **(variables or {})}
            math_tokens, math_to_orig = _build_math(
                tokens, math_start, conv_start, eof_idx, all_vars
            )
            result, consumed = _try_parse(math_tokens)

            if result is not None:
                for i in range(consumed):
                    active.add(math_to_orig[i])
            else:
                for i, orig_idx in enumerate(math_to_orig):
                    if math_tokens[i][0] in ("NUM", "PCT"):
                        active.add(orig_idx)

    spans = []
    pos = 0
    for idx, t in enumerate(tokens):
        if t[0] == "EOF":
            break
        start, end = t[2], t[3]
        if start > pos:
            spans.append([pos, start, True])
        spans.append([start, end, idx not in active])
        pos = end
    if pos < len(text):
        spans.append([pos, len(text), True])
    return spans


def colorize_expr(text, variables):
    """Return text with dim escapes around ignored (non-math) words."""
    cls = classify_line(text, variables)
    if isinstance(cls, str):
        return text
    parts = []
    for start, end, dim in cls:
        chunk = text[start:end]
        if dim:
            parts.append(DIM + chunk + RESET)
        else:
            parts.append(chunk)
    return "".join(parts)


def colorize_line(line, result, fmt_result_str, align, variables):
    """Return a colorized version of an output line."""
    stripped = line.strip()
    if result is not None:
        colored_expr = colorize_expr(stripped, variables)
        # Reconstruct with leading whitespace preserved
        leading = line[: len(line) - len(line.lstrip())]
        pad = max(align - len(line.rstrip()), 2)
        return (
            leading
            + colored_expr
            + " " * pad
            + DIM
            + "# => "
            + RESET
            + GREEN
            + fmt_result_str
            + RESET
        )
    if stripped.startswith("#"):
        return BOLD + line + RESET
    if DIRECTIVE_RE.match(stripped):
        return DIM + line + RESET
    return line


class Parser:
    """Recursive descent parser for math expressions."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ("EOF", None)

    def consume(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def parse_expr(self):
        left = self.parse_term()
        while self.peek()[0] == "ADDOP":
            op = self.consume()[1]
            # Handle percentage: 100 + 25% means 100 * 1.25
            if self.peek()[0] == "PCT":
                pct = self.consume()[1]
                if op == "+":
                    left *= 1 + pct / 100
                else:
                    left *= 1 - pct / 100
            else:
                right = self.parse_term()
                left = left + right if op == "+" else left - right
        return left

    def parse_term(self):
        left = self.parse_power()
        while self.peek()[0] == "MULOP":
            op = self.consume()[1]
            right = self.parse_power()
            if op == "*":
                left *= right
            elif op == "/":
                if right == 0:
                    raise ZeroDivisionError
                left /= right
            elif op == "%":
                if right == 0:
                    raise ZeroDivisionError
                left %= right
        return left

    def parse_power(self):
        base = self.parse_unary()
        if self.peek()[0] == "POW":
            self.consume()
            exp = self.parse_unary()
            return base**exp
        return base

    def parse_unary(self):
        if self.peek()[0] == "ADDOP":
            op = self.consume()[1]
            val = self.parse_primary()
            return -val if op == "-" else val
        return self.parse_primary()

    def parse_primary(self):
        t = self.peek()
        if t[0] == "NUM":
            self.consume()
            return t[1]
        if t[0] == "PCT":
            self.consume()
            pct = t[1]
            if self.peek()[0] == "OF":
                self.consume()
                base = self.parse_expr()
                return pct / 100 * base
            return pct / 100  # standalone percentage
        if t[0] == "FUNC":
            name = self.consume()[1]
            if self.peek()[0] != "LPAREN":
                raise ParseError(f"Expected ( after {name}")
            self.consume()
            args = [self.parse_expr()]
            while self.peek()[0] == "COMMA":
                self.consume()
                args.append(self.parse_expr())
            if self.peek()[0] != "RPAREN":
                raise ParseError("Missing )")
            self.consume()
            if name in BUILTIN_FUNCS_1:
                if len(args) != 1:
                    raise ParseError(f"{name} takes 1 argument")
                return BUILTIN_FUNCS_1[name](args[0])
            if name in BUILTIN_FUNCS_N:
                return BUILTIN_FUNCS_N[name](args)
            raise ParseError(f"Unknown function: {name}")
        if t[0] == "LPAREN":
            self.consume()
            val = self.parse_expr()
            if self.peek()[0] != "RPAREN":
                raise ParseError("Missing )")
            self.consume()
            return val
        raise ParseError(f"Unexpected: {t}")


def _detect_conversion(tokens):
    """Detect unit conversion suffix: ... <from_unit> in|to <to_unit> EOF."""
    eof_idx = len(tokens) - 1
    if eof_idx >= 4:
        t_fr = tokens[eof_idx - 3]
        t_kw = tokens[eof_idx - 2]
        t_to = tokens[eof_idx - 1]
        if (
            t_to[0] in ("WORD", "FUNC")
            and t_kw[0] == "WORD"
            and t_kw[1].lower() in ("in", "to")
            and t_fr[0] in ("WORD", "FUNC")
        ):
            fr_name = t_fr[1].lower()
            to_name = t_to[1].lower()
            if fr_name in UNIT_LOOKUP and to_name in UNIT_LOOKUP:
                fr_dim, fr_factor = UNIT_LOOKUP[fr_name]
                to_dim, to_factor = UNIT_LOOKUP[to_name]
                if fr_dim == to_dim:
                    return (fr_dim, fr_factor, to_factor), eof_idx - 3
    return None, eof_idx


def _build_math(tokens, start, conv_start, eof_idx, all_vars):
    """Build math token list, resolving variables and skipping non-math tokens.

    Returns (math_tokens, math_to_orig) where math_to_orig[i] is the
    original token index that math_tokens[i] came from.
    """
    math_tokens = []
    math_to_orig = []
    paren_depth = 0
    for idx in range(start, len(tokens)):
        t = tokens[idx]
        if conv_start <= idx < eof_idx:
            continue
        if t[0] == "WORD":
            wl = t[1].lower()
            if wl in all_vars:
                math_tokens.append(("NUM", all_vars[wl], t[2], t[3]))
                math_to_orig.append(idx)
        elif t[0] == "EQ":
            pass
        elif t[0] == "COMMA" and paren_depth == 0:
            pass
        else:
            if t[0] == "LPAREN":
                paren_depth += 1
            elif t[0] == "RPAREN":
                paren_depth -= 1
            math_tokens.append(t)
            math_to_orig.append(idx)
    return math_tokens, math_to_orig


def _try_parse(math_tokens):
    """Parse math tokens, allowing trailing balanced parenthetical annotations.

    Returns (result, consumed) on success, or (None, -1) on failure.
    """
    try:
        parser = Parser(math_tokens)
        result = parser.parse_expr()
        if parser.peek()[0] == "EOF":
            return result, parser.pos
        depth = 0
        ok = True
        for t in math_tokens[parser.pos :]:
            if t[0] == "EOF":
                break
            if depth == 0 and t[0] != "LPAREN":
                ok = False
                break
            if t[0] == "LPAREN":
                depth += 1
            elif t[0] == "RPAREN":
                depth -= 1
        if ok and depth == 0:
            return result, parser.pos
        return None, -1
    except (ParseError, ZeroDivisionError, ValueError, OverflowError):
        return None, -1


def evaluate_line(text, variables):
    """Evaluate a line. Returns (result, variables) or (None, variables)."""
    tokens = tokenize(text)

    if any(t[0] == "TOTAL" for t in tokens):
        return "TOTAL", variables

    all_vars = {**BUILTIN_CONSTS, **variables}

    has_value = any(
        t[0] in ("NUM", "PCT", "FUNC") or (t[0] == "WORD" and t[1].lower() in all_vars)
        for t in tokens
    )
    if not has_value:
        return None, variables

    pos = 0
    var_name = None
    if len(tokens) >= 3 and tokens[0][0] == "WORD" and tokens[1][0] == "EQ":
        var_name = tokens[0][1].lower()
        pos = 2

    conversion, conv_start = _detect_conversion(tokens)
    eof_idx = len(tokens) - 1
    math_tokens, _ = _build_math(tokens, pos, conv_start, eof_idx, all_vars)
    result, _ = _try_parse(math_tokens)

    if result is None:
        return None, variables
    if conversion is not None:
        dim, from_factor, to_factor = conversion
        if dim == "temperature":
            result = convert_temperature(result, from_factor, to_factor)
        else:
            result = result * from_factor / to_factor
    if var_name:
        variables = {**variables, var_name: result}
    return result, variables


def format_result(n, fmt_opts=None):
    """Format a number according to fmt_opts."""
    if fmt_opts is None:
        fmt_opts = {"mode": "minSig", "precision": 3, "separator": "underscore"}
    mode = fmt_opts["mode"]
    prec = fmt_opts["precision"]
    sep = fmt_opts["separator"]

    def apply_sep(s):
        if sep == "comma":
            return s
        if sep == "underscore":
            return s.replace(",", "_")
        if sep == "space":
            return s.replace(",", " ")
        return s.replace(",", "")  # "off"

    if mode == "minSig":
        if n == 0:
            s = "0"
        else:
            from math import log10, floor

            show_dec = max(-floor(log10(abs(n)) + 1) + prec, 0)
            rounded = round(n, show_dec)
            if show_dec == 0:
                s = f"{int(rounded):,}"
            else:
                s = f"{rounded:,.{show_dec}f}"
                s = s.rstrip("0").rstrip(".")
        return apply_sep(s)

    if mode == "fixed":
        return apply_sep(f"{n:,.{prec}f}")

    if mode == "scientific":
        # prec = sig figs; Python's e format takes decimal places = sig figs - 1
        return f"{n:.{max(prec - 1, 0)}e}"

    if mode == "auto":
        return f"{n:.{prec}g}"

    return str(n)


def process_file(filepath, show=False):
    """Read, evaluate, and write back the file with results (or print to stdout)."""
    with open(filepath, "r") as f:
        original = f.read()

    use_color = show and not os.environ.get("NO_COLOR", "")

    lines = original.split("\n")
    # Remove trailing empty element from split (file ended with \n)
    if lines and lines[-1] == "":
        lines = lines[:-1]

    variables = {}
    results_acc = []  # for total/sum accumulation
    fmt_opts = {"mode": "minSig", "precision": 3, "separator": "underscore"}
    evaluated = []  # list of (clean_line, result_or_none, fmt_opts_snapshot, vars_snapshot)

    for line in lines:
        clean = RESULT_RE.sub("", line).rstrip()
        stripped = clean.strip()

        # Check for format directives
        dm = DIRECTIVE_RE.match(stripped)
        if dm:
            key = dm.group(1).lower()
            val = dm.group(2).strip()
            if key == "format":
                fm = FORMAT_RE.match(val)
                if fm:
                    mode = fm.group(1).lower()
                    # Normalize mode name
                    mode_map = {
                        "minsig": "minSig",
                        "fixed": "fixed",
                        "scientific": "scientific",
                        "auto": "auto",
                    }
                    fmt_opts["mode"] = mode_map.get(mode, mode)
                    if fm.group(2) is not None:
                        fmt_opts["precision"] = int(fm.group(2))
                    else:
                        # defaults: scientific/auto default to 3
                        fmt_opts["precision"] = 3
            elif key == "separator":
                v = val.lower()
                if v in ("off", "underscore", "comma", "space"):
                    fmt_opts["separator"] = v
            evaluated.append((clean, None, None, None))
            continue

        # Header lines reset the accumulator
        if stripped.startswith("#"):
            results_acc.clear()
            evaluated.append((clean, None, None, None))
            continue

        # Empty lines
        if not stripped:
            results_acc.append(None)
            evaluated.append(("", None, None, None))
            continue

        vars_before = dict(variables)
        result, variables = evaluate_line(stripped, variables)

        if result == "TOTAL":
            total = sum(r for r in results_acc if r is not None)
            results_acc.append(total)
            evaluated.append((clean, total, dict(fmt_opts), vars_before))
        elif result is not None:
            results_acc.append(result)
            evaluated.append((clean, result, dict(fmt_opts), vars_before))
        else:
            results_acc.append(None)
            evaluated.append((clean, None, None, None))

    # Compute alignment column from longest line that has a result
    result_lines = [c for c, r, _, _ in evaluated if r is not None]
    if result_lines:
        max_len = max(len(l) for l in result_lines)
        align = max(max_len + 2, 40)
    else:
        align = 40

    # Format output
    output = []
    colored_output = []
    for clean, result, opts, vsnap in evaluated:
        if result is not None:
            fmt_str = format_result(result, opts)
            output.append(f"{clean.ljust(align)}# => {fmt_str}")
            if use_color:
                colored_output.append(
                    colorize_line(clean, result, fmt_str, align, vsnap)
                )
        else:
            output.append(clean)
            if use_color:
                colored_output.append(colorize_line(clean, None, None, align, None))

    new_content = "\n".join(output) + "\n"
    if show:
        if use_color:
            sys.stdout.write("\n".join(colored_output) + "\n")
        else:
            sys.stdout.write(new_content)
        return new_content != original
    if new_content != original:
        with open(filepath, "w") as f:
            f.write(new_content)
        return True
    return False


def watch_file(filepath, show=False, interval=0.5):
    """Watch file for changes and re-process."""
    last_mtime = os.path.getmtime(filepath)
    print(f"Watching {filepath} for changes... (Ctrl+C to stop)", file=sys.stderr)
    try:
        while True:
            try:
                mtime = os.path.getmtime(filepath)
                if mtime != last_mtime:
                    if show:
                        sys.stderr.write("\033[2J\033[H")
                        sys.stderr.flush()
                    if process_file(filepath, show=show):
                        if not show:
                            print(f"  Updated results.")
                    last_mtime = os.path.getmtime(filepath)
            except FileNotFoundError:
                pass
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        prog="calced",
        description="A notepad calculator that evaluates expressions in text files.",
    )
    parser.add_argument("file", help="path to .md file")
    parser.add_argument(
        "-w", "--watch", action="store_true", help="watch for changes and auto-update"
    )
    parser.add_argument(
        "-s",
        "--show",
        action="store_true",
        help="print result to stdout instead of updating the file",
    )
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    if args.show and args.watch:
        sys.stderr.write("\033[2J\033[H")
        sys.stderr.flush()
    process_file(args.file, show=args.show)

    if args.watch:
        watch_file(args.file, show=args.show)


if __name__ == "__main__":
    main()
