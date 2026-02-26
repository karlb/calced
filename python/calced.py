#!/usr/bin/env python3
"""calced - a notepad calculator that updates files with results."""

import argparse
import base64
import calendar
import datetime
import difflib
import importlib.metadata
import json
import math
import os
import re
from decimal import Decimal, InvalidOperation
import sys
import time
import zlib

RESULT_RE = re.compile(r"\s{2,}# => .*$")
DIRECTIVE_RE = re.compile(r"^@(format|separator)\s*=\s*(.+)$", re.IGNORECASE)
FORMAT_RE = re.compile(r"^(minSig|fixed|scientific|auto)(?:\((\d+)\))?$", re.IGNORECASE)
RATE_RE = re.compile(r"^@rate\s+(\w+)/(\w+)\s*=\s*(.+)$", re.IGNORECASE)

# --- Date/time support ---
DATE = "DATE"
ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
DATE_KEYWORDS = {"today", "tomorrow", "yesterday"}
DURATION_UNITS = {"day", "days", "week", "weeks", "month", "months", "year", "years"}


def _resolve_date_keyword(keyword):
    """Return a datetime.date for a date keyword."""
    today = datetime.date.today()
    if keyword == "today":
        return today
    if keyword == "tomorrow":
        return today + datetime.timedelta(days=1)
    if keyword == "yesterday":
        return today - datetime.timedelta(days=1)
    raise ValueError(f"Unknown date keyword: {keyword}")


def _add_months(d, months):
    """Add months to a date, clamping day to valid range."""
    month = d.month - 1 + months
    year = d.year + month // 12
    month = month % 12 + 1
    max_day = calendar.monthrange(year, month)[1]
    return datetime.date(year, month, min(d.day, max_day))

# SI prefixes (case-sensitive: M=mega, m=milli)
SI_PREFIX = {
    "Q": Decimal("1e30"),  # quetta
    "R": Decimal("1e27"),  # ronna
    "Y": Decimal("1e24"),  # yotta
    "Z": Decimal("1e21"),  # zetta
    "E": Decimal("1e18"),  # exa
    "P": Decimal("1e15"),  # peta
    "T": Decimal("1e12"),  # tera
    "G": Decimal("1e9"),  # giga
    "M": Decimal("1e6"),  # mega
    "K": Decimal("1e3"),  # kilo (unofficial but common)
    "k": Decimal("1e3"),  # kilo
    "m": Decimal("1e-3"),  # milli
    "u": Decimal("1e-6"),  # micro (ASCII)
    "μ": Decimal("1e-6"),  # micro
    "n": Decimal("1e-9"),  # nano
    "p": Decimal("1e-12"),  # pico
    "f": Decimal("1e-15"),  # femto
    "a": Decimal("1e-18"),  # atto
    "z": Decimal("1e-21"),  # zepto
    "y": Decimal("1e-24"),  # yocto
}
SI_SUFFIX_RE = "[" + re.escape("".join(SI_PREFIX.keys())) + "]"

def _float_func(fn):
    """Wrap a math.* function: Decimal -> float -> compute -> Decimal."""
    def wrapper(x):
        return Decimal(str(fn(float(x))))
    return wrapper

BUILTIN_FUNCS_1 = {
    "sqrt": lambda x: x.sqrt() if isinstance(x, Decimal) else Decimal(str(math.sqrt(x))),
    "abs": abs,
    "floor": math.floor,
    "ceil": math.ceil,
    "log": _float_func(math.log),
    "log2": _float_func(math.log2),
    "log10": _float_func(math.log10),
    "sin": _float_func(math.sin),
    "cos": _float_func(math.cos),
    "tan": _float_func(math.tan),
    "asin": _float_func(math.asin),
    "acos": _float_func(math.acos),
    "atan": _float_func(math.atan),
    "exp": _float_func(math.exp),
}
BUILTIN_FUNCS_N = {
    "round": lambda args: round(args[0])
    if len(args) == 1
    else round(args[0], int(args[1])),
    "min": lambda args: min(args),
    "max": lambda args: max(args),
}
BUILTIN_FUNC_NAMES = set(BUILTIN_FUNCS_1) | set(BUILTIN_FUNCS_N)

BUILTIN_CONSTS = {
    "pi": Decimal(str(math.pi)),
    "e": Decimal(str(math.e)),
    "tau": Decimal(str(math.tau)),
}

# --- Unit conversion tables ---
UNIT_TABLE = {
    "length": {
        "_base": "meter",
        "mm": Decimal("0.001"),
        "millimeter": Decimal("0.001"),
        "millimeters": Decimal("0.001"),
        "cm": Decimal("0.01"),
        "centimeter": Decimal("0.01"),
        "centimeters": Decimal("0.01"),
        "m": 1,
        "meter": 1,
        "meters": 1,
        "km": 1000,
        "kilometer": 1000,
        "kilometers": 1000,
        "in": Decimal("0.0254"),
        "inch": Decimal("0.0254"),
        "inches": Decimal("0.0254"),
        "ft": Decimal("0.3048"),
        "foot": Decimal("0.3048"),
        "feet": Decimal("0.3048"),
        "yd": Decimal("0.9144"),
        "yard": Decimal("0.9144"),
        "yards": Decimal("0.9144"),
        "mi": Decimal("1609.344"),
        "mile": Decimal("1609.344"),
        "miles": Decimal("1609.344"),
    },
    "mass": {
        "_base": "gram",
        "mg": Decimal("0.001"),
        "milligram": Decimal("0.001"),
        "milligrams": Decimal("0.001"),
        "g": 1,
        "gram": 1,
        "grams": 1,
        "kg": 1000,
        "kilogram": 1000,
        "kilograms": 1000,
        "oz": Decimal("28.3495"),
        "ounce": Decimal("28.3495"),
        "ounces": Decimal("28.3495"),
        "lb": Decimal("453.592"),
        "lbs": Decimal("453.592"),
        "pound": Decimal("453.592"),
        "pounds": Decimal("453.592"),
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
        "mb": Decimal("1e6"),
        "megabyte": Decimal("1e6"),
        "megabytes": Decimal("1e6"),
        "gb": Decimal("1e9"),
        "gigabyte": Decimal("1e9"),
        "gigabytes": Decimal("1e9"),
        "tb": Decimal("1e12"),
        "terabyte": Decimal("1e12"),
        "terabytes": Decimal("1e12"),
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
        "ms": Decimal("0.001"),
        "millisecond": Decimal("0.001"),
        "milliseconds": Decimal("0.001"),
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
        "tsp": Decimal("4.929"),
        "teaspoon": Decimal("4.929"),
        "teaspoons": Decimal("4.929"),
        "tbsp": Decimal("14.787"),
        "tablespoon": Decimal("14.787"),
        "tablespoons": Decimal("14.787"),
        "floz": Decimal("29.574"),
        "cup": Decimal("236.588"),
        "cups": Decimal("236.588"),
        "pt": Decimal("473.176"),
        "pint": Decimal("473.176"),
        "pints": Decimal("473.176"),
        "qt": Decimal("946.353"),
        "quart": Decimal("946.353"),
        "quarts": Decimal("946.353"),
        "gal": Decimal("3785.41"),
        "gallon": Decimal("3785.41"),
        "gallons": Decimal("3785.41"),
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
        k = value + Decimal("273.15")
    elif from_key == "f":
        k = (value - Decimal("32")) * Decimal("5") / Decimal("9") + Decimal("273.15")
    else:
        k = value
    # From Kelvin
    if to_key == "c":
        return k - Decimal("273.15")
    elif to_key == "f":
        return (k - Decimal("273.15")) * Decimal("9") / Decimal("5") + Decimal("32")
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

        # ISO date: 2025-01-15 (must check before number parsing)
        if text[i].isdigit():
            dm = ISO_DATE_RE.match(text, i)
            if dm:
                try:
                    d = datetime.date.fromisoformat(dm.group())
                    tokens.append((DATE, d, start, dm.end()))
                    i = dm.end()
                    continue
                except ValueError:
                    pass  # fall through to number parsing

        # Hex/binary/octal: 0xFF, 0b1010, 0o77
        if text[i] == "0" and i + 1 < n and text[i + 1] in "xXbBoO":
            m = re.match(r"0[xX][0-9a-fA-F]+|0[bB][01]+|0[oO][0-7]+", text[i:])
            if m:
                val = Decimal(int(m.group(), 0))
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
                val = Decimal(raw + exp)
            else:
                val = Decimal(raw)
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
            if wl in DATE_KEYWORDS:
                tokens.append((DATE, _resolve_date_keyword(wl), start, end))
            elif wl == "of":
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
RED = "\033[31m"
GREEN = "\033[32m"
CYAN = "\033[36m"
RESET = "\033[0m"


def classify_line(text, variables, rates=None):
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
    if RATE_RE.match(stripped):
        return "directive"

    tokens = tokenize(text)
    all_names = set(BUILTIN_CONSTS) | set(variables or {})

    has_date = any(t[0] == DATE for t in tokens if t[0] != "EOF")
    # Also check for date variables
    if not has_date and variables:
        for t in tokens:
            if t[0] == "WORD" and isinstance((variables or {}).get(t[1].lower()), datetime.date):
                has_date = True
                break

    has_math = any(
        t[0] in ("NUM", "PCT", "FUNC", "TOTAL", DATE)
        or (t[0] == "WORD" and t[1].lower() in all_names)
        for t in tokens
        if t[0] != "EOF"
    )

    active = set()

    if has_date and has_math:
        # If it's a date expression, mark all non-EOF tokens as active
        date_result = _try_date_eval(tokens, variables or {})
        if date_result is not None:
            for idx, t in enumerate(tokens):
                if t[0] != "EOF":
                    active.add(idx)
        # else fall through to normal classification
    if has_math and not active:
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

            conversion, conv_start = _detect_conversion(tokens, rates=rates)
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


def colorize_expr(text, variables, rates=None):
    """Return text with dim escapes around ignored (non-math) words."""
    cls = classify_line(text, variables, rates=rates)
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


def colorize_line(line, result, fmt_result_str, align, variables, rates=None):
    """Return a colorized version of an output line."""
    stripped = line.strip()
    if result is not None:
        colored_expr = colorize_expr(stripped, variables, rates=rates)
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
    if DIRECTIVE_RE.match(stripped) or RATE_RE.match(stripped):
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
            exp = self.parse_power()
            try:
                return base**exp
            except InvalidOperation:
                return Decimal(str(float(base) ** float(exp)))
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


def _detect_conversion(tokens, rates=None):
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
            if rates:
                pair = (fr_name, to_name)
                rev = (to_name, fr_name)
                if pair in rates:
                    return ("rate", rates[pair], Decimal(1)), eof_idx - 3
                elif rev in rates:
                    return ("rate", Decimal(1), rates[rev]), eof_idx - 3
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
            if wl in all_vars and not isinstance(all_vars[wl], datetime.date):
                math_tokens.append(("NUM", all_vars[wl], t[2], t[3]))
                math_to_orig.append(idx)
        elif t[0] in ("EQ", DATE):
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
    except (ParseError, ZeroDivisionError, ValueError, OverflowError, InvalidOperation):
        return None, -1


def _try_date_eval(tokens, variables):
    """Try to evaluate a date expression. Returns (result, variables) or None.

    Patterns:
    1. days until/since DATE → number
    2. DATE ± N duration_unit → date
    3. DATE - DATE → number (days)
    """
    try:
        return _try_date_eval_inner(tokens, variables)
    except Exception:
        return None


def _try_date_eval_inner(tokens, variables):
    # Resolve date-holding variables: replace WORD tokens whose variable is a date
    resolved = []
    for t in tokens:
        if t[0] == "WORD":
            wl = t[1].lower()
            val = variables.get(wl)
            if isinstance(val, datetime.date):
                resolved.append((DATE, val, t[2], t[3]))
                continue
        resolved.append(t)

    # Check if there are any DATE tokens
    if not any(t[0] == DATE for t in resolved):
        return None

    # Strip assignment prefix
    var_name = None
    toks = resolved
    if len(toks) >= 3 and toks[0][0] == "WORD" and toks[1][0] == "EQ":
        var_name = toks[0][1].lower()
        toks = toks[2:]

    # Filter out EOF for pattern matching
    body = [t for t in toks if t[0] != "EOF"]
    if not body:
        return None

    # Strip outer parentheses
    while (
        len(body) >= 2
        and body[0][0] == "LPAREN"
        and body[-1][0] == "RPAREN"
    ):
        body = body[1:-1]
    if not body:
        return None

    def _finish(result):
        if var_name:
            return result, {**variables, var_name: result}
        return result, variables

    # Pattern 0: bare DATE (e.g., "today", "2025-01-15")
    if len(body) == 1 and body[0][0] == DATE:
        return _finish(body[0][1])

    # Pattern 1: "days/weeks until/since DATE"
    if (
        len(body) == 3
        and body[0][0] == "WORD"
        and body[0][1].lower() in ("days", "weeks")
        and body[1][0] == "WORD"
        and body[1][1].lower() in ("until", "since")
        and body[2][0] == DATE
    ):
        today = datetime.date.today()
        direction = body[1][1].lower()
        target = body[2][1]
        diff_days = (target - today).days if direction == "until" else (today - target).days
        if body[0][1].lower() == "weeks":
            return _finish(Decimal(diff_days) / Decimal(7))
        return _finish(Decimal(diff_days))

    # Pattern 2: DATE ± expr duration_unit
    if (
        len(body) >= 4
        and body[0][0] == DATE
        and body[1][0] == "ADDOP"
        and body[-1][0] == "WORD"
        and body[-1][1].lower() in DURATION_UNITS
    ):
        d = body[0][1]
        op = body[1][1]
        unit = body[-1][1].lower()
        # Build math tokens for the numeric part between op and unit
        math_toks = body[2:-1]
        if not math_toks:
            return None
        # Resolve variables in math tokens
        resolved_math = []
        all_vars = {**BUILTIN_CONSTS, **variables}
        for t in math_toks:
            if t[0] == "WORD":
                wl = t[1].lower()
                if wl in all_vars and not isinstance(all_vars[wl], datetime.date):
                    resolved_math.append(("NUM", all_vars[wl], t[2], t[3]))
                else:
                    return None  # can't resolve
            else:
                resolved_math.append(t)
        resolved_math.append(("EOF", None, 0, 0))
        n_val, _ = _try_parse(resolved_math)
        if n_val is None:
            return None
        n = int(n_val)
        if op == "-":
            n = -n
        if unit in ("day", "days"):
            result = d + datetime.timedelta(days=n)
        elif unit in ("week", "weeks"):
            result = d + datetime.timedelta(weeks=n)
        elif unit in ("month", "months"):
            result = _add_months(d, n)
        elif unit in ("year", "years"):
            result = _add_months(d, n * 12)
        else:
            return None
        return _finish(result)

    # Pattern 3: DATE - DATE → number of days
    if (
        len(body) == 3
        and body[0][0] == DATE
        and body[1][0] == "ADDOP"
        and body[1][1] == "-"
        and body[2][0] == DATE
    ):
        d1 = body[0][1]
        d2 = body[2][1]
        return _finish(Decimal((d1 - d2).days))

    return None


def evaluate_line(text, variables, rates=None):
    """Evaluate a line. Returns (result, variables) or (None, variables)."""
    tokens = tokenize(text)

    if any(t[0] == "TOTAL" for t in tokens):
        return "TOTAL", variables

    # Try date evaluation first
    date_result = _try_date_eval(tokens, variables)
    if date_result is not None:
        return date_result

    all_vars = {**BUILTIN_CONSTS, **variables}

    has_value = any(
        t[0] in ("NUM", "PCT", "FUNC", DATE)
        or (t[0] == "WORD" and t[1].lower() in all_vars)
        for t in tokens
    )
    if not has_value:
        return None, variables

    pos = 0
    var_name = None
    if len(tokens) >= 3 and tokens[0][0] == "WORD" and tokens[1][0] == "EQ":
        var_name = tokens[0][1].lower()
        pos = 2

    conversion, conv_start = _detect_conversion(tokens, rates=rates)
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
    if isinstance(n, datetime.date):
        return n.isoformat()
    if fmt_opts is None:
        fmt_opts = {"mode": "minSig", "precision": 10, "separator": "underscore"}
    n = float(n)  # Decimal→float for display (float's ~15 digits > max display precision)
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
            show_dec = max(-math.floor(math.log10(abs(n)) + 1) + prec, 0)
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


def process_file(filepath, show=False, no_color=False, stdin_content=None, dry_run=False):
    """Read, evaluate, and write back the file with results (or print to stdout)."""
    if stdin_content is not None:
        original = stdin_content
    else:
        with open(filepath, "r") as f:
            original = f.read()

    use_color = (
        show
        and not no_color
        and sys.stdout.isatty()
        and not os.environ.get("NO_COLOR", "")
        and os.environ.get("TERM") != "dumb"
    )

    lines = original.split("\n")
    # Remove trailing empty element from split (file ended with \n)
    if lines and lines[-1] == "":
        lines = lines[:-1]

    variables = {}
    rates = {}
    results_acc = []  # for total/sum accumulation
    fmt_opts = {"mode": "minSig", "precision": 10, "separator": "underscore"}
    evaluated = []  # list of (clean_line, result_or_none, fmt_opts_snapshot, vars_snapshot)

    for line in lines:
        clean = RESULT_RE.sub("", line).rstrip()
        stripped = clean.strip()

        # Check for rate directives
        rm = RATE_RE.match(stripped)
        if rm:
            fr = rm.group(1).lower()
            to = rm.group(2).lower()
            rates[(fr, to)] = Decimal(rm.group(3).strip())
            evaluated.append((clean, None, None, None))
            continue

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
                        fmt_opts["precision"] = 10 if mode == "minsig" else 3
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
        result, variables = evaluate_line(stripped, variables, rates=rates)

        if result == "TOTAL":
            total = sum(r for r in results_acc if r is not None and not isinstance(r, datetime.date))
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
                    colorize_line(clean, result, fmt_str, align, vsnap, rates=rates)
                )
        else:
            output.append(clean)
            if use_color:
                colored_output.append(colorize_line(clean, None, None, align, None, rates=rates))

    new_content = "\n".join(output) + "\n"
    if show:
        if use_color:
            sys.stdout.write("\n".join(colored_output) + "\n")
        else:
            sys.stdout.write(new_content)
        return new_content != original
    if dry_run:
        if new_content != original:
            diff = list(difflib.unified_diff(
                original.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=filepath,
                tofile=filepath,
            ))
            color_diff = (
                not no_color
                and sys.stdout.isatty()
                and not os.environ.get("NO_COLOR", "")
                and os.environ.get("TERM") != "dumb"
            )
            if color_diff:
                for line in diff:
                    if line.startswith("---") or line.startswith("+++"):
                        sys.stdout.write(BOLD + line + RESET)
                    elif line.startswith("@@"):
                        sys.stdout.write(CYAN + line + RESET)
                    elif line.startswith("-"):
                        sys.stdout.write(RED + line + RESET)
                    elif line.startswith("+"):
                        sys.stdout.write(GREEN + line + RESET)
                    else:
                        sys.stdout.write(line)
            else:
                sys.stdout.writelines(diff)
            return True
        return False
    if new_content != original:
        with open(filepath, "w") as f:
            f.write(new_content)
        return True
    return False


def process_json(content):
    """Evaluate content and return structured results as a list of dicts."""
    lines = content.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    variables = {}
    rates = {}
    results_acc = []
    fmt_opts = {"mode": "minSig", "precision": 10, "separator": "underscore"}
    output = []

    for line in lines:
        clean = RESULT_RE.sub("", line).rstrip()
        stripped = clean.strip()

        rm = RATE_RE.match(stripped)
        if rm:
            fr = rm.group(1).lower()
            to = rm.group(2).lower()
            rates[(fr, to)] = Decimal(rm.group(3).strip())
            output.append({"input": clean, "result": None})
            continue

        dm = DIRECTIVE_RE.match(stripped)
        if dm:
            key = dm.group(1).lower()
            val = dm.group(2).strip()
            if key == "format":
                fm = FORMAT_RE.match(val)
                if fm:
                    mode = fm.group(1).lower()
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
                        fmt_opts["precision"] = 10 if mode == "minsig" else 3
            elif key == "separator":
                v = val.lower()
                if v in ("off", "underscore", "comma", "space"):
                    fmt_opts["separator"] = v
            output.append({"input": clean, "result": None})
            continue

        if stripped.startswith("#"):
            results_acc.clear()
            output.append({"input": clean, "result": None})
            continue

        if not stripped:
            results_acc.append(None)
            output.append({"input": "", "result": None})
            continue

        result, variables = evaluate_line(stripped, variables, rates=rates)

        if result == "TOTAL":
            total = sum(r for r in results_acc if r is not None and not isinstance(r, datetime.date))
            results_acc.append(total)
            output.append({"input": clean, "result": float(total)})
        elif result is not None:
            results_acc.append(result)
            if isinstance(result, datetime.date):
                output.append({"input": clean, "result": result.isoformat()})
            else:
                output.append({"input": clean, "result": float(result)})
        else:
            results_acc.append(None)
            output.append({"input": clean, "result": None})

    return output


def watch_file(filepath, show=False, no_color=False, interval=0.5):
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
                    if process_file(filepath, show=show, no_color=no_color):
                        if not show:
                            print(f"  Updated results.")
                    last_mtime = os.path.getmtime(filepath)
            except FileNotFoundError:
                pass
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        sys.exit(130)


def _get_version():
    """Get version from package metadata or pyproject.toml fallback."""
    try:
        return importlib.metadata.version("calced")
    except importlib.metadata.PackageNotFoundError:
        toml_path = os.path.join(os.path.dirname(__file__), "pyproject.toml")
        with open(toml_path) as f:
            for line in f:
                if line.startswith("version"):
                    return line.split('"')[1]
        return "0"


def main():
    parser = argparse.ArgumentParser(
        prog="calced",
        description="A notepad calculator that evaluates expressions in text files. Updates the input file in-place with results.",
        epilog="examples:\n  calced expenses.txt        evaluate and update file in-place\n  calced -s expenses.txt     print results to stdout\n  calced -w expenses.txt     watch file and re-evaluate on changes\n\ndocs & issues: https://github.com/karlb/calced",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {_get_version()}")
    parser.add_argument("file", help="path to input file")
    parser.add_argument(
        "-w", "--watch", action="store_true", help="watch for changes and auto-update"
    )
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "-s",
        "--show",
        action="store_true",
        help="print result to stdout instead of updating the file",
    )
    output_group.add_argument(
        "-u",
        "--url",
        action="store_true",
        help="print URL for the web version of the file",
    )
    output_group.add_argument(
        "--json",
        action="store_true",
        help="output results as JSON",
    )
    output_group.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="show diff of what would change without updating the file",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="disable colored output",
    )
    args = parser.parse_args()

    if args.watch and (args.url or args.json or args.dry_run):
        parser.error("--watch cannot be used with --url, --json, or --dry-run")

    if args.file == "-":
        if args.json:
            content = sys.stdin.read()
            print(json.dumps(process_json(content), indent=2))
        else:
            content = sys.stdin.read()
            process_file(None, show=True, no_color=args.no_color, stdin_content=content)
        return

    if not os.path.exists(args.file):
        print(f"Error: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    if args.url:
        content = open(args.file).read()
        content = re.sub(r"\s{2,}# => .*$", "", content, flags=re.MULTILINE)
        compressed = zlib.compress(content.encode(), wbits=-15)
        encoded = base64.b64encode(compressed).decode()
        encoded = encoded.replace("+", "-").replace("/", "_").rstrip("=")
        major = _get_version().split(".")[0]
        print(f"https://calced.karl.berlin/{major}/#{encoded}")
        return

    if args.json:
        with open(args.file) as f:
            content = f.read()
        print(json.dumps(process_json(content), indent=2))
        return

    if args.dry_run:
        changed = process_file(args.file, dry_run=True)
        sys.exit(1 if changed else 0)

    if args.show and args.watch:
        sys.stderr.write("\033[2J\033[H")
        sys.stderr.flush()
    process_file(args.file, show=args.show, no_color=args.no_color)

    if args.watch:
        watch_file(args.file, show=args.show, no_color=args.no_color)


if __name__ == "__main__":
    main()
