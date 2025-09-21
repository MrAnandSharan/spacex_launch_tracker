from datetime import datetime
import csv
import io
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from typing import Optional
from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from app.spacex.client import SpaceXClient
from app.spacex.dependency import get_spacex_client
from app.spacex.schema import PaginatedResponse
from app.spacex.utils import export_object, get_launches, paginate

router = APIRouter(
    tags=["Launch Data"],
)

templates = Jinja2Templates(directory="templates")

@router.get("/", response_model=PaginatedResponse)
async def all_launches(
        request: Request, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        rocket: Optional[str] = None,
        success: Optional[bool] = None,
        launchpad: Optional[str] = None,
        limit: int = 10,
        offset: int = 0,
        client: SpaceXClient = Depends(get_spacex_client)
    ):
    response = await get_launches(client, start_date, end_date, rocket, success, launchpad)
    return paginate(request, response, limit, offset)


@router.get("/export")
async def export_launches(
    client: SpaceXClient = Depends(get_spacex_client),
    format: str = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    rocket_name: Optional[str] = None,
    success: Optional[bool] = None,
    launch_site: Optional[str] = None,
):
    launches = await get_launches(client, start_date, end_date, rocket_name, success, launch_site)
    return export_object(launches, format)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    rocket_name: Optional[str] = None,
    success: Optional[bool] = None,
    launch_site: Optional[str] = None,
    limit: int = 10,
    offset: int = 0,
    client: SpaceXClient = Depends(get_spacex_client),
):
    response = await get_launches(client, start_date, end_date, rocket_name, success, launch_site)
    launches_page = paginate(request, response, limit, offset)

    return templates.TemplateResponse(
        "data.html",
        {
            "request": request,
            "launches_page": launches_page,
        }
    )