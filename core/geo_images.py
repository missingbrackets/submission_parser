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


def diagnose_google_apis(api_key: str, lat: float = 51.5145, lon: float = -0.0814) -> dict:
    """
    Test each Google Maps API endpoint and return a status dict.
    Used by the UI to surface misconfiguration to the user.
    Returns: {"geocoding": "OK"|error, "streetview_meta": "OK"|error, "static_maps": "OK"|error}
    """
    results = {}

    # 1. Geocoding
    try:
        r = requests.get(
            _GEOCODE_URL,
            params={"address": "London, UK", "key": api_key},
            timeout=10, verify=False,
        ).json()
        results["geocoding"] = r.get("status", "UNKNOWN")
        if "error_message" in r:
            results["geocoding"] += f": {r['error_message']}"
    except Exception as e:
        results["geocoding"] = f"EXCEPTION: {e}"

    # 2. Street View metadata
    try:
        r = requests.get(
            _STREETVIEW_META,
            params={"location": f"{lat},{lon}", "key": api_key},
            timeout=10, verify=False,
        ).json()
        results["streetview_meta"] = r.get("status", "UNKNOWN")
        if "error_message" in r:
            results["streetview_meta"] += f": {r['error_message']}"
    except Exception as e:
        results["streetview_meta"] = f"EXCEPTION: {e}"

    # 3. Static Maps (satellite) — a tiny 64x64 tile to keep it cheap
    try:
        r = requests.get(
            _STATICMAP_URL,
            params={
                "center": f"{lat},{lon}", "zoom": "15",
                "size": "64x64", "maptype": "satellite", "key": api_key,
            },
            timeout=10, verify=False,
        )
        ct = r.headers.get("Content-Type", "")
        if r.status_code == 200 and ct.startswith("image/"):
            results["static_maps"] = "OK"
        else:
            results["static_maps"] = f"HTTP {r.status_code} / Content-Type: {ct}"
            try:
                err = r.json()
                results["static_maps"] += f" / {err.get('error_message', '')}"
            except Exception:
                pass
    except Exception as e:
        results["static_maps"] = f"EXCEPTION: {e}"

    return results


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
        # Check metadata first to confirm imagery exists.
        # Try outdoor-only first; fall back to any source if no outdoor panorama found.
        meta = requests.get(
            _STREETVIEW_META,
            params={
                "location": f"{lat},{lon}",
                "radius": 50,
                "source": "outdoor",
                "key": api_key,
            },
            timeout=10,
            verify=False,
        ).json()

        if meta.get("status") != "OK":
            # Retry without source restriction (catches indoor / photo-sphere)
            meta = requests.get(
                _STREETVIEW_META,
                params={
                    "location": f"{lat},{lon}",
                    "radius": 100,
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
