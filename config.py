
import dotenv
import os

# You can configure all allowed clients here
# If you don't want to validate the hash, you can leave the value empty
CLIENT_HASHES = {
    'b20130606.1': '93f0c72fdb32fc2cbc8fdf253b741a27'
}

# This is optional, but it will improve performance
IP_DATABASE_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"

dotenv.load_dotenv(override=False)

POSTGRES_HOST = os.environ.get('POSTGRES_HOST')
POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT'))
POSTGRES_USER = os.environ.get('POSTGRES_USER')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')

REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = int(os.environ.get('REDIS_PORT'))

PORTS = eval(os.environ.get('BANCHO_PORTS'))

MENUICON_IMAGE = os.environ.get('BANCHO_MENUICON_IMAGE')
MENUICON_URL = os.environ.get('BANCHO_MENUICON_URL')

FREE_SUPPORTER = os.environ.get('FREE_SUPPORTER').lower() == 'true'
