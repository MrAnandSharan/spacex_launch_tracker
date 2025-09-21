from collections import Counter, defaultdict
from datetime import datetime, timezone
import logging
import csv
import io
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Any, Dict, List, Optional, Union
from fastapi import HTTPException, status, Request
from app.spacex.client import SpaceXClient
from app.spacex.schema import FrequencyStats, Launch, Launchpad, LaunchpadStats, Rocket, PaginatedResponse, RocketStats

logger = logging.getLogger(__name__)


async def get_launches(
        client: SpaceXClient, 
        start_date: Optional[datetime], 
        end_date: Optional[datetime], 
        rocket: Optional[str],
        success: Optional[bool], 
        launchpad: Optional[str]
    ) -> List[Launch]:
    try:
        # Fetch responses from external APIs
        launch_response = await client.get_launches()
        launchpads_response = await client.get_launchpads()
        rockets_response = await client.get_rockets()
        logger.info(f"Fetched {len(launch_response)} launches, {len(rockets_response)} rockets, {len(launchpads_response)} launchpads")
        
		# Map the rockets and launchpads info
        rockets_map: Dict[str, str] = {i["id"]: i for i in rockets_response}
        launchpads_map: Dict[str, str] = {i["id"]: i for i in launchpads_response}
        
		# Create a response object
        response: List[Launch] = []
        for i in launch_response:
            rocket_data = rockets_map.get(i["rocket"])
            launchpad_data = launchpads_map.get(i["launchpad"])
            response.append(Launch(
                id=i["id"],
                name=i["name"],
                date_utc=i["date_utc"],
                rocket=Rocket(**rocket_data) if rocket_data else None,
                success=i.get("success"),
                launchpad=Launchpad(**launchpad_data) if launchpad_data else None
            ))
        
        # Filter data according to query params if present
        if start_date:
            response = [i for i in response if i.date_utc >= start_date.astimezone(timezone.utc)]
        if end_date:
            response = [i for i in response if i.date_utc <= end_date.astimezone(timezone.utc)]
        if rocket:
            response = [i for i in response if i.rocket and rocket.lower() in i.rocket.name.lower()]
        if success is not None:
            response = [i for i in response if i.success == success]
        if launchpad:
            response = [i for i in response if i.launchpad and launchpad.lower() in i.launchpad.name.lower()]
        logger.info(f"Filtered {len(response)} launches from external API / Cache.", )
        return response
    except Exception as e:
        logger.exception(f"Failed to fetch spaceX data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch spaceX data: {str(e)}"
        )

def paginate(request: Request, items: List[Launch], limit: int, offset: int) -> PaginatedResponse:
    try:
        total: int = len(items)
        paginated_data: List[Launch] = items[offset: offset + limit]

        def make_url(new_offset: int) -> Optional[str]:
            if new_offset < 0 or new_offset >= total:
                return None
            return str(request.url.replace_query_params(limit=limit, offset=new_offset))

        return PaginatedResponse(
            total=total,
            limit=limit,
            offset=offset,
            data=paginated_data,
            next=make_url(offset + limit),
            previous=make_url(offset - limit),
        )
    except Exception as e:
        logger.exception(f"Failed to paginate data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to paginate spaceX data: {str(e)}"
        )

async def get_rocket_succes_rate(client: SpaceXClient) -> List[RocketStats]:
    try:
        # Fetch responses from external APIs
        logger.info(f"Calculation started for rocket success rates.")
        launch_response: Dict[str, Any] = await client.get_launches()
        rockets_response: Dict[str, Any] = await client.get_rockets()

        # Map rocket object from response
        rocket_map: Dict[str, str] = {i["id"]: i["name"] for i in rockets_response}
        stats: defaultdict[Any, dict[str, int]] = defaultdict(lambda: {"total": 0, "success": 0})

        for i in launch_response:
            rocket_id = i.get("rocket")
            stats[rocket_id]["total"] += 1
            if i.get("success") is True:
                stats[rocket_id]["success"] += 1

        # Create response
        response: List[RocketStats] = []
        for rocket_id, values in stats.items():
            total = values["total"]
            success = values["success"]
            success_rate = (success / total) * 100 if total > 0 else 0.0
            response.append(
                RocketStats(
                    rocket_name=rocket_map.get(rocket_id, ""),
                    total=total,
                    success=success,
                    success_rate=success_rate,
                )
            )
        logger.info(f"Calculated completed success rate for {len(response)} rockets.")
        return response
    except Exception as e:
        logger.exception(f"Failed to fetch rocket stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch rocket stats: {str(e)}"
        )

async def get_launch_site_rate(client: SpaceXClient) -> List[LaunchpadStats]:
    try:
        # Fetch responses from external APIs
        logger.info(f"Calculation started for launchsite rates.")
        launches: Dict[str, Any] = await client.get_launches()
        launchpads: Dict[str, Any] = await client.get_launchpads()

        # map launchpad from reseponse
        launchpad_map: Dict[str, str] = {lp["id"]: lp["name"] for lp in launchpads}

        # Process and count launchpad 
        counts: Counter = Counter()
        for i in launches:
            launchpad_id = i.get("launchpad")
            if launchpad_id:
                counts[launchpad_id] += 1

        # Create response
        response: List[LaunchpadStats] = []
        for lp_id, total in counts.items():
            response.append(
                LaunchpadStats(
                    launchpad_name=launchpad_map.get(lp_id, ""),
                    total=total
                )
            )
        logger.info(f"Calculated launch counts for {len(response)} launchpads")
        return response
    except Exception as e:
        logger.exception(f"Failed to fetch launch site stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch launch site stats: {str(e)}"
        )

async def get_launch_frequency(client: SpaceXClient) -> FrequencyStats:
    try:
        # Fetch responses from external API
        logger.info(f"Calculation started for launch frequency by months and years.")
        launches: Dict[str, Any] = await client.get_launches()

        # Process year and month from datetime
        by_year: Dict = {}
        by_month: Dict = {}
        for i in launches:
            dt = datetime.fromisoformat(i["date_utc"].replace("Z", "+00:00"))
            year = dt.year
            by_year[year] = by_year.get(year, 0) + 1
            month = f"{dt.year}-{dt.month:02d}"
            by_month[month] = by_month.get(month, 0) + 1
        
        # Log and retunr response
        logger.info(f"Calculated launch frequency: {len(by_year)} years, {len(by_month)} months")
        return FrequencyStats(by_year=by_year, by_month=by_month)
    except Exception as e:
        logger.exception(f"Failed to fetch launch frequency stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch launch frequency stats: {str(e)}"
        )

def export_object(data: any, format: str) -> Union[JSONResponse, StreamingResponse]:
    try:
        # JSON
        if format == "json":
            headers = {"Content-Disposition": "attachment; filename=launches.json"}
            return JSONResponse(content=jsonable_encoder(data), headers=headers)

        # CSV
        elif format == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["id", "name", "date_utc", "rocket", "success", "launchpad"]) # Heading row for the csv
            for i in data:
                writer.writerow([
                    i.id,
                    i.name,
                    i.date_utc.isoformat(),
                    i.rocket.name if i.rocket else "",
                    i.success,
                    i.launchpad.name if i.launchpad else "",
                ])
            output.seek(0)
            headers = {"Content-Disposition": "attachment; filename=launches.csv"}
            logger.info("Export object has been created")
            return StreamingResponse(output, media_type="text/csv", headers=headers)
    except Exception as e:
        logger.exception(f"Failed to create export object: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create export object: {str(e)}"
        )