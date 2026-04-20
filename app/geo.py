"""Offline geocoding using GeoNames cities1000.txt gazetteer."""

import csv
import io
import os
import zipfile
from dataclasses import dataclass

import aiohttp
from loguru import logger
from rapidfuzz import process, fuzz

from app.config import settings

GEONAMES_URL = "https://download.geonames.org/export/dump/cities1000.zip"

# ISO 3166-1 alpha-2 → (lat, lon, display_name) for country-level entity resolution
COUNTRY_CENTROIDS: dict[str, tuple[float, float, str]] = {
    "AF": (33.939, 67.710, "Afghanistan"), "AL": (41.153, 20.168, "Albania"),
    "DZ": (28.034, 1.660, "Algeria"), "AO": (-11.203, 17.874, "Angola"),
    "AR": (-38.416, -63.617, "Argentina"), "AM": (40.069, 45.038, "Armenia"),
    "AU": (-25.274, 133.775, "Australia"), "AT": (47.516, 14.550, "Austria"),
    "AZ": (40.143, 47.577, "Azerbaijan"), "BD": (23.685, 90.356, "Bangladesh"),
    "BY": (53.710, 27.953, "Belarus"), "BE": (50.504, 4.470, "Belgium"),
    "BJ": (9.308, 2.316, "Benin"), "BO": (-16.290, -63.589, "Bolivia"),
    "BA": (43.916, 17.679, "Bosnia and Herzegovina"), "BR": (-14.235, -51.925, "Brazil"),
    "BG": (42.734, 25.486, "Bulgaria"), "BF": (12.365, -1.562, "Burkina Faso"),
    "MM": (21.914, 95.956, "Myanmar"), "BI": (-3.373, 29.919, "Burundi"),
    "CM": (7.370, 12.355, "Cameroon"), "CA": (56.130, -106.347, "Canada"),
    "CF": (6.611, 20.939, "Central African Republic"), "TD": (15.454, 18.732, "Chad"),
    "CL": (-35.675, -71.543, "Chile"), "CN": (35.862, 104.195, "China"),
    "CO": (4.571, -74.297, "Colombia"), "CD": (-4.038, 21.759, "DR Congo"),
    "CG": (-0.228, 15.828, "Congo"), "CR": (9.749, -83.753, "Costa Rica"),
    "HR": (45.100, 15.200, "Croatia"), "CU": (21.522, -77.781, "Cuba"),
    "CZ": (49.817, 15.473, "Czech Republic"), "DK": (56.264, 9.502, "Denmark"),
    "DJ": (11.825, 42.590, "Djibouti"), "DO": (18.736, -70.163, "Dominican Republic"),
    "EC": (-1.831, -78.183, "Ecuador"), "EG": (26.821, 30.802, "Egypt"),
    "SV": (13.794, -88.897, "El Salvador"), "ER": (15.179, 39.782, "Eritrea"),
    "EE": (58.595, 25.014, "Estonia"), "ET": (9.145, 40.490, "Ethiopia"),
    "FI": (61.924, 25.748, "Finland"), "FR": (46.228, 2.214, "France"),
    "GA": (-0.804, 11.609, "Gabon"), "GM": (13.443, -15.310, "Gambia"),
    "GE": (42.315, 43.357, "Georgia"), "DE": (51.166, 10.452, "Germany"),
    "GH": (7.947, -1.023, "Ghana"), "GR": (39.074, 21.824, "Greece"),
    "GT": (15.783, -90.231, "Guatemala"), "GN": (9.946, -9.697, "Guinea"),
    "GW": (11.804, -15.180, "Guinea-Bissau"), "HT": (18.971, -72.285, "Haiti"),
    "HN": (15.200, -86.242, "Honduras"), "HU": (47.162, 19.503, "Hungary"),
    "IN": (20.594, 78.963, "India"), "ID": (-0.789, 113.921, "Indonesia"),
    "IR": (32.428, 53.688, "Iran"), "IQ": (33.223, 43.679, "Iraq"),
    "IE": (53.413, -8.244, "Ireland"), "IL": (31.046, 34.852, "Israel"),
    "IT": (41.872, 12.567, "Italy"), "JM": (18.110, -77.298, "Jamaica"),
    "JP": (36.205, 138.253, "Japan"), "JO": (30.585, 36.238, "Jordan"),
    "KZ": (48.020, 66.924, "Kazakhstan"), "KE": (-0.024, 37.906, "Kenya"),
    "KP": (40.340, 127.510, "North Korea"), "KR": (35.908, 127.767, "South Korea"),
    "KW": (29.312, 47.482, "Kuwait"), "KG": (41.204, 74.766, "Kyrgyzstan"),
    "LA": (19.856, 102.495, "Laos"), "LV": (56.880, 24.603, "Latvia"),
    "LB": (33.855, 35.862, "Lebanon"), "LY": (26.335, 17.228, "Libya"),
    "LT": (55.169, 23.881, "Lithuania"), "MK": (41.609, 21.745, "North Macedonia"),
    "MG": (-18.767, 46.869, "Madagascar"), "MW": (-13.254, 34.302, "Malawi"),
    "MY": (4.210, 101.976, "Malaysia"), "ML": (17.571, -3.996, "Mali"),
    "MR": (21.008, -10.941, "Mauritania"), "MX": (23.635, -102.553, "Mexico"),
    "MD": (47.412, 28.370, "Moldova"), "MN": (46.862, 103.847, "Mongolia"),
    "ME": (42.709, 19.374, "Montenegro"), "MA": (31.792, -7.093, "Morocco"),
    "MZ": (-18.666, 35.530, "Mozambique"), "NA": (-22.958, 18.490, "Namibia"),
    "NP": (28.395, 84.124, "Nepal"), "NL": (52.133, 5.291, "Netherlands"),
    "NZ": (-40.901, 174.886, "New Zealand"), "NI": (12.865, -85.207, "Nicaragua"),
    "NE": (17.608, 8.082, "Niger"), "NG": (9.082, 8.675, "Nigeria"),
    "NO": (60.472, 8.469, "Norway"), "OM": (21.513, 55.923, "Oman"),
    "PK": (30.375, 69.345, "Pakistan"), "PS": (31.952, 35.233, "Palestine"),
    "PA": (8.538, -80.782, "Panama"), "PG": (-6.315, 143.956, "Papua New Guinea"),
    "PY": (-23.443, -58.444, "Paraguay"), "PE": (-9.190, -75.015, "Peru"),
    "PH": (12.880, 121.774, "Philippines"), "PL": (51.919, 19.145, "Poland"),
    "PT": (39.400, -8.224, "Portugal"), "QA": (25.355, 51.184, "Qatar"),
    "RO": (45.943, 24.967, "Romania"), "RU": (61.524, 105.319, "Russia"),
    "RW": (-1.940, 29.874, "Rwanda"), "SA": (23.886, 45.079, "Saudi Arabia"),
    "SN": (14.497, -14.452, "Senegal"), "RS": (44.017, 21.006, "Serbia"),
    "SL": (8.461, -11.780, "Sierra Leone"), "SO": (5.152, 46.200, "Somalia"),
    "ZA": (-30.559, 22.938, "South Africa"), "SS": (4.852, 31.571, "South Sudan"),
    "ES": (40.464, -3.749, "Spain"), "LK": (7.873, 80.772, "Sri Lanka"),
    "SD": (12.863, 30.218, "Sudan"), "SR": (3.919, -56.028, "Suriname"),
    "SE": (60.128, 18.644, "Sweden"), "CH": (46.818, 8.228, "Switzerland"),
    "SY": (34.802, 38.997, "Syria"), "TW": (23.698, 120.961, "Taiwan"),
    "TJ": (38.861, 71.276, "Tajikistan"), "TZ": (-6.369, 34.889, "Tanzania"),
    "TH": (15.870, 100.993, "Thailand"), "TL": (-8.874, 125.728, "Timor-Leste"),
    "TG": (8.620, 0.825, "Togo"), "TN": (33.887, 9.537, "Tunisia"),
    "TR": (38.964, 35.243, "Turkey"), "TM": (38.970, 59.556, "Turkmenistan"),
    "UG": (1.373, 32.290, "Uganda"), "UA": (48.379, 31.166, "Ukraine"),
    "AE": (23.424, 53.848, "UAE"), "GB": (55.378, -3.436, "United Kingdom"),
    "US": (37.090, -95.713, "United States"), "UY": (-32.523, -55.766, "Uruguay"),
    "UZ": (41.377, 64.585, "Uzbekistan"), "VE": (6.424, -66.590, "Venezuela"),
    "VN": (14.058, 108.277, "Vietnam"), "YE": (15.553, 48.516, "Yemen"),
    "ZM": (-13.134, 27.849, "Zambia"), "ZW": (-19.015, 29.155, "Zimbabwe"),
}

_COUNTRY_ALIASES: dict[str, str] = {
    "afghanistan": "AF", "albania": "AL", "algeria": "DZ", "angola": "AO",
    "argentina": "AR", "armenia": "AM", "australia": "AU", "austria": "AT",
    "azerbaijan": "AZ", "bangladesh": "BD", "belarus": "BY", "belgium": "BE",
    "benin": "BJ", "bolivia": "BO", "bosnia": "BA", "bosnia and herzegovina": "BA",
    "brazil": "BR", "brasil": "BR", "bulgaria": "BG", "burkina faso": "BF",
    "myanmar": "MM", "burma": "MM", "burundi": "BI", "cameroon": "CM",
    "canada": "CA", "central african republic": "CF", "car": "CF",
    "chad": "TD", "chile": "CL", "china": "CN", "prc": "CN",
    "colombia": "CO", "dr congo": "CD", "democratic republic of the congo": "CD",
    "democratic republic of congo": "CD", "drc": "CD", "congo": "CG",
    "costa rica": "CR", "croatia": "HR", "cuba": "CU",
    "czech republic": "CZ", "czechia": "CZ", "denmark": "DK",
    "djibouti": "DJ", "dominican republic": "DO", "ecuador": "EC",
    "egypt": "EG", "el salvador": "SV", "eritrea": "ER", "estonia": "EE",
    "ethiopia": "ET", "finland": "FI", "france": "FR", "gabon": "GA",
    "gambia": "GM", "georgia": "GE", "germany": "DE", "ghana": "GH",
    "greece": "GR", "guatemala": "GT", "guinea": "GN",
    "guinea-bissau": "GW", "haiti": "HT", "honduras": "HN", "hungary": "HU",
    "india": "IN", "indonesia": "ID", "iran": "IR", "iraq": "IQ",
    "ireland": "IE", "israel": "IL", "italy": "IT", "jamaica": "JM",
    "japan": "JP", "jordan": "JO", "kazakhstan": "KZ", "kenya": "KE",
    "north korea": "KP", "dprk": "KP", "south korea": "KR", "korea": "KR",
    "kuwait": "KW", "kyrgyzstan": "KG", "laos": "LA", "latvia": "LV",
    "lebanon": "LB", "libya": "LY", "lithuania": "LT",
    "north macedonia": "MK", "macedonia": "MK", "madagascar": "MG",
    "malawi": "MW", "malaysia": "MY", "mali": "ML", "mauritania": "MR",
    "mexico": "MX", "moldova": "MD", "mongolia": "MN", "montenegro": "ME",
    "morocco": "MA", "mozambique": "MZ", "namibia": "NA", "nepal": "NP",
    "netherlands": "NL", "holland": "NL", "new zealand": "NZ",
    "nicaragua": "NI", "niger": "NE", "nigeria": "NG", "norway": "NO",
    "oman": "OM", "pakistan": "PK", "palestine": "PS", "west bank": "PS",
    "gaza": "PS", "gaza strip": "PS", "panama": "PA",
    "papua new guinea": "PG", "png": "PG",
    "paraguay": "PY", "peru": "PE", "philippines": "PH", "poland": "PL",
    "portugal": "PT", "qatar": "QA", "romania": "RO", "russia": "RU",
    "russian federation": "RU", "rwanda": "RW", "saudi arabia": "SA",
    "senegal": "SN", "serbia": "RS", "sierra leone": "SL", "somalia": "SO",
    "south africa": "ZA", "south sudan": "SS", "spain": "ES",
    "sri lanka": "LK", "ceylon": "LK", "sudan": "SD", "suriname": "SR",
    "sweden": "SE", "switzerland": "CH", "syria": "SY", "taiwan": "TW",
    "tajikistan": "TJ", "tanzania": "TZ", "thailand": "TH",
    "timor-leste": "TL", "east timor": "TL", "togo": "TG", "tunisia": "TN",
    "turkey": "TR", "türkiye": "TR", "turkiye": "TR", "turkmenistan": "TM",
    "uganda": "UG", "ukraine": "UA", "uae": "AE",
    "united arab emirates": "AE", "united kingdom": "GB", "uk": "GB",
    "great britain": "GB", "britain": "GB", "england": "GB",
    "scotland": "GB", "wales": "GB", "northern ireland": "GB",
    "united states": "US", "usa": "US", "america": "US",
    "u.s.": "US", "u.s.a.": "US",
    "uruguay": "UY", "uzbekistan": "UZ", "venezuela": "VE", "vietnam": "VN",
    "viet nam": "VN", "yemen": "YE", "zambia": "ZM", "zimbabwe": "ZW",
}


@dataclass(frozen=True)
class GeoMatch:
    lat: float
    lon: float
    city: str
    country: str
    population: int = 0


_city_index: dict[str, GeoMatch] = {}


async def ensure_gazetteer() -> None:
    """Download cities1000.txt if not present (one-time, ~7MB)."""
    path = settings.gazetteer_path
    if os.path.exists(path):
        return

    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    logger.info("Downloading GeoNames cities1000 gazetteer...")
    async with aiohttp.ClientSession() as session:
        async with session.get(GEONAMES_URL) as resp:
            data = await resp.read()

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        with zf.open("cities1000.txt") as f:
            content = f.read()

    with open(path, "wb") as f:
        f.write(content)

    logger.info("Gazetteer saved to {}", path)


def build_index() -> None:
    """Load cities1000.txt into an in-memory lookup dict.

    Uses population-based tiebreaking: largest city wins for ambiguous names,
    so Paris (France, pop ~2M) beats Paris (Texas, pop ~26k).
    """
    path = settings.gazetteer_path
    if not os.path.exists(path):
        logger.warning("Gazetteer not found at {}; geo-resolution disabled", path)
        return

    # Collect all (name, entry) pairs then sort by population desc
    raw: list[tuple[str, GeoMatch]] = []

    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 15:
                continue
            try:
                name = row[1].lower()
                alt_names = row[3].lower()
                lat = float(row[4])
                lon = float(row[5])
                country = row[8]
                city = row[1]
                population = int(row[14]) if row[14] else 0

                entry = GeoMatch(lat=lat, lon=lon, city=city, country=country, population=population)
                raw.append((name, entry))
                for alt in alt_names.split(","):
                    alt = alt.strip()
                    if alt:
                        raw.append((alt, entry))
            except (ValueError, IndexError):
                continue

    # Sort descending by population so highest-pop city wins name conflicts
    raw.sort(key=lambda pair: pair[1].population, reverse=True)
    for name, entry in raw:
        if name not in _city_index:
            _city_index[name] = entry

    logger.info("Geo index built: {} entries", len(_city_index))


def resolve(entity_text: str) -> GeoMatch | None:
    """Resolve a spaCy GPE/LOC entity to a GeoMatch.

    Resolution order:
      1. Country alias (returns centroid for country-level entities)
      2. Exact city name match
      3. Fuzzy match with score >= 85 (higher cutoff reduces false positives)
    """
    if not _city_index:
        return None

    key = entity_text.lower().strip()

    iso = _COUNTRY_ALIASES.get(key)
    if iso and iso in COUNTRY_CENTROIDS:
        lat, lon, display = COUNTRY_CENTROIDS[iso]
        return GeoMatch(lat=lat, lon=lon, city=display, country=iso, population=0)

    if key in _city_index:
        return _city_index[key]

    result = process.extractOne(
        key, _city_index.keys(), scorer=fuzz.WRatio, score_cutoff=85
    )
    if result is not None:
        match, _score, _ = result
        return _city_index[match]

    return None
