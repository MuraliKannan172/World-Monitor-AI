"""Server-side map rendering: Folium 2D (17 tile layers) and globe.gl 3D (4 textures)."""

import json

import folium
import folium.plugins

from app import db
from app.layers import LAYER_DEFS

_SEVERITY_COLORS = {
    0: "#6b7280", 1: "#10b981", 2: "#10b981", 3: "#34d399",
    4: "#fbbf24", 5: "#f59e0b", 6: "#f59e0b", 7: "#ef4444",
    8: "#ef4444", 9: "#dc2626", 10: "#b91c1c",
}

# All free/open-source tile layers: (name, tiles_or_url, attr, show_by_default)
_TILE_LAYERS: list[dict] = [
    # ── Dark themes ──────────────────────────────────────────────────────
    {"name": "🌑 Dark Matter",
     "tiles": "CartoDB dark_matter", "attr": None, "show": True},
    {"name": "🌑 Dark (No Labels)",
     "tiles": "https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png",
     "attr": "© CartoDB © OpenStreetMap contributors"},
    {"name": "🌑 Stadia Dark",
     "tiles": "https://tiles.stadiamaps.com/tiles/alidade_smooth_dark/{z}/{x}/{y}{r}.png",
     "attr": "© Stadia Maps © OpenMapTiles © OpenStreetMap contributors"},
    # ── Light themes ─────────────────────────────────────────────────────
    {"name": "☀️ Positron (Light)",
     "tiles": "CartoDB positron", "attr": None},
    {"name": "☀️ Light (No Labels)",
     "tiles": "https://{s}.basemaps.cartocdn.com/light_nolabels/{z}/{x}/{y}{r}.png",
     "attr": "© CartoDB © OpenStreetMap contributors"},
    {"name": "☀️ Stadia Smooth",
     "tiles": "https://tiles.stadiamaps.com/tiles/alidade_smooth/{z}/{x}/{y}{r}.png",
     "attr": "© Stadia Maps © OpenMapTiles © OpenStreetMap contributors"},
    # ── Street maps ──────────────────────────────────────────────────────
    {"name": "🗺️ Voyager",
     "tiles": "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
     "attr": "© CartoDB © OpenStreetMap contributors"},
    {"name": "🗺️ OpenStreetMap",
     "tiles": "OpenStreetMap", "attr": None},
    {"name": "🗺️ OSM Humanitarian",
     "tiles": "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
     "attr": "© OpenStreetMap contributors, HOT"},
    {"name": "🗺️ OSM Bright (Stadia)",
     "tiles": "https://tiles.stadiamaps.com/tiles/osm_bright/{z}/{x}/{y}{r}.png",
     "attr": "© Stadia Maps © OpenMapTiles © OpenStreetMap contributors"},
    {"name": "🗺️ Esri World Streets",
     "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
     "attr": "Esri, HERE, Garmin, © OpenStreetMap contributors"},
    # ── Satellite ────────────────────────────────────────────────────────
    {"name": "🛰️ Satellite (Esri)",
     "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
     "attr": "Esri, Maxar, Earthstar Geographics"},
    {"name": "🛰️ Stadia Satellite",
     "tiles": "https://tiles.stadiamaps.com/tiles/alidade_satellite/{z}/{x}/{y}{r}.png",
     "attr": "© Stadia Maps © CNES/Airbus DS © Esri © OpenStreetMap contributors"},
    # ── Terrain / Topo ───────────────────────────────────────────────────
    {"name": "⛰️ Topo (Esri)",
     "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{z}/{y}/{x}",
     "attr": "Esri, HERE, Garmin, FAO, NOAA, USGS"},
    {"name": "⛰️ OpenTopoMap",
     "tiles": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
     "attr": "© OpenTopoMap contributors (CC-BY-SA)"},
    {"name": "⛰️ Stadia Outdoors",
     "tiles": "https://tiles.stadiamaps.com/tiles/outdoors/{z}/{x}/{y}{r}.png",
     "attr": "© Stadia Maps © OpenMapTiles © OpenStreetMap contributors"},
    # ── Specialty ────────────────────────────────────────────────────────
    {"name": "🌿 NatGeo (Esri)",
     "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/NatGeo_World_Map/MapServer/tile/{z}/{y}/{x}",
     "attr": "Esri, National Geographic, Garmin"},
    {"name": "⬜ Gray Canvas (Esri)",
     "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
     "attr": "Esri, HERE, Garmin, FAO"},
    {"name": "🚲 CyclOSM",
     "tiles": "https://{s}.tile-cyclosm.openstreetmap.fr/cyclosm/{z}/{x}/{y}.png",
     "attr": "CyclOSM Map © OpenStreetMap contributors"},
    # ── Artistic / Stylised ─────────────────────────────────────────────
    {"name": "🎨 Watercolor (Stadia)",
     "tiles": "https://tiles.stadiamaps.com/tiles/stamen_watercolor/{z}/{x}/{y}.jpg",
     "attr": "© Stadia Maps © OpenStreetMap contributors"},
    {"name": "🖤 Toner (Stadia)",
     "tiles": "https://tiles.stadiamaps.com/tiles/stamen_toner/{z}/{x}/{y}{r}.png",
     "attr": "© Stadia Maps © OpenStreetMap contributors"},
    {"name": "🔲 Toner Lite (Stadia)",
     "tiles": "https://tiles.stadiamaps.com/tiles/stamen_toner_lite/{z}/{x}/{y}{r}.png",
     "attr": "© Stadia Maps © OpenStreetMap contributors"},
    # ── Terrain variants ────────────────────────────────────────────────
    {"name": "🏔️ Terrain (Stadia)",
     "tiles": "https://tiles.stadiamaps.com/tiles/stamen_terrain/{z}/{x}/{y}{r}.png",
     "attr": "© Stadia Maps © OpenStreetMap contributors"},
    # ── USGS (US-focused, free, no key) ────────────────────────────────
    {"name": "🇺🇸 USGS Imagery",
     "tiles": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSImageryOnly/MapServer/tile/{z}/{y}/{x}",
     "attr": "USGS National Map"},
    {"name": "🇺🇸 USGS Topo",
     "tiles": "https://basemap.nationalmap.gov/arcgis/rest/services/USGSTopo/MapServer/tile/{z}/{y}/{x}",
     "attr": "USGS National Map"},
    # ── Ocean / Relief ──────────────────────────────────────────────────
    {"name": "🌊 Ocean Base (Esri)",
     "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/Ocean/World_Ocean_Base/MapServer/tile/{z}/{y}/{x}",
     "attr": "Esri, GEBCO, NOAA, National Geographic"},
    {"name": "🌄 Shaded Relief (Esri)",
     "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}",
     "attr": "Esri, USGS, NPS"},
    {"name": "⬛ Dark Gray (Esri)",
     "tiles": "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
     "attr": "Esri, HERE, Garmin, © OpenStreetMap contributors"},
    # ── Wikimedia ───────────────────────────────────────────────────────
    {"name": "📖 Wikimedia Maps",
     "tiles": "https://maps.wikimedia.org/osm-intl/{z}/{x}/{y}{r}.png",
     "attr": "Wikimedia Maps | © OpenStreetMap contributors"},
]


def _color(severity: int) -> str:
    return _SEVERITY_COLORS.get(severity, "#6b7280")


async def render_2d() -> str:
    """Render Folium map with 19 free tile layer options."""
    events = await db.fetch_events(limit=500)

    m = folium.Map(location=[20, 0], zoom_start=2, tiles=None, prefer_canvas=True)

    for layer in _TILE_LAYERS:
        show = layer.get("show", False)
        if layer["attr"] is None:
            # Built-in Folium tile name
            folium.TileLayer(layer["tiles"], name=layer["name"], show=show).add_to(m)
        else:
            folium.TileLayer(
                tiles=layer["tiles"],
                attr=layer["attr"],
                name=layer["name"],
                show=show,
            ).add_to(m)

    cluster = folium.plugins.MarkerCluster(name="📍 Events", show=True).add_to(m)
    heat_data = []

    for ev in events:
        if ev["lat"] is None or ev["lon"] is None:
            continue
        color = _color(ev["severity"] or 0)
        popup_html = (
            f"<b>{ev['title']}</b><br>"
            f"<small>{ev.get('source_name', '')} — {(ev.get('published_at') or '')[:10]}</small><br>"
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
        folium.plugins.HeatMap(
            heat_data, name="🔥 Heat Map", min_opacity=0.3, radius=20, blur=15, show=False
        ).add_to(m)

    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    _inject_ws_script(m, LAYER_DEFS)
    return m.get_root().render()


def _inject_ws_script(m: folium.Map, layer_defs: list[dict]) -> None:
    """Inject WS live markers + postMessage layer toggle support."""
    js = """
<script>
(function() {
  // ── resolve map reference ────────────────────────────────────────────
  function getMap() {
    if (window._map) return window._map;
    const found = Object.values(window).find(v => v && v._container && v.setView);
    if (found) window._map = found;
    return window._map;
  }
  document.addEventListener('DOMContentLoaded', getMap);
  setTimeout(getMap, 800);

  // ── live WS events ───────────────────────────────────────────────────
  const colors = {"0":"#6b7280","1":"#10b981","2":"#10b981","3":"#34d399",
                  "4":"#fbbf24","5":"#f59e0b","6":"#f59e0b","7":"#ef4444",
                  "8":"#ef4444","9":"#dc2626","10":"#b91c1c"};
  (function connectWS() {
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(proto + '://' + location.host + '/ws');
    ws.onmessage = function(e) {
      const msg = JSON.parse(e.data);
      if (msg.type !== 'new_event') return;
      const ev = msg.event;
      if (ev.lat == null || ev.lon == null) return;
      const map = getMap(); if (!map) return;
      const color = colors[String(ev.severity || 0)] || '#6b7280';
      L.circleMarker([ev.lat, ev.lon], {
        radius: 6, color: color, fillColor: color, fillOpacity: 0.8
      }).bindPopup('<b>' + ev.title + '</b>').addTo(map);
    };
    ws.onclose = function() { setTimeout(connectWS, 3000); };
    setInterval(function(){ if(ws.readyState===1) ws.send('ping'); }, 25000);
  })();

  // ── overlay layer registry ───────────────────────────────────────────
  const LAYER_STYLES = {
    natural_events:    {color:'#f97316', radius:6},
    fires:             {color:'#ef4444', radius:4},
    aviation:          {color:'#38bdf8', radius:3},
    military_activity: {color:'#6366f1', radius:4},
    nuclear_sites:     {color:'#10b981', radius:8},
    gamma_irradiators: {color:'#f59e0b', radius:7},
    radiation_watch:   {color:'#22c55e', radius:6},
    military_bases:    {color:'#64748b', radius:7},
    chokepoints:       {color:'#fb923c', radius:9},
    spaceports:        {color:'#f0abfc', radius:7},
    ai_data_centers:   {color:'#8b5cf6', radius:7},
    economic_centers:  {color:'#34d399', radius:8},
    critical_minerals: {color:'#818cf8', radius:7},
    conflict_zones:    {color:'#ef4444', radius:6},
    armed_conflict:    {color:'#dc2626', radius:6},
    iran_attacks:      {color:'#ef4444', radius:7},
    intel_hotspots:    {color:'#f97316', radius:7},
    protests:          {color:'#f59e0b', radius:5},
    displacement:      {color:'#fb923c', radius:5},
    disease:           {color:'#a855f7', radius:6},
    weather_alerts:    {color:'#fbbf24', radius:7},
    cyber_threats:     {color:'#00d4ff', radius:6},
    gps_jamming:       {color:'#f59e0b', radius:6},
    orbital_surveillance:{color:'#a78bfa',radius:5},
    internet_disruptions:{color:'#94a3b8',radius:5},
    ship_traffic:      {color:'#0ea5e9', radius:3},
    sanctions:         {color:'#f43f5e', radius:7},
    cii_instability:   {color:'#ef4444', radius:6},
    resilience:        {color:'#10b981', radius:6},
  };

  const _overlays = {};

  async function loadOverlay(id) {
    const map = getMap(); if (!map) return;
    if (_overlays[id]) { map.addLayer(_overlays[id]); return; }
    try {
      const res = await fetch('/api/layers/' + id);
      const gj  = await res.json();
      const st  = LAYER_STYLES[id] || {color:'#60a5fa', radius:5};
      const lg  = L.layerGroup();
      if (gj.type === 'FeatureCollection') {
        gj.features.forEach(f => {
          const g = f.geometry;
          if (!g) return;
          const p = f.properties || {};
          const tip = p.name || p.title || p.callsign || id;
          if (g.type === 'Point') {
            L.circleMarker([g.coordinates[1], g.coordinates[0]], {
              radius: st.radius, color: st.color,
              fillColor: st.color, fillOpacity: 0.85, weight: 1.5,
            }).bindPopup('<b>' + tip + '</b>' +
              (p.country ? '<br>' + p.country : '') +
              (p.type || p.note || p.mineral ? '<br><small>' + (p.type||p.note||p.mineral||'') + '</small>' : '')
            ).addTo(lg);
          } else if (g.type === 'LineString' || g.type === 'MultiLineString') {
            const coords = g.type === 'LineString'
              ? g.coordinates.map(c => [c[1], c[0]])
              : g.coordinates.map(line => line.map(c => [c[1], c[0]]));
            L.polyline(g.type === 'LineString' ? coords : coords, {
              color: st.color, weight: 1.5, opacity: 0.7,
            }).bindPopup('<b>' + (p.name||id) + '</b>').addTo(lg);
          }
        });
      }
      _overlays[id] = lg;
      map.addLayer(lg);
    } catch(err) { console.warn('Layer load failed:', id, err); }
  }

  function removeOverlay(id) {
    const map = getMap(); if (!map) return;
    if (_overlays[id]) map.removeLayer(_overlays[id]);
  }

  // ── postMessage from parent page ─────────────────────────────────────
  window.addEventListener('message', function(e) {
    const d = e.data;
    if (!d || d.action !== 'toggle_layer') return;
    if (d.active) loadOverlay(d.layer_id);
    else removeOverlay(d.layer_id);
  });
})();
</script>
"""
    m.get_root().html.add_child(folium.Element(js))
    m.get_root().html.add_child(folium.Element(_build_overlay_panel(json.dumps(layer_defs))))


def _build_overlay_panel(layers_json: str) -> str:
    """Build floating overlay layer panel injected into the 2D Folium map."""
    template = """<script>
(function() {
  const WM_LAYERS = LAYERS_PLACEHOLDER;

  const css =
    '#wm-tog{position:absolute;top:70px;left:10px;z-index:999;background:rgba(10,14,26,.9);' +
    'border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:5px 12px;color:#94a3b8;' +
    'font:12px Inter,system-ui;cursor:pointer;white-space:nowrap}' +
    '#wm-tog:hover,#wm-tog.on{border-color:#00d4ff;color:#00d4ff}' +
    '#wm-panel{position:absolute;top:108px;left:10px;z-index:998;display:none;' +
    'background:rgba(10,14,26,.95);border:1px solid rgba(255,255,255,.12);' +
    'border-radius:10px;padding:10px;width:195px;max-height:55vh;overflow-y:auto;' +
    'font-family:Inter,system-ui;font-size:12px}' +
    '.wm-grp{color:#475569;font-size:10px;text-transform:uppercase;letter-spacing:.07em;' +
    'margin:8px 0 3px;border-top:1px solid rgba(255,255,255,.06);padding-top:7px}' +
    '.wm-grp:first-child{border-top:none;margin-top:0;padding-top:0}' +
    '.wm-lb{display:flex;gap:7px;align-items:center;width:100%;text-align:left;' +
    'background:rgba(255,255,255,.04);border:1px solid transparent;border-radius:6px;' +
    'padding:5px 9px;color:#94a3b8;cursor:pointer;margin-bottom:3px;transition:all .15s}' +
    '.wm-lb:hover{border-color:rgba(255,255,255,.2);color:#e2e8f0}' +
    '.wm-lb.on{border-color:#00d4ff;color:#00d4ff;background:rgba(0,212,255,.08)}';
  const st = document.createElement('style');
  st.textContent = css;
  document.head.appendChild(st);

  const tog = document.createElement('button');
  tog.id = 'wm-tog';
  tog.textContent = '🗂 Layers';
  document.body.appendChild(tog);

  const panel = document.createElement('div');
  panel.id = 'wm-panel';
  document.body.appendChild(panel);

  const groups = [...new Set(WM_LAYERS.map(function(l) { return l.group; }))];
  const active = {};

  groups.forEach(function(g) {
    const gt = document.createElement('div');
    gt.className = 'wm-grp';
    gt.textContent = g;
    panel.appendChild(gt);
    WM_LAYERS.filter(function(l) { return l.group === g; }).forEach(function(layer) {
      const b = document.createElement('button');
      b.className = 'wm-lb';
      b.innerHTML = '<span>' + layer.icon + '</span><span>' + layer.label + '</span>';
      b.onclick = function() {
        active[layer.id] = !active[layer.id];
        b.classList.toggle('on', !!active[layer.id]);
        if (active[layer.id]) loadOverlay(layer.id);
        else removeOverlay(layer.id);
      };
      panel.appendChild(b);
    });
  });

  let open = false;
  tog.onclick = function() {
    open = !open;
    panel.style.display = open ? 'block' : 'none';
    tog.classList.toggle('on', open);
  };
})();
</script>"""
    return template.replace('LAYERS_PLACEHOLDER', layers_json)


# Globe textures (all hosted on unpkg — free, no API key)
_GLOBE_TEXTURES = [
    {"id": "night",    "label": "🌑 Night Earth",    "url": "https://unpkg.com/three-globe/example/img/earth-night.jpg"},
    {"id": "day",      "label": "☀️ Day Earth",      "url": "https://unpkg.com/three-globe/example/img/earth-day.jpg"},
    {"id": "marble",   "label": "🔵 Blue Marble",    "url": "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg"},
    {"id": "dark",     "label": "⬛ Dark Earth",     "url": "https://unpkg.com/three-globe/example/img/earth-dark.jpg"},
]

_GLOBE_BACKGROUNDS = [
    {"id": "stars",  "label": "✨ Starfield", "url": "https://unpkg.com/three-globe/example/img/night-sky.png"},
    {"id": "stars2", "label": "🌌 Deep Sky",  "url": "https://unpkg.com/three-globe/example/img/stars.jpg"},
    {"id": "black",  "label": "⬛ Black",     "url": ""},
]


async def render_3d() -> str:
    """Return a globe.gl spinning Earth page with texture switcher and live WebSocket updates."""
    events = await db.fetch_events(limit=1000)
    initial_data = json.dumps([
        {
            "lat": ev["lat"], "lon": ev["lon"],
            "title": ev["title"][:80],
            "severity": ev["severity"] or 0,
            "source": ev.get("source_name", ""),
            "country": ev.get("country", ""),
        }
        for ev in events
        if ev["lat"] is not None and ev["lon"] is not None
    ])
    textures_json = json.dumps(_GLOBE_TEXTURES)
    backgrounds_json = json.dumps(_GLOBE_BACKGROUNDS)
    layers_json = json.dumps(LAYER_DEFS)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    *{{margin:0;padding:0;box-sizing:border-box}}
    body{{background:#000510;overflow:hidden;font-family:Inter,system-ui,sans-serif}}
    #globe-container{{width:100vw;height:100vh}}

    /* HUD */
    #hud{{position:fixed;top:14px;right:14px;display:flex;flex-direction:column;gap:8px;align-items:flex-end;z-index:10}}
    .badge{{background:rgba(10,14,26,.88);border:1px solid rgba(255,255,255,.1);border-radius:20px;padding:5px 14px;font-size:12px;color:#94a3b8;display:flex;align-items:center;gap:7px}}
    .pulse{{width:7px;height:7px;border-radius:50%;background:#10b981;animation:pulse 2s infinite}}
    @keyframes pulse{{0%,100%{{opacity:1;transform:scale(1)}}50%{{opacity:.4;transform:scale(1.5)}}}}

    /* Legend */
    #legend{{position:fixed;bottom:20px;left:20px;z-index:10;background:rgba(10,14,26,.88);border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:12px 16px;color:#94a3b8;font-size:12px;line-height:1.8}}
    #legend strong{{color:#e2e8f0;display:block;margin-bottom:4px}}
    .dot{{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}}

    /* Controls toolbar */
    #controls{{position:fixed;bottom:20px;right:20px;z-index:10;display:flex;flex-direction:column;gap:6px;align-items:flex-end}}
    .ctrl-row{{display:flex;gap:6px}}
    .ctrl-btn{{background:rgba(10,14,26,.88);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:5px 11px;color:#94a3b8;font-size:11px;cursor:pointer;transition:all .15s;white-space:nowrap}}
    .ctrl-btn:hover{{border-color:#00d4ff;color:#00d4ff}}
    .ctrl-btn.active{{border-color:#00d4ff;color:#00d4ff;background:rgba(0,212,255,.1)}}

    /* Layer panel */
    #layer-panel{{position:fixed;top:14px;left:14px;z-index:10;background:rgba(10,14,26,.92);border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:12px;width:220px;max-height:82vh;overflow-y:auto;display:none}}
    #layer-panel.open{{display:block}}
    #layer-panel h4{{color:#e2e8f0;font-size:11px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}}
    .layer-group{{margin-bottom:10px}}
    .layer-group label{{font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.06em;display:block;margin-bottom:4px}}
    .layer-btn{{display:block;width:100%;text-align:left;background:rgba(255,255,255,.04);border:1px solid transparent;border-radius:6px;padding:5px 9px;color:#94a3b8;font-size:12px;cursor:pointer;margin-bottom:3px;transition:all .15s}}
    .layer-btn:hover{{border-color:rgba(255,255,255,.15);color:#e2e8f0}}
    .layer-btn.active{{border-color:#00d4ff;color:#00d4ff;background:rgba(0,212,255,.08)}}
  </style>
</head>
<body>
  <div id="globe-container"></div>

  <!-- Layer picker panel -->
  <div id="layer-panel">
    <h4>Globe Layers</h4>
    <div class="layer-group">
      <label>Earth Texture</label>
      <div id="texture-btns"></div>
    </div>
    <div class="layer-group">
      <label>Background</label>
      <div id="bg-btns"></div>
    </div>
  </div>

  <!-- HUD -->
  <div id="hud">
    <div class="badge"><div class="pulse"></div><span id="ev-count">Loading…</span></div>
  </div>

  <!-- Legend -->
  <div id="legend">
    <strong>Severity</strong>
    <div><span class="dot" style="background:#10b981"></span>Low (1–3)</div>
    <div><span class="dot" style="background:#f59e0b"></span>Medium (4–6)</div>
    <div><span class="dot" style="background:#ef4444"></span>High (7–9)</div>
    <div><span class="dot" style="background:#b91c1c"></span>Critical (10)</div>
  </div>

  <!-- Controls -->
  <div id="controls">
    <div class="ctrl-row">
      <button class="ctrl-btn active" id="btn-layers" onclick="toggleLayerPanel()">🗂 Layers</button>
      <button class="ctrl-btn active" id="btn-rotate" onclick="toggleRotate()">↺ Rotate</button>
    </div>
    <div class="ctrl-row">
      <button class="ctrl-btn active" id="btn-arcs" onclick="toggleArcs()">☄ Arcs</button>
      <button class="ctrl-btn" id="btn-atmo" onclick="toggleAtmo()">🌍 Glow</button>
      <button class="ctrl-btn" id="btn-rings" onclick="toggleRings()">◎ Rings</button>
    </div>
  </div>

  <script src="https://unpkg.com/three@0.177.0/build/three.min.js"></script>
  <script src="https://unpkg.com/globe.gl@2/dist/globe.gl.min.js"></script>
  <script>
  const INITIAL   = {initial_data};
  const TEXTURES  = {textures_json};
  const BGROUNDS  = {backgrounds_json};
  const LAYERS    = {layers_json};
  let overlayData = {{}};

  const SEV_COLOR = s => ['#6b7280','#10b981','#10b981','#34d399','#fbbf24',
    '#f59e0b','#f59e0b','#ef4444','#ef4444','#dc2626','#b91c1c'][s] || '#6b7280';

  let evData     = [...INITIAL];
  let autoRotate = true;
  let showArcs   = true;
  let showAtmo   = false;
  let showRings  = false;
  let layerOpen  = false;
  let curTexture = 0;
  let curBg      = 0;

  // ── Build arc data from high-severity events ──────────────────────────
  function buildArcs(pts) {{
    const high = pts.filter(p => p.severity >= 7).slice(0, 40);
    if (high.length < 2) return [];
    return Array.from({{length: Math.min(high.length - 1, 20)}},
      (_, i) => ({{ src: high[i], dst: high[(i+1) % high.length] }}));
  }}

  // ── Build ring data for critical events ───────────────────────────────
  function buildRings(pts) {{
    return pts.filter(p => p.severity >= 9).slice(0, 20).map(p => ({{
      lat: p.lat, lng: p.lon,
      maxR: 3, propagationSpeed: 1.5, repeatPeriod: 1200,
    }}));
  }}

  // ── Initialise globe ──────────────────────────────────────────────────
  const globe = Globe()(document.getElementById('globe-container'))
    .globeImageUrl(TEXTURES[0].url)
    .bumpImageUrl('https://unpkg.com/three-globe/example/img/earth-topology.png')
    .backgroundImageUrl(BGROUNDS[0].url)
    .showAtmosphere(false)
    .atmosphereColor('rgba(0,180,255,0.18)')
    .atmosphereAltitude(0.18)
    .pointsData(evData)
    .pointLat('lat').pointLng('lon')
    .pointColor(d => SEV_COLOR(d.severity))
    .pointAltitude(d => Math.max(0.01, d.severity * 0.008))
    .pointRadius(d => Math.max(0.18, d.severity * 0.06))
    .pointResolution(8)
    .pointLabel(d =>
      `<div style="background:rgba(10,14,26,.92);border:1px solid rgba(255,255,255,.1);
       border-radius:8px;padding:8px 12px;max-width:260px;font:13px Inter,sans-serif;
       color:#e2e8f0;line-height:1.5">
       <b>${{d.title}}</b><br>
       <small style="color:#94a3b8">${{d.source}} · ${{d.country}} · Sev ${{d.severity}}</small>
       </div>`)
    .arcsData(buildArcs(evData))
    .arcStartLat(d => d.src.lat).arcStartLng(d => d.src.lon)
    .arcEndLat(d => d.dst.lat).arcEndLng(d => d.dst.lon)
    .arcColor(() => ['rgba(239,68,68,0.7)', 'rgba(185,28,28,0.05)'])
    .arcDashLength(0.4).arcDashGap(0.2).arcDashAnimateTime(2200)
    .arcAltitude(0.15)
    .ringsData([])
    .ringColor(() => t => `rgba(239,68,68,${{1-t}})`)
    .ringMaxRadius('maxR').ringPropagationSpeed('propagationSpeed')
    .ringRepeatPeriod('repeatPeriod')
    .htmlElementsData([])
    .htmlElement(d => {{
      const el = document.createElement('div');
      el.title = d.label;
      el.style.cssText = 'font-size:14px;cursor:pointer;user-select:none;line-height:1';
      el.textContent = d.icon;
      return el;
    }})
    .htmlLat('lat').htmlLng('lng')
    .width(window.innerWidth).height(window.innerHeight);

  const controls = globe.controls();
  controls.autoRotate = true;
  controls.autoRotateSpeed = 0.4;
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;

  // ── Update helpers ───────────────────────────────────────────────────
  function updateGlobe() {{
    globe.pointsData(evData);
    if (showArcs)  globe.arcsData(buildArcs(evData));
    if (showRings) globe.ringsData(buildRings(evData));
    document.getElementById('ev-count').textContent = evData.length + ' events live';
  }}
  updateGlobe();

  // ── Control toggles ──────────────────────────────────────────────────
  function toggleLayerPanel() {{
    layerOpen = !layerOpen;
    document.getElementById('layer-panel').classList.toggle('open', layerOpen);
    document.getElementById('btn-layers').classList.toggle('active', layerOpen);
  }}
  function toggleRotate() {{
    autoRotate = !autoRotate;
    controls.autoRotate = autoRotate;
    document.getElementById('btn-rotate').classList.toggle('active', autoRotate);
  }}
  function toggleArcs() {{
    showArcs = !showArcs;
    globe.arcsData(showArcs ? buildArcs(evData) : []);
    document.getElementById('btn-arcs').classList.toggle('active', showArcs);
  }}
  function toggleAtmo() {{
    showAtmo = !showAtmo;
    globe.showAtmosphere(showAtmo);
    document.getElementById('btn-atmo').classList.toggle('active', showAtmo);
  }}
  function toggleRings() {{
    showRings = !showRings;
    globe.ringsData(showRings ? buildRings(evData) : []);
    document.getElementById('btn-rings').classList.toggle('active', showRings);
  }}

  // ── Overlay layer functions ──────────────────────────────────────────
  function refreshOverlayHtml() {{
    const all = Object.values(overlayData).reduce(function(a, b) {{ return a.concat(b); }}, []);
    globe.htmlElementsData(all);
  }}
  async function loadGlobeOverlay(id, icon, color) {{
    try {{
      const res = await fetch('/api/layers/' + id);
      const gj  = await res.json();
      const pts = [];
      (gj.features || []).forEach(function(f) {{
        const g = f.geometry;
        if (!g || g.type !== 'Point') return;
        const p = f.properties || {{}};
        pts.push({{lat:g.coordinates[1], lng:g.coordinates[0],
          label:(p.name || p.title || p.callsign || id), icon:icon, color:color}});
      }});
      overlayData[id] = pts;
      refreshOverlayHtml();
    }} catch(e) {{ console.warn('Globe overlay load failed:', id, e); }}
  }}
  function removeGlobeOverlay(id) {{
    delete overlayData[id];
    refreshOverlayHtml();
  }}

  // ── Layer panel buttons ───────────────────────────────────────────────
  function setTexture(idx) {{
    curTexture = idx;
    globe.globeImageUrl(TEXTURES[idx].url);
    document.querySelectorAll('#texture-btns .layer-btn')
      .forEach((b, i) => b.classList.toggle('active', i === idx));
  }}
  function setBg(idx) {{
    curBg = idx;
    globe.backgroundImageUrl(BGROUNDS[idx].url || null);
    document.querySelectorAll('#bg-btns .layer-btn')
      .forEach((b, i) => b.classList.toggle('active', i === idx));
  }}

  TEXTURES.forEach((t, i) => {{
    const b = document.createElement('button');
    b.className = 'layer-btn' + (i === 0 ? ' active' : '');
    b.textContent = t.label;
    b.onclick = () => setTexture(i);
    document.getElementById('texture-btns').appendChild(b);
  }});
  BGROUNDS.forEach((t, i) => {{
    const b = document.createElement('button');
    b.className = 'layer-btn' + (i === 0 ? ' active' : '');
    b.textContent = t.label;
    b.onclick = () => setBg(i);
    document.getElementById('bg-btns').appendChild(b);
  }});

  // ── Overlay layer toggle buttons ─────────────────────────────────────
  const groups3d = [...new Set(LAYERS.map(l => l.group))];
  const activeOvl = {{}};
  const ovDiv = document.createElement('div');
  ovDiv.style.cssText = 'border-top:1px solid rgba(255,255,255,.08);margin-top:10px;padding-top:8px';
  const ovLbl = document.createElement('label');
  ovLbl.style.cssText = 'font-size:10px;color:#475569;text-transform:uppercase;letter-spacing:.06em;display:block;margin-bottom:6px';
  ovLbl.textContent = 'Overlay Layers';
  ovDiv.appendChild(ovLbl);
  groups3d.forEach(g => {{
    const gt = document.createElement('div');
    gt.style.cssText = 'font-size:9px;color:#334155;text-transform:uppercase;letter-spacing:.06em;margin:6px 0 3px;padding-top:5px;border-top:1px solid rgba(255,255,255,.04)';
    gt.textContent = g;
    ovDiv.appendChild(gt);
    LAYERS.filter(l => l.group === g).forEach(layer => {{
      const b = document.createElement('button');
      b.className = 'layer-btn';
      b.textContent = layer.icon + ' ' + layer.label;
      b.onclick = () => {{
        activeOvl[layer.id] = !activeOvl[layer.id];
        b.classList.toggle('active', !!activeOvl[layer.id]);
        activeOvl[layer.id]
          ? loadGlobeOverlay(layer.id, layer.icon, layer.color)
          : removeGlobeOverlay(layer.id);
      }};
      ovDiv.appendChild(b);
    }});
  }});
  document.getElementById('layer-panel').appendChild(ovDiv);

  window.addEventListener('resize', () =>
    globe.width(window.innerWidth).height(window.innerHeight));

  // ── WebSocket live updates ────────────────────────────────────────────
  function connectWs() {{
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(proto + '://' + location.host + '/ws');
    ws.onmessage = function(e) {{
      const msg = JSON.parse(e.data);
      if (msg.type === 'new_event') {{
        const ev = msg.event;
        if (ev.lat != null && ev.lon != null) {{
          evData.unshift({{lat:ev.lat,lon:ev.lon,title:ev.title,
            severity:ev.severity||0,source:ev.source_name||'',country:ev.country||''}});
          if (evData.length > 2000) evData.pop();
          updateGlobe();
        }}
      }}
      if (msg.type === 'ingest_complete') {{
        fetch('/api/events?limit=1000').then(r=>r.json()).then(json=>{{
          evData = json.events.filter(e=>e.lat!=null&&e.lon!=null)
            .map(e=>({{lat:e.lat,lon:e.lon,title:e.title,
              severity:e.severity||0,source:e.source_name||'',country:e.country||''}}));
          updateGlobe();
        }});
      }}
    }};
    ws.onclose = () => setTimeout(connectWs, 3000);
    setInterval(() => {{ if (ws.readyState===1) ws.send('ping'); }}, 25000);
  }}
  connectWs();
  </script>
</body>
</html>"""
