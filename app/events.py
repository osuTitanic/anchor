
import app

@app.session.events.register('user_update')
def user_update(user_id: int):
    if not (player := app.session.players.by_id(user_id)):
        return
    
    player.reload_object()

@app.session.events.register('bot_message')
def bot_message(message: str, target: str):
    if not (channel := app.session.channels.by_name(target)):
        return

    messages = message.split('\n')

    for message in messages:
        channel.send_message(
            app.session.bot_player,
            message,
            ignore_privs=True
        )

@app.session.events.register('restrict')
def restrict(user_id: int, reason: str = ''):
    if not (player := app.session.players.by_id(user_id)):
        return

    # TODO: Restrict...

@app.session.events.register('announcement')
def announcement(message: str):
    app.session.logger.info(f'Announcement: "{message}"')
    app.session.players.announce(message)
