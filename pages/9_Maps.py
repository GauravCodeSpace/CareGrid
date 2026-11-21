"""
CareGrid AI — Facility Maps Page
===================================
Interactive map visualization using Folium + streamlit-folium.
Shows facility markers with status colors, redistribution routes,
and nearest facility finder.
"""

import streamlit as st

from utils.auth import require_auth
from utils.helper import section_header_html


def render_page() -> None:
    """Render the facility maps page."""
    if not require_auth():
        return

    st.markdown(
        '<div class="page-title">🗺️ Facility Maps</div>'
        '<div class="page-subtitle">Interactive map of healthcare facilities with status indicators</div>',
        unsafe_allow_html=True,
    )

    try:
        import folium
        from streamlit_folium import st_folium
        from services.map_service import MapService
    except ImportError as e:
        st.error(f"Map dependencies not available: {e}. Run `pip install folium streamlit-folium`.")
        return

    # ── Controls ──
    col1, col2 = st.columns([3, 1])
    with col2:
        show_routes = st.checkbox("🔄 Show Redistribution Routes", value=False, key="map_routes_toggle")
        show_labels = st.checkbox("🏷️ Show Labels", value=True, key="map_labels_toggle")

    # ── Build Map ──
    st.markdown(section_header_html("🗺️", "District Healthcare Facilities"), unsafe_allow_html=True)

    with st.spinner("Loading map..."):
        try:
            markers = MapService.get_facility_markers()
        except Exception as e:
            st.error(f"Error loading facility data: {e}")
            markers = []

    if not markers:
        st.warning("No facility data available. Please run the data seeder.")
        return

    # Center map on India by default
    m = folium.Map(
        location=[20.5937, 78.9629],
        zoom_start=5,
        tiles="CartoDB positron",
        control_scale=True,
    )

    # Color mapping
    color_map = {"green": "green", "orange": "orange", "red": "red"}
    icon_map = {"green": "ok-sign", "orange": "warning-sign", "red": "exclamation-sign"}

    # ── Add Facility Markers ──
    for marker in markers:
        color = color_map.get(marker["status_color"], "blue")
        icon_name = icon_map.get(marker["status_color"], "plus-sign")

        # Popup HTML
        popup_html = f"""
        <div style="font-family:Inter,sans-serif;width:220px;padding:4px;">
            <h4 style="color:#2563EB;margin:0 0 6px 0;font-size:14px;">
                🏥 {marker['name']}
            </h4>
            <hr style="margin:4px 0;border-color:#E2E8F0;">
            <table style="font-size:12px;width:100%;border-collapse:collapse;">
                <tr><td style="color:#64748B;padding:2px 0;">Type</td>
                    <td style="font-weight:600;">{marker['type']}</td></tr>
                <tr><td style="color:#64748B;padding:2px 0;">Status</td>
                    <td><span style="background:{'#DCFCE7' if color == 'green' else '#FEF3C7' if color == 'orange' else '#FEE2E2'};
                    color:{'#166534' if color == 'green' else '#92400E' if color == 'orange' else '#991B1B'};
                    padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;text-transform:uppercase;">
                    {marker['status_color'].upper()}</span></td></tr>
            </table>
            {marker.get('popup_html', '')}
        </div>
        """

        tooltip = marker["name"] if show_labels else None

        folium.Marker(
            location=[marker["lat"], marker["lon"]],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=tooltip,
            icon=folium.Icon(
                color=color,
                icon=icon_name,
                prefix="glyphicon",
            ),
        ).add_to(m)

    # ── Add Redistribution Routes ──
    if show_routes:
        try:
            routes = MapService.get_redistribution_routes()
            for route in routes:
                coords = route.get("route_coords", [])
                if len(coords) >= 2:
                    folium.PolyLine(
                        locations=coords,
                        color="#2563EB",
                        weight=3,
                        opacity=0.7,
                        dash_array="10",
                        tooltip=f"Transfer: {route.get('medicine', 'N/A')} ({route.get('quantity', 0)} units)",
                    ).add_to(m)

                    # Add arrow marker at midpoint
                    mid_idx = len(coords) // 2
                    if mid_idx < len(coords):
                        folium.Marker(
                            location=coords[mid_idx],
                            icon=folium.DivIcon(
                                html='<div style="font-size:16px;">🔄</div>',
                                icon_size=(20, 20),
                                icon_anchor=(10, 10),
                            ),
                        ).add_to(m)
        except Exception as e:
            st.warning(f"Could not load redistribution routes: {e}")

    # ── Add Legend ──
    legend_html = """
    <div style="position:fixed;bottom:30px;left:50px;z-index:1000;
    background:white;padding:12px 16px;border-radius:12px;
    box-shadow:0 2px 12px rgba(0,0,0,0.1);font-family:Inter,sans-serif;font-size:12px;">
        <div style="font-weight:600;margin-bottom:6px;color:#1E293B;">Legend</div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
            <span style="width:12px;height:12px;background:#22C55E;border-radius:50%;display:inline-block;"></span>
            Healthy
        </div>
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
            <span style="width:12px;height:12px;background:#F59E0B;border-radius:50%;display:inline-block;"></span>
            Warning
        </div>
        <div style="display:flex;align-items:center;gap:6px;">
            <span style="width:12px;height:12px;background:#EF4444;border-radius:50%;display:inline-block;"></span>
            Critical
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    # ── Render Map ──
    map_data = st_folium(m, width=None, height=550, returned_objects=["last_clicked"])

    # ── Nearest Facility Finder ──
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(section_header_html("📍", "Find Nearest Facility"), unsafe_allow_html=True)

    col_lat, col_lon, col_btn = st.columns([2, 2, 1])

    with col_lat:
        search_lat = st.number_input(
            "Latitude", value=26.85, format="%.4f",
            min_value=20.0, max_value=35.0, key="map_search_lat",
        )
    with col_lon:
        search_lon = st.number_input(
            "Longitude", value=80.95, format="%.4f",
            min_value=70.0, max_value=90.0, key="map_search_lon",
        )
    with col_btn:
        st.markdown("<br>", unsafe_allow_html=True)
        search_clicked = st.button("🔍 Find Nearest", key="map_search_btn")

    if search_clicked:
        try:
            nearest = MapService.get_nearest_facility(search_lat, search_lon)
            if nearest:
                st.success(
                    f"📍 Nearest facility: **{nearest['name']}** "
                    f"({nearest['type']}) — {nearest['distance_km']:.1f} km away"
                )
                st.markdown(
                    f"""<div class="glass-card">
                        <h3>🏥 {nearest['name']}</h3>
                        <p><strong>Type:</strong> {nearest['type']} |
                        <strong>Distance:</strong> {nearest['distance_km']:.1f} km |
                        <strong>Coordinates:</strong> ({nearest['lat']:.4f}, {nearest['lon']:.4f})</p>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.warning("No facilities found.")
        except Exception as e:
            st.error(f"Search error: {e}")

    # ── Clicked location ──
    if map_data and map_data.get("last_clicked"):
        clicked = map_data["last_clicked"]
        st.info(f"📌 Clicked location: ({clicked['lat']:.4f}, {clicked['lng']:.4f})")


# ── Page Entry Point ──
render_page()
