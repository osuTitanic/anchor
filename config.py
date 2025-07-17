
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
S3_BASEURL = os.environ.get('S3_BASEURL')

REDIS_HOST = os.environ.get('REDIS_HOST')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))

AUTOJOIN_CHANNELS = eval(os.environ.get('AUTOJOIN_CHANNELS', "['#osu', '#announce']"))
BANCHO_WORKERS = int(os.environ.get('BANCHO_WORKERS', 15))
TCP_PORTS = eval(os.environ.get('BANCHO_TCP_PORTS', '[13381, 13382, 13383]'))
HTTP_PORT = int(os.environ.get('BANCHO_HTTP_PORT', 5000))
IRC_PORT = int(os.environ.get('BANCHO_IRC_PORT', 6667))
WS_PORT = int(os.environ.get('BANCHO_WS_PORT', 5001))

IRC_PORT_SSL = int(os.environ.get('BANCHO_IRC_PORT_SSL', 6697))
SSL_KEYFILE = os.environ.get('BANCHO_SSL_KEYFILE')
SSL_CERTFILE = os.environ.get('BANCHO_SSL_CERTFILE')
SSL_VERIFY_FILE = os.environ.get('BANCHO_SSL_VERIFY_FILE')
SSL_ENABLED = SSL_KEYFILE and SSL_CERTFILE

DOMAIN_NAME = os.environ.get('DOMAIN_NAME')

EMAIL_PROVIDER = os.environ.get('EMAIL_PROVIDER', '')
EMAIL_SENDER = os.environ.get('EMAIL_SENDER', '')
EMAIL_DOMAIN = EMAIL_SENDER.split('@')[-1]
EMAILS_ENABLED = bool(EMAIL_PROVIDER and EMAIL_SENDER)

SMTP_HOST = os.environ.get('SMTP_HOST')
SMTP_PORT = int(os.environ.get('SMTP_PORT') or '587')
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD')

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY')
MAILGUN_API_KEY = os.environ.get('MAILGUN_API_KEY')
MAILGUN_URL = os.environ.get('MAILGUN_URL', 'api.eu.mailgun.net')

MENUICON_IMAGE = os.environ.get('MENUICON_IMAGE')
MENUICON_URL = os.environ.get('MENUICON_URL')

DISABLE_CLIENT_VERIFICATION = eval(os.environ.get('DISABLE_CLIENT_VERIFICATION', 'True').capitalize())
ALLOW_MULTIACCOUNTING = eval(os.environ.get('ALLOW_MULTIACCOUNTING', 'False').capitalize())
APPROVED_MAP_REWARDS = eval(os.environ.get('APPROVED_MAP_REWARDS', 'False').capitalize())
FROZEN_RANK_UPDATES = eval(os.environ.get('FROZEN_RANK_UPDATES', 'False').capitalize())
MAINTENANCE = eval(os.environ.get('BANCHO_MAINTENANCE', 'False').capitalize())
OSU_IRC_ENABLED = eval(os.environ.get('ENABLE_OSU_IRC', 'True').capitalize())
IRC_ENABLED = eval(os.environ.get('ENABLE_IRC', 'True').capitalize())
S3_ENABLED = eval(os.environ.get('ENABLE_S3', 'True').capitalize())
DEBUG = eval(os.environ.get('DEBUG', 'False').capitalize())

OFFICER_WEBHOOK_URL = os.environ.get('OFFICER_WEBHOOK_URL')
EVENT_WEBHOOK_URL = os.environ.get('EVENT_WEBHOOK_URL')

CHAT_WEBHOOK_CHANNELS = os.environ.get('ALLOWED_WEBHOOK_CHANNELS', '#osu').split(',')
CHAT_WEBHOOK_URL = os.environ.get('CHAT_WEBHOOK_URL')

DATA_PATH = os.path.abspath('.data')
MULTIPLAYER_MAX_SLOTS = 8
PROTOCOL_VERSION = 18
VERSION = '1.7.5'
