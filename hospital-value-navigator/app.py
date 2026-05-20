import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# ── Page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Hospital Value Navigator",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Load data ──────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    vt  = pd.read_csv('hospital_value_table.csv')
    drg = pd.read_csv('hospital_drg_detail.csv')
    return vt, drg

vt, drg = load_data()

# ── Sidebar filters ────────────────────────────────────────────────────────
st.sidebar.title("🏥 Hospital Value Navigator")
st.sidebar.caption("Medicare Inpatient Data · 2,840 Hospitals · 50 States")
st.sidebar.markdown("---")

states = ['All'] + sorted(vt['state'].dropna().unique().tolist())
sel_state = st.sidebar.selectbox("Filter by State", states)

peer_groups = ['All'] + sorted(vt['peer_group'].dropna().unique().tolist())
sel_peer = st.sidebar.selectbox("Hospital Type", peer_groups)

ownership_opts = ['All'] + sorted(vt['ownership_simplified'].dropna().unique().tolist())
sel_ownership = st.sidebar.selectbox("Ownership", ownership_opts)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Data Sources:** CMS Medicare IPPS, "
    "CMS Hospital Compare (Mortality, Readmissions, HCAHPS)  \n"
    "**Note:** CPR = Charge-to-Payment Ratio. "
    "Value scores are peer-group adjusted."
)

# ── Apply filters ──────────────────────────────────────────────────────────
filtered = vt.copy()
if sel_state    != 'All': filtered = filtered[filtered['state'] == sel_state]
if sel_peer     != 'All': filtered = filtered[filtered['peer_group'] == sel_peer]
if sel_ownership!= 'All': filtered = filtered[filtered['ownership_simplified'] == sel_ownership]

# ── Tabs ───────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "🔍 Hospital Lookup",
    "🗺️ National Rankings",
    "📊 DRG Drill-Down",
    "📋 Peer Benchmarking"
])

# ══════════════════════════════════════════════════════════════════
# TAB 1: Hospital Lookup
# ══════════════════════════════════════════════════════════════════
with tab1:
    st.header("Hospital Scorecard")

    search = st.text_input(
        "Search hospital by name",
        placeholder="e.g. Mayo Clinic, NYU Langone, Johns Hopkins..."
    )

    if search:
        matches = vt[vt['hospital_name'].str.contains(search, case=False, na=False)]
        if matches.empty:
            st.warning("No hospitals found. Try a shorter search term.")
        else:
            hosp_names = matches['hospital_name'] + ' (' + matches['state'] + ')'
            sel_name = st.selectbox("Select hospital", hosp_names.tolist())
            sel_idx  = hosp_names[hosp_names == sel_name].index[0]
            h = vt.loc[sel_idx]

            # ── Header card
            quadrant_color = {
                '🌟 High Value'           : 'green',
                '💰 High Quality, High Cost': 'orange',
                '⚠️ Low Quality, Low Cost' : 'orange',
                '🔴 Low Value'            : 'red',
                'Insufficient Data'       : 'gray',
            }
            color = quadrant_color.get(h['value_quadrant'], 'gray')

            st.markdown(f"## {h['hospital_name']}")
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("State", h['state'])
            col_b.metric("Ownership", h['ownership_simplified'])
            col_c.metric("Peer Group", h['peer_group'])
            col_d.metric("Value Quadrant", h['value_quadrant'])

            st.markdown("---")

            # ── Key metrics row
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric(
                "Value Score",
                f"{h['value_score']:.1f}/100" if pd.notna(h['value_score']) else "N/A",
                help="Peer-adjusted composite: mortality 30%, readmission 25%, experience 20%, cost 25%"
            )
            c2.metric(
                "Median CPR",
                f"{h['median_cpr']:.2f}×" if pd.notna(h['median_cpr']) else "N/A",
                delta=f"{h['median_cpr_vs_peers']:+.1f}% vs peers" if pd.notna(h.get('median_cpr_vs_peers')) else None,
                delta_color="inverse",
                help="Charge-to-Payment Ratio. Lower = more efficient pricing."
            )
            c3.metric(
                "Mortality Rate",
                f"{h['avg_mortality_rate']:.1f}%" if pd.notna(h['avg_mortality_rate']) else "N/A",
                delta=f"{h['avg_mortality_rate_vs_peers']:+.1f}% vs peers" if pd.notna(h.get('avg_mortality_rate_vs_peers')) else None,
                delta_color="inverse"
            )
            c4.metric(
                "Readmission Rate",
                f"{h['avg_readmission_rate']:.1f}%" if pd.notna(h['avg_readmission_rate']) else "N/A",
                delta=f"{h['avg_readmission_rate_vs_peers']:+.1f}% vs peers" if pd.notna(h.get('avg_readmission_rate_vs_peers')) else None,
                delta_color="inverse"
            )
            c5.metric(
                "Patient Experience",
                f"{h['avg_star_rating']:.1f}★" if pd.notna(h['avg_star_rating']) else "N/A",
                delta=f"{h['avg_patient_experience_linear_vs_peers']:+.1f}% vs peers" if pd.notna(h.get('avg_patient_experience_linear_vs_peers')) else None
            )

            st.markdown("---")

            # ── Radar chart of normalized scores
            if pd.notna(h['value_score']):
                categories = ['Cost\nEfficiency','Mortality\nQuality',
                              'Readmission\nQuality','Patient\nExperience']
                values = [
                    h.get('score_cost', 50),
                    h.get('score_mortality', 50),
                    h.get('score_readmission', 50),
                    h.get('score_experience', 50),
                ]
                values_closed = values + [values[0]]
                categories_closed = categories + [categories[0]]

                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=values_closed,
                    theta=categories_closed,
                    fill='toself',
                    fillcolor='rgba(1,105,111,0.2)',
                    line=dict(color='#01696f', width=2),
                    name=h['hospital_name'][:30]
                ))
                fig_radar.add_trace(go.Scatterpolar(
                    r=[50,50,50,50,50],
                    theta=categories_closed,
                    line=dict(color='gray', width=1, dash='dash'),
                    name='Peer Median'
                ))
                fig_radar.update_layout(
                    polar=dict(radialaxis=dict(visible=True, range=[0,100])),
                    showlegend=True,
                    title="Performance vs Peer Median (50 = peer median)",
                    height=400
                )
                st.plotly_chart(fig_radar, use_container_width=True)

            # ── CMS comparison flags
            if h.get('n_worse_than_national', 0) > 0:
                st.warning(
                    f"⚠️ This hospital is rated **Worse Than National** "
                    f"on {int(h['n_worse_than_national'])} CMS quality measures."
                )
            else:
                st.success("✅ No CMS measures rated 'Worse Than National'.")

    else:
        st.info("👆 Type a hospital name above to see its full scorecard.")

# ══════════════════════════════════════════════════════════════════
# TAB 2: National Rankings + Quadrant Chart
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.header("National Rankings")

    col_l, col_r = st.columns([1.2, 1])

    with col_l:
        # Sortable rankings table
        st.subheader(f"Hospitals ({len(filtered):,} shown)")
        display_cols = {
            'hospital_name'        : 'Hospital',
            'state'                : 'State',
            'ownership_simplified' : 'Ownership',
            'peer_group'           : 'Peer Group',
            'value_score'          : 'Value Score',
            'median_cpr'           : 'Median CPR',
            'avg_mortality_rate'   : 'Mortality %',
            'avg_readmission_rate' : 'Readmission %',
            'avg_star_rating'      : 'Star Rating',
            'value_quadrant'       : 'Quadrant',
        }
        sort_col = st.selectbox(
            "Sort by",
            ['value_score','median_cpr','avg_mortality_rate',
             'avg_readmission_rate','avg_star_rating'],
            index=0
        )
        sort_asc = st.checkbox("Ascending", value=False)

        tbl = (
            filtered[list(display_cols.keys())]
            .rename(columns=display_cols)
            .sort_values(sort_col.replace('_',' ').title()
                         if sort_col in display_cols else 'Value Score',
                         ascending=sort_asc, na_position='last')
            .reset_index(drop=True)
        )
        # Actually sort correctly
        tbl = (
            filtered[list(display_cols.keys())]
            .rename(columns=display_cols)
            .sort_values('Value Score', ascending=sort_asc, na_position='last')
            .reset_index(drop=True)
        )
        st.dataframe(tbl, height=500, use_container_width=True)

    with col_r:
        # Value quadrant scatter
        st.subheader("Value Quadrant")
        scatter_df = filtered.dropna(
            subset=['avg_mortality_rate','median_cpr','value_quadrant']
        ).copy()
        scatter_df['label'] = scatter_df['hospital_name'].str[:30]

        color_map = {
            '🌟 High Value'            : '#1E8449',
            '💰 High Quality, High Cost': '#E67E22',
            '⚠️ Low Quality, Low Cost'  : '#F39C12',
            '🔴 Low Value'             : '#C0392B',
            'Insufficient Data'        : '#BDC3C7',
        }

        fig_quad = px.scatter(
            scatter_df,
            x='median_cpr',
            y='avg_mortality_rate',
            color='value_quadrant',
            color_discrete_map=color_map,
            hover_data=['hospital_name','state','ownership_simplified',
                        'avg_readmission_rate','value_score'],
            labels={
                'median_cpr'          : 'Median CPR (lower = more efficient)',
                'avg_mortality_rate'  : '30-Day Mortality Rate % (lower = better)',
                'value_quadrant'      : 'Value Quadrant'
            },
            title="Cost vs Mortality by Hospital",
            height=500,
            opacity=0.7
        )
        fig_quad.update_traces(marker=dict(size=6))
        st.plotly_chart(fig_quad, use_container_width=True)

    # ── Value quadrant summary
    st.markdown("---")
    st.subheader("Quadrant Summary")
    quad_counts = filtered['value_quadrant'].value_counts().reset_index()
    quad_counts.columns = ['Quadrant','Count']
    quad_counts['% of Hospitals'] = (
        quad_counts['Count'] / len(filtered) * 100
    ).round(1)
    st.dataframe(quad_counts, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════════════
# TAB 3: DRG Drill-Down
# ══════════════════════════════════════════════════════════════════
with tab3:
    st.header("DRG Procedure Drill-Down")
    st.caption("Identify which procedures are driving pricing above peer levels.")

    search3 = st.text_input(
        "Search hospital",
        placeholder="Type hospital name...",
        key="drg_search"
    )

    if search3:
        matches3 = vt[vt['hospital_name'].str.contains(search3, case=False, na=False)]
        if matches3.empty:
            st.warning("No hospital found.")
        else:
            names3 = matches3['hospital_name'] + ' (' + matches3['state'] + ')'
            sel3   = st.selectbox("Select hospital", names3.tolist(), key="drg_sel")
            idx3   = names3[names3 == sel3].index[0]
            ccn3   = vt.loc[idx3, 'ccn']

            hosp_drgs = drg[drg['ccn'] == ccn3].copy()

            if hosp_drgs.empty:
                st.warning("No DRG detail available for this hospital.")
            else:
                # DRG-level metrics
                hosp_drgs['short_desc'] = hosp_drgs['drg_desc'].str[:60]

                c1, c2, c3 = st.columns(3)
                c1.metric("DRGs Treated", hosp_drgs['drg_code'].nunique())
                c2.metric("Total Discharges",
                          f"{hosp_drgs['total_discharges'].sum():,}")
                c3.metric("Median CPR",
                          f"{hosp_drgs['charge_to_payment_ratio'].median():.2f}×")

                # Top DRGs by volume
                st.subheader("Top 15 DRGs by Volume")
                top_drgs = (
                    hosp_drgs.nlargest(15, 'total_discharges')
                    [['short_desc','total_discharges',
                      'avg_charge','avg_total_payment',
                      'charge_to_payment_ratio']]
                    .rename(columns={
                        'short_desc'             : 'DRG Description',
                        'total_discharges'       : 'Discharges',
                        'avg_charge'             : 'Avg Charge',
                        'avg_total_payment'      : 'Avg Payment',
                        'charge_to_payment_ratio': 'CPR'
                    })
                )
                top_drgs['Avg Charge']   = top_drgs['Avg Charge'].apply(
                    lambda x: f"${x:,.0f}")
                top_drgs['Avg Payment'] = top_drgs['Avg Payment'].apply(
                    lambda x: f"${x:,.0f}")
                top_drgs['CPR'] = top_drgs['CPR'].apply(lambda x: f"{x:.2f}×")
                st.dataframe(top_drgs, use_container_width=True, hide_index=True)

                # Top DRGs by CPR
                st.subheader("Top 15 DRGs by Pricing Intensity (CPR)")
                top_cpr = (
                    hosp_drgs[hosp_drgs['total_discharges'] >= 5]
                    .nlargest(15, 'charge_to_payment_ratio')
                    [['short_desc','total_discharges',
                      'avg_charge','charge_to_payment_ratio']]
                    .rename(columns={
                        'short_desc'             : 'DRG Description',
                        'total_discharges'       : 'Discharges',
                        'avg_charge'             : 'Avg Charge',
                        'charge_to_payment_ratio': 'CPR'
                    })
                )
                top_cpr['Avg Charge'] = top_cpr['Avg Charge'].apply(
                    lambda x: f"${x:,.0f}")
                top_cpr['CPR'] = top_cpr['CPR'].apply(lambda x: f"{x:.2f}×")

                fig_bar = px.bar(
                    hosp_drgs[hosp_drgs['total_discharges'] >= 5]
                    .nlargest(15, 'charge_to_payment_ratio'),
                    x='charge_to_payment_ratio',
                    y='short_desc',
                    orientation='h',
                    labels={'charge_to_payment_ratio': 'CPR',
                            'short_desc': 'DRG'},
                    title="Top 15 DRGs by CPR (min 5 discharges)",
                    color='charge_to_payment_ratio',
                    color_continuous_scale='RdYlGn_r',
                    height=500
                )
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
                st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.info("👆 Search for a hospital to see its DRG breakdown.")

# ══════════════════════════════════════════════════════════════════
# TAB 4: Peer Benchmarking
# ══════════════════════════════════════════════════════════════════
with tab4:
    st.header("Peer Group Benchmarking")

    peer_sel = st.selectbox(
        "Select peer group to analyze",
        sorted(vt['peer_group'].dropna().unique().tolist()),
        key="peer_sel"
    )
    peer_df = vt[vt['peer_group'] == peer_sel].dropna(subset=['value_score'])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Hospitals in Group", len(peer_df))
    c2.metric("Avg Value Score",    f"{peer_df['value_score'].mean():.1f}")
    c3.metric("Avg Mortality",      f"{peer_df['avg_mortality_rate'].mean():.1f}%")
    c4.metric("Avg CPR",            f"{peer_df['median_cpr'].mean():.2f}×")

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        # Value score distribution
        fig_hist = px.histogram(
            peer_df,
            x='value_score',
            color='ownership_simplified',
            nbins=30,
            title=f"Value Score Distribution — {peer_sel}",
            labels={'value_score': 'Value Score', 'ownership_simplified': 'Ownership'},
            barmode='overlay',
            opacity=0.7,
            height=350
        )
        st.plotly_chart(fig_hist, use_container_width=True)

    with col_right:
        # CPR by ownership
        fig_box = px.box(
            peer_df.dropna(subset=['median_cpr','ownership_simplified']),
            x='ownership_simplified',
            y='median_cpr',
            color='ownership_simplified',
            title=f"CPR by Ownership — {peer_sel}",
            labels={'median_cpr': 'Median CPR',
                    'ownership_simplified': 'Ownership'},
            height=350,
            points='outliers'
        )
        fig_box.update_layout(showlegend=False)
        st.plotly_chart(fig_box, use_container_width=True)

    # Top and bottom performers
    st.markdown("---")
    col_t, col_b = st.columns(2)

    with col_t:
        st.subheader("🏆 Top 10 in Peer Group")
        st.dataframe(
            peer_df.nlargest(10, 'value_score')
            [['hospital_name','state','ownership_simplified',
              'value_score','median_cpr','avg_mortality_rate',
              'avg_readmission_rate','value_quadrant']]
            .reset_index(drop=True),
            use_container_width=True,
            hide_index=True
        )

    with col_b:
        st.subheader("⚠️ Bottom 10 in Peer Group")
        st.dataframe(
            peer_df.nsmallest(10, 'value_score')
            [['hospital_name','state','ownership_simplified',
              'value_score','median_cpr','avg_mortality_rate',
              'avg_readmission_rate','value_quadrant']]
            .reset_index(drop=True),
            use_container_width=True,
            hide_index=True
        )
