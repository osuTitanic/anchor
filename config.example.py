
POSTGRES_HOST = '127.0.0.1'
POSTGRES_PASSWORD = 'examplePassword'
POSTGRES_USER = 'bancho'
POSTGRES_PORT = 5432

# You can configure all allowed clients here, including one or more hash(es) of the executable
# If you don't want to verify a hash, then set it to 'None'
CLIENT_HASHES = {
    'b20130606.1': ['d9aa83c11aedf14cbecbd2cf7efa472b'],
    'b20130303': None
}

# This is optional, but it will improve performance
IP_DATABASE_URL = "https://github.com/P3TERX/GeoLite.mmdb/raw/download/GeoLite2-City.mmdb"

PORTS = [13381, 13382, 13383]

# This will be visible inside the menu
# Example: https://osu.ppy.sh/ss/18600390/1055
MENUICON_IMAGE = ''
MENUICON_URL = ''

DISABLE_CLIENT_VERIFICATION = False
FREE_SUPPORTER = True
