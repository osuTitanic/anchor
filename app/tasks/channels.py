
import app

@app.session.tasks.submit(interval=60*10, threaded=True)
def channel_housekeeping() -> None:
	"""Remove inactive players from all channels every 10 minutes"""
	for channel in app.session.channels.values():
		channel.remove_inactive_users()
