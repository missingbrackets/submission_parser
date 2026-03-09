# ============================================================
#  ui/components/gap_analysis.py
#  Streamlit rendering of the gap analysis block.
# ============================================================

import streamlit as st


def render_gap_analysis(gap: dict) -> None:
    """Render the gap analysis score, counts, and missing field lists."""
    score       = gap["data_quality_score"]
    score_color = "#22C55E" if score >= 75 else "#F59E0B" if score >= 50 else "#EF4444"
    score_label = "GOOD" if score >= 75 else "MODERATE" if score >= 50 else "POOR"

    col_score, col_crit, col_adv, col_ok = st.columns(4)

    with col_score:
        st.markdown(f"""
        <div style="text-align:center; padding:12px; background:#111827; border-radius:6px; border:1px solid #1E2D45;">
          <div style="font-size:0.7rem; color:#6B7B99; text-transform:uppercase; letter-spacing:0.1em;">Data Quality</div>
          <div style="font-size:2rem; font-weight:700; color:{score_color};">{score}</div>
          <div style="font-size:0.75rem; color:{score_color};">{score_label}</div>
        </div>""", unsafe_allow_html=True)
    with col_crit:
        st.metric("Critical Gaps", gap["critical_count"],
                  delta="blocking" if gap["critical_count"] else "none", delta_color="inverse")
    with col_adv:
        st.metric("Advisory Gaps", gap["advisory_count"], delta="review", delta_color="off")
    with col_ok:
        st.metric("Fields Present", f"{gap['present_count']}/{gap['total_fields']}")

    gcol1, gcol2 = st.columns(2)
    with gcol1:
        if gap["critical_gaps"]:
            st.markdown("**🔴 Critical Missing Fields**")
            for _, label in gap["critical_gaps"]:
                st.markdown(f'<div class="gap-critical">✗ {label}</div>', unsafe_allow_html=True)
        else:
            st.markdown("**✅ No critical gaps**")
    with gcol2:
        if gap["advisory_gaps"]:
            st.markdown("**🟡 Advisory Missing Fields**")
            for _, label in gap["advisory_gaps"]:
                st.markdown(f'<div class="gap-advisory">⚑ {label}</div>', unsafe_allow_html=True)
        else:
            st.markdown("**✅ No advisory gaps**")
