from app.spacex.client import SpaceXClient
from app.config import settings

spacex_client = SpaceXClient(settings.BASE_URL)

def get_spacex_client():
    return spacex_client
