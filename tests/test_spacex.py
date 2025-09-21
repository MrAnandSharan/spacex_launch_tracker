import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock
import pytest_asyncio
from app.spacex.utils import get_launches, get_rocket_succes_rate, get_launch_site_rate, get_launch_frequency


@pytest_asyncio.fixture
def mock_client():
    """I have created a demo response for SpaceXClient API"""
    client = AsyncMock()
    client.get_launches.return_value = [
        {
            "id": "L1",
            "name": "FalconSat",
            "date_utc": "2020-01-01T00:00:00Z",
            "rocket": "R1",
            "success": True,
            "launchpad": "LP1"
        },
        {
            "id": "L2",
            "name": "DemoSat",
            "date_utc": "2020-06-01T00:00:00Z",
            "rocket": "R1",
            "success": False,
            "launchpad": "LP1"
        },
        {
            "id": "L3",
            "name": "Trailblazer",
            "date_utc": "2021-01-01T00:00:00Z",
            "rocket": "R2",
            "success": True,
            "launchpad": "LP2"
        }
    ]
    client.get_rockets.return_value = [
        {"id": "R1", "name": "Falcon 1"},
        {"id": "R2", "name": "Falcon 9"}
    ]
    client.get_launchpads.return_value = [
        {"id": "LP1", "name": "Kwajalein Atoll"},
        {"id": "LP2", "name": "Cape Canaveral"}
    ]
    return client


@pytest.mark.asyncio
async def test_fetch_and_filter_launches(mock_client):
    launches = await get_launches(mock_client, None, None, None, None, None)
    assert len(launches) == 3
    assert launches[0].name == "FalconSat"

    # Filter by date range
    start_date = datetime(2020, 5, 1, tzinfo=timezone.utc)
    end_date = datetime(2020, 12, 31, tzinfo=timezone.utc)
    filtered = await get_launches(mock_client, start_date, end_date, None, None, None)
    assert len(filtered) == 1
    assert filtered[0].name == "DemoSat"

    # Filter by rocket
    filtered = await get_launches(mock_client, None, None, "Falcon 9", None, None)
    assert len(filtered) == 1
    assert filtered[0].rocket.name == "Falcon 9"

    # Filter by success
    filtered = await get_launches(mock_client, None, None, None, True, None)
    assert all(l.success for l in filtered)


@pytest.mark.asyncio
async def test_rocket_success_rate(mock_client):
    stats = await get_rocket_succes_rate(mock_client)
    assert len(stats) == 2

    falcon1 = next(s for s in stats if s.rocket_name == "Falcon 1")
    assert falcon1.total == 2
    assert falcon1.success == 1
    assert round(falcon1.success_rate, 2) == 50.0

    falcon9 = next(s for s in stats if s.rocket_name == "Falcon 9")
    assert falcon9.total == 1
    assert falcon9.success == 1
    assert falcon9.success_rate == 100.0


@pytest.mark.asyncio
async def test_launch_site_rate(mock_client):
    stats = await get_launch_site_rate(mock_client)
    assert len(stats) == 2

    lp1 = next(s for s in stats if s.launchpad_name == "Kwajalein Atoll")
    assert lp1.total == 2

    lp2 = next(s for s in stats if s.launchpad_name == "Cape Canaveral")
    assert lp2.total == 1


@pytest.mark.asyncio
async def test_launch_frequency(mock_client):
    stats = await get_launch_frequency(mock_client)
    assert stats.by_year[2020] == 2
    assert stats.by_year[2021] == 1
    assert stats.by_month["2020-01"] == 1
    assert stats.by_month["2020-06"] == 1
    assert stats.by_month["2021-01"] == 1
