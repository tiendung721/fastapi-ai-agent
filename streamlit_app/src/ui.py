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

def sections_editor_with_add_delete(df_1based: pd.DataFrame, key_prefix: str = "sec"):
    """
    Editor có checkbox 'Xóa?' + form 'Tạo section mới (1-based)'.
    Trả về (edited_zero_df, delete_indices, create_payload_zero_based)
    """
    st.markdown("**Danh sách sections (1-based)**")
    df_show = df_1based.copy()
    df_show["Xóa?"] = False

    edited = st.data_editor(
        df_show,
        num_rows="dynamic",
        use_container_width=True,
        key=f"{key_prefix}_editor",
        column_config={
            "Section": st.column_config.NumberColumn(disabled=True),
            "header_row": st.column_config.NumberColumn(min_value=1),
            "start_row": st.column_config.NumberColumn(min_value=1),
            "end_row": st.column_config.NumberColumn(min_value=1),
            "label": st.column_config.TextColumn(),
            "Xóa?": st.column_config.CheckboxColumn(),
        },
    )

    # Các dòng được tick để xóa
    del_rows = [i for i, v in enumerate(edited["Xóa?"].tolist()) if v]

    # Form tạo mới
    st.markdown("**Tạo section mới (1-based)**")
    c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
    with c1:
        new_start = st.number_input(
            "start_row",
            min_value=1,
            value=int(df_1based["start_row"].max() + 1) if not df_1based.empty else 1,
            key=f"{key_prefix}_ns",
        )
    with c2:
        new_end = st.number_input("end_row", min_value=new_start, value=new_start, key=f"{key_prefix}_ne")
    with c3:
        new_header = st.number_input(
            "header_row", min_value=new_start, max_value=new_end, value=new_start, key=f"{key_prefix}_nh"
        )
    with c4:
        new_label = st.text_input("label", value="", key=f"{key_prefix}_nl")

    create_payload = {
        "start_row": int(new_start - 1),
        "end_row": int(new_end - 1),
        "header_row": int(new_header - 1),
        "label": (new_label or "").strip(),
    }

    # Chuẩn hóa bảng đã sửa -> zero-based
    out = []
    for _, row in edited.iterrows():
        out.append({
            "header_row": int(row["header_row"]) - 1,
            "start_row": int(row["start_row"]) - 1,
            "end_row": int(row["end_row"]) - 1,
            "label": str(row["label"] or "").strip(),
        })
    edited_zero_df = pd.DataFrame(out)
    return edited_zero_df, del_rows, create_payload

