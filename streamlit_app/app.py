# streamlit_app/app.py
import streamlit as st
from src.state import init_state
from src import api
from src.ui import sections_to_df_1based, render_sections_editor

st.set_page_config(page_title="AI Agent UI", layout="wide")
init_state()


st.title("AI Agent – One Window")
st.caption("Upload → Preview & Adjust & Chat → Run Final → History")


st.subheader(" Upload")
u1, u2, u3 = st.columns([2,1,1])
with u1:
    file = st.file_uploader("Chọn file .xlsx/.xls/.csv", type=["xlsx", "xls", "csv"])
with u2:
    st.text_input("User ID", key="user_id")
with u3:
    st.text_input("Sheet name (tùy chọn)", key="sheet_name")

c1, c2 = st.columns([1,1])
with c1:
    if st.button("Gửi file lên BE"):
        if not file:
            st.warning("Chưa chọn file.")
        else:
            res = api.upload_file(file, st.session_state.user_id, st.session_state.sheet_name or None)
            with st.expander("Resp /upload"):
                st.json(res)
            if isinstance(res, dict) and res.get("ok"):
                sid = res.get("data", {}).get("session_id") or ""
                if sid:
                    st.session_state.session_id = sid
                    st.session_state._preview_fetched = False
                    st.success(f"Upload OK. session_id = {sid}")
                else:
                    st.error("Upload OK nhưng không nhận được session_id.")
            else:
                st.error(f"{res.get('code')} – {res.get('error')}")

with c2:
    if st.button("Test /health"):
        st.json(api.health())

st.markdown("---")


st.subheader(" Preview +  Chat Adjust")

sid = (st.session_state.session_id or "").strip()
uid = (st.session_state.user_id or "").strip()
sheet = (st.session_state.sheet_name or "").strip() or None
st.caption(f"Session: **{sid or '∅'}** | User: **{uid or '∅'}** | Sheet: **{sheet or 'None'}**")

def _extract_sections_any_shape(obj):
    data = obj if isinstance(obj, dict) else {}
    for key in ("sections", "auto_sections", "confirmed_sections"):
        if isinstance(data.get(key), list):
            return data[key]
    for k in ("data", "preview", "analysis", "result"):
        d = data.get(k)
        if isinstance(d, dict):
            for key in ("sections", "auto_sections", "confirmed_sections"):
                if isinstance(d.get(key), list):
                    return d[key]
    return []

def _extract_used_rule_any_shape(obj):
    data = obj if isinstance(obj, dict) else {}
    if isinstance(data.get("used_rule"), (bool, int)):
        return bool(data["used_rule"])
    for k in ("data", "preview", "meta", "result"):
        d = data.get(k)
        if isinstance(d, dict) and isinstance(d.get("used_rule"), (bool, int)):
            return bool(d["used_rule"])
    return False

def fetch_preview():
    if not sid:
        st.warning("Chưa có session_id. Hãy upload file trước.")
        return
    r = api.preview(sid, uid, sheet)
    if isinstance(r, dict) and r.get("ok") is False and r.get("error"):
        st.error(f"{r.get('code')} – {r.get('error')}")
        return
    data = r.get("data", {}) if isinstance(r, dict) else {}
    sections = _extract_sections_any_shape(r) or _extract_sections_any_shape(data)
    st.session_state.used_rule = _extract_used_rule_any_shape(r) or _extract_used_rule_any_shape(data)
    if not sections:
        st.error("Preview OK nhưng không thấy sections.")
        with st.expander("Payload /preview"):
            st.json(r)
    else:
        st.session_state.sections = sections
        st.success(f"Preview OK. used_rule = {st.session_state.used_rule}")

p1, p2, p3 = st.columns([1,1,2])
with p1:
    if st.button("Tải lại Preview"):
        fetch_preview()
with p2:
    if not st.session_state.get("_preview_fetched", False) and sid:
        st.session_state._preview_fetched = True
        fetch_preview()

# layout 2 cột: trái (bảng + editor + confirm), phải (chat)
left, right = st.columns([2, 1])

with left:
    if st.session_state.sections:
        st.markdown("**Danh sách sections (1-based)**")
        st.dataframe(
            sections_to_df_1based(st.session_state.sections),
            use_container_width=True, hide_index=True
        )

        st.divider()
        st.markdown("**Chỉnh sửa sections (áp dụng cho session)**")
        edited = render_sections_editor(st.session_state.sections)

        a1, a2 = st.columns([1,1])
        with a1:
            if st.button("Áp dụng thay đổi (FE)"):
                st.session_state.sections = edited
                st.success("Đã cập nhật sections trong FE (chưa gửi BE).")
        with a2:
            if st.button("XÁC NHẬN SECTIONS (gửi BE)", type="primary"):
                # LẤY STATE NGAY LÚC BẤM (tránh rỗng do rerun)
                sid_now   = (st.session_state.get("session_id") or "").strip()
                uid_now   = (st.session_state.get("user_id") or "").strip()
                sheet_now = (st.session_state.get("sheet_name") or "").strip() or None

                if not sid_now:
                    st.error("session_id đang trống. Vui lòng Upload hoặc bấm 'Tải lại Preview'.")
                elif not isinstance(st.session_state.sections, list) or not st.session_state.sections:
                    st.error("Danh sách sections đang trống.")
                else:
                    r = api.confirm_sections(sid_now, st.session_state.sections, uid_now, sheet_now)
                    with st.expander("Resp /confirm_sections"):
                        st.json(r)

                    ok = False
                    if isinstance(r, dict) and (r.get("ok") is True or "message" in r or "data" in r):
                        ok = True
                    if ok:
                        st.session_state.confirmed = True
                        st.success("Đã xác nhận sections.")
                    else:
                        st.error(f"{r.get('code')} – {r.get('error')}")

    else:
        st.info("Chưa có sections. Bấm 'Tải lại Preview' sau khi Upload.")

with right:
    st.markdown("** Chat Adjust**")
    msg = st.text_area("Nhập yêu cầu (VD: 'Đổi header_row Section 1 thành 6')", height=160)
    if st.button("Gửi Chat"):
        if not sid:
            st.warning("Chưa có session_id. Upload trước đã.")
        elif not msg.strip():
            st.warning("Vui lòng nhập nội dung.")
        else:
            r = api.chat(sid, msg.strip(), sheet)
            with st.expander("Resp /chat"):
                st.json(r)
            # làm mới preview để thấy thay đổi tức thì
            fetch_preview()

st.markdown("---")


st.subheader(" Run Final")
rf1, rf2 = st.columns([1,1])
with rf1:
    if st.button("Run Final"):
        if not sid:
            st.warning("Chưa có session_id. Upload trước đã.")
        else:
            r = api.run_final(sid, uid, sheet)
            st.session_state.final_result = r

res = st.session_state.get("final_result") or {}
if isinstance(res, dict) and res:
    with st.expander("Payload /final"):
        st.json(res)

    # gom các file URL ở nhiều key
    def _collect_files(res_dict):
        cands = []
        data = res_dict.get("data") if isinstance(res_dict.get("data"), dict) else None
        for obj in [res_dict, data, (data or {}).get("result") if isinstance(data, dict) else None]:
            if not isinstance(obj, dict):
                continue
            for k in ("files", "file_urls", "outputs", "artifacts"):
                v = obj.get(k)
                if isinstance(v, list) and v:
                    cands = v
                    break
        out = []
        for f in cands:
            if isinstance(f, dict):
                name = f.get("name") or f.get("filename") or f.get("file") or f.get("title") or "file"
                url  = f.get("url") or f.get("href") or f.get("path")
            elif isinstance(f, str):
                name = f.rsplit("/", 1)[-1] or "file"
                url  = f
            else:
                continue
            if url:
                if url.startswith("/"):
                    url = api.BASE + url
                out.append({"name": name, "url": url})
        return out

    files = _collect_files(res)
    st.markdown("**Files:**")
    if files:
        for f in files:
            st.markdown(f"- [{f['name']}]({f['url']})")
    else:
        st.info("Không tìm thấy danh sách file trong payload.")

st.markdown("---")


st.subheader(" History")
h1, h2 = st.columns([1,1])
with h1:
    if st.button("Xem lịch sử chat"):
        st.json(api.get_history(uid or "default_user"))
with h2:
    if st.button("Xóa lịch sử chat"):
        st.json(api.delete_history(uid or "default_user"))
