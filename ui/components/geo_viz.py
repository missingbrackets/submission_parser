# ============================================================
#  ui/components/geo_viz.py
#  Map & Imagery tab renderer.
#
#  Renders:
#   1. Interactive plotly scatter_geo map — all SOV locations,
#      bubbles sized by TIV where available.
#   2. Per-location image cards — Street View + satellite,
#      fetched live from Google Maps APIs.
#
#  Google API key is read from st.secrets["GOOGLE_API_KEY"].
#  If the key is absent the imagery section is hidden; the map
#  still renders using extracted lat/lon coordinates.
# ============================================================

from __future__ import annotations
import streamlit as st


def render_geo_viz_tab(extracted: dict) -> None:
    """Main entry point called from data_tabs.py for GEO_VIZ section."""
    import pandas as pd

    google_api_key = st.secrets.get("GOOGLE_API_KEY", "")

    sov_locs = [
        loc for loc in (extracted.get("sov_locations") or [])
        if isinstance(loc, dict)
    ]

    if not sov_locs:
        # No SOV — try a single aggregate point from insured_country
        country = extracted.get("insured_country") or extracted.get("primary_country_risk")
        if country:
            st.info(f"No per-location SOV data — showing country-level view for **{country}**.")
            _render_country_fallback(country, google_api_key)
        else:
            st.warning("No location data available for mapping.")
        return

    # ── Build display dataframe ───────────────────────────────
    rows = []
    for loc in sov_locs:
        lat = _to_float(loc.get("latitude") or loc.get("lat"))
        lon = _to_float(loc.get("longitude") or loc.get("lon"))
        name    = loc.get("location_name") or loc.get("name") or "Unnamed"
        address = loc.get("address") or loc.get("street_address") or ""
        city    = loc.get("city") or ""
        country = loc.get("country") or ""
        tiv     = _to_float(loc.get("tiv") or loc.get("tiv_total") or loc.get("tiv_pd"))
        rows.append({
            "name":    name,
            "address": address,
            "city":    city,
            "country": country,
            "lat":     lat,
            "lon":     lon,
            "tiv":     tiv or 0,
            "label":   f"{name}<br>{address + '<br>' if address else ''}{city}, {country}<br>TIV: {_fmt_tiv(tiv)}",
        })

    df = pd.DataFrame(rows)

    # ── 1. Map ────────────────────────────────────────────────
    _render_map(df, extracted)

    st.markdown("---")

    # ── 2. Per-location imagery ───────────────────────────────
    _render_imagery_grid(rows, google_api_key)


# ── Map section ───────────────────────────────────────────────

def _render_map(df, extracted):
    try:
        import plotly.express as px
        import plotly.graph_objects as go

        # Rows with valid coords
        df_map = df.dropna(subset=["lat", "lon"])

        if df_map.empty:
            st.info("Coordinates not available — cannot render map. Extract lat/lon in the submission or enable geocoding.")
            return

        # Bubble size: TIV relative, min visible size 8
        max_tiv = df_map["tiv"].max() or 1
        df_map = df_map.copy()
        df_map["size"] = ((df_map["tiv"] / max_tiv) * 25 + 8).clip(lower=8)

        fig = px.scatter_geo(
            df_map,
            lat="lat",
            lon="lon",
            hover_name="name",
            hover_data={
                "address": True,
                "city":    True,
                "country": True,
                "tiv":     ":,.0f",
                "lat":     False,
                "lon":     False,
                "size":    False,
                "label":   False,
            },
            size="size",
            size_max=35,
            color="tiv",
            color_continuous_scale=[
                [0.0,  "#1E3A5F"],
                [0.4,  "#0066CC"],
                [0.7,  "#F59E0B"],
                [1.0,  "#EF4444"],
            ],
            color_continuous_midpoint=df_map["tiv"].median(),
            projection="natural earth",
            title=None,
        )

        fig.update_layout(
            paper_bgcolor="#0F1523",
            plot_bgcolor="#0F1523",
            geo=dict(
                bgcolor="#0F1523",
                landcolor="#1E293B",
                oceancolor="#0D1B2A",
                lakecolor="#0D1B2A",
                countrycolor="#334155",
                coastlinecolor="#334155",
                showland=True,
                showocean=True,
                showlakes=True,
                showcountries=True,
                showcoastlines=True,
                framecolor="#334155",
            ),
            coloraxis_colorbar=dict(
                title="TIV",
                tickfont=dict(color="#94A3B8", size=10),
                titlefont=dict(color="#94A3B8", size=11),
                bgcolor="#0F1523",
                bordercolor="#334155",
            ),
            margin=dict(l=0, r=0, t=10, b=0),
            height=420,
            font=dict(color="#E2E8F0"),
        )

        fig.update_traces(
            marker=dict(
                line=dict(width=1, color="#E2E8F0"),
                opacity=0.9,
            )
        )

        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        # Summary metrics below map
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Locations plotted", len(df_map))
        mc2.metric(
            "Total TIV",
            _fmt_tiv(df_map["tiv"].sum()) if df_map["tiv"].sum() > 0 else "—",
        )
        mc3.metric(
            "Countries",
            df_map["country"].nunique() if "country" in df_map.columns else "—",
        )

    except ImportError:
        # Plotly not installed — fall back to st.map
        df_valid = df.dropna(subset=["lat", "lon"])
        if df_valid.empty:
            st.warning("No coordinates available for map.")
            return
        st.map(df_valid.rename(columns={"lat": "latitude", "lon": "longitude"}))
        st.caption(f"{len(df_valid)} location(s) plotted. Install plotly for richer map visualisation.")


# ── Imagery grid ──────────────────────────────────────────────

def _render_imagery_grid(rows: list[dict], google_api_key: str) -> None:
    from core.geo_images import geocode_address

    st.markdown("#### Location Imagery")

    if not google_api_key or google_api_key.startswith("your-"):
        st.info("Add `GOOGLE_API_KEY` to `.streamlit/secrets.toml` to enable Street View and satellite imagery.")
        return

    # Resolve precise coordinates for each location.
    # Priority: (1) street address geocoded → building-level precision
    #           (2) existing lat/lon (usually city-centre from Claude) → fallback
    #           (3) geocode from city + country → last resort
    fetchable = []
    for loc in rows:
        lat, lon   = loc.get("lat"), loc.get("lon")
        address    = loc.get("address") or ""
        city       = loc.get("city") or ""
        country    = loc.get("country") or ""
        geocode_src = None

        if address:
            # Always geocode from street address — Claude's lat/lon are often
            # city-centre approximations, not building-level.
            full_addr = ", ".join(p for p in [address, city, country] if p)
            coords = geocode_address(full_addr, google_api_key)
            if coords:
                lat, lon = coords
                geocode_src = f"Geocoded from: {full_addr}"
        elif lat is None or lon is None:
            # No address and no coords — try city + country
            addr_parts = [p for p in [city, country] if p]
            if addr_parts:
                coords = geocode_address(", ".join(addr_parts), google_api_key)
                if coords:
                    lat, lon = coords
                    geocode_src = f"Geocoded from: {', '.join(addr_parts)}"

        if lat is not None and lon is not None:
            fetchable.append({**loc, "lat": lat, "lon": lon, "_geocode_src": geocode_src})

    if not fetchable:
        st.warning("No geocodable locations found — imagery unavailable.")
        return

    # Render in pairs
    for i in range(0, len(fetchable), 2):
        cols = st.columns(2)
        for j, loc in enumerate(fetchable[i : i + 2]):
            with cols[j]:
                _render_location_card(loc, google_api_key)


def _render_location_card(loc: dict, api_key: str) -> None:
    lat, lon     = loc["lat"], loc["lon"]
    name         = loc.get("name") or "Location"
    address      = loc.get("address") or ""
    city         = loc.get("city") or ""
    country      = loc.get("country") or ""
    tiv_label    = _fmt_tiv(loc.get("tiv"))
    geocode_src  = loc.get("_geocode_src") or ""

    subtitle = " · ".join(p for p in [address, city, country] if p)

    st.markdown(
        f'<div style="background:#111827; border:1px solid #1E2D45; border-radius:6px; '
        f'padding:10px 12px; margin-bottom:4px;">'
        f'<div style="font-size:0.82rem; font-weight:700; color:#E2E8F0;">{name}</div>'
        + (f'<div style="font-size:0.75rem; color:#64748B;">{subtitle}</div>' if subtitle else "")
        + (f'<div style="font-size:0.72rem; color:#00C2FF; margin-top:2px;">TIV: {tiv_label}</div>' if tiv_label != "—" else "")
        + (f'<div style="font-size:0.68rem; color:#374151; margin-top:3px;">{geocode_src}</div>' if geocode_src else "")
        + f'</div>',
        unsafe_allow_html=True,
    )

    sv_col, sat_col = st.columns(2)

    with sv_col:
        with st.spinner("Street View…"):
            sv_bytes = _cached_streetview(lat, lon, api_key)
        if sv_bytes:
            st.image(sv_bytes, caption="Street View", use_container_width=True)
        else:
            st.markdown(
                '<div style="background:#0D1117; border:1px dashed #334155; border-radius:4px; '
                'padding:20px; text-align:center; color:#475569; font-size:0.75rem;">No Street View</div>',
                unsafe_allow_html=True,
            )

    with sat_col:
        with st.spinner("Satellite…"):
            sat_bytes = _cached_satellite(lat, lon, api_key)
        if sat_bytes:
            st.image(sat_bytes, caption="Satellite", use_container_width=True)
        else:
            st.markdown(
                '<div style="background:#0D1117; border:1px dashed #334155; border-radius:4px; '
                'padding:20px; text-align:center; color:#475569; font-size:0.75rem;">No Satellite Image</div>',
                unsafe_allow_html=True,
            )


# ── Country-level fallback (no SOV) ──────────────────────────

def _render_country_fallback(country: str, api_key: str) -> None:
    from core.geo_images import geocode_address, get_satellite_image

    coords = geocode_address(country, api_key) if api_key else None
    if coords:
        lat, lon = coords
        try:
            import plotly.express as px
            import pandas as pd
            df = pd.DataFrame([{"lat": lat, "lon": lon, "label": country}])
            fig = px.scatter_geo(
                df, lat="lat", lon="lon", hover_name="label",
                projection="natural earth",
            )
            fig.update_layout(
                paper_bgcolor="#0F1523",
                geo=dict(bgcolor="#0F1523", landcolor="#1E293B",
                         oceancolor="#0D1B2A", showcountries=True),
                margin=dict(l=0, r=0, t=10, b=0),
                height=300,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
        except ImportError:
            pass

        if api_key and not api_key.startswith("your-"):
            sat = _cached_satellite(lat, lon, api_key, zoom=7)
            if sat:
                st.image(sat, caption=f"Satellite — {country}", use_container_width=True)


# ── Cached API fetchers (avoid re-fetching on every re-render) ─

@st.cache_data(show_spinner=False, ttl=3600)
def _cached_streetview(lat: float, lon: float, api_key: str) -> bytes | None:
    from core.geo_images import get_streetview_image
    return get_streetview_image(lat, lon, api_key)


@st.cache_data(show_spinner=False, ttl=3600)
def _cached_satellite(lat: float, lon: float, api_key: str, zoom: int = 17) -> bytes | None:
    from core.geo_images import get_satellite_image
    return get_satellite_image(lat, lon, api_key, zoom=zoom)


# ── Helpers ───────────────────────────────────────────────────

def _to_float(val) -> float | None:
    if val is None:
        return None
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def _fmt_tiv(val) -> str:
    if val is None or val == 0:
        return "—"
    try:
        v = float(val)
        if v >= 1_000_000_000:
            return f"{v/1_000_000_000:.1f}bn"
        if v >= 1_000_000:
            return f"{v/1_000_000:.1f}m"
        if v >= 1_000:
            return f"{v/1_000:.0f}k"
        return f"{v:,.0f}"
    except (ValueError, TypeError):
        return str(val)
