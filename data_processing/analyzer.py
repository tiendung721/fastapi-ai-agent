from __future__ import annotations
from typing import List, Dict, Any, Optional
import pandas as pd

from .auto_group_by import choose_group_by

# -----------------------------
# Utilities
# -----------------------------

def _normalize_region(df: pd.DataFrame, header_row: int, end_row: int) -> pd.DataFrame:
    """
    Convert a sheet-level dataframe into a region dataframe using 0-based indexes.
    - header_row: 0-based header row index in the sheet df
    - end_row   : 0-based inclusive end row index in the sheet df

    Returns:
      region df with columns set from the header row, and data rows with the header removed.
    """
    n = df.shape[0]
    if n == 0:
        return pd.DataFrame()

    # clamp to 0-based valid bounds
    header_row = max(0, min(header_row, n - 1))
    end_row = max(header_row, min(end_row, n - 1))

    # set columns from header row (0-based)
    header_values = df.iloc[header_row].astype(str).tolist()
    # slice inclusive of end_row → iloc uses [start:end), so +1
    region = df.iloc[header_row : end_row + 1].copy()

    # Disambiguate duplicated/empty column names
    cols: List[str] = []
    seen: Dict[str, int] = {}
    for c in header_values:
        k = c.strip() if isinstance(c, str) else str(c)
        if k == "" or k.lower() == "nan":
            k = "col"
        if k in seen:
            seen[k] += 1
            cols.append(f"{k}_{seen[k]}")
        else:
            seen[k] = 0
            cols.append(k)
    region.columns = cols

    # drop the header row from data
    if region.shape[0] > 0:
        region = region.iloc[1:].reset_index(drop=True)

    # Trim empty columns (all-nan)
    if region.shape[0] > 0:
        region = region.dropna(axis=1, how="all")

    return region


def _column_quality(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Return basic quality metrics per column."""
    out: Dict[str, Dict[str, Any]] = {}
    n = len(df)
    for col in df.columns:
        s = df[col]
        null_rate = float(s.isna().mean()) if n else 0.0
        nunique = int(s.nunique(dropna=True))
        sample = s.dropna().astype(str).head(5).tolist()
        coltype = str(s.dtype)
        out[col] = {
            "dtype": coltype,
            "null_rate": round(null_rate, 4),
            "nunique": nunique,
            "sample": sample,
        }
    return out


def _top_categories(df: pd.DataFrame, col: str, k: int = 10) -> Dict[str, int]:
    try:
        vc = (
            df[col]
            .dropna()
            .astype(str)
            .replace({"": None, "nan": None})
            .dropna()
            .value_counts()
            .head(k)
        )
        return {str(i): int(v) for i, v in vc.items()}
    except Exception:
        return {}


def _numeric_summary(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    """Summary for numeric columns."""
    out: Dict[str, Dict[str, float]] = {}
    num_df = df.select_dtypes(include=["number"])  # integers & floats
    for c in num_df.columns:
        s = num_df[c].dropna()
        if s.empty:
            continue
        out[c] = {
            "count": float(s.count()),
            "mean": float(s.mean()),
            "std": float(s.std(ddof=1)) if s.count() > 1 else 0.0,
            "min": float(s.min()),
            "q25": float(s.quantile(0.25)),
            "median": float(s.median()),
            "q75": float(s.quantile(0.75)),
            "max": float(s.max()),
        }
    return out


def _analyze_single_region(
    sheet_df: pd.DataFrame,
    section: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Analyze one region defined by a section (0-based indices, end_row inclusive).
    section = {start_row, end_row, header_row, label?}
    """
    params = params or {}
    sr = int(section["start_row"])
    er = int(section["end_row"])
    hr = int(section["header_row"])

    region = _normalize_region(sheet_df, header_row=hr, end_row=er)

    # choose group_by
    group_by = params.get("group_by")
    if not group_by or (region.shape[1] > 0 and group_by not in region.columns):
        group_by = choose_group_by(region)

    # aggregation: if group_by exists
    group_summary: Dict[str, int] = {}
    if group_by and group_by in region.columns:
        try:
            group_summary = (
                region.groupby(group_by, dropna=True)
                .size()
                .sort_values(ascending=False)
                .to_dict()
            )
            group_summary = {str(k): int(v) for k, v in group_summary.items()}
        except Exception:
            group_summary = {}

    # quality + numeric summary
    quality = _column_quality(region)
    numeric = _numeric_summary(region)

    quick_notes: List[str] = []
    if group_by:
        topk = _top_categories(region, group_by, k=5)
        if topk:
            head = ", ".join([f"{k}: {v}" for k, v in list(topk.items())[:3]])
            quick_notes.append(f"group_by='{group_by}' top: {head}")

    if len(numeric) > 0:
        ncols = list(numeric.keys())[:3]
        quick_notes.append(f"numeric cols: {', '.join(ncols)}")

    return {
        "label": section.get("label"),
        "header_row": hr,
        "start_row": sr,
        "end_row": er,
        "rows": int(region.shape[0]),
        "cols": int(region.shape[1]),
        "group_by": group_by,
        "group_summary": group_summary,
        "quality": quality,
        "numeric": numeric,
        "quick_notes": quick_notes,
    }


# -----------------------------
# Public entry
# -----------------------------

def run_analysis(
    sheet_df: pd.DataFrame,
    sections: List[Dict[str, Any]],
    params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run analysis for all sections on a single sheet dataframe.
    - Expects **0-based** validated sections (validate before calling).
    - Returns a machine-friendly dict.
    """
    results: List[Dict[str, Any]] = []

    for s in sections:
        try:
            res = _analyze_single_region(sheet_df, s, params=params)
        except Exception as e:
            # Fail-safe per region to avoid whole pipeline break
            res = {
                "label": s.get("label"),
                "error": str(e),
                "header_row": s.get("header_row"),
                "start_row": s.get("start_row"),
                "end_row": s.get("end_row"),
            }
        results.append(res)

    total_rows = int(sum(r.get("rows", 0) for r in results if isinstance(r.get("rows"), int)))

    return {
        "ok": True,
        "sections_count": len(results),
        "total_rows": total_rows,
        "sections": results,
    }
