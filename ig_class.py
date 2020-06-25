import inspect
import datetime
import mysql.connector as cn
import requests
import ig_constant as ig
import pandas as pd
from talib import abstract as ta
from sqlalchemy import create_engine


class IGWrapper():
    def __init__(self):
        self.session = requests.Session()
        self.headers = ig.headers
        method = 'POST'
        url = '/session'
        data = dict(identifier=ig.API_USERNAME, password=ig.API_PASSWORD)
        endpoint_url = ig.ENDPOINT_URL
        endpoint_url += url
        response = self.session.request(method, endpoint_url, headers=self.headers, json=data).json()
        oauthToken = response['oauthToken']
        ig.headers['Authorization'] = oauthToken['token_type'] + ' ' + oauthToken['access_token']
        ig.headers['IG-ACCOUNT-ID'] = response['accountId']

    def getWorkingOrders(self):
        self.headers['Version'] = '2'
        method = 'GET'
        url = '/workingorders'
        endpoint_url = ig.ENDPOINT_URL
        endpoint_url += url
        response = self.session.request(method, endpoint_url, headers=self.headers).json()
        return response

    def getPrices(self, data):
        self.headers['Version'] = '3'
        method = 'GET'
        url = '/prices'
        endpoint_url = ig.ENDPOINT_URL
        endpoint_url += url
        endpoint_url += '/' + data['epic'] + '?resolution=' + data['resolution'] + '&from=' \
                        + data['start_date'] + '&to=' + data['end_date']
        response = self.session.request(method, endpoint_url, headers=self.headers).json()
        response.update(epic=data['epic'], resolution=data['resolution'])
        return response

    def getLatestPrices(self, data):
        self.headers['Version'] = '3'
        method = 'GET'
        url = '/prices'
        endpoint_url = ig.ENDPOINT_URL
        endpoint_url += url
        endpoint_url += '/' + data['epic'] + '?resolution=' + data['resolution'] + '&max=2'  # hardcoded
        response = self.session.request(method, endpoint_url, headers=self.headers).json()
        response.update(epic=data['epic'], resolution=data['resolution'])
        return response


class TradingTools():
    def __init__(self):
        pass

    @staticmethod
    def strToTime(time, destination):
        global source_time_format
        if 'T' in time:
            source_time_format = '%Y-%m-%dT%H:%M:%S'
        elif '/' in time:
            source_time_format = '%Y/%m/%d %H:%M:%S'
        mysql_time_format = '%Y-%m-%d %H:%M:%S'
        broker_time_format = '%Y-%m-%dT%H:%M:%S'
        # change raw string datetime to datetime object
        raw_datetime = datetime.datetime.strptime(time, source_time_format)
        mysql_datetime = raw_datetime.strftime(mysql_time_format)
        broker_datetime = raw_datetime.strftime(broker_time_format)
        return mysql_datetime if destination.upper() == 'DB' else broker_datetime

    def parsePrices(self, d_getPrice, response):
        l_prices = []
        for price in response['prices']:
            data = dict(epic=d_getPrice.get('epic'),
                        resolution=d_getPrice.get('resolution'),
                        snapshotTime=TradingTools.strToTime(price.get('snapshotTime'), 'DB'),
                        snapshotTimeUTC=TradingTools.strToTime(price.get('snapshotTimeUTC'), 'DB'),
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
        return l_prices

    def selectActionTable(self):
        global conn, mycursor, query, rows
        try:
            conn = cn.connect(user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD,
                              host=ig.MYSQL_HOST, database=ig.MYSQL_DATABASE)
            mycursor = conn.cursor(buffered=True, dictionary=True)
            query = """
            SELECT *
            FROM action
            """
            mycursor.execute(query)
            rows = mycursor.fetchall()
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
        finally:
            mycursor.close()
            conn.close()
        return rows

    def updateActionTable(self, action_name, action_value, action_message):
        global conn, mycursor, query
        try:
            conn = cn.connect(user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD,
                              host=ig.MYSQL_HOST, database=ig.MYSQL_DATABASE)
            mycursor = conn.cursor(buffered=True)
            query = """
             update action
             set action_value = %(action_value)s, action_message = %(action_message)s
             where action_name = %(action_name)s
             and coalesce(action_value, '') <> %(action_value)s
             """
            d_action = dict(action_name=action_name, action_value=action_value, action_message=action_message)
            mycursor.execute(query, d_action)
            conn.commit()
            if d_action.get('action_name') == 'batch_status':
                if d_action.get('action_value') == 'R':
                    print('****************** BATCH RUNNING ******************')
                    print('Start time: ', datetime.datetime.now())
                    print()
                elif d_action.get('action_value') == 'C':
                    print()
                    print('End time: ', datetime.datetime.now())
                    print('****************** BATCH COMPLETED ******************')
            else:
                print('ACTION: [', d_action.get('action_name'), '] = ', d_action.get('action_value'))
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
        finally:
            mycursor.close()
            conn.close()

    def insertPrices(self, l_prices):
        global conn, mycursor, query, i, epic, resolution
        try:
            conn = cn.connect(user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD,
                              host=ig.MYSQL_HOST, database=ig.MYSQL_DATABASE)
            mycursor = conn.cursor(buffered=True, dictionary=True)
            query = """insert into price (epic, resolution, snapshotTime, snapshotTimeUTC, openPrice_bid, 
            openPrice_ask, openPrice_mid, closePrice_bid, closePrice_ask, closePrice_mid, highPrice_bid, 
            highPrice_ask, highPrice_mid, lowPrice_bid, lowPrice_ask, lowPrice_mid, lastTradedVolume) 
            select %(epic)s, %(resolution)s, %(snapshotTime)s, %(snapshotTimeUTC)s, %(openPrice_bid)s, 
            %(openPrice_ask)s, %(openPrice_mid)s, %(closePrice_bid)s, %(closePrice_ask)s, %(closePrice_mid)s, 
            %(highPrice_bid)s, %(highPrice_ask)s, %(highPrice_mid)s, %(lowPrice_bid)s, %(lowPrice_ask)s, 
            %(lowPrice_mid)s, %(lastTradedVolume)s from dual where not exists (select 1 from price p where
            p.epic = %(epic)s and p.resolution = %(resolution)s and p.snapshotTime = %(snapshotTime)s and 
            p.snapshotTimeUTC = %(snapshotTimeUTC)s and p.lastTradedVolume = %(lastTradedVolume)s) """
            i = 0
            for l_price in l_prices:
                mycursor.execute(query, l_price)
                i += mycursor.rowcount
                epic, resolution = l_price.get('epic'), l_price.get('resolution')
            conn.commit()
            print('PRICE [', epic, '-', resolution, ']: ', i, 'records inserted') if i > 0 \
                else print('PRICE [', epic, '-', resolution, ']: Nothing to insert')
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
        finally:
            mycursor.close()
            conn.close()

    def selectLatestPrices(self, d_selectLatestPrices):
        global conn, mycursor, query, rows, updated_rows
        try:
            conn = cn.connect(user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD,
                              host=ig.MYSQL_HOST, database=ig.MYSQL_DATABASE)
            mycursor = conn.cursor(buffered=True, dictionary=True)
            query = """
            SELECT *
            FROM vw_minmax_available_price
            WHERE 1=1 
            """
            if d_selectLatestPrices:
                query += " AND epic='" + d_selectLatestPrices.get('epic') + "'"
                query += " AND resolution='" + d_selectLatestPrices.get('resolution') + "'"
            mycursor.execute(query)
            rows = mycursor.fetchall()
            updated_rows = []
            for row in rows:
                row.update(start_date=row.get('max_snapshotTime').strftime('%Y-%m-%dT%H:%M:%S'))
                updated_rows.append(row)
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
        finally:
            mycursor.close()
            conn.close()
        return updated_rows

    def parseActionTable(self, d_action_table):
        d_action_names = {}
        for row in d_action_table:
            for key, val in row.items():
                if key == 'action_name':
                    d_action_names[val] = dict(row)
        return d_action_names

    def selectMissingAnalysis(self, d_selectMissingAnalysis):
        global conn, mycursor, query, rows
        try:
            conn = cn.connect(user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD,
                              host=ig.MYSQL_HOST, database=ig.MYSQL_DATABASE)
            mycursor = conn.cursor(buffered=True, dictionary=True)
            query = """
            SELECT *
            FROM vw_missing_analysis
            WHERE 1=1 
            """
            if d_selectMissingAnalysis:
                query += " AND epic='" + d_selectMissingAnalysis.get('epic') + "'"
                query += " AND resolution='" + d_selectMissingAnalysis.get('resolution') + "'"
            mycursor.execute(query)
            rows = mycursor.fetchall()
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
        finally:
            mycursor.close()
            conn.close()
        return rows

    def updateAnalysisTable(self, d_updateAnalysisTable):
        try:
            cnx = create_engine(
                'mysql+pymysql://' + ig.MYSQL_USERNAME + ':' + ig.MYSQL_PASSWORD + '@' + ig.MYSQL_HOST + '/' + ig.MYSQL_DATABASE)
            for d_updateAnalysisRow in d_updateAnalysisTable:
                query = """
                select *
                from vw_missing_analysis_details
                where epic = %(epic)s and resolution = %(resolution)s
                order by epic, resolution, snapshotTime_from
                """
                df = pd.read_sql(query, cnx, params=d_updateAnalysisRow, index_col=['snapshotTime_from'])
                if df.dropna().empty:
                    print('ANALYSIS: Nothing to update')
                else:
                    # add EMA 22
                    df['ema_22'] = ta.EMA(df, timeperiod=22, price='close') #hardcoded
                    # round them to 8 decimals
                    df = df.round({'ema_22': 8}) #hardcoded
                    query = """
                    truncate table temp_analysis
                    """
                    cnx.execute(query)
                    # drop columns to fit temp table
                    delColumns = ['epic', 'resolution', 'open', 'high', 'low', 'close']
                    for delColumn in delColumns: df.pop(delColumn)
                    df.reset_index(drop=True, inplace=True)
                    df.set_index('price_id_fk', inplace=True)
                    df.to_sql(name='temp_analysis', con=cnx, if_exists='append')
                    # hardcoded
                    query = """
                    update price_analysis pa
                    join temp_analysis t on t.price_id_fk = pa.price_id_fk
                    SET pa.ema_22 = coalesce(t.ema_22, pa.ema_22)
                    """
                    cnx.execute(query)
                    print('ANALYSIS: [', d_updateAnalysisRow.get('epic'), '-', d_updateAnalysisRow.get('resolution'), ']: Updated')
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
        finally:
            cnx.dispose()

    def deletePrices(self, days):
        global conn, mycursor, query, i
        try:
            conn = cn.connect(user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD,
                              host=ig.MYSQL_HOST, database=ig.MYSQL_DATABASE)
            mycursor = conn.cursor(buffered=True)
            query = """
            DELETE
            FROM price
            WHERE snapshotTime <= ADDDATE(CURRENT_TIMESTAMP(), INTERVAL -%s day)
            """
            i = 0
            t_days = (days, )
            mycursor.execute(query, t_days)
            i += mycursor.rowcount
            conn.commit()
            print('CLEANED: ', i, 'records') if i > 0 else print('CLEANED: Nothing')
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
        finally:
            mycursor.close()
            conn.close()