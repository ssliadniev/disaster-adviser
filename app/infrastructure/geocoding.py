import httpx
import logging
from typing import TypedDict

from app.core.config import settings
from app.utils.functional import compose

logger = logging.getLogger(__name__)


class Coordinates(TypedDict):
    latitude: float
    longitude: float


def _is_valid_location_name(location_name: str) -> bool:
    return bool(location_name and location_name.strip())


def _extract_first_feature(data: dict) -> dict | None:
    features = data.get("features", [])
    return features[0] if features else None


def _extract_coordinates(feature: dict | None) -> list | None:
    if not feature:
        return None
    return feature.get("geometry", {}).get("coordinates")


def _build_coordinates(coords: list | None) -> Coordinates | None:
    if not coords or len(coords) < 2:
        return None
    try:
        return Coordinates(latitude=coords[1], longitude=coords[0])
    except (KeyError, TypeError, IndexError):
        return None


def _parse_geoapify_response(data: dict) -> Coordinates | None:
    return compose(
        _extract_first_feature,
        _extract_coordinates,
        _build_coordinates,
    )(data)


def _build_geocoding_params(location_name: str, api_key: str) -> dict:
    return {"text": location_name, "apiKey": api_key}


async def _fetch_geocoding_data(location_name: str, api_key: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.geoapify.com/v1/geocode/search",
            params=_build_geocoding_params(location_name, api_key),
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


def _log_result(
    location_name: str, coordinates: Coordinates | None
) -> Coordinates | None:
    if coordinates:
        logger.info(
            f"Geocoded '{location_name}' successfully: lat={coordinates['latitude']}, lon={coordinates['longitude']}"
        )
    else:
        logger.info(f"Failed to geocode '{location_name}' - no results found")
    return coordinates


def _log_error(location_name: str, exc: Exception) -> None:
    logger.error(f"Error geocoding '{location_name}': {type(exc).__name__}: {str(exc)}")


async def geocode_location(location_name: str) -> Coordinates | None:
    """Geocode a location using Geoapify API.

    Returns latitude and longitude coordinates for the given location name.
    Returns None if geocoding fails or API key is not configured.
    """
    if not _is_valid_location_name(location_name):
        return None

    api_key = settings.GEOAPIFY_API_KEY
    if not api_key:
        logger.info(f"Skipping geocoding for '{location_name}' - no API key configured")
        return None

    try:
        data = await _fetch_geocoding_data(location_name, api_key)
        coordinates = _parse_geoapify_response(data)
        return _log_result(location_name, coordinates)

    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        _log_error(location_name, exc)
        return None
