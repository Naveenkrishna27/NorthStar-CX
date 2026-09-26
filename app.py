"""
NorthStar CX - Streamlit Dashboard (v4 - Snowflake-branded)

Deep navy + cyan visual identity (Snowflake's own palette), structured as
a disciplined evidence record rather than a generic SaaS card grid.

Run: streamlit run app.py
"""

import streamlit as st

from skills.customer_360 import get_connection, fetch_customer_data, build_prompt, call_cortex_complete
from skills.churn_risk import churn_risk_score
from skills.audit_trail import build_audit_record
from skills.next_best_action import next_best_action

st.set_page_config(
    page_title="NorthStar CX",
    page_icon="❄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------
# Design tokens
# Deep navy + Snowflake cyan, cool paper content area. Space
# Grotesk for display/brand type (geometric, technical feel),
# IBM Plex Sans for body, IBM Plex Mono for data/IDs/figures.
# Hairline rules over drop-shadow cards; cyan reserved for the
# hero moment (recommended action) and structural accents.
# ---------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    :root {
        --navy: #0B2A3D;
        --navy-deep: #071C2B;
        --cyan: #29B5E8;
        --cyan-deep: #1897C9;
        --paper: #F1F6F9;
        --ink: #0E2233;
        --body-text: #2C4657;
        --muted: #6E8493;
        --line: #D3E3EA;
        --risk-high: #C0392B;
        --risk-medium: #B8860B;
        --risk-low: #1E8F6F;
    }

    .stApp { background-color: var(--paper); }

    section[data-testid="stSidebar"] {
        background: var(--navy);
        border-right: 1px solid var(--navy-deep);
    }
    section[data-testid="stSidebar"] * { color: #CFE3EC !important; }
    section[data-testid="stSidebar"] .ns-side-label {
        color: var(--cyan) !important;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.2px;
    }

    html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; color: var(--body-text); }
    .ns-mono { font-family: 'IBM Plex Mono', monospace; }

    .ns-masthead {
        background: var(--navy);
        margin: -1rem -1rem 1.8rem -1rem;
        padding: 1.5rem 2.2rem 1.3rem 2.2rem;
        border-bottom: 3px solid var(--cyan);
    }
    .ns-masthead .brand {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 1.55rem;
        color: #FFFFFF;
        letter-spacing: -0.2px;
    }
    .ns-masthead .brand span { color: var(--cyan); }
    .ns-masthead .tagline {
        color: #9FC3D4;
        font-size: 0.9rem;
        margin-top: 0.2rem;
    }

    .ns-record-header {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 1.9rem;
        color: var(--ink);
        margin-bottom: 0.15rem;
    }
    .ns-record-meta { color: var(--muted); font-size: 0.95rem; margin-bottom: 1.1rem; }

    .ns-metrics {
        display: flex;
        border-top: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
        padding: 0.9rem 0;
        margin-bottom: 1.6rem;
    }
    .ns-metric { flex: 1; padding: 0 1.4rem; border-left: 1px solid var(--line); }
    .ns-metric:first-child { border-left: none; padding-left: 0; }
    .ns-metric-label { color: var(--muted); font-size: 0.78rem; font-weight: 500; margin-bottom: 0.15rem; }
    .ns-metric-value { font-family: 'IBM Plex Mono', monospace; font-size: 1.5rem; font-weight: 500; color: var(--ink); }

    .ns-section-label {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--navy);
        margin-bottom: 0.5rem;
        padding-bottom: 0.3rem;
        border-bottom: 2px solid var(--cyan);
        display: inline-block;
    }
    .ns-body-text { line-height: 1.65; font-size: 0.98rem; color: var(--body-text); max-width: 72ch; }

    .ns-risk-row { display: flex; align-items: baseline; gap: 0.8rem; margin-bottom: 0.6rem; }
    .ns-risk-square { display: inline-block; width: 13px; height: 13px; border-radius: 2px; margin-right: 0.4rem; }
    .ns-risk-score { font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 2.4rem; color: var(--navy); line-height: 1; }
    .ns-risk-level { font-weight: 600; font-size: 1.05rem; }
    .ns-risk-of100 { color: var(--muted); font-size: 0.95rem; }

    .ns-action-box {
        border-left: 4px solid var(--cyan);
        background: #E4F4FA;
        padding: 1.1rem 1.4rem;
        margin-bottom: 0.9rem;
    }
    .ns-action-box .action-name {
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 1.25rem;
        color: var(--cyan-deep);
        margin-bottom: 0.4rem;
    }
    .ns-action-box .action-just { color: var(--body-text); font-size: 0.94rem; line-height: 1.55; }

    .ns-divider { border: none; border-top: 1px solid var(--line); margin: 1.8rem 0; }

    .ns-pipeline-item { font-size: 0.86rem; padding: 0.35rem 0; border-bottom: 1px dashed #26485C; }
    .ns-pipeline-num { font-family: 'IBM Plex Mono', monospace; color: var(--cyan); font-weight: 500; margin-right: 0.5rem; }

    .ns-footer { color: var(--muted); font-size: 0.8rem; padding-top: 1.5rem; border-top: 1px solid var(--line); margin-top: 2rem; }

    div[data-testid="stTextInput"] input {
        font-family: 'IBM Plex Mono', monospace;
        border-radius: 3px;
        border: 1px solid #26485C;
        background: #0E3348;
        color: #FFFFFF !important;
    }
    .stButton button {
        background: var(--cyan);
        color: var(--navy-deep);
        border-radius: 3px;
        border: none;
        font-weight: 700;
        font-family: 'Space Grotesk', sans-serif;
    }
    .stButton button:hover { background: #FFFFFF; color: var(--navy); }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Masthead
# ---------------------------------------------------------------
st.markdown("""
<div class="ns-masthead">
    <div class="brand">North<span>Star</span> CX</div>
    <div class="tagline">Customer 360 record and next-best-action assessment — built on Snowflake Cortex</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------
with st.sidebar:
    st.markdown('<div class="ns-side-label">LOOK UP A RECORD</div>', unsafe_allow_html=True)
    customer_id = st.text_input("Customer ID", value="CUST0001", label_visibility="collapsed").strip().upper()
    run_button = st.button("Pull record", use_container_width=True)

    st.markdown('<hr class="ns-divider" style="border-color:#26485C;">', unsafe_allow_html=True)
    st.markdown('<div class="ns-side-label">ASSESSMENT PIPELINE</div>', unsafe_allow_html=True)
    pipeline_steps = [
        "Customer 360 assemble",
        "Churn risk score",
        "Next best action",
        "Action audit trail",
    ]
    for idx, step in enumerate(pipeline_steps, start=1):
        st.markdown(
            f'<div class="ns-pipeline-item"><span class="ns-pipeline-num">{idx:02d}</span>{step}</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<hr class="ns-divider" style="border-color:#26485C;">', unsafe_allow_html=True)
    st.caption(
        "Unifies structured records (policies, claims) and unstructured "
        "signals (call transcripts) into one evidence-backed assessment, "
        "with every recommendation traceable to source data."
    )

RISK_COLORS = {
    "High": "var(--risk-high)",
    "Medium": "var(--risk-medium)",
    "Low": "var(--risk-low)",
}

if run_button and customer_id:
    with st.spinner("Assembling record through Snowflake Cortex..."):
        try:
            conn = get_connection()
            data = fetch_customer_data(conn, customer_id)

            if data is None:
                st.error(f"No record found for {customer_id}.")
            else:
                profile_text = call_cortex_complete(conn, build_prompt(data))
                risk_result = churn_risk_score(customer_id, data=data, conn=conn)
                action_result = next_best_action(
                    customer_id, data=data, risk_result=risk_result, conn=conn
                )
                audit_record = build_audit_record(
                    customer_id, data, risk_result, action_result
                )
                conn.close()

                customer = data["customer"]
                risk_color = RISK_COLORS.get(risk_result["risk_level"], "var(--muted)")

                st.markdown(f"""
                <div class="ns-record-header">{customer['NAME']}</div>
                <div class="ns-record-meta">{customer['SEGMENT']} segment, {customer['CITY']} — <span class="ns-mono">{customer_id}</span></div>
                """, unsafe_allow_html=True)

                st.markdown(f"""
                <div class="ns-metrics">
                    <div class="ns-metric"><div class="ns-metric-label">Tenure</div><div class="ns-metric-value">{customer['TENURE_YEARS']}y</div></div>
                    <div class="ns-metric"><div class="ns-metric-label">Policies</div><div class="ns-metric-value">{len(data['policies'])}</div></div>
                    <div class="ns-metric"><div class="ns-metric-label">Claims</div><div class="ns-metric-value">{len(data['claims'])}</div></div>
                    <div class="ns-metric"><div class="ns-metric-label">Interactions</div><div class="ns-metric-value">{len(data['interactions'])}</div></div>
                </div>
                """, unsafe_allow_html=True)

                col_left, col_right = st.columns([3, 2], gap="large")

                with col_left:
                    st.markdown('<div class="ns-section-label">UNIFIED PROFILE</div>', unsafe_allow_html=True)
                    st.markdown(f'<div class="ns-body-text">{profile_text}</div>', unsafe_allow_html=True)

                    st.markdown('<hr class="ns-divider">', unsafe_allow_html=True)

                    st.markdown('<div class="ns-section-label">RECOMMENDED NEXT ACTION</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="ns-action-box">
                        <div class="action-name">{action_result['action']}</div>
                        <div class="action-just">{action_result['justification']}</div>
                    </div>
                    """, unsafe_allow_html=True)

                with col_right:
                    st.markdown('<div class="ns-section-label">CHURN RISK</div>', unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class="ns-risk-row">
                        <span class="ns-risk-score">{risk_result['risk_score']}</span>
                        <span class="ns-risk-of100">/100</span>
                    </div>
                    <div style="margin-bottom:0.9rem;">
                        <span class="ns-risk-square" style="background:{risk_color};"></span>
                        <span class="ns-risk-level" style="color:{risk_color};">{risk_result['risk_level']}</span>
                    </div>
                    <div class="ns-body-text" style="font-size:0.92rem;">{risk_result['reasoning']}</div>
                    """, unsafe_allow_html=True)

                st.markdown('<hr class="ns-divider">', unsafe_allow_html=True)

                st.markdown('<div class="ns-section-label">AUDIT TRAIL</div>', unsafe_allow_html=True)
                st.caption("Every figure above is traceable to the source records below.")
                with st.expander("View evidence and full reasoning trail"):
                    st.json(audit_record)

        except Exception as e:
            st.error(f"Something went wrong: {e}")
else:
    st.markdown("""
    <div class="ns-body-text" style="padding: 2rem 0;">
        Enter a customer ID in the sidebar and select <strong>Pull record</strong> to
        generate a unified profile, churn risk assessment, and next-best-action
        recommendation. Try any ID from <span class="ns-mono">CUST0001</span> through
        <span class="ns-mono">CUST0120</span>.
    </div>
    """, unsafe_allow_html=True)

st.markdown(
    '<div class="ns-footer">NorthStar CX — Snowflake CoCo CLI Hackathon, GCC Edition</div>',
    unsafe_allow_html=True,
)