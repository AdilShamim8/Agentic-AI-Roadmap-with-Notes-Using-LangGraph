"""Heuristic table detector.

Two strategies, tried in order:

1. **Line-grid detection** (default). ReportLab and most PDF generators
   draw tables as a set of horizontal and vertical line segments rather
   than full rectangles. We collect all line segments on the page, group
   them into rows (shared y) and columns (shared x), and the resulting
   grid defines the cells. We then read the text inside each cell.

2. **Rectangle detection** (fallback). Some PDFs do draw explicit
   rectangles; we collect those and treat their intersections as cells.

Both strategies produce the same output: a list of 2-D string grids.
This is intentionally lightweight (no ML). For messy scanned PDFs, swap
in `unstructured` or LlamaParse — the rest of the pipeline is
unaffected.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class _Line:
    """A horizontal or vertical line segment."""
    orientation: str  # 'h' or 'v'
    a: float  # constant coordinate (y for h, x for v)
    b0: float  # span start
    b1: float  # span end


@dataclass
class _Rect:
    x0: float
    y0: float
    x1: float
    y1: float


# ----------------------------------------------------------------------
# Strategy 1: line grid
# ----------------------------------------------------------------------
def _gather_lines(page) -> list[_Line]:
    """Extract horizontal and vertical line segments from page drawings."""
    out: list[_Line] = []
    for d in page.get_drawings():
        for item in d.get("items", []):
            kind = item[0]
            if kind == "l":  # line
                p1, p2 = item[1], item[2]
                x0, y0 = float(p1.x), float(p1.y)
                x1, y1 = float(p2.x), float(p2.y)
                if abs(y0 - y1) < 0.5 and x0 != x1:  # horizontal
                    out.append(_Line("h", (y0 + y1) / 2.0, min(x0, x1), max(x0, x1)))
                elif abs(x0 - x1) < 0.5 and y0 != y1:  # vertical
                    out.append(_Line("v", (x0 + x1) / 2.0, min(y0, y1), max(y0, y1)))
            elif kind == "re":  # rectangle — split into 4 lines
                r = item[1]
                x0, y0, x1, y1 = float(r.x0), float(r.y0), float(r.x1), float(r.y1)
                out.append(_Line("h", y0, x0, x1))
                out.append(_Line("h", y1, x0, x1))
                out.append(_Line("v", x0, y0, y1))
                out.append(_Line("v", x1, y0, y1))
    return out


def _cluster(values: list[float], tol: float = 3.0) -> list[float]:
    if not values:
        return []
    values = sorted(values)
    clusters = [values[0]]
    for v in values[1:]:
        if abs(v - clusters[-1]) > tol:
            clusters.append(v)
    return clusters


def _find_grids(lines: list[_Line]) -> list[tuple[list[float], list[float]]]:
    """Find one or more (x_coords, y_coords) grids in the line set.

    A grid is a maximal set of vertical lines that all share a common
    horizontal span, plus the horizontal lines that span the same x-range.
    """
    if not lines:
        return []

    h_lines = [l for l in lines if l.orientation == "h"]
    v_lines = [l for l in lines if l.orientation == "v"]

    if not h_lines or not v_lines:
        return []

    # Cluster by constant coordinate first.
    h_ys = _cluster([l.a for l in h_lines])
    v_xs = _cluster([l.a for l in v_lines])

    if len(h_ys) < 2 or len(v_xs) < 2:
        return []

    # Check that the lines actually span the grid (i.e. the horizontal
    # lines stretch across the vertical columns and vice versa). We
    # approximate by checking the union of spans.
    h_span = (min(l.b0 for l in h_lines), max(l.b1 for l in h_lines))
    v_span = (min(l.b0 for l in v_lines), max(l.b1 for l in v_lines))

    # The grid's x range is the v-lines' x positions, the grid's y range
    # is the h-lines' y positions. The h-lines should span the x range
    # and the v-lines should span the y range.
    x_min, x_max = v_xs[0], v_xs[-1]
    y_min, y_max = h_ys[0], h_ys[-1]

    # Filter h-lines that actually cover the grid horizontally.
    good_h = [a for a in h_ys if any(
        abs(l.a - a) < 3.0 and l.b0 <= x_min + 6.0 and l.b1 >= x_max - 6.0
        for l in h_lines
    )]
    good_v = [a for a in v_xs if any(
        abs(l.a - a) < 3.0 and l.b0 <= y_min + 6.0 and l.b1 >= y_max - 6.0
        for l in v_lines
    )]

    if len(good_h) < 2 or len(good_v) < 2:
        # Fall back to the simpler clustered view.
        return [(v_xs, h_ys)]

    return [(good_v, good_h)]


def _read_cells(page, x_coords: list[float], y_coords: list[float]) -> list[list[str]]:
    table: list[list[str]] = []
    for ry in range(len(y_coords) - 1):
        row: list[str] = []
        for rx in range(len(x_coords) - 1):
            clip = (x_coords[rx], y_coords[ry], x_coords[rx + 1], y_coords[ry + 1])
            words = page.get_text("words", clip=clip)
            text = " ".join(w[4] for w in words).strip()
            row.append(text)
        table.append(row)
    return table


# ----------------------------------------------------------------------
# Strategy 2: rectangle union (kept for backwards compat with old code)
# ----------------------------------------------------------------------
def _gather_rects(page) -> list[_Rect]:
    rects: list[_Rect] = []
    for d in page.get_drawings():
        for item in d.get("items", []):
            if item[0] == "re":
                r = item[1]
                rects.append(_Rect(r.x0, r.y0, r.x1, r.y1))
    return rects


def _rectangles_to_grid(page, rects: list[_Rect]) -> list[list[str]] | None:
    if not rects:
        return None
    x_lines = _cluster([r.x0 for r in rects] + [r.x1 for r in rects])
    y_lines = _cluster([r.y0 for r in rects] + [r.y1 for r in rects])
    if len(x_lines) < 3 or len(y_lines) < 3:
        return None
    return _read_cells(page, x_lines, y_lines)


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
def detect_tables(page) -> list[list[list[str]]]:
    """Detect tables on a PyMuPDF page and return them as 2-D string grids."""
    # Strategy 1: line grid (works for ReportLab and most generators).
    lines = _gather_lines(page)
    grids = _find_grids(lines)
    out: list[list[list[str]]] = []
    for x_coords, y_coords in grids:
        table = _read_cells(page, x_coords, y_coords)
        # Only keep the grid if it has at least one non-empty cell.
        if any(any(c for c in row) for row in table):
            out.append(table)

    # Strategy 2: rectangle-based (used only if strategy 1 found nothing).
    if not out:
        rects = _gather_rects(page)
        grid = _rectangles_to_grid(page, rects)
        if grid is not None and any(any(c for c in row) for row in grid):
            out.append(grid)

    return out
