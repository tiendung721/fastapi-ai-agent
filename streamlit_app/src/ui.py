# streamlit_app/src/ui.py
import streamlit as st
import pandas as pd
from typing import List, Dict, Any

def sections_to_df_1based(sections: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for i, s in enumerate(sections, 1):
        rows.append({
            "Section": i,
            "header_row": int(s.get("header_row", 0)) + 1,
            "start_row": int(s.get("start_row", 0)) + 1,
            "end_row":   int(s.get("end_row", 0)) + 1,
            "label":     s.get("label", ""),
        })
    return pd.DataFrame(rows)

def render_sections_editor(sections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    df = sections_to_df_1based(sections)
    edited_df = st.data_editor(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Section": st.column_config.NumberColumn(disabled=True),
            "header_row": st.column_config.NumberColumn(min_value=1),
            "start_row": st.column_config.NumberColumn(min_value=1),
            "end_row": st.column_config.NumberColumn(min_value=1),
            "label": st.column_config.TextColumn(),
        }
    )
    # Trả về lại list dict (giữ 1-based; BE sẽ tự convert về 0-based)
    out: List[Dict[str, Any]] = []
    for _, row in edited_df.iterrows():
        out.append({
            "header_row": int(row["header_row"]) - 1,
            "start_row":  int(row["start_row"]) - 1,
            "end_row":    int(row["end_row"]) - 1,
            "label":      str(row["label"] or "").strip(),
        })
    return out
