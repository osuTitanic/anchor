
from app.common.constants import COUNTRIES

from geoip2.errors import AddressNotFoundError
from geoip2.database import Reader

from dataclasses import dataclass
from typing import Optional

import config
import app

@dataclass
class Geolocation:
    ip: str = '127.0.0.1'
    latitude: float = 0.0
    longitude: float = 0.0
    country_code: str = 'XX'
    country_index: int = 0
    timezone: int = 0

def download_database():
    app.session.logger.info('Downloading geolite database...')

    response = app.session.requests.get(config.IP_DATABASE_URL)

    if not response.ok:
        app.session.logger.error(f'Download failed. ({response.status_code})')
        app.session.logger.warning('Skipping...')
        return

    with open(f'{config.DATA_PATH}/geolite.mmdb', 'wb') as f:
        f.write(response.content)

def fetch_geolocation(ip: str, is_local: bool = False) -> Geolocation:
    if is_local:
        if not (geo := fetch_web(ip, is_local)):
            return Geolocation()

        return geo

    if (geo := fetch_db(ip)):
        return geo

    if (geo := fetch_web(ip)):
        return geo

    return Geolocation()

def fetch_db(ip: str) -> Optional[Geolocation]:
    try:
        with Reader(f'{config.DATA_PATH}/geolite.mmdb') as reader:
            response = reader.city(ip)

            return Geolocation(
                ip,
                response.location.latitude,
                response.location.longitude,
                response.country.iso_code,
                list(COUNTRIES.keys()).index(
                    response.country.iso_code
                ),
                response.location.time_zone
            )
    except AddressNotFoundError:
        return
    except Exception as e:
        app.session.logger.warning(e)

def fetch_web(ip: str, is_local: bool = False) -> Optional[Geolocation]:
    response = app.session.requests.get(f'http://ip-api.com/line/{ip if not is_local else ""}')

    if not response.ok:
        return None

    status, *lines = response.text.split('\n')

    if status != 'success':
        app.session.logger.error(
            f'Failed to get geolocation: {status} ({lines[0]})'
        )
        return None

    index = list(COUNTRIES.keys()).index(lines[1])

    return Geolocation(
        ip=lines[12],
        latitude=lines[6],
        longitude=lines[7],
        country_code=lines[1],
        country_index=index,
        timezone=lines[8]
    )
