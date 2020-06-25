login = {
    'api_username': 'kucingjoget',
    'api_password': 'Dangdutan123!',
    'api_key': '344e0ef3719055d215069ea9a44110ff50d95ba7',
    'endpoint_url': 'https://demo-api.ig.com/gateway/deal',
    'mysql_username': 'root',
    'mysql_password': 'KucingjogetAbrakadabra123!',
    'mysql_host': '206.189.207.174',  # '198.199.74.158',
    'mysql_database': 'ig'
}

headers = {
    'Content-Type': 'application/json; charset=UTF-8',
    'Accept': 'application/json; charset=UTF-8',
    'Version': '3',
    'X-IG-API-KEY': login.get('api_key')
}

API_USERNAME = login.get('api_username')
API_PASSWORD = login.get('api_password')
API_KEY = login.get('api_key')
ENDPOINT_URL = login.get('endpoint_url')
MYSQL_USERNAME = login.get('mysql_username')
MYSQL_PASSWORD = login.get('mysql_password')
MYSQL_HOST = login.get('mysql_host')
MYSQL_DATABASE = login.get('mysql_database')

