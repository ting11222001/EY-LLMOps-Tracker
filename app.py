import streamlit as st
import uuid
from database import init_db, save_run, get_runs_by_run_id, get_all_run_ids
from experiment import run_experiments

init_db()

st.set_page_config(page_title="LLMOps Experiment Tracker", layout="wide")

st.markdown("""
<style>
    .metric-box { background: #1e1e1e; border: 1px solid #2e2e2e; border-radius: 8px; padding: 14px 18px; margin-bottom: 8px; color: #f0f0f0; }
    .metric-label { font-size: 11px; color: #aaa; text-transform: uppercase; letter-spacing: 0.05em; }
    .metric-value { font-size: 26px; font-weight: 600; font-family: monospace; color: #f0f0f0; }
    .badge-best { background: #0f3d2e; color: #4ecca3; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
    .badge-ok   { background: #3d2e0f; color: #f5c842; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
    .badge-low  { background: #3d0f0f; color: #f57070; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500; }
    .response-box { background: #1e1e1e; border: 1px solid #2e2e2e; border-radius: 8px; padding: 16px; font-family: sans-serif; font-size: 15px; line-height: 1.7; white-space: pre-wrap; color: #f0f0f0; }
</style>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### LLMOps Tracker")
    st.markdown("---")

    clause = st.text_area(
        "Contract clause",
        height=180,
        placeholder="Paste a contract clause here...",
        value="This agreement limits liability to direct damages only, capped at the total contract value. The client waives all rights to claim consequential, indirect, or punitive damages regardless of the cause of action or the theory of liability, even if advised of the possibility of such damages."
    )

    task = st.selectbox("Task", [
        "Extract the top 3 risks",
        "Summarise key obligations",
        "Flag unusual or unfair terms",
    ])

    st.markdown("**Variants**")
    st.markdown("- conservative (temp 0.2)")
    st.markdown("- balanced (temp 0.7)")
    st.markdown("- creative (temp 1.0)")

    run_btn = st.button("Run experiments", use_container_width=True, type="primary")

    st.markdown("---")
    st.markdown("**Past runs**")
    past_runs = get_all_run_ids()
    past_run_options = {f"{r[2][:16]}  —  {r[1]}": r[0] for r in past_runs}
    selected_past = st.selectbox("Load a past run", options=["(none)"] + list(past_run_options.keys()))

# Main area
st.markdown("## Results")

active_run_id = None

if run_btn:
    if not clause.strip():
        st.error("Please paste a contract clause first.")
    else:
        with st.spinner("Running experiments..."):
            run_id = str(uuid.uuid4())[:8]
            results = run_experiments(clause, task, run_id)
            for r in results:
                save_run(
                    r["run_id"], r["variant_name"], r["temperature"],
                    r["task"], r["clause_text"], r["response"],
                    r["score"], r["score_reason"], r["latency_seconds"]
                )
            st.session_state["last_run_id"] = run_id

if "last_run_id" in st.session_state and not (selected_past and selected_past != "(none)"):
    active_run_id = st.session_state["last_run_id"]

if selected_past and selected_past != "(none)":
    active_run_id = past_run_options[selected_past]

if active_run_id:
    rows = get_runs_by_run_id(active_run_id)

    if rows:
        best_score = max(r["score"] for r in rows)
        avg_latency = round(sum(r["latency_seconds"] for r in rows) / len(rows), 1)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f'<div class="metric-box"><div class="metric-label">Total runs</div><div class="metric-value">{len(rows)}</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="metric-box"><div class="metric-label">Best score</div><div class="metric-value" style="color:#1d9e75">{best_score}</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="metric-box"><div class="metric-label">Avg latency</div><div class="metric-value">{avg_latency}s</div></div>', unsafe_allow_html=True)

        st.markdown("---")

        st.markdown("#### Score by variant")
        for r in rows:
            st.markdown(f"**{r['variant_name']}** (temp {r['temperature']})")
            st.progress(r["score"] / 100, text=f"{r['score']} / 100")
            if r.get("score_reason"):
                st.caption(f"Judge: {r['score_reason']}")

        st.markdown("---")

        st.markdown("#### Responses")
        sorted_scores = sorted([r["score"] for r in rows], reverse=True)
        for r in rows:
            score = r["score"]
            if score == sorted_scores[0]:
                badge = f'<span class="badge-best">best</span>'
            elif score == sorted_scores[-1]:
                badge = f'<span class="badge-low">low</span>'
            else:
                badge = f'<span class="badge-ok">ok</span>'

            with st.expander(f"{r['variant_name']} (temp {r['temperature']})  —  score: {score}"):
                st.markdown(badge, unsafe_allow_html=True)
                st.markdown(f'<div class="response-box">{r["response"]}</div>', unsafe_allow_html=True)
                st.caption(f"Latency: {r['latency_seconds']}s  |  Run ID: {r['run_id']}  |  {r['created_at']}")

else:
    st.info("Paste a clause and click 'Run experiments' to start.")