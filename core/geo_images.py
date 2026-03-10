# ============================================================
#  core/geo_images.py
#  Google Maps API utilities — geocoding, Street View, satellite.
#
#  All functions return None (rather than raising) on failure,
#  so callers can display graceful fallbacks in the UI.
# ============================================================

from __future__ import annotations
import requests


_GEOCODE_URL     = "https://maps.googleapis.com/maps/api/geocode/json"
_STREETVIEW_META = "https://maps.googleapis.com/maps/api/streetview/metadata"
_STREETVIEW_URL  = "https://maps.googleapis.com/maps/api/streetview"
_STATICMAP_URL   = "https://maps.googleapis.com/maps/api/staticmap"


def geocode_address(address: str, api_key: str) -> tuple[float, float] | None:
    """
    Convert a free-text address to (lat, lon).
    Returns None if geocoding fails or key is missing.
    """
    if not api_key or not address:
        return None
    try:
        resp = requests.get(
            _GEOCODE_URL,
            params={"address": address, "key": api_key},
            timeout=10,
            verify=False,
        )
        data = resp.json()
        if data.get("status") != "OK":
            return None
        loc = data["results"][0]["geometry"]["location"]
        return float(loc["lat"]), float(loc["lng"])
    except Exception:
        return None


def get_streetview_image(
    lat: float,
    lon: float,
    api_key: str,
    size: str = "800x500",
    fov: int = 100,
    pitch: int = 10,
) -> bytes | None:
    """
    Fetch a Street View image for the given coordinates.
    Returns raw JPEG bytes, or None if no imagery is available.
    """
    if not api_key:
        return None
    try:
        # Check metadata first to confirm imagery exists
        meta = requests.get(
            _STREETVIEW_META,
            params={
                "location": f"{lat},{lon}",
                "source": "outdoor",
                "key": api_key,
            },
            timeout=10,
            verify=False,
        ).json()

        if meta.get("status") != "OK":
            return None

        pano_id = meta.get("pano_id")

        img_resp = requests.get(
            _STREETVIEW_URL,
            params={
                "size": size,
                "pano": pano_id,
                "location": f"{lat},{lon}",
                "fov": fov,
                "pitch": pitch,
                "key": api_key,
            },
            timeout=15,
            verify=False,
        )
        if img_resp.status_code == 200 and img_resp.content:
            return img_resp.content
        return None
    except Exception:
        return None


def get_satellite_image(
    lat: float,
    lon: float,
    api_key: str,
    zoom: int = 17,
    size: str = "800x500",
    scale: int = 2,
) -> bytes | None:
    """
    Fetch a satellite static map image centred on (lat, lon).
    Returns raw JPEG bytes, or None on failure.
    """
    if not api_key:
        return None
    try:
        resp = requests.get(
            _STATICMAP_URL,
            params={
                "center": f"{lat},{lon}",
                "zoom": zoom,
                "size": size,
                "maptype": "satellite",
                "key": api_key,
                "markers": f"color:red|size:mid|{lat},{lon}",
                "scale": scale,
            },
            timeout=15,
            verify=False,
        )
        if resp.status_code == 200 and resp.content:
            return resp.content
        return None
    except Exception:
        return None
