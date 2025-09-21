from typing import List
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.spacex.client import SpaceXClient
from app.spacex.dependency import get_spacex_client
from app.spacex.schema import FrequencyStats, LaunchpadStats, RocketStats
from app.spacex.utils import get_launch_frequency, get_launch_site_rate, get_rocket_succes_rate

router = APIRouter(
    tags=["Launch Statistics"]
)

templates = Jinja2Templates(directory="templates")

@router.get("/success-rate", response_model=List[RocketStats])
async def rocket_success_rate(client: SpaceXClient = Depends(get_spacex_client)):
    return await get_rocket_succes_rate(client)

@router.get("/launch-site-rate", response_model=List[LaunchpadStats])
async def launch_site_rate(client: SpaceXClient = Depends(get_spacex_client)):
    return await get_launch_site_rate(client)

@router.get("/launch-frequency", response_model=FrequencyStats)
async def launch_frequency(client: SpaceXClient = Depends(get_spacex_client)):
    return await get_launch_frequency(client)

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    client: SpaceXClient = Depends(get_spacex_client),
):
    rocket_stats = await get_rocket_succes_rate(client)
    launchpad_stats = await get_launch_site_rate(client)
    frequency_stats = await get_launch_frequency(client)

    return templates.TemplateResponse(
        "statistics.html",
        {
            "request": request,
            "rocket_stats": rocket_stats,
            "launchpad_stats": launchpad_stats,
            "frequency_stats": frequency_stats,
        }
    )
