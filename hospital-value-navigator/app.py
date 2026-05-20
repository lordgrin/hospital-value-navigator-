import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hospital Value Navigator",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent

# ── Load data ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    vt  = pd.read_csv(BASE_DIR / "hospital_value_table.csv")
    drg = pd.read_csv(BASE_DIR / "hospital_drg_detail.csv")
    return vt, drg

vt, drg = load_data()

# ── Sidebar filters ────────────────────────────────────────────────────────
st.sidebar.title("🏥 Hospital Value Navigator")
st.sidebar.caption("Medicare Inpatient Data · 2,840 Hospitals · 50 States")
st.sidebar.markdown("---")

states       = ["All"] + sorted(vt["state"].dropna().unique().tolist())
peer_groups  = ["All"] + sorted(vt["peer_group"].dropna().unique().tolist())
own_opts     = ["All"] + sorted(vt["ownership_simplified"].dropna().unique().tolist())

sel_state    = st.sidebar.selectbox("Filter by State", states)
sel_peer     = st.sidebar.selectbox("Hospital Type",   peer_groups)
sel_ownership= st.sidebar.selectbox("Ownership",       own_opts)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Data Sources:** CMS Medicare IPPS · CMS Hospital Compare "
    "(Mortality, Readmissions, HCAHPS)  \n"
    "**Note:** CPR = Charge-to-Payment Ratio. "
    "Value scores are peer-group adjusted."
)

# ── Apply filters ──────────────────────────────────────────────────────────
filtered = vt.copy()
if sel_state     != "All": filtered = filtered[filtered["state"]                == sel_state]
if sel_peer      != "All": filtered = filtered[filtered["peer_group"]           == sel_peer]
if sel_ownership != "All": filtered = filtered[filtered["ownership_simplified"] == sel_ownership]

# ── Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Hospital Lookup",
    "🗺️ National Rankings",
    "📊 DRG Drill-Down",
    "📋 Peer Benchmarking",
])

# ══════════════════════════════════════════════════════════════════
# TAB 1 — Hospital Lookup
# ══════════════════════════════════════════════════════════════════
with tab1:
    st.header("Hospital Scorecard")

    search = st.text_input(
        "Search hospital by name",
        placeholder="e.g. Mayo Clinic, NYU Langone, Johns Hopkins..."
    )

    if search:
        matches = vt[vt["hospital_name"].str.contains(search, case=False, na=False)]
        if matches.empty:
            st.warning("No hospitals found. Try a shorter search term.")
        else:
            hosp_labels = matches["hospital_name"] + " (" + matches["state"] + ")"
            sel_label   = st.selectbox("Select hospital", hosp_labels.tolist())
            sel_idx     = hosp_labels[hosp_labels == sel_label].index[0]
            h           = vt.loc[sel_idx]

            # Header
            st.markdown(f"## {h['hospital_name']}")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("State",          h["state"])
            c2.metric("Ownership",      h["ownership_simplified"])
            c3.metric("Peer Group",     h["peer_group"])
            c4.metric("Value Quadrant", h["value_quadrant"])

            st.markdown("---")

            # Key metrics
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric(
                "Value Score",
                f"{h['value_score']:.1f}/100" if pd.notna(h["value_score"]) else "N/A",
                help="Peer-adjusted: mortality 30%, readmission 25%, experience 20%, cost 25%"
            )
            m2.metric(
                "Median CPR",
                f"{h['median_cpr']:.2f}×" if pd.notna(h["median_cpr"]) else "N/A",
                delta=f"{h['median_cpr_vs_peers']:+.1f}% vs peers"
                      if pd.notna(h.get("median_cpr_vs_peers")) else None,
                delta_color="inverse"
            )
            m3.metric(
                "Mortality Rate",
                f"{h['avg_mortality_rate']:.1f}%" if pd.notna(h["avg_mortality_rate"]) else "N/A",
                delta=f"{h['avg_mortality_rate_vs_peers']:+.1f}% vs peers"
                      if pd.notna(h.get("avg_mortality_rate_vs_peers")) else None,
                delta_color="inverse"
            )
            m4.metric(
                "Readmission Rate",
                f"{h['avg_readmission_rate']:.1f}%" if pd.notna(h["avg_readmission_rate"]) else "N/A",
                delta=f"{h['avg_readmission_rate_vs_peers']:+.1f}% vs peers"
                      if pd.notna(h.get("avg_readmission_rate_vs_peers")) else None,
                delta_color="inverse"
            )
            m5.metric(
                "Patient Experience",
                f"{h['avg_star_rating']:.1f}★" if pd.notna(h["avg_star_rating"]) else "N/A",
                delta=f"{h['avg_patient_experience_linear_vs_peers']:+.1f}% vs peers"
                      if pd.notna(h.get("avg_patient_experience_linear_vs_peers")) else None
            )

            st.markdown("---")

            # Radar chart
            if pd.notna(h.get("value_score")):
                cats   = ["Cost Efficiency","Mortality Quality",
                          "Readmission Quality","Patient Experience"]
                vals   = [
                    float(h.get("score_cost",       50) or 50),
                    float(h.get("score_mortality",  50) or 50),
                    float(h.get("score_readmission",50) or 50),
                    float(h.get("score_experience", 50) or 50),
                ]
                cats_c = cats + [cats[0]]
                vals_c = vals + [vals[0]]

                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals_c, theta=cats_c, fill="toself",
                    fillcolor="rgba(1,105,111,0.2)",
                    line=dict(color="#01696f", width=2),
                    name=str(h["hospital_name"])[:30]
                ))
                fig_radar.add_trace(go.Scatterpolar(
                    r=[50,50,50,50,50], theta=cats_c,
                    line=dict(color="gray", width=1, dash="dash"),
                    name="Peer Median"
                ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                    showlegend=True,
                    title="Performance vs Peer Median (50 = peer median)",
                    height=420
                )
                st.plotly_chart(fig_radar, use_container_width=True)

            # CMS flag
            n_worse = h.get("n_worse_than_national", 0)
            if pd.notna(n_worse) and int(n_worse) > 0:
                st.warning(
                    f"⚠️ Rated **Worse Than National** on "
                    f"{int(n_worse)} CMS quality measure(s)."
                )
            else:
                st.success("✅ No CMS measures rated 'Worse Than National'.")
    else:
        st.info("👆 Type a hospital name above to see its full scorecard.")

# ══════════════════════════════════════════════════════════════════
# TAB 2 — National Rankings
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.header("National Rankings")

    col_l, col_r = st.columns([1.2, 1])

    with col_l:
        st.subheader(f"Hospitals ({len(filtered):,} shown)")

        sort_by  = st.selectbox(
            "Sort by",
            ["value_score","median_cpr","avg_mortality_rate",
             "avg_readmission_rate","avg_star_rating"],
            index=0
        )
        sort_asc = st.checkbox("Ascending", value=False)

        disp = {
            "hospital_name"       : "Hospital",
            "state"               : "State",
            "ownership_simplified": "Ownership",
            "peer_group"          : "Peer Group",
            "value_score"         : "Value Score",
            "median_cpr"          : "Median CPR",
            "avg_mortality_rate"  : "Mortality %",
            "avg_readmission_rate": "Readmission %",
            "avg_star_rating"     : "Star Rating",
            "value_quadrant"      : "Quadrant",
        }
        tbl = (
            filtered[[c for c in disp if c in filtered.columns]]
            .rename(columns=disp)
            .sort_values(disp.get(sort_by, "Value Score"),
                         ascending=sort_asc, na_position="last")
            .reset_index(drop=True)
        )
        st.dataframe(tbl, height=500, use_container_width=True)

    with col_r:
        st.subheader("Value Quadrant Map")
        scatter_df = filtered.dropna(
            subset=["avg_mortality_rate","median_cpr","value_quadrant"]
        ).copy()

        color_map = {
            "🌟 High Value"            : "#1E8449",
            "💰 High Quality, High Cost": "#E67E22",
            "⚠️ Low Quality, Low Cost"  : "#F39C12",
            "🔴 Low Value"             : "#C0392B",
            "Insufficient Data"        : "#BDC3C7",
        }
        fig_q = px.scatter(
            scatter_df,
            x="median_cpr",
            y="avg_mortality_rate",
            color="value_quadrant",
            color_discrete_map=color_map,
            hover_data=["hospital_name","state","ownership_simplified",
                        "avg_readmission_rate","value_score"],
            labels={
                "median_cpr"         : "Median CPR (↓ better)",
                "avg_mortality_rate" : "30-Day Mortality % (↓ better)",
                "value_quadrant"     : "Quadrant",
            },
            title="Cost vs Mortality",
            height=500, opacity=0.7
        )
        fig_q.update_traces(marker=dict(size=6))
        st.plotly_chart(fig_q, use_container_width=True)

    st.markdown("---")
    st.subheader("Quadrant Summary")
    qc = filtered["value_quadrant"].value_counts().reset_index()
    qc.columns = ["Quadrant","Count"]
    qc["% of Hospitals"] = (qc["Count"] / len(filtered) * 100).round(1)
    st.dataframe(qc, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════
# TAB 3 — DRG Drill-Down
# ══════════════════════════════════════════════════════════════════
with tab3:
    st.header("DRG Procedure Drill-Down")
    st.caption("Identify which procedures drive pricing above peer levels.")

    search3 = st.text_input(
        "Search hospital",
        placeholder="Type hospital name...",
        key="drg_search"
    )

    if search3:
        matches3 = vt[vt["hospital_name"].str.contains(search3, case=False, na=False)]
        if matches3.empty:
            st.warning("No hospital found.")
        else:
            names3 = matches3["hospital_name"] + " (" + matches3["state"] + ")"
            sel3   = st.selectbox("Select hospital", names3.tolist(), key="drg_sel")
            idx3   = names3[names3 == sel3].index[0]
            ccn3   = vt.loc[idx3, "ccn"]

            hosp_drgs = drg[drg["ccn"] == ccn3].copy()

            if hosp_drgs.empty:
                st.warning("No DRG detail available for this hospital.")
            else:
                hosp_drgs["short_desc"] = hosp_drgs["drg_desc"].astype(str).str[:60]

                c1, c2, c3 = st.columns(3)
                c1.metric("DRGs Treated",    hosp_drgs["drg_code"].nunique())
                c2.metric("Total Discharges",f"{int(hosp_drgs['total_discharges'].sum()):,}")
                c3.metric("Median CPR",      f"{hosp_drgs['charge_to_payment_ratio'].median():.2f}×")

                # Top by volume
                st.subheader("Top 15 DRGs by Volume")
                top_v = (
                    hosp_drgs.nlargest(15, "total_discharges")
                    [["short_desc","total_discharges","avg_charge",
                      "avg_total_payment","charge_to_payment_ratio"]]
                    .rename(columns={
                        "short_desc"             : "DRG",
                        "total_discharges"       : "Discharges",
                        "avg_charge"             : "Avg Charge",
                        "avg_total_payment"      : "Avg Payment",
                        "charge_to_payment_ratio": "CPR",
                    })
                    .reset_index(drop=True)
                )
                top_v["Avg Charge"]  = top_v["Avg Charge"].apply(lambda x: f"${x:,.0f}")
                top_v["Avg Payment"] = top_v["Avg Payment"].apply(lambda x: f"${x:,.0f}")
                top_v["CPR"]         = top_v["CPR"].apply(lambda x: f"{x:.2f}×")
                st.dataframe(top_v, use_container_width=True, hide_index=True)

                # Top by CPR
                st.subheader("Top 15 DRGs by Pricing Intensity (CPR)")
                top_cpr_df = (
                    hosp_drgs[hosp_drgs["total_discharges"] >= 5]
                    .nlargest(15, "charge_to_payment_ratio")
                )
                if not top_cpr_df.empty:
                    fig_bar = px.bar(
                        top_cpr_df,
                        x="charge_to_payment_ratio",
                        y="short_desc",
                        orientation="h",
                        labels={
                            "charge_to_payment_ratio": "CPR",
                            "short_desc": "DRG"
                        },
                        title="Top 15 DRGs by CPR (min 5 discharges)",
                        color="charge_to_payment_ratio",
                        color_continuous_scale="RdYlGn_r",
                        height=500
                    )
                    fig_bar.update_layout(
                        yaxis={"categoryorder":"total ascending"},
                        coloraxis_showscale=False
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)
                else:
                    st.info("Not enough DRGs with ≥5 discharges to show CPR chart.")
    else:
        st.info("👆 Search for a hospital to see its DRG breakdown.")

# ══════════════════════════════════════════════════════════════════
# TAB 4 — Peer Benchmarking
# ══════════════════════════════════════════════════════════════════
with tab4:
    st.header("Peer Group Benchmarking")

    peer_sel = st.selectbox(
        "Select peer group",
        sorted(vt["peer_group"].dropna().unique().tolist()),
        key="peer_sel"
    )
    peer_df = vt[vt["peer_group"] == peer_sel].dropna(subset=["value_score"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hospitals in Group", len(peer_df))
    c2.metric("Avg Value Score",    f"{peer_df['value_score'].mean():.1f}")
    c3.metric("Avg Mortality",      f"{peer_df['avg_mortality_rate'].mean():.1f}%"
                                    if peer_df["avg_mortality_rate"].notna().any() else "N/A")
    c4.metric("Avg CPR",            f"{peer_df['median_cpr'].mean():.2f}×"
                                    if peer_df["median_cpr"].notna().any() else "N/A")

    st.markdown("---")
    col_l2, col_r2 = st.columns(2)

    with col_l2:
        fig_hist = px.histogram(
            peer_df,
            x="value_score",
            color="ownership_simplified",
            nbins=30,
            title=f"Value Score Distribution — {peer_sel}",
            labels={"value_score":"Value Score","ownership_simplified":"Ownership"},
            barmode="overlay", opacity=0.7, height=350
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_r2:
        box_df = peer_df.dropna(subset=["median_cpr","ownership_simplified"])
        if not box_df.empty:
            fig_box = px.box(
                box_df,
                x="ownership_simplified",
                y="median_cpr",
                color="ownership_simplified",
                title=f"CPR by Ownership — {peer_sel}",
                labels={"median_cpr":"Median CPR","ownership_simplified":"Ownership"},
                height=350, points="outliers"
            )
            fig_box.update_layout(showlegend=False)
            st.plotly_chart(fig_box, use_container_width=True)

    st.markdown("---")
    col_t, col_b = st.columns(2)

    show_cols = [c for c in ["hospital_name","state","ownership_simplified",
                              "value_score","median_cpr","avg_mortality_rate",
                              "avg_readmission_rate","value_quadrant"]
                 if c in peer_df.columns]

    with col_t:
        st.subheader("🏆 Top 10 in Peer Group")
        st.dataframe(
            peer_df.nlargest(10,"value_score")[show_cols].reset_index(drop=True),
            use_container_width=True, hide_index=True
        )

    with col_b:
        st.subheader("⚠️ Bottom 10 in Peer Group")
        st.dataframe(
            peer_df.nsmallest(10,"value_score")[show_cols].reset_index(drop=True),
            use_container_width=True, hide_index=True
        )
