
import dotenv
import os

# You can configure all allowed clients here, including one or more hash(es) of the executable
# If you don't want to verify a hash, then set it to 'None'
CLIENT_HASHES = {
    'b20130606.1': ['d9aa83c11aedf14cbecbd2cf7efa472b'],
    'b20130303': None
}

# This is optional, but it will improve performance
IP_DATABASE_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"

dotenv.load_dotenv(override=False)

POSTGRES_HOST = os.environ.get('POSTGRES_HOST')
POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT', 5432))
POSTGRES_USER = os.environ.get('POSTGRES_USER')
POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')

PORTS = eval(os.environ.get('BANCHO_PORTS', '[13381]'))

MENUICON_IMAGE = os.environ.get('BANCHO_MENUICON_IMAGE')
MENUICON_URL = os.environ.get('BANCHO_MENUICON_URL')

FREE_SUPPORTER = os.environ.get('FREE_SUPPORTER', 'True').lower() == 'true'
