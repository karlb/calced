"""Property-based tests for calced using Hypothesis.

Run with: make test-property
(Not discovered by unittest — requires pytest + hypothesis.)
"""

import datetime
import sys
import os

try:
    import pytest
    from hypothesis import given, assume, settings, example
    from hypothesis import strategies as st
except ImportError:
    # Skip entirely when discovered by unittest (which lacks these deps).
    import unittest
    raise unittest.SkipTest("requires pytest and hypothesis")

from decimal import Decimal, InvalidOperation
from itertools import combinations

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "python"))
from calced import (
    tokenize,
    evaluate_line,
    format_result,
    convert_temperature,
    SI_PREFIX,
    UNIT_TABLE,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

# Decimals that won't blow up arithmetic: avoid extreme exponents, NaN, Inf.
# Limit to 15 significant digits to stay well within Decimal28 context precision
# (the tokenizer round-trips through Decimal parsing which uses 28-digit context).
sane_decimals = st.decimals(
    allow_nan=False,
    allow_infinity=False,
    min_value=Decimal("-1e12"),
    max_value=Decimal("1e12"),
    places=10,
).filter(lambda d: d.is_finite())

# Decimals suitable for formatting (format_result converts to float internally)
format_decimals = st.decimals(
    allow_nan=False,
    allow_infinity=False,
    min_value=Decimal("-1e15"),
    max_value=Decimal("1e15"),
).filter(lambda d: d.is_finite() and abs(d.as_tuple().exponent) < 20)

# Non-zero decimals for division tests
nonzero_decimals = sane_decimals.filter(lambda d: d != 0)

fmt_modes = st.sampled_from(["minSig", "fixed", "scientific", "auto"])
fmt_separators = st.sampled_from(["underscore", "comma", "space", "off"])
fmt_precisions = st.integers(min_value=1, max_value=15)


def decimal_to_str(d):
    """Format a Decimal as a string the tokenizer can parse (no E notation)."""
    sign, digits, exp = d.as_tuple()
    if not digits:
        return "0"
    # Build a plain decimal string
    s = "-" if sign else ""
    num_digits = len(digits)
    dot_pos = num_digits + exp  # position of decimal point from left
    digit_str = "".join(str(d) for d in digits)
    if dot_pos <= 0:
        # e.g. 0.00123
        s += "0." + "0" * (-dot_pos) + digit_str
    elif dot_pos >= num_digits:
        # integer, possibly with trailing zeros
        s += digit_str + "0" * (dot_pos - num_digits)
    else:
        s += digit_str[:dot_pos] + "." + digit_str[dot_pos:]
    return s


# ---------------------------------------------------------------------------
# 1. Tokenizer robustness (fuzz)
# ---------------------------------------------------------------------------


@given(text=st.text(max_size=200))
@settings(max_examples=500)
def test_tokenize_never_crashes(text):
    """tokenize() should never raise on arbitrary input."""
    tokens = tokenize(text)
    assert isinstance(tokens, list)
    assert len(tokens) >= 1
    assert tokens[-1][0] == "EOF"


# ---------------------------------------------------------------------------
# 2. Arithmetic identities via evaluate_line
# ---------------------------------------------------------------------------


@given(a=sane_decimals)
@settings(max_examples=200)
def test_additive_identity(a):
    """a + 0 == a"""
    s = decimal_to_str(a)
    result, _ = evaluate_line(f"{s} + 0", {})
    assert result is not None
    assert result == a


@given(a=sane_decimals)
@settings(max_examples=200)
def test_multiplicative_identity(a):
    """a * 1 == a"""
    s = decimal_to_str(a)
    result, _ = evaluate_line(f"{s} * 1", {})
    assert result is not None
    assert result == a


@given(a=sane_decimals, b=sane_decimals)
@settings(max_examples=200)
def test_addition_commutativity(a, b):
    """a + b == b + a"""
    sa, sb = decimal_to_str(a), decimal_to_str(b)
    r1, _ = evaluate_line(f"{sa} + {sb}", {})
    r2, _ = evaluate_line(f"{sb} + {sa}", {})
    assert r1 == r2


@given(a=sane_decimals, b=sane_decimals)
@settings(max_examples=200)
def test_multiplication_commutativity(a, b):
    """a * b == b * a"""
    sa, sb = decimal_to_str(a), decimal_to_str(b)
    r1, _ = evaluate_line(f"{sa} * {sb}", {})
    r2, _ = evaluate_line(f"{sb} * {sa}", {})
    assert r1 == r2


@given(a=sane_decimals)
@settings(max_examples=200)
def test_self_subtraction(a):
    """a - a == 0"""
    s = decimal_to_str(a)
    result, _ = evaluate_line(f"{s} - {s}", {})
    assert result is not None
    assert result == 0


@given(a=nonzero_decimals)
@settings(max_examples=200)
def test_self_division(a):
    """a / a == 1 (for a != 0)"""
    s = decimal_to_str(a)
    result, _ = evaluate_line(f"{s} / {s}", {})
    assert result is not None
    assert result == 1


@given(a=sane_decimals)
@settings(max_examples=200)
def test_double_negation(a):
    """-(-a) == a"""
    s = decimal_to_str(a)
    # Wrap in parens to ensure correct parsing: -(-(value))
    result, _ = evaluate_line(f"-(-({s}))", {})
    assert result is not None
    assert result == a


# ---------------------------------------------------------------------------
# 3. Unit conversion roundtrips (non-temperature)
# ---------------------------------------------------------------------------

# Build list of (dimension, unit_a, factor_a, unit_b, factor_b) pairs
_unit_pairs = []
for dim_name, units in UNIT_TABLE.items():
    if dim_name == "temperature":
        continue
    short_names = [
        (name, factor)
        for name, factor in units.items()
        if not name.startswith("_") and len(name) <= 4  # use abbreviations only
    ]
    for (na, fa), (nb, fb) in combinations(short_names, 2):
        _unit_pairs.append((dim_name, na, fa, nb, fb))


@given(
    pair=st.sampled_from(_unit_pairs),
    value=st.decimals(
        allow_nan=False,
        allow_infinity=False,
        min_value=Decimal("1"),
        max_value=Decimal("1000"),
    ).filter(lambda d: d.is_finite() and abs(d.as_tuple().exponent) < 6),
)
@settings(max_examples=300)
def test_unit_conversion_roundtrip(pair, value):
    """Converting a→b→a should return approximately the original value."""
    dim, unit_a, factor_a, unit_b, factor_b = pair
    vs = decimal_to_str(value)

    # a → b
    r1, _ = evaluate_line(f"{vs} {unit_a} to {unit_b}", {})
    assume(r1 is not None)
    rs = decimal_to_str(r1)

    # b → a
    r2, _ = evaluate_line(f"{rs} {unit_b} to {unit_a}", {})
    assume(r2 is not None)

    # Allow small relative error from Decimal division
    diff = abs(r2 - value)
    assert diff < value * Decimal("1e-6") + Decimal("1e-6"), (
        f"{value} {unit_a}→{unit_b}→{unit_a} = {r2}, diff={diff}"
    )


# ---------------------------------------------------------------------------
# 4. Temperature conversion roundtrips
# ---------------------------------------------------------------------------

_temp_keys = ["c", "f", "k"]
_temp_unit_names = {"c": "celsius", "f": "fahrenheit", "k": "kelvin"}
_temp_pairs = [(a, b) for a in _temp_keys for b in _temp_keys if a != b]


@given(
    pair=st.sampled_from(_temp_pairs),
    value=st.decimals(
        allow_nan=False,
        allow_infinity=False,
        min_value=Decimal("-100"),
        max_value=Decimal("1000"),
    ).filter(lambda d: d.is_finite() and abs(d.as_tuple().exponent) < 6),
)
@settings(max_examples=200)
def test_temperature_roundtrip_function(pair, value):
    """convert_temperature(convert_temperature(v, a, b), b, a) ≈ v"""
    a, b = pair
    intermediate = convert_temperature(value, a, b)
    roundtrip = convert_temperature(intermediate, b, a)
    diff = abs(roundtrip - value)
    assert diff < Decimal("1e-6"), (
        f"{value} {a}→{b}→{a} = {roundtrip}, diff={diff}"
    )


@given(
    pair=st.sampled_from(_temp_pairs),
    value=st.decimals(
        allow_nan=False,
        allow_infinity=False,
        min_value=Decimal("-100"),
        max_value=Decimal("1000"),
    ).filter(lambda d: d.is_finite() and abs(d.as_tuple().exponent) < 4),
)
@settings(max_examples=200)
def test_temperature_roundtrip_evaluate(pair, value):
    """Temperature roundtrip through evaluate_line."""
    a, b = pair
    ua, ub = _temp_unit_names[a], _temp_unit_names[b]
    vs = decimal_to_str(value)

    r1, _ = evaluate_line(f"{vs} {ua} to {ub}", {})
    assume(r1 is not None)
    rs = decimal_to_str(r1)

    r2, _ = evaluate_line(f"{rs} {ub} to {ua}", {})
    assume(r2 is not None)

    diff = abs(r2 - value)
    assert diff < Decimal("0.01"), (
        f"{value} {ua}→{ub}→{ua} = {r2}, diff={diff}"
    )


# ---------------------------------------------------------------------------
# 5. evaluate_line robustness (fuzz)
# ---------------------------------------------------------------------------


@given(text=st.text(max_size=200))
@settings(max_examples=500)
def test_evaluate_line_never_crashes(text):
    """evaluate_line() should never raise on arbitrary input."""
    result, variables = evaluate_line(text, {})
    assert isinstance(variables, dict)
    assert result is None or isinstance(result, (Decimal, str, datetime.date))


# ---------------------------------------------------------------------------
# 6. Evaluation idempotency
# ---------------------------------------------------------------------------

# Strategy: generate simple arithmetic expressions from a grammar
_operands = st.sampled_from(["1", "2", "3", "7", "10", "0.5", "100"])
_binops = st.sampled_from([" + ", " - ", " * ", " / "])


@st.composite
def simple_expressions(draw):
    """Generate simple arithmetic expressions."""
    n_terms = draw(st.integers(min_value=1, max_value=4))
    expr = draw(_operands)
    for _ in range(n_terms - 1):
        op = draw(_binops)
        operand = draw(_operands)
        # Avoid division by zero
        if op == " / " and operand == "0":
            operand = "1"
        expr += op + operand
    return expr


@given(expr=simple_expressions())
@settings(max_examples=300)
def test_evaluation_idempotent(expr):
    """Evaluating the same expression twice gives the same result."""
    r1, _ = evaluate_line(expr, {})
    r2, _ = evaluate_line(expr, {})
    assert r1 == r2


# ---------------------------------------------------------------------------
# 7. format_result robustness
# ---------------------------------------------------------------------------


@given(
    n=format_decimals,
    mode=fmt_modes,
    precision=fmt_precisions,
    separator=fmt_separators,
)
@settings(max_examples=500)
def test_format_result_never_crashes(n, mode, precision, separator):
    """format_result() should never raise for valid inputs."""
    fmt_opts = {"mode": mode, "precision": precision, "separator": separator}
    result = format_result(n, fmt_opts)
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# 8. SI prefix values (parametrized)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("prefix,expected_multiplier", list(SI_PREFIX.items()))
def test_si_prefix_tokenizes_correctly(prefix, expected_multiplier):
    """1{prefix} should tokenize to a NUM token equal to expected_multiplier."""
    tokens = tokenize(f"1{prefix}")
    num_tokens = [t for t in tokens if t[0] == "NUM"]
    assert len(num_tokens) == 1, f"Expected 1 NUM token for '1{prefix}', got {num_tokens}"
    assert num_tokens[0][1] == expected_multiplier, (
        f"1{prefix}: expected {expected_multiplier}, got {num_tokens[0][1]}"
    )
