
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
BANCHO_WORKERS = int(os.environ.get('BANCHO_WORKERS', 15))
TCP_PORTS = eval(os.environ.get('BANCHO_TCP_PORTS', '[13381, 13382, 13383]'))
HTTP_PORT = int(os.environ.get('BANCHO_HTTP_PORT', 5000))

DOMAIN_NAME = os.environ.get('DOMAIN_NAME')

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
SENDGRID_EMAIL = os.environ.get('SENDGRID_EMAIL')

MAILGUN_API_KEY = os.environ.get('MAILGUN_API_KEY')
MAILGUN_EMAIL = os.environ.get('MAILGUN_EMAIL', '')
MAILGUN_URL = os.environ.get('MAILGUN_URL', 'api.eu.mailgun.net')
MAILGUN_DOMAIN = MAILGUN_EMAIL.split('@')[-1]

EMAILS_ENABLED = MAILGUN_API_KEY is not None or SENDGRID_API_KEY is not None
EMAIL = MAILGUN_EMAIL or SENDGRID_EMAIL

AMPLITUDE_API_KEY = os.environ.get('AMPLITUDE_API_KEY')

MENUICON_IMAGE = os.environ.get('MENUICON_IMAGE')
MENUICON_URL = os.environ.get('MENUICON_URL')

DISABLE_CLIENT_VERIFICATION = eval(os.environ.get('DISABLE_CLIENT_VERIFICATION', 'True').capitalize())
ALLOW_MULTIACCOUNTING = eval(os.environ.get('ALLOW_MULTIACCOUNTING', 'False').capitalize())
APPROVED_MAP_REWARDS = eval(os.environ.get('APPROVED_MAP_REWARDS', 'False').capitalize())
MAINTENANCE = eval(os.environ.get('BANCHO_MAINTENANCE', 'False').capitalize())
S3_ENABLED = eval(os.environ.get('ENABLE_S3', 'True').capitalize())
DEBUG = eval(os.environ.get('DEBUG', 'False').capitalize())

OFFICER_WEBHOOK_URL = os.environ.get('OFFICER_WEBHOOK_URL')
EVENT_WEBHOOK_URL = os.environ.get('EVENT_WEBHOOK_URL')

IP_DATABASE_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"

DATA_PATH = os.path.abspath('.data')
MULTIPLAYER_MAX_SLOTS = 8
PROTOCOL_VERSION = 18
VERSION = '1.4.2'
