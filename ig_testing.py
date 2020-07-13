from decimal import Decimal
res = {'epic': 'CS.D.USDJPY.MINI.IP', 'expiry': '-', 'direction': 'SELL', 'size': Decimal('3.5'), 'orderType': 'MARKET', 'timeInForce': None, 'level': None, 'guaranteedStop': False, 'stopLevel': None, 'stopDistance': 5.0, 'trailingStop': None, 'trailingStopIncrement': None, 'forceOpen': True, 'limitLevel': None, 'limitDistance': 6.0, 'quoteId': None, 'currencyCode': 'JPY'}
res['size'] = float(res['size'])

print(res)
