
import dotenv
import os

dotenv.load_dotenv(override=False)

POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD')
POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT', 5432))
POSTGRES_USER = os.environ.get('POSTGRES_USER')
POSTGRES_HOST = os.environ.get('POSTGRES_HOST')

POSTGRES_POOLSIZE = int(os.environ.get('POSTGRES_POOLSIZE', 10))
POSTGRES_POOLSIZE_OVERFLOW = int(os.environ.get('POSTGRES_POOLSIZE_OVERFLOW', 30))

S3_ACCESS_KEY = os.environ.get('S3_ACCESS_KEY')
S3_SECRET_KEY = os.environ.get('S3_SECRET_KEY')
S3_BASEURL    = os.environ.get('S3_BASEURL')

REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

AUTOJOIN_CHANNELS = eval(os.environ.get('AUTOJOIN_CHANNELS', "['#osu', '#announce']"))

PORTS = eval(os.environ.get('BANCHO_PORTS', '[13381, 13382, 13383]'))

PACKET_WORKERS = int(os.environ.get('BANCHO_PACKET_WORKERS', 10))
LOGIN_WORKERS = int(os.environ.get('BANCHO_LOGIN_WORKERS', 5))
DB_WORKERS = int(os.environ.get('BANCHO_DB_WORKERS', 2))

DOMAIN_NAME = os.environ.get('DOMAIN_NAME')

MENUICON_IMAGE = os.environ.get('MENUICON_IMAGE')
MENUICON_URL = os.environ.get('MENUICON_URL')

DISABLE_CLIENT_VERIFICATION = eval(os.environ.get('DISABLE_CLIENT_VERIFICATION', 'False').capitalize())
APPROVED_MAP_REWARDS = eval(os.environ.get('APPROVED_MAP_REWARDS', 'False').capitalize())
SKIP_IP_DATABASE = eval(os.environ.get('SKIP_IP_DATABASE', 'False').capitalize())
MAINTENANCE = eval(os.environ.get('BANCHO_MAINTENANCE', 'False').capitalize())
FREE_SUPPORTER = eval(os.environ.get('FREE_SUPPORTER', 'True').capitalize())
S3_ENABLED = eval(os.environ.get('ENABLE_S3', 'True').capitalize())
DEBUG = eval(os.environ.get('DEBUG', 'False').capitalize())

IP_DATABASE_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"

DATA_PATH = os.path.abspath('.data')
PROTOCOL_VERSION = 18
VERSION = 'dev'
