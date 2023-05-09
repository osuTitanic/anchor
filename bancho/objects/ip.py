
from typing      import Optional, List
from datetime    import datetime
from ..constants import Countries

import requests
import pytz

class IPAddress:

    status: str  = 'fail'
    country: str = 'Unknown'
    country_code: str = 'XX'

    region: int = 0
    region_name: str = 'Unknown'
    city: str = 'Unknown'
    zip: int  = 0

    latitude: float  = 0.0
    longitude: float = 0.0
    timezone: str    = 'Unknown/Unknown'
    utc_offset: int  = 0

    isp: str = 'Unknown'
    org: str = 'Unknown'
    ans: str = 'Unknown'

    def __init__(self, ip: str) -> None:
        self.host = ip

        if self.is_local:
            self.host = ''
        
        self.parse_request(
            self.do_request()
        )

    def __repr__(self) -> str:
        return self.host
    
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
        return Countries.values()[self.country_code]
    
    @property
    def country_num(self) -> int:
        return list(Countries.keys()).index(self.country_code)

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
