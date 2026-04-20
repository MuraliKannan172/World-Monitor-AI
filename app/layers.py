"""Layer registry and GeoJSON data fetchers for all map overlay layers."""
from __future__ import annotations

import aiohttp
from loguru import logger

# ── Layer registry ────────────────────────────────────────────────────────────

LAYER_DEFS: list[dict] = [
    # Crisis
    {"id": "iran_attacks",         "icon": "🎯", "label": "Iran Attacks",         "group": "Crisis",         "color": "#ef4444"},
    {"id": "intel_hotspots",       "icon": "🎯", "label": "Intel Hotspots",        "group": "Crisis",         "color": "#f97316"},
    {"id": "conflict_zones",       "icon": "⚔",  "label": "Conflict Zones",        "group": "Crisis",         "color": "#ef4444"},
    {"id": "protests",             "icon": "📢", "label": "Protests",              "group": "Crisis",         "color": "#f59e0b"},
    {"id": "armed_conflict",       "icon": "⚔",  "label": "Armed Conflict Events", "group": "Crisis",         "color": "#dc2626"},
    {"id": "displacement",         "icon": "👥", "label": "Displacement Flows",    "group": "Crisis",         "color": "#fb923c"},
    {"id": "disease",              "icon": "🦠", "label": "Disease Outbreaks",     "group": "Crisis",         "color": "#a855f7"},
    # Military
    {"id": "military_bases",       "icon": "🏛", "label": "Military Bases",        "group": "Military",       "color": "#64748b"},
    {"id": "nuclear_sites",        "icon": "☢",  "label": "Nuclear Sites",         "group": "Military",       "color": "#10b981"},
    {"id": "gamma_irradiators",    "icon": "⚠",  "label": "Gamma Irradiators",     "group": "Military",       "color": "#f59e0b"},
    {"id": "radiation_watch",      "icon": "☢",  "label": "Radiation Watch",       "group": "Military",       "color": "#22c55e"},
    {"id": "military_activity",    "icon": "✈",  "label": "Military Activity",     "group": "Military",       "color": "#6366f1"},
    # Infrastructure
    {"id": "undersea_cables",      "icon": "🔌", "label": "Undersea Cables",       "group": "Infrastructure", "color": "#06b6d4"},
    {"id": "pipelines",            "icon": "🛢",  "label": "Pipelines",             "group": "Infrastructure", "color": "#84cc16"},
    {"id": "ai_data_centers",      "icon": "🖥",  "label": "AI Data Centers",       "group": "Infrastructure", "color": "#8b5cf6"},
    {"id": "spaceports",           "icon": "🚀", "label": "Spaceports",            "group": "Infrastructure", "color": "#f0abfc"},
    {"id": "trade_routes",         "icon": "⚓", "label": "Trade Routes",          "group": "Infrastructure", "color": "#38bdf8"},
    {"id": "chokepoints",          "icon": "⚓", "label": "Chokepoints",           "group": "Infrastructure", "color": "#fb923c"},
    # Transport
    {"id": "ship_traffic",         "icon": "🚢", "label": "Ship Traffic",          "group": "Transport",      "color": "#0ea5e9"},
    {"id": "aviation",             "icon": "✈",  "label": "Aviation",              "group": "Transport",      "color": "#38bdf8"},
    # Environment
    {"id": "natural_events",       "icon": "🌋", "label": "Natural Events",        "group": "Environment",    "color": "#f97316"},
    {"id": "fires",                "icon": "🔥", "label": "Fires",                 "group": "Environment",    "color": "#ef4444"},
    {"id": "weather_alerts",       "icon": "⛈",  "label": "Weather Alerts",        "group": "Environment",    "color": "#fbbf24"},
    {"id": "climate_anomalies",    "icon": "🌫",  "label": "Climate Anomalies",     "group": "Environment",    "color": "#94a3b8"},
    # Intelligence
    {"id": "cyber_threats",        "icon": "🛡",  "label": "Cyber Threats",         "group": "Intelligence",   "color": "#00d4ff"},
    {"id": "gps_jamming",          "icon": "📡", "label": "GPS Jamming",           "group": "Intelligence",   "color": "#f59e0b"},
    {"id": "internet_disruptions", "icon": "📡", "label": "Internet Disruptions",  "group": "Intelligence",   "color": "#94a3b8"},
    {"id": "orbital_surveillance", "icon": "🛰",  "label": "Orbital Surveillance",  "group": "Intelligence",   "color": "#a78bfa"},
    # Economy
    {"id": "economic_centers",     "icon": "💰", "label": "Economic Centers",      "group": "Economy",        "color": "#34d399"},
    {"id": "critical_minerals",    "icon": "💎", "label": "Critical Minerals",     "group": "Economy",        "color": "#818cf8"},
    {"id": "sanctions",            "icon": "🚫", "label": "Sanctions",             "group": "Economy",        "color": "#f43f5e"},
    {"id": "cii_instability",      "icon": "🌎", "label": "CII Instability",       "group": "Economy",        "color": "#ef4444"},
    {"id": "resilience",           "icon": "📈", "label": "Resilience",            "group": "Economy",        "color": "#10b981"},
    # Other
    {"id": "day_night",            "icon": "🌓", "label": "Day/Night",             "group": "Other",          "color": "#475569"},
    {"id": "live_webcams",         "icon": "📷", "label": "Live Webcams",          "group": "Other",          "color": "#60a5fa"},
]


def _fc(features: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": features}


def _pt(lat: float, lon: float, props: dict) -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": props,
    }


def _static_pts(rows: list[dict]) -> dict:
    return _fc([_pt(r["lat"], r["lon"], {k: v for k, v in r.items() if k not in ("lat", "lon")}) for r in rows])


# ── Static curated data ───────────────────────────────────────────────────────

_NUCLEAR = [
    {"name": "Yongbyon Nuclear Complex",  "country": "North Korea", "type": "Research/Production", "lat": 39.770, "lon": 125.753},
    {"name": "Punggye-ri Test Site",      "country": "North Korea", "type": "Test Site",           "lat": 41.294, "lon": 129.082},
    {"name": "Natanz Enrichment Facility","country": "Iran",        "type": "Enrichment",          "lat": 33.724, "lon": 51.727},
    {"name": "Fordow (FFEP)",             "country": "Iran",        "type": "Enrichment",          "lat": 34.880, "lon": 50.574},
    {"name": "Bushehr NPP",               "country": "Iran",        "type": "Power Reactor",       "lat": 28.831, "lon": 50.913},
    {"name": "Arak IR-40 Reactor",        "country": "Iran",        "type": "Research Reactor",    "lat": 34.150, "lon": 49.210},
    {"name": "Negev Nuclear Research",    "country": "Israel",      "type": "Suspected",           "lat": 31.000, "lon": 35.152},
    {"name": "Khushab Reactor Complex",   "country": "Pakistan",    "type": "Production",          "lat": 32.070, "lon": 72.193},
    {"name": "Kahuta (Khan Research)",    "country": "Pakistan",    "type": "Enrichment",          "lat": 33.744, "lon": 73.419},
    {"name": "Chashma NPP",               "country": "Pakistan",    "type": "Power Reactor",       "lat": 32.453, "lon": 71.452},
    {"name": "Tarapur Atomic Station",    "country": "India",       "type": "Power Reactor",       "lat": 19.843, "lon": 72.715},
    {"name": "Kudankulam NPP",            "country": "India",       "type": "Power Reactor",       "lat": 8.171,  "lon": 77.720},
    {"name": "Seversk (Tomsk-7)",         "country": "Russia",      "type": "Production",          "lat": 56.603, "lon": 84.873},
    {"name": "Ozersk / Mayak",            "country": "Russia",      "type": "Reprocessing",        "lat": 55.755, "lon": 60.731},
    {"name": "Sarov (Arzamas-16)",        "country": "Russia",      "type": "Weapons Design",      "lat": 54.934, "lon": 43.315},
    {"name": "Jiuquan Atomic Energy",     "country": "China",       "type": "Production",          "lat": 39.739, "lon": 98.288},
    {"name": "Fuqing NPP",                "country": "China",       "type": "Power Reactor",       "lat": 25.425, "lon": 119.652},
    {"name": "Oak Ridge National Lab",    "country": "USA",         "type": "Research",            "lat": 35.930, "lon": -84.308},
    {"name": "Hanford Site",              "country": "USA",         "type": "Cleanup/Former",      "lat": 46.549, "lon": -119.605},
    {"name": "Savannah River Site",       "country": "USA",         "type": "Production",          "lat": 33.348, "lon": -81.723},
    {"name": "Tricastin NPP",             "country": "France",      "type": "Power Reactor",       "lat": 44.332, "lon": 4.732},
    {"name": "Sellafield",                "country": "UK",          "type": "Reprocessing",        "lat": 54.421, "lon": -3.497},
    {"name": "Fukushima Daiichi",         "country": "Japan",       "type": "Decommissioned",      "lat": 37.421, "lon": 141.033},
    {"name": "Rokkasho Reprocessing",     "country": "Japan",       "type": "Reprocessing",        "lat": 40.978, "lon": 141.328},
]

_MILITARY_BASES = [
    {"name": "Ramstein Air Base",       "country": "USA",          "type": "Air Base",          "lat": 49.437, "lon": 7.600},
    {"name": "USAG Wiesbaden",          "country": "USA",          "type": "Army",              "lat": 50.058, "lon": 8.251},
    {"name": "Yokosuka Naval Base",     "country": "USA",          "type": "Naval",             "lat": 35.282, "lon": 139.672},
    {"name": "Camp Humphreys",          "country": "USA",          "type": "Army",              "lat": 36.963, "lon": 127.031},
    {"name": "Kadena Air Base",         "country": "USA",          "type": "Air Base",          "lat": 26.355, "lon": 127.768},
    {"name": "Diego Garcia",            "country": "USA",          "type": "Naval",             "lat": -7.320, "lon": 72.423},
    {"name": "Al Udeid Air Base",       "country": "USA",          "type": "Air Base",          "lat": 25.117, "lon": 51.315},
    {"name": "Incirlik Air Base",       "country": "USA/NATO",     "type": "Air Base",          "lat": 37.002, "lon": 35.426},
    {"name": "Guam (Andersen AFB)",     "country": "USA",          "type": "Air Base",          "lat": 13.584, "lon": 144.929},
    {"name": "Camp Lemonnier (USA)",    "country": "USA",          "type": "Joint",             "lat": 11.547, "lon": 43.158},
    {"name": "Tartus Naval Base",       "country": "Russia",       "type": "Naval",             "lat": 34.923, "lon": 35.883},
    {"name": "Hmeimim Air Base",        "country": "Russia",       "type": "Air Base",          "lat": 35.401, "lon": 35.948},
    {"name": "Sevastopol Fleet HQ",     "country": "Russia",       "type": "Naval",             "lat": 44.624, "lon": 33.535},
    {"name": "PLA Djibouti Base",       "country": "China",        "type": "Naval",             "lat": 11.573, "lon": 43.148},
    {"name": "Woody Island (Paracel)",  "country": "China",        "type": "Air Base",          "lat": 16.835, "lon": 112.340},
    {"name": "Fiery Cross Reef",        "country": "China",        "type": "Artificial Island", "lat": 9.550,  "lon": 112.893},
    {"name": "RAF Akrotiri",            "country": "UK",           "type": "Air Base",          "lat": 34.590, "lon": 32.987},
    {"name": "Abu Dhabi (France)",      "country": "France",       "type": "Air Base",          "lat": 24.402, "lon": 54.476},
    {"name": "Faslane (HMNB Clyde)",    "country": "UK",           "type": "Submarine Base",    "lat": 56.073, "lon": -4.822},
]

_CHOKEPOINTS = [
    {"name": "Strait of Hormuz",    "note": "30% global oil transit",  "lat": 26.563, "lon": 56.261},
    {"name": "Strait of Malacca",   "note": "25% global trade",        "lat": 1.273,  "lon": 103.808},
    {"name": "Bab-el-Mandeb",       "note": "Red Sea gateway",         "lat": 12.600, "lon": 43.450},
    {"name": "Suez Canal",          "note": "12% global trade",        "lat": 30.582, "lon": 32.356},
    {"name": "Panama Canal",        "note": "5% global trade",         "lat": 8.972,  "lon": -79.583},
    {"name": "Bosphorus Strait",    "note": "Black Sea access",        "lat": 41.120, "lon": 29.080},
    {"name": "Strait of Gibraltar", "note": "Mediterranean gateway",   "lat": 35.992, "lon": -5.370},
    {"name": "Lombok Strait",       "note": "Pacific-Indian route",    "lat": -8.730, "lon": 115.830},
    {"name": "Sunda Strait",        "note": "Malacca alternative",     "lat": -6.040, "lon": 105.740},
    {"name": "Taiwan Strait",       "note": "East Asia shipping",      "lat": 24.650, "lon": 120.060},
    {"name": "Luzon Strait",        "note": "Pacific access",          "lat": 20.400, "lon": 120.700},
    {"name": "Dover Strait",        "note": "Busiest shipping lane",   "lat": 51.020, "lon": 1.450},
    {"name": "GIUK Gap",            "note": "NATO strategic ASW",      "lat": 60.000, "lon": -25.000},
    {"name": "Cape of Good Hope",   "note": "Africa circumnavigation", "lat": -34.357, "lon": 18.476},
]

_SPACEPORTS = [
    {"name": "Baikonur Cosmodrome",    "country": "Kazakhstan",    "operator": "Russia",        "lat": 45.920, "lon": 63.342},
    {"name": "Kennedy Space Center",   "country": "USA",           "operator": "NASA/SpaceX",   "lat": 28.573, "lon": -80.648},
    {"name": "Cape Canaveral SFS",     "country": "USA",           "operator": "USSF/SpaceX",   "lat": 28.488, "lon": -80.577},
    {"name": "Vandenberg SFB",         "country": "USA",           "operator": "USSF/SpaceX",   "lat": 34.740, "lon": -120.574},
    {"name": "Guiana Space Centre",    "country": "French Guiana", "operator": "ESA/Arianespace","lat": 5.239,  "lon": -52.769},
    {"name": "Jiuquan Satellite LC",   "country": "China",         "operator": "CNSA",           "lat": 40.960, "lon": 100.291},
    {"name": "Xichang Satellite LC",   "country": "China",         "operator": "CNSA",           "lat": 28.246, "lon": 102.026},
    {"name": "Wenchang Space LC",      "country": "China",         "operator": "CNSA",           "lat": 19.614, "lon": 110.961},
    {"name": "Satish Dhawan SC",       "country": "India",         "operator": "ISRO",           "lat": 13.733, "lon": 80.235},
    {"name": "Tanegashima SC",         "country": "Japan",         "operator": "JAXA",           "lat": 30.400, "lon": 130.968},
    {"name": "Plesetsk Cosmodrome",    "country": "Russia",        "operator": "MoD Russia",     "lat": 62.927, "lon": 40.577},
    {"name": "Vostochny Cosmodrome",   "country": "Russia",        "operator": "Roscosmos",      "lat": 51.884, "lon": 128.334},
    {"name": "Mahia Launch Complex",   "country": "New Zealand",   "operator": "Rocket Lab",     "lat": -39.259, "lon": 177.864},
    {"name": "Wallops Flight Facility","country": "USA",           "operator": "NASA/Northrop",  "lat": 37.940, "lon": -75.466},
    {"name": "Palmachim Air Base",     "country": "Israel",        "operator": "IAF/IAI",        "lat": 31.896, "lon": 34.689},
    {"name": "Naro Space Centre",      "country": "South Korea",   "operator": "KARI",           "lat": 34.432, "lon": 127.535},
    {"name": "Alcântara LC",           "country": "Brazil",        "operator": "AEB",            "lat": -2.372, "lon": -44.396},
]

_AI_CENTERS = [
    {"name": "Microsoft Azure East US",   "operator": "Microsoft", "type": "Hyperscale", "lat": 38.793, "lon": -77.526},
    {"name": "Microsoft Azure West EU",   "operator": "Microsoft", "type": "Hyperscale", "lat": 52.370, "lon": 4.895},
    {"name": "Microsoft Azure East Asia", "operator": "Microsoft", "type": "Hyperscale", "lat": 22.319, "lon": 114.169},
    {"name": "AWS us-east-1 N. Virginia", "operator": "Amazon",    "type": "Hyperscale", "lat": 38.860, "lon": -77.428},
    {"name": "AWS eu-west-1 Ireland",     "operator": "Amazon",    "type": "Hyperscale", "lat": 53.339, "lon": -6.257},
    {"name": "AWS ap-southeast-1",        "operator": "Amazon",    "type": "Hyperscale", "lat": 1.352,  "lon": 103.820},
    {"name": "Google Council Bluffs",     "operator": "Google",    "type": "Hyperscale", "lat": 41.263, "lon": -95.885},
    {"name": "Google The Dalles",         "operator": "Google",    "type": "Hyperscale", "lat": 45.601, "lon": -121.185},
    {"name": "Google Hamina Finland",     "operator": "Google",    "type": "Hyperscale", "lat": 60.568, "lon": 27.188},
    {"name": "Meta Prineville Oregon",    "operator": "Meta",      "type": "Hyperscale", "lat": 44.303, "lon": -120.851},
    {"name": "Meta Forest City Iowa",     "operator": "Meta",      "type": "Hyperscale", "lat": 43.302, "lon": -93.624},
    {"name": "Meta Odense Denmark",       "operator": "Meta",      "type": "Hyperscale", "lat": 55.404, "lon": 10.403},
    {"name": "Alibaba Cloud Hangzhou",    "operator": "Alibaba",   "type": "Hyperscale", "lat": 30.274, "lon": 120.155},
    {"name": "Baidu AI Cloud Beijing",    "operator": "Baidu",     "type": "AI-Compute", "lat": 39.914, "lon": 116.394},
    {"name": "DeepMind London",           "operator": "Google",    "type": "AI-Research","lat": 51.536, "lon": -0.122},
    {"name": "OpenAI HQ San Francisco",   "operator": "OpenAI",    "type": "AI-Research","lat": 37.782, "lon": -122.391},
    {"name": "Anthropic San Francisco",   "operator": "Anthropic", "type": "AI-Research","lat": 37.773, "lon": -122.418},
]

_ECONOMIC_CENTERS = [
    {"name": "New York (NYSE/NASDAQ)",  "type": "Financial Hub",  "lat": 40.712, "lon": -74.006},
    {"name": "London (LSE/BoE)",        "type": "Financial Hub",  "lat": 51.507, "lon": -0.127},
    {"name": "Tokyo (TSE/BoJ)",         "type": "Financial Hub",  "lat": 35.689, "lon": 139.692},
    {"name": "Shanghai (SSE)",          "type": "Financial Hub",  "lat": 31.224, "lon": 121.469},
    {"name": "Hong Kong (HKEX)",        "type": "Financial Hub",  "lat": 22.319, "lon": 114.169},
    {"name": "Singapore (SGX)",         "type": "Financial Hub",  "lat": 1.352,  "lon": 103.820},
    {"name": "Frankfurt (DAX/ECB)",     "type": "Financial Hub",  "lat": 50.111, "lon": 8.682},
    {"name": "Dubai (DIFC)",            "type": "Financial Hub",  "lat": 25.204, "lon": 55.270},
    {"name": "Riyadh (Saudi Aramco)",   "type": "Energy/Oil",     "lat": 24.688, "lon": 46.722},
    {"name": "Houston (Energy Capital)","type": "Energy/Oil",     "lat": 29.760, "lon": -95.369},
    {"name": "Rotterdam Port",          "type": "Trade Hub",      "lat": 51.924, "lon": 4.479},
    {"name": "Shanghai Port",           "type": "Trade Hub",      "lat": 31.229, "lon": 121.562},
]

_CRITICAL_MINERALS = [
    {"name": "DRC Cobalt Belt",     "mineral": "Cobalt/Copper",   "country": "DRC",       "lat": -10.800, "lon": 26.200},
    {"name": "Atacama Lithium",     "mineral": "Lithium",         "country": "Chile",     "lat": -23.490, "lon": -67.900},
    {"name": "Pilbara Region",      "mineral": "Iron/Lithium",    "country": "Australia", "lat": -21.980, "lon": 120.030},
    {"name": "South Africa PGM",    "mineral": "Platinum Group",  "country": "S. Africa", "lat": -25.700, "lon": 27.100},
    {"name": "Baotou Rare Earths",  "mineral": "Rare Earths",     "country": "China",     "lat": 40.660, "lon": 109.850},
    {"name": "Nevada Lithium",      "mineral": "Lithium",         "country": "USA",       "lat": 40.370, "lon": -118.150},
    {"name": "Kazakhstan Uranium",  "mineral": "Uranium",         "country": "Kazakhstan","lat": 48.100, "lon": 70.200},
    {"name": "Indonesia Nickel",    "mineral": "Nickel",          "country": "Indonesia", "lat": -2.500, "lon": 122.000},
    {"name": "Guinea Bauxite",      "mineral": "Bauxite/Aluminium","country": "Guinea",   "lat": 11.000, "lon": -12.000},
    {"name": "Bolivia Lithium",     "mineral": "Lithium",         "country": "Bolivia",   "lat": -21.400, "lon": -68.400},
    {"name": "DR Congo Coltan",     "mineral": "Coltan/Tantalum", "country": "DRC",       "lat": -3.000, "lon": 28.000},
    {"name": "Greenland Minerals",  "mineral": "Rare Earths",     "country": "Greenland", "lat": 67.000, "lon": -45.000},
]

_TRADE_ROUTE_LINES = [
    {"name": "Asia-Europe (Suez)", "coords": [
        [121.5, 31.2], [119.0, 25.0], [115.0, 5.0], [100.0, 2.0],
        [80.0, 15.0], [52.0, 11.5], [43.5, 13.0], [32.0, 30.5],
        [20.0, 33.0], [5.0, 36.0], [-5.0, 36.0], [4.5, 52.0]]},
    {"name": "Trans-Pacific", "coords": [
        [121.5, 31.2], [155.0, 35.0], [180.0, 40.0], [-155.0, 35.0], [-118.2, 33.7]]},
    {"name": "Transatlantic", "coords": [
        [-74.0, 40.7], [-60.0, 43.0], [-40.0, 45.0], [-20.0, 48.0], [-0.1, 51.5]]},
    {"name": "Cape of Good Hope Route", "coords": [
        [115.0, 5.0], [80.0, -10.0], [55.0, -25.0], [30.0, -35.0],
        [18.5, -34.4], [10.0, -20.0], [-10.0, 5.0], [-40.0, 20.0], [-60.0, 30.0]]},
    {"name": "Indian Ocean (East Africa-Asia)", "coords": [
        [39.0, -4.0], [55.0, 10.0], [70.0, 15.0], [80.0, 12.0], [103.8, 1.3]]},
]


# ── Live data fetchers ────────────────────────────────────────────────────────

async def _fetch_natural_events() -> dict:
    """USGS M2.5+ earthquakes last 24h — free, no key."""
    url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_day.geojson"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                return await r.json(content_type=None)
    except Exception as exc:
        logger.warning(f"USGS fetch failed: {exc}")
        return _fc([])


async def _fetch_aviation() -> dict:
    """OpenSky Network live aircraft — free, no key."""
    url = "https://opensky-network.org/api/states/all"
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=15)) as r:
                data = await r.json(content_type=None)
        features = []
        for st in (data.get("states") or [])[:800]:
            if st[5] is None or st[6] is None:
                continue
            features.append(_pt(st[6], st[5], {
                "callsign": (st[1] or "").strip(),
                "country": st[2],
                "altitude_m": st[7],
                "velocity_ms": st[9],
                "heading": st[10],
                "on_ground": st[8],
            }))
        return _fc(features)
    except Exception as exc:
        logger.warning(f"OpenSky fetch failed: {exc}")
        return _fc([])


async def _fetch_fires() -> dict:
    """NASA FIRMS VIIRS active fires 24h — free, no key for CSV endpoint."""
    url = ("https://firms.modaps.eosdis.nasa.gov/data/active_fire/"
           "noaa-20-viirs-c2/text/J1_VIIRS_C2_Global_24h.txt")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
                text = await r.text()
        lines = text.strip().splitlines()
        if len(lines) < 2:
            return _fc([])
        headers = lines[0].split(",")
        lat_i, lon_i = headers.index("latitude"), headers.index("longitude")
        frp_i = headers.index("frp") if "frp" in headers else None
        features = []
        for row in lines[1:1001]:
            parts = row.split(",")
            try:
                lat, lon = float(parts[lat_i]), float(parts[lon_i])
                frp = float(parts[frp_i]) if frp_i is not None else 1.0
                features.append(_pt(lat, lon, {"frp": round(frp, 1), "type": "fire"}))
            except (ValueError, IndexError):
                continue
        return _fc(features)
    except Exception as exc:
        logger.warning(f"NASA FIRMS fetch failed: {exc}")
        return _fc([])


async def _fetch_weather_alerts() -> dict:
    """NOAA NWS active alerts — free, no key (US-focused)."""
    url = "https://api.weather.gov/alerts/active?status=actual&urgency=Immediate,Expected"
    try:
        async with aiohttp.ClientSession(headers={"User-Agent": "WorldMonitorAI/1.0"}) as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                return await r.json(content_type=None)
    except Exception as exc:
        logger.warning(f"NWS alerts fetch failed: {exc}")
        return _fc([])


async def _fetch_undersea_cables() -> dict:
    """TeleGeography submarine cable map — free public GitHub."""
    url = ("https://raw.githubusercontent.com/telegeography/www.submarinecablemap.com"
           "/master/data/cable/cable-geo.json")
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=20)) as r:
                return await r.json(content_type=None)
    except Exception as exc:
        logger.warning(f"Cable map fetch failed: {exc}")
        return _fc([])


async def _fetch_conflict_data(categories: list[str]) -> dict:
    """Pull conflict/protest/displacement events from the local DB."""
    from app import db as database
    events = await database.fetch_events(categories=categories, limit=300)
    features = [
        _pt(ev["lat"], ev["lon"], {
            "title": ev["title"],
            "severity": ev["severity"] or 0,
            "source": ev.get("source_name", ""),
            "date": (ev.get("published_at") or "")[:10],
        })
        for ev in events
        if ev["lat"] is not None and ev["lon"] is not None
    ]
    return _fc(features)


def _trade_routes_geojson() -> dict:
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": r["coords"]},
            "properties": {"name": r["name"]},
        }
        for r in _TRADE_ROUTE_LINES
    ]
    return _fc(features)


# ── Dispatcher ────────────────────────────────────────────────────────────────

async def fetch_layer(layer_id: str) -> dict:
    match layer_id:
        case "natural_events":
            return await _fetch_natural_events()
        case "aviation" | "military_activity":
            return await _fetch_aviation()
        case "fires":
            return await _fetch_fires()
        case "weather_alerts":
            return await _fetch_weather_alerts()
        case "undersea_cables":
            return await _fetch_undersea_cables()
        case "conflict_zones" | "armed_conflict" | "iran_attacks" | "intel_hotspots":
            return await _fetch_conflict_data(["conflict"])
        case "protests" | "displacement":
            return await _fetch_conflict_data(["conflict", "world"])
        case "nuclear_sites" | "gamma_irradiators" | "radiation_watch":
            return _static_pts(_NUCLEAR)
        case "military_bases":
            return _static_pts(_MILITARY_BASES)
        case "chokepoints":
            return _static_pts(_CHOKEPOINTS)
        case "spaceports":
            return _static_pts(_SPACEPORTS)
        case "ai_data_centers":
            return _static_pts(_AI_CENTERS)
        case "economic_centers":
            return _static_pts(_ECONOMIC_CENTERS)
        case "critical_minerals":
            return _static_pts(_CRITICAL_MINERALS)
        case "trade_routes":
            return _trade_routes_geojson()
        case _:
            return _fc([])
