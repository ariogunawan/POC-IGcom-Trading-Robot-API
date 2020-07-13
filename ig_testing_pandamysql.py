import pandas as pd
import mysql.connector as cn
import ig_constant as ig

db = cn.connect(host=ig.MYSQL_HOST, user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD, database=ig.MYSQL_DATABASE)
cur = db.cursor()
query = """
select epic, resolution, snapshotTime, diff_ema_21_55
from vw_price_analysis
where 1=1
and epic = 'CS.D.USDJPY.MINI.IP'
and resolution = 'MINUTE_5'
and snapshotTime between '2020-07-09 21:25:00' and '2020-07-09 22:55:00'
order by snapshotTime desc
"""
# SELL: and snapshotTime between '2020-07-09 21:25:00' and '2020-07-09 22:55:00'
# BUY:  and snapshotTime between '2020-07-11 00:50:00' and '2020-07-11 03:15:00'
cur.execute(query)
df = pd.DataFrame(cur.fetchall())
df.columns = cur.column_names
db.close()


print(df)

d_strategy = dict(name='EMA 21 & 55 Crossing. EMA 21 > 55 = BUY else SELL',
                  minWide=0.015,
                  minOppositeIndex=5,
                  orderType='BUY' if df['diff_ema_21_55'].iloc[0] > 0 else 'SELL',
                  rowCount=len(df),
                  firstOppositeIndex=None,
                  minWideStatus='Passed',
                  firstOppositeStatus='Passed',
                  beforeCrossingStatus='Passed',
                  afterCrossingStatus='Passed',
                  finalResult='Failed'
                  )
# Get first index where sign is opposite
if d_strategy['orderType'] == 'BUY':
    d_strategy['firstOppositeIndex'] = df[df['diff_ema_21_55'] < 0].index[0]
else:
    d_strategy['firstOppositeIndex'] = df[df['diff_ema_21_55'] > 0].index[0]
# Failed if less than 5 candles
if d_strategy['firstOppositeIndex'] < d_strategy['minOppositeIndex']:
    d_strategy['firstOppositeStatus'] = 'Failed'
# Failed if pips < 0.015
if abs(df['diff_ema_21_55'].iloc[0]) < d_strategy['minWide']:
    d_strategy['minWideStatus'] = 'Failed'
# Before sign = incrementally weaker
for i in range(d_strategy['firstOppositeIndex'], d_strategy['rowCount']-1):
    if d_strategy['orderType'] == 'BUY' and df['diff_ema_21_55'].iloc[i] < df['diff_ema_21_55'].iloc[i+1]:
        d_strategy['beforeCrossingStatus'] = 'Failed'
        break
    elif d_strategy['orderType'] == 'SELL' and df['diff_ema_21_55'].iloc[i] > df['diff_ema_21_55'].iloc[i+1]:
        d_strategy['beforeCrossingStatus'] = 'Failed'
        break
# After sign = incrementally stronger
for i in range(0, d_strategy['firstOppositeIndex']):
    if d_strategy['orderType'] == 'BUY' and df['diff_ema_21_55'].iloc[i] < df['diff_ema_21_55'].iloc[i+1]:
        d_strategy['afterCrossingStatus'] = 'Failed'
        break
    elif d_strategy['orderType'] == 'SELL' and df['diff_ema_21_55'].iloc[i] > df['diff_ema_21_55'].iloc[i+1]:
        d_strategy['afterCrossingStatus'] = 'Failed'
        break
# Decide final result
if d_strategy['minWideStatus'] == 'Passed' and d_strategy['firstOppositeStatus'] == 'Passed' and d_strategy['beforeCrossingStatus'] == 'Passed' and d_strategy['afterCrossingStatus'] == 'Passed':
    d_strategy['finalResult'] = 'Passed'
print(d_strategy)
