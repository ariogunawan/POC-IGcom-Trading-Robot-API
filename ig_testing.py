res = {'prices': [{'snapshotTime': '2020/06/24 12:50:00', 'snapshotTimeUTC': '2020-06-24T02:50:00',
                   'openPrice': {'bid': 106.512, 'ask': 106.519, 'lastTraded': None},
                   'closePrice': {'bid': 106.541, 'ask': 106.551, 'lastTraded': None},
                   'highPrice': {'bid': 106.548, 'ask': 106.556, 'lastTraded': None},
                   'lowPrice': {'bid': 106.505, 'ask': 106.512, 'lastTraded': None}, 'lastTradedVolume': 398},
                  {'snapshotTime': '2020/06/24 12:55:00', 'snapshotTimeUTC': '2020-06-24T02:55:00',
                   'openPrice': {'bid': 106.542, 'ask': 106.549, 'lastTraded': None},
                   'closePrice': {'bid': 106.528, 'ask': 106.535, 'lastTraded': None},
                   'highPrice': {'bid': 106.542, 'ask': 106.549, 'lastTraded': None},
                   'lowPrice': {'bid': 106.522, 'ask': 106.53, 'lastTraded': None}, 'lastTradedVolume': 300}],
       'instrumentType': 'CURRENCIES',
       'metadata': {'allowance': {'remainingAllowance': 9965, 'totalAllowance': 10000, 'allowanceExpiry': 598278},
                    'size': 2, 'pageData': {'pageSize': 20, 'pageNumber': 1, 'totalPages': 1}}}

d_getPrices = dict(epic='CS.D.USDJPY.MINI.IP',
                   resolution='MINUTE_5',
                   start_date='2020-06-24T12:50:00',
                   end_date='2020-06-24T12:55:00')

l_prices = []
for price in res['prices']:
    data = dict(epic=d_getPrices.get('epic'),
                resolution=d_getPrices.get('resolution'),
                snapshotTime=price.get('snapshotTime'),
                snapshotTimeUTC=price.get('snapshotTimeUTC'),
                openPrice_bid=price['openPrice'].get('bid'),
                openPrice_ask=price['openPrice'].get('ask'),
                openPrice_mid=round((price['openPrice'].get('bid') + price['openPrice'].get('ask')) / 2, 8),
                closePrice_bid=price['closePrice'].get('bid'),
                closePrice_ask=price['closePrice'].get('ask'),
                closePrice_mid=round((price['closePrice'].get('bid') + price['closePrice'].get('ask')) / 2, 8),
                highPrice_bid=price['highPrice'].get('bid'),
                highPrice_ask=price['highPrice'].get('ask'),
                highPrice_mid=round((price['highPrice'].get('bid') + price['highPrice'].get('ask')) / 2, 8),
                lowPrice_bid=price['lowPrice'].get('bid'),
                lowPrice_ask=price['lowPrice'].get('ask'),
                lowPrice_mid=round((price['lowPrice'].get('bid') + price['lowPrice'].get('ask')) / 2, 8),
                lastTradedVolume=price.get('lastTradedVolume')
                )
    l_prices.append(data)

for l_price in l_prices:
    print(l_price)

    query = """insert into price (epic, resolution, snapshotTime, snapshotTimeUTC, openPrice_bid, 
    openPrice_ask, openPrice_mid, closePrice_bid, closePrice_ask, closePrice_mid, highPrice_bid, 
    highPrice_ask, highPrice_mid, lowPrice_bid, lowPrice_ask, lowPrice_mid, lastTradedVolume) 
    select %(epic)s, %(resolution)s, %(snapshotTime)s, %(snapshotTimeUTC)s, %(openPrice_bid)s, 
    %(openPrice_ask)s, %(openPrice_mid)s, %(closePrice_bid)s, %(closePrice_ask)s, %(closePrice_mid)s, 
    %(highPrice_bid)s, %(highPrice_ask)s, %(highPrice_mid)s, %(lowPrice_bid)s, %(lowPrice_ask)s, 
    %(lowPrice_mid)s, %(lastTradedVolume)s from dual where not exists (select 1 from price p where
    p.epic = %(epic)s and p.resolution = %(resolution)s and p.snapshotTime = %(snapshotTime) and 
    p.snapshotTimeUTC = %(snapshotTimeUTC)s and p.lastTradedVolume = %(lastTradedVolume)s) """