import streamlit as st
import requests
import json

API_BASE = "http://localhost:8000"


def _to_vega_lite(spec: dict) -> dict:
    if not spec:
        return spec
    if "mark" in spec or "layer" in spec:
        return spec
    x_field = spec.get("x") or spec.get("x_axis", "")
    y_field = spec.get("y") or spec.get("y_axis", "")
    type_map = {"bar": "bar", "line": "line", "scatter": "point"}
    mark_type = type_map.get(spec.get("type", "bar"), "bar")
    chart = {
        "mark": {"type": mark_type},
        "encoding": {
            "x": {"field": x_field, "type": "nominal"},
            "y": {"field": y_field, "type": "quantitative"},
        },
        "title": spec.get("title", ""),
    }
    if spec.get("data"):
        chart["data"] = {"values": spec["data"]}
    return chart


st.set_page_config(page_title="AI Data Analyst", layout="wide")
st.title("AI Data Analyst Agent")

if "session_id" not in st.session_state:
    st.session_state.session_id = None

with st.sidebar:
    st.header("1. Upload Data")
    uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])
    if uploaded_file and st.button("Upload CSV"):
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "text/csv")}
        resp = requests.post(f"{API_BASE}/upload", files=files)
        if resp.ok:
            data = resp.json()
            st.session_state.session_id = data["session_id"]
            st.success(f"Session: {data['session_id']}")
            st.info(f"{data['row_count']} rows x {data['column_count']} columns")
            st.write("Columns:", data["column_names"])
        else:
            st.error(f"Upload failed: {resp.text}")

    if st.session_state.session_id:
        st.header("Session")
        st.code(st.session_state.session_id)
        if st.button("Delete Session"):
            requests.delete(f"{API_BASE}/sessions/{st.session_state.session_id}")
            st.session_state.session_id = None
            st.rerun()

st.header("2. Ask a Question")
query = st.text_area(
    "What would you like to know about your data?",
    placeholder="e.g. Show me total sales by category",
    disabled=not st.session_state.session_id,
)

if st.button("Analyze", disabled=not st.session_state.session_id or not query.strip()):
    with st.spinner("Running analysis..."):
        resp = requests.post(
            f"{API_BASE}/analyze",
            json={"session_id": st.session_state.session_id, "query": query},
        )
    if not resp.ok:
        st.error(f"Analysis failed: {resp.text}")
        st.stop()

    result = resp.json()
    st.header("3. Results")

    col1, col2, col3 = st.columns(3)
    col1.metric("Complete", "Yes" if result.get("complete") else "No")
    col2.metric("Iterations", result.get("iterations", 0))
    col3.metric("Insights", len(result.get("insights", [])))

    if result.get("error"):
        st.error(result["error"])

    if result.get("insights"):
        st.subheader("Insights")
        for ins in result["insights"]:
            st.markdown(f"- {ins}")

    if result.get("chart_spec"):
        st.subheader("Chart")
        try:
            spec = _to_vega_lite(result["chart_spec"])
            st.vega_lite_chart(spec, use_container_width=True)
        except Exception as e:
            st.warning(f"Could not render chart: {e}")

    if result.get("tool_results"):
        st.subheader("Tool Execution Trace")
        for i, tr in enumerate(result["tool_results"]):
            with st.expander(f"Step {i+1}: {tr['tool']} ({tr.get('analysis', '')[:80]})"):
                st.write("**Params:**", tr.get("params", {}))
                resp_data = tr.get("response", {})
                st.write("**Success:**", resp_data.get("success"))
                if resp_data.get("data"):
                    st.json(resp_data["data"])
                if resp_data.get("error"):
                    st.error(resp_data["error"])
                st.caption(f"Time: {resp_data.get('metadata', {}).get('execution_time_ms', '?')}ms")
