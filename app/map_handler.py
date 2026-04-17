"""Server-side map rendering: Folium (2D) and pydeck (3D)."""

import json
from typing import Any

import folium
import folium.plugins
import pydeck as pdk

from app import db

_SEVERITY_COLORS = {
    0: "#6b7280",   # unscored — gray
    1: "#10b981",   # green
    2: "#10b981",
    3: "#34d399",
    4: "#fbbf24",
    5: "#f59e0b",   # amber
    6: "#f59e0b",
    7: "#ef4444",   # red
    8: "#ef4444",
    9: "#dc2626",
    10: "#b91c1c",
}


def _color(severity: int) -> str:
    return _SEVERITY_COLORS.get(severity, "#6b7280")


async def render_2d() -> str:
    """Render Folium map shell as HTML string."""
    events = await db.fetch_events(limit=500)

    m = folium.Map(
        location=[20, 0],
        zoom_start=2,
        tiles="CartoDB dark_matter",
        prefer_canvas=True,
    )

    cluster = folium.plugins.MarkerCluster(name="Events").add_to(m)
    heat_data = []

    for ev in events:
        if ev["lat"] is None or ev["lon"] is None:
            continue
        color = _color(ev["severity"] or 0)
        popup_html = (
            f"<b>{ev['title']}</b><br>"
            f"<small>{ev.get('source_name','')} — {(ev.get('published_at') or '')[:10]}</small><br>"
            f"Severity: {ev['severity'] or 'N/A'}<br>"
            f'<a href="{ev["link"]}" target="_blank">Read more</a>'
        )
        folium.CircleMarker(
            location=[ev["lat"], ev["lon"]],
            radius=6,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=ev["title"][:60],
        ).add_to(cluster)
        heat_data.append([ev["lat"], ev["lon"], (ev["severity"] or 0) / 10])

    if heat_data:
        folium.plugins.HeatMap(heat_data, min_opacity=0.3, radius=20, blur=15).add_to(m)

    folium.LayerControl().add_to(m)

    # Inject WS listener for live marker updates
    _inject_ws_script(m)

    return m._repr_html_()


def _inject_ws_script(m: folium.Map) -> None:
    """Add a JS snippet that listens on the parent WS and appends new markers."""
    js = """
<script>
(function() {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(proto + '://' + window.location.host + '/ws');
  ws.onmessage = function(e) {
    const msg = JSON.parse(e.data);
    if (msg.type !== 'new_event') return;
    const ev = msg.event;
    if (ev.lat == null || ev.lon == null) return;
    const sev = ev.severity || 0;
    const colors = {"0":"#6b7280","1":"#10b981","2":"#10b981","3":"#34d399",
                    "4":"#fbbf24","5":"#f59e0b","6":"#f59e0b","7":"#ef4444",
                    "8":"#ef4444","9":"#dc2626","10":"#b91c1c"};
    const color = colors[String(sev)] || '#6b7280';
    L.circleMarker([ev.lat, ev.lon], {
      radius: 6, color: color, fillColor: color, fillOpacity: 0.8
    }).bindPopup('<b>' + ev.title + '</b>').addTo(window._map);
  };
  // expose map globally for the WS handler
  document.addEventListener('DOMContentLoaded', function() {
    const maps = Object.values(window).filter(v => v && v._container && v.setView);
    if (maps.length) window._map = maps[0];
  });
})();
</script>
"""
    m.get_root().html.add_child(folium.Element(js))


async def render_3d() -> str:
    """Render a pydeck globe as an HTML string."""
    events = await db.fetch_events(limit=1000)
    data = [
        {
            "lat": ev["lat"],
            "lon": ev["lon"],
            "title": ev["title"][:60],
            "severity": ev["severity"] or 0,
        }
        for ev in events
        if ev["lat"] is not None and ev["lon"] is not None
    ]

    scatter = pdk.Layer(
        "ScatterplotLayer",
        data=data,
        get_position="[lon, lat]",
        get_color="[severity * 25, 100, 255 - severity * 20, 180]",
        get_radius=80000,
        pickable=True,
        auto_highlight=True,
    )

    hex_layer = pdk.Layer(
        "HexagonLayer",
        data=data,
        get_position="[lon, lat]",
        radius=200000,
        elevation_scale=4,
        elevation_range=[0, 1000],
        pickable=True,
        extruded=True,
        coverage=0.8,
    )

    view = pdk.ViewState(latitude=20, longitude=0, zoom=1.5, pitch=45)

    deck = pdk.Deck(
        layers=[hex_layer, scatter],
        initial_view_state=view,
        map_style="mapbox://styles/mapbox/dark-v10",
        tooltip={"text": "{title}"},
    )

    return deck.to_html(as_string=True)
