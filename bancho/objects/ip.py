
from typing      import Optional, List
from datetime    import datetime
from ..constants import Countries

from geoip2.errors   import AddressNotFoundError
from geoip2.database import Reader

import requests
import bancho
import config
import pytz

class IPAddress:

    status: str  = 'fail'
    country: str = ''
    country_code: str = ''

    region: int = 0
    region_name: str = ''
    city: str = ''
    zip: int  = 0

    latitude: float  = 0.0
    longitude: float = 0.0
    timezone: str    = ''
    utc_offset: int  = 0

    isp: str = ''
    org: str = ''
    ans: str = ''

    def __init__(self, ip: str) -> None:
        self.host = ip

        if self.from_cache():
            return

        if not self.from_database():
            if self.is_local:
                self.host = ''

            self.parse_request(
                self.do_request()
            )

        bancho.services.ip_cache.add(self)

    def __repr__(self) -> str:
        return f'<{self.host} ({self.country_name})>'

    def __hash__(self) -> int:
        return int(self.host.encode().hex(), 16)

    def __eq__(self, ip: object) -> bool:
        return ip.host == self.host

    @property
    def is_local(self) -> bool:
        if self.host.startswith('192.168') or self.host.startswith('127.0.0.1'):
            return True

        if self.host.startswith('172'):
            octets = self.host.split('.')

            if int(octets[1]) in range(16, 31):
                return True

        return False

    @property
    def country_name(self) -> str:
        return Countries[self.country_code]

    @property
    def country_num(self) -> int:
        return list(Countries.keys()).index(self.country_code)

    @classmethod
    def download_gopip_database(cls):
        bancho.services.logger.info('Downloading geolite database...')

        response = requests.get(config.IP_DATABASE_URL)

        if not response.ok:
            bancho.services.logger.error(f'Download failed. ({response.status_code})')
            bancho.services.logger.warning('Skipping...')
            return

        with open(f'{config.DATA_PATH}/geolite.mmdb', 'wb') as f:
            f.write(response.content)

    def from_cache(self):
        for ip in bancho.services.ip_cache:
            if self.host == ip.host:
                self.__dict__ = ip.__dict__.copy()

                return True

        return False

    def from_database(self) -> bool:
        try:
            with Reader(f'{config.DATA_PATH}/geolite.mmdb') as reader:
                response = reader.city(self.host)

                self.country = response.country.name
                self.country_code = response.country.iso_code
                self.city = response.city.name

                self.latitude  = response.location.latitude
                self.longitude = response.location.longitude
                self.timezone  = response.location.time_zone

                if not self.latitude or not self.longitude:
                    return False

                if not self.timezone:
                    return False

                self.utc_offset = int(
                    datetime.now(
                        pytz.timezone(self.timezone)
                    ).utcoffset().total_seconds() / 60 / 60
                )

                return True
        except AddressNotFoundError:
            pass
        except Exception as e:
            bancho.services.logger.warning(e)
        
        return False

    def parse_request(self, response: List[str]):
        self.status = response[0]
        self.host = response[-1]

        if self.status != 'success':
            return

        self.country      = response[1]
        self.country_code = response[2]
        self.region       = response[3]
        self.region_name  = response[4]
        self.city         = response[5]

        if response[6]:
            self.zip = int(response[6])

        self.latitude  = float(response[7])
        self.longitude = float(response[8])
        self.timezone  = response[9]
        self.isp       = response[10]
        self.org       = response[11]
        self.ans       = response[12]

        self.utc_offset = int(
            datetime.now(
                pytz.timezone(self.timezone)
            ).utcoffset().total_seconds() / 60 / 60
        )

    def do_request(self) -> Optional[list]:
        response = requests.get(
            f'http://ip-api.com/line/{self.host}',
            headers={
                'User-Agent': 'anchor'
            }
        )

        if not response.ok:
            return None

        return response.text.splitlines()
