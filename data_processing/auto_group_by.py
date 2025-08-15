import pandas as pd
from typing import Optional

def choose_group_by(df: pd.DataFrame) -> Optional[str]:
    n = len(df)
    if n == 0:
        return None
    best = None
    best_score = -1.0
    for col in df.columns:
        s = df[col]
        if s.isna().mean() > 0.5:
            continue
        ur = s.nunique(dropna=True) / max(1, n)  # unique ratio
        if ur < 0.02 or ur > 0.6:
            continue
        score = 1.0 - abs(ur - 0.25) - 0.2 * s.isna().mean()
        if score > best_score:
            best_score = score
            best = col
    return best or (df.columns[0] if len(df.columns) else None)
