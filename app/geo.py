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

@dataclass(frozen=True)
class GeoMatch:
    lat: float
    lon: float
    city: str
    country: str


# Module-level lookup index built once at startup
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
    """Load cities1000.txt into an in-memory lookup dict."""
    path = settings.gazetteer_path
    if not os.path.exists(path):
        logger.warning("Gazetteer not found at {}; geo-resolution disabled", path)
        return

    with open(path, encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        for row in reader:
            if len(row) < 9:
                continue
            try:
                name = row[1].lower()          # asciiname
                alt_names = row[3].lower()     # alternatenames (comma-sep)
                lat = float(row[4])
                lon = float(row[5])
                country = row[8]               # ISO 3166-1 alpha-2
                city = row[1]                  # preserve case for display

                entry = GeoMatch(lat=lat, lon=lon, city=city, country=country)
                _city_index[name] = entry
                for alt in alt_names.split(","):
                    alt = alt.strip()
                    if alt and alt not in _city_index:
                        _city_index[alt] = entry
            except (ValueError, IndexError):
                continue

    logger.info("Geo index built: {} entries", len(_city_index))


def resolve(entity_text: str) -> GeoMatch | None:
    """Resolve a spaCy GPE/LOC entity to (lat, lon, city, country)."""
    if not _city_index:
        return None

    key = entity_text.lower().strip()
    if key in _city_index:
        return _city_index[key]

    match, score, _ = process.extractOne(
        key, _city_index.keys(), scorer=fuzz.WRatio, score_cutoff=80
    ) or (None, 0, None)

    if match:
        return _city_index[match]
    return None
