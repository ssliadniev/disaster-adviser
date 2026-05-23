from datetime import UTC, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DisasterSource(str, Enum):
    NASA = "NASA"
    PDC = "PDC"


class DisasterCategory(str, Enum):
    EARTHQUAKE = "earthquake"
    HURRICANE = "hurricane"
    TROPICAL_CYCLONE = "tropical_cyclone"
    FLOOD = "flood"
    WILDFIRE = "wildfire"
    TORNADO = "tornado"
    TSUNAMI = "tsunami"
    VOLCANIC_ERUPTION = "volcanic_eruption"
    SEVERE_STORM = "severe_storm"
    DROUGHT = "drought"
    LANDSLIDE = "landslide"
    AVALANCHE = "avalanche"
    EXTREME_TEMPERATURE = "extreme_temperature"
    WINTER_STORM = "winter_storm"
    DUST_STORM = "dust_storm"
    UNKNOWN = "unknown"

    @classmethod
    def from_string(cls, category_str: str) -> "DisasterCategory":
        def normalize(s: str) -> str:
            return s.lower().strip().replace(" ", "_").replace("-", "_")

        def try_parse(s: str) -> "DisasterCategory | None":
            try:
                return cls(s)
            except ValueError:
                return None

        category_map = {
            "earthquakes": cls.EARTHQUAKE,
            "seismic": cls.EARTHQUAKE,
            "quake": cls.EARTHQUAKE,
            "hurricanes": cls.HURRICANE,
            "cyclone": cls.TROPICAL_CYCLONE,
            "typhoon": cls.TROPICAL_CYCLONE,
            "tropical_storm": cls.HURRICANE,
            "floods": cls.FLOOD,
            "flooding": cls.FLOOD,
            "flash_flood": cls.FLOOD,
            "wildfires": cls.WILDFIRE,
            "forest_fire": cls.WILDFIRE,
            "fire": cls.WILDFIRE,
            "fires": cls.WILDFIRE,
            "tornadoes": cls.TORNADO,
            "tsunamis": cls.TSUNAMI,
            "volcano": cls.VOLCANIC_ERUPTION,
            "volcanoes": cls.VOLCANIC_ERUPTION,
            "volcanic_activity": cls.VOLCANIC_ERUPTION,
            "storm": cls.SEVERE_STORM,
            "storms": cls.SEVERE_STORM,
            "severe_storm": cls.SEVERE_STORM,
            "severe_storms": cls.SEVERE_STORM,
            "severe_weather": cls.SEVERE_STORM,
            "droughts": cls.DROUGHT,
            "landslides": cls.LANDSLIDE,
            "mudslide": cls.LANDSLIDE,
            "avalanches": cls.AVALANCHE,
            "snow_avalanche": cls.AVALANCHE,
            "heat_wave": cls.EXTREME_TEMPERATURE,
            "cold_wave": cls.EXTREME_TEMPERATURE,
            "extreme_heat": cls.EXTREME_TEMPERATURE,
            "extreme_cold": cls.EXTREME_TEMPERATURE,
            "blizzard": cls.WINTER_STORM,
            "ice_storm": cls.WINTER_STORM,
            "snow_storm": cls.WINTER_STORM,
            "sandstorm": cls.DUST_STORM,
            "dust": cls.DUST_STORM,
        }

        return (
            cls.UNKNOWN
            if not category_str
            else try_parse(normalized := normalize(category_str))
            or category_map.get(normalized, cls.UNKNOWN)
        )

    @classmethod
    def get_all_values(cls) -> list[str]:
        """Get list of all disaster category values (excluding UNKNOWN)"""
        return [cat.value for cat in cls if cat != cls.UNKNOWN]


class StandardDisasterEvent(BaseModel):
    """
    Immutable contract representing a normalized disaster event.
    """

    model_config = ConfigDict(frozen=True)

    id: str = Field(..., description="Unique identifier from the source API")
    title: str
    category: DisasterCategory
    latitude: float
    longitude: float
    date: datetime
    source: DisasterSource
    closed: datetime | None = None

    @field_validator("category", mode="before")
    @classmethod
    def _normalize_category(cls, value: DisasterCategory | str) -> DisasterCategory:
        if isinstance(value, DisasterCategory):
            return value
        return DisasterCategory.from_string(str(value))

    @field_validator("date", "closed", mode="before")
    @classmethod
    def _normalize_dt(cls, value: datetime | str | None) -> datetime | None:
        if value is None:
            return value
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return value if value.tzinfo else value.replace(tzinfo=UTC)
