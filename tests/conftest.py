from __future__ import annotations

from datetime import datetime, timezone

import pytest

from firms_monitor.domain.models import FireHotspot


@pytest.fixture
def make_hotspot():
    def _make(frp: float = 5.0, confidence: str = "n", lat: float = -10.0, lon: float = -50.0) -> FireHotspot:
        return FireHotspot(
            latitude=lat,
            longitude=lon,
            acquired_at=datetime(2026, 11, 10, 3, 12, tzinfo=timezone.utc),
            satellite="N20",
            instrument="VIIRS",
            confidence=confidence,
            frp=frp,
            daynight="N",
            brightness=330.5,
            source="VIIRS_NOAA20_NRT",
            country="BRA",
        )

    return _make
