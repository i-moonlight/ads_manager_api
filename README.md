# Link Clicks Ads Manager API

The Link Clicks Ads Manager uses a Django API server.

Simple starter built with Python / Django Rest / Sqlite3 and JWT Auth. Passwordless authentication is done by email.
<br />


## ✨ How to use the code

> 👉 **Step #1** -  Clone the sources

```bash
$ git clone https://github.com/LinkClicks/ads_manager_api.git
$ cd ads_manager_api
```
<br />

> 👉 **Step #2** - Create a virtual environment

```bash
$ # Virtualenv modules installation (Unix based systems)
$ virtualenv env
$ source env/bin/activate
$
$ # Virtualenv modules installation (Windows based systems)
$ # virtualenv env
$ # .\env\Scripts\activate
```

<br />

> 👉 **Step #3** - Install dependencies using PIP

```bash
$ pip install -r requirements.txt
```

<br />

> 👉 **Step #4** - Create a new `.env` file using sample `env.sample`

<br />

> 👉 **Step #5** - Set up the databases

```bash
python manage.py migrate
python manage.py meta_setup
```

> 👉 **Step #6** - Start the API servers

```bash
python manage.py qcluster
```

in another window run
```bash
uvicorn core.asgi:application --port 8000 --workers 4 --log-level debug --reload
```

The API server will start using the default port `8000`.

<br />
