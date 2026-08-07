"""Calculator MCP server.

Pure-function arithmetic, algebra and unit-conversion helpers. No filesystem,
no network – safe to expose to any agent. Designed so that the LLM has ONE
well-described tool per common operation rather than a single ``eval`` that
hides its capabilities.

Run as a stdio MCP server::

    python3 -m mcp_servers.calculator_server
"""

from __future__ import annotations

import ast
import math
import operator
from typing import Dict

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("calculator")

# Safe AST node handlers – we deliberately do NOT expose Python's ``eval``.
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
        return _BIN_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        name = node.func.id
        fn = getattr(math, name, None)
        if callable(fn) and name in {"sqrt", "log", "log10", "log2", "sin",
                                     "cos", "tan", "exp", "floor", "ceil",
                                     "radians", "degrees", "fabs"}:
            return float(fn(*(_eval(a) for a in node.args)))
    raise ValueError(f"Unsupported expression node: {ast.dump(node)}")


@mcp.tool()
def evaluate(expression: str) -> float:
    """Evaluate an arithmetic / math expression and return the numeric result.

    Supports ``+ - * / // % **`` and the functions ``sqrt, log, log10, log2,
    sin, cos, tan, exp, floor, ceil, radians, degrees, fabs``. Constants pi
    and e are available as ``pi`` and ``e``.

    Examples:
        evaluate("2 + 3 * 4")               -> 14
        evaluate("sqrt(144) + log10(1000)") -> 17
        evaluate("(10 ** 2) / 4")           -> 25

    Args:
        expression: A single arithmetic expression as a string.

    Returns:
        The numeric result as a float.
    """
    tree = ast.parse(expression.replace("pi", "math.pi").replace(" e ", " math.e ").replace("(e)", "(math.e)"), mode="eval")
    # The replace() is a tiny convenience; _eval itself only allows allow-listed nodes.
    return float(_eval(tree.body))


@mcp.tool()
def statistics(numbers: list) -> Dict[str, float]:
    """Compute mean, median, min, max and population stddev for a list of
    numbers.

    Use this when the user asks "what's the average of …", "summarise these
    numbers", or needs aggregate stats. For a single arithmetic expression,
    prefer ``evaluate``.

    Args:
        numbers: A JSON list of numbers, e.g. ``[1, 2, 3, 4, 5]``.

    Returns:
        Dict with keys: ``count``, ``sum``, ``mean``, ``median``, ``min``,
        ``max``, ``stdev``.
    """
    nums = [float(n) for n in numbers]
    if not nums:
        raise ValueError("Cannot compute statistics on an empty list")
    n = len(nums)
    mean = sum(nums) / n
    sorted_nums = sorted(nums)
    median = (sorted_nums[n // 2] if n % 2 == 1
              else (sorted_nums[n // 2 - 1] + sorted_nums[n // 2]) / 2)
    var = sum((x - mean) ** 2 for x in nums) / n
    return {
        "count": n,
        "sum": sum(nums),
        "mean": mean,
        "median": median,
        "min": min(nums),
        "max": max(nums),
        "stdev": math.sqrt(var),
    }


@mcp.tool()
def convert_units(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a value between common units of the same dimension.

    Supported dimensions: length (m, km, mi, ft, in, cm), mass (g, kg, lb,
    oz), temperature (C, F, K), volume (l, ml, gal, qt).

    Examples:
        convert_units(100, "km", "mi")   -> 62.137
        convert_units(32, "F", "C")      -> 0.0
        convert_units(1, "gal", "l")     -> 3.7854

    Args:
        value: Numeric value to convert.
        from_unit: Source unit symbol (case-sensitive for temperature).
        to_unit: Target unit symbol (case-sensitive for temperature).

    Returns:
        The converted value as a float.
    """
    # Normalise non-temperature symbols to lowercase.
    f = from_unit
    t = to_unit
    if {f, t} <= {"C", "F", "K"}:
        # Temperature – convert through Celsius.
        if f == "C":
            c = value
        elif f == "F":
            c = (value - 32) * 5 / 9
        elif f == "K":
            c = value - 273.15
        else:
            raise ValueError(f"Unknown temperature unit: {f}")
        if t == "C":
            return c
        if t == "F":
            return c * 9 / 5 + 32
        if t == "K":
            return c + 273.15
        raise ValueError(f"Unknown temperature unit: {t}")

    # Length / mass / volume – convert through a base unit.
    table = {
        # length (base: metre)
        "m": 1.0, "km": 1000.0, "cm": 0.01, "mi": 1609.344,
        "ft": 0.3048, "in": 0.0254,
        # mass (base: gram)
        "g": 1.0, "kg": 1000.0, "lb": 453.592, "oz": 28.3495,
        # volume (base: litre)
        "l": 1.0, "ml": 0.001, "gal": 3.78541, "qt": 0.946353,
    }
    f = f.lower()
    t = t.lower()
    if f not in table or t not in table:
        raise ValueError(f"Unsupported units: {from_unit} -> {to_unit}")
    return value * table[f] / table[t]


@mcp.tool()
def percentage(part: float, whole: float) -> float:
    """Return what percentage ``part`` is of ``whole`` (i.e. part/whole*100).

    Use this when the user asks "what percent of X is Y" or "what percentage
    of the budget is left". For arbitrary arithmetic, use ``evaluate``.

    Args:
        part: The numerator.
        whole: The denominator.

    Returns:
        Percentage value as a float (e.g. 25.0 for 25%).
    """
    if whole == 0:
        raise ValueError("whole must not be zero")
    return part / whole * 100.0


if __name__ == "__main__":
    mcp.run(transport="stdio")
