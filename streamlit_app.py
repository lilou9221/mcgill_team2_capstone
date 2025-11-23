# ============================================================
# DISPLAY RESULTS – CLEAN TWO-TAB VERSION WITH LEGENDS
# ============================================================

if st.session_state.analysis_results:

    csv_path = Path(st.session_state.analysis_results["csv_path"])
    df = pd.read_csv(csv_path)
    map_paths = {k: Path(v) for k, v in st.session_state.analysis_results["map_paths"].items()}

    farmer_tab, investor_tab = st.tabs(["🌱 Farmer Perspective", "📊 Investor Perspective"])

    # ====================== FARMER TAB ======================
    with farmer_tab:

        st.markdown("### Soil Health, Suitability & Biochar Recommendations")

        # Summary Metrics
        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Hexagons Analyzed", f"{len(df):,}")
        with c2:
            st.metric("Mean Suitability Score", f"{df['suitability_score'].mean():.2f}")
        with c3:
            high = (df["suitability_score"] >= 7).sum()
            st.metric("Highly Suitable (≥7)", f"{high:,} ({high/len(df)*100:.1f}%)")

        # Sub-tabs for individual soil layers
        tab1, tab2, tab3, tab4, rec_tab = st.tabs([
            "Suitability",
            "Soil Organic Carbon (SOC)",
            "Soil pH",
            "Soil Moisture",
            "Top 10 Recommendations"
        ])

        def show_map(tab, title, key, legend_html):
            with tab:
                st.subheader(title)
                path = map_paths.get(key)
                if path and path.exists():
                    with open(path, "r", encoding="utf-8") as f:
                        st.components.v1.html(f.read(), height=700, scrolling=False)
                    st.markdown(legend_html, unsafe_allow_html=True)
                else:
                    st.warning(f"{title} map not generated.")

        # Suitability Legend
        suit_legend = """
            <div class="legend-box">
                <div class="legend-title">Suitability Score (0–10)</div>
                <div class="legend-row">
                    <div class="legend-item"><span class="legend-color" style="background:#8B0000;"></span>0–2 Very Low</div>
                    <div class="legend-item"><span class="legend-color" style="background:#FF4500;"></span>2–4 Low</div>
                    <div class="legend-item"><span class="legend-color" style="background:#FFD700;"></span>4–6 Moderate</div>
                    <div class="legend-item"><span class="legend-color" style="background:#90EE90;"></span>6–8 High</div>
                    <div class="legend-item"><span class="legend-color" style="background:#006400;"></span>8–10 Very High</div>
                </div>
                <p><strong>Higher score = higher biochar impact potential</strong></p>
            </div>
        """

        # SOC Legend
        soc_legend = """
            <div class="legend-box">
                <div class="legend-title">Soil Organic Carbon (g/kg)</div>
                <div class="legend-row">
                    <div class="legend-item"><span class="legend-color" style="background:#FFFFCC;"></span><10 Very Low</div>
                    <div class="legend-item"><span class="legend-color" style="background:#C7E9B4;"></span>10–20 Low</div>
                    <div class="legend-item"><span class="legend-color" style="background:#7FCDBB;"></span>20–30 Moderate</div>
                    <div class="legend-item"><span class="legend-color" style="background:#41B6C4;"></span>30–40 High</div>
                    <div class="legend-item"><span class="legend-color" style="background:#253494;"></span>>50 Very High</div>
                </div>
            </div>
        """

        # pH Legend
        ph_legend = """
            <div class="legend-box">
                <div class="legend-title">Soil pH</div>
                <div class="legend-row">
                    <div class="legend-item"><span class="legend-color" style="background:#8B0000;"></span><5 Strongly Acidic</div>
                    <div class="legend-item"><span class="legend-color" style="background:#FF6347;"></span>5–5.5 Acidic</div>
                    <div class="legend-item"><span class="legend-color" style="background:#FFD700;"></span>5.5–7 Ideal</div>
                    <div class="legend-item"><span class="legend-color" style="background:#87CEEB;"></span>7–8 Alkaline</div>
                </div>
            </div>
        """

        # Moisture Legend
        moisture_legend = """
            <div class="legend-box">
                <div class="legend-title">Soil Moisture (%)</div>
                <div class="legend-row">
                    <div class="legend-item"><span class="legend-color" style="background:#8B4513;"></span><10% Very Dry</div>
                    <div class="legend-item"><span class="legend-color" style="background:#D2691E;"></span>10–20 Dry</div>
                    <div class="legend-item"><span class="legend-color" style="background:#F4A460;"></span>20–30 Moderate</div>
                    <div class="legend-item"><span class="legend-color" style="background:#87CEEB;"></span>30–40 Moist</div>
                    <div class="legend-item"><span class="legend-color" style="background:#1E90FF;"></span>>40 Very Moist</div>
                </div>
            </div>
        """

        show_map(tab1, "Biochar Suitability", "suitability", suit_legend)
        show_map(tab2, "Soil Organic Carbon (SOC)", "soc", soc_legend)
        show_map(tab3, "Soil pH", "ph", ph_legend)
        show_map(tab4, "Soil Moisture", "moisture", moisture_legend)

        # ===== TOP 10 RECOMMENDATIONS =====
        with rec_tab:
            st.subheader("Top 10 Recommended Locations for Biochar Application")

            feed_col = next((c for c in df.columns if "feedstock" in c.lower()), None)
            reason_col = next((c for c in df.columns if "reason" in c.lower()), None)

            if feed_col and reason_col:
                cols = ["h3_index", "suitability_score", "mean_soc", "mean_ph", "mean_moisture", feed_col, reason_col]
                cols = [c for c in cols if c in df.columns]

                top10 = df[cols].sort_values("suitability_score", ascending=False).head(10).round(3)
                st.dataframe(top10, use_container_width=True, hide_index=True)
            else:
                st.info("Feedstock recommendation columns not found.")

    # ====================== INVESTOR TAB ======================
    with investor_tab:

        st.markdown("### Crop Residue & Biomass Opportunity Across Brazil")

        if not st.session_state.investor_map_available:
            st.warning("Investor data files not found.")
        else:
            from src.map_generators.pydeck_maps.municipality_waste_map import (
                prepare_investor_crop_area_geodata,
                create_municipality_waste_deck,
            )

            @st.cache_data
            def get_gdf():
                return prepare_investor_crop_area_geodata(
                    PROJECT_ROOT / "data/boundaries/BR_Municipios_2024",
                    PROJECT_ROOT / "data/crop_data/Updated_municipality_crop_production_data.csv",
                    simplify_tolerance=0.05
                )

            gdf = get_gdf()

            data_type = st.radio(
                "Select dataset to visualize:",
                ["area", "production", "residue"],
                format_func=lambda x: {"area": "Crop Area (ha)", "production": "Crop Production (t)", "residue": "Crop Residue (t)"}[x],
                horizontal=True
            )

            deck = create_municipality_waste_deck(gdf, data_type=data_type)
            st.pydeck_chart(deck, use_container_width=True)

            # Legend specific to investor maps
            st.markdown("""
                <div class="legend-box">
                    <div class="legend-title">Biomass Availability (tons/year)</div>
                    <div class="legend-row">
                        <div class="legend-item"><span class="legend-color" style="background:#FFFFCC;"></span>Low</div>
                        <div class="legend-item"><span class="legend-color" style="background:#C7E9B4;"></span>Moderate</div>
                        <div class="legend-item"><span class="legend-color" style="background:#41B6C4;"></span>High</div>
                        <div class="legend-item"><span class="legend-color" style="background:#225EA8;"></span>Very High</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            # Metrics
            c1, c2, c3 = st.columns(3)
            with c1: st.metric("Total Crop Area", f"{gdf['total_crop_area_ha'].sum():,.0f} ha")
            with c2: st.metric("Total Production", f"{gdf['total_crop_production_ton'].sum():,.0f} t")
            with c3: st.metric("Total Residue", f"{gdf['total_crop_residue_ton'].sum():,.0f} t")
