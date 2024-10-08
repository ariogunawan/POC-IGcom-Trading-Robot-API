login = {
    'ig_api_username': '',
    'ig_api_password': '',
    'ig_api_key': '',
    'ig_endpoint_url': 'https://demo-api.ig.com/gateway/deal',
    'mysql_username': '',
    'mysql_password': '',
    'mysql_host': '',  # '198.199.74.158',
    'mysql_database': 'ig',
    'fixer_api_key': '',
    'fixer_endpoint_url': 'http://data.fixer.io/api'
}

headers = {
    'Content-Type': 'application/json; charset=UTF-8',
    'Accept': 'application/json; charset=UTF-8',
    'Version': '3',
    'X-IG-API-KEY': login.get('ig_api_key')
}

IG_API_USERNAME = login.get('ig_api_username')
IG_API_PASSWORD = login.get('ig_api_password')
IG_API_KEY = login.get('ig_api_key')
IG_ENDPOINT_URL = login.get('ig_endpoint_url')
MYSQL_USERNAME = login.get('mysql_username')
MYSQL_PASSWORD = login.get('mysql_password')
MYSQL_HOST = login.get('mysql_host')
MYSQL_DATABASE = login.get('mysql_database')
FIXER_API_KEY = login.get('fixer_api_key')
FIXER_ENDPOINT_URL = login.get('fixer_endpoint_url')
