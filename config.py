
POSTGRES_HOST='127.0.0.1'
POSTGRES_PORT=5432
POSTGRES_USER='bancho'
POSTGRES_PASSWORD='examplePassword'

REDIS_HOST='127.0.0.1'
REDIS_PORT=6379
REDIS_PASS='examplePassword'

# You can set up multiple ports here
PORTS = [13381, 13382]

# This will be visible inside the menu
# Example: https://osu.ppy.sh/ss/18600390/1055
MENUICON_IMAGE=""
MENUICON_URL=""

# This will give every player supporter permissions
FREE_SUPPORTER=True

# You can configure all allowed clients here
# If you don't want to validate the hash, you can leave the value empty
CLIENT_HASHES = {
    'b20130606.1': 'f84642c6251bda9b40a3ad3b5ee1a984'
}
