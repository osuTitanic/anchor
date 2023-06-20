# Anchor

Anchor is a bancho server designed for older osu! clients.
My goal was to gain deeper insights into the inner workings of bancho and how it changed over the years.

It currently supports clients from b1807 to b2013606 and I will try to expand support in the future.

If you have any questions, feel free to contact me on discord: `lekuru`

## Quick start

To get started you will need to install python and set up a postgres database.

Apply this [migration file](https://github.com/lekuru-static/download/raw/main/base.sql) to your postgres instance.

Clone this repository onto your machine:
```shell
git clone https://github.com/Lekuruu/titanic-anchor.git
```

Install the requirements for python:
```shell
python -m pip install -r requirements.txt
```

Rename the `config.example.py` to `config.py` and edit it.

Start the server:
```shell
python main.py
```

and hope that nothing goes wrong 😅

## Creating a user

To create a user you will need to edit the database manually, because the old clients don't support registrations.

Inside the `users` table, you will need to create a new row, with these attributes:

- name
- safe_name
- email
- pw (bcrypt)
- activated (true)

## Contributing

If you want to clean up the mess that I made, then feel free to make a pull request.

## Patching the client

To actually use the client, you will need to patch it, and I would recommend using [dnspy](https://github.com/dnSpy/dnSpy) for that.

Also, some older clients may be obfuscated.
As far as I know, [b2013606.1](https://osekai.net/snapshots/?version=179) is the latest non-obfuscated version that will work with this server.

You will need to find a line inside `osu.Online.BanchoClient` that looks something like this:

![unpatched](https://raw.githubusercontent.com/lekuru-static/download/main/patched.png)

and edit the ip address to match your setup:

![patched](https://raw.githubusercontent.com/lekuru-static/download/main/patched.png)

Remember to update the client hash inside your config!

## Screenshots

![sanic](https://raw.githubusercontent.com/lekuru-static/download/main/screenshot005.jpg)
![cool](https://raw.githubusercontent.com/lekuru-static/download/main/screenshot003.jpg)
![nice](https://raw.githubusercontent.com/lekuru-static/download/main/screenshot007.jpg)
![multiplayer](https://raw.githubusercontent.com/lekuru-static/download/main/screenshot008.jpg)
