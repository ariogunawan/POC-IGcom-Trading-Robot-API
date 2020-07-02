import inspect
from datetime import datetime
from dateutil import tz
import mysql.connector as cn
import requests
import ig_constant as ig
import pandas as pd
from talib import abstract as ta
from sqlalchemy import create_engine

# HARDCODED PARTS
# 1. IGWrapper.getLatestPrices
# 2. TradingTools.updateAnalysisTable
# 3. Database:
# - vw_missing_analysis (WHERE condition)
# - vw_price_analysis (COLUMN to add from analysis table)
# - price_analysis
# - temp_analysis
# END HARDCODED PARTS

class IGWrapper():
    def __init__(self):
        self.session = requests.Session()
        self.headers = ig.headers
        method = 'POST'
        url = '/session'
        data = dict(identifier=ig.IG_API_USERNAME, password=ig.IG_API_PASSWORD)
        endpoint_url = ig.IG_ENDPOINT_URL
        endpoint_url += url
        response = self.session.request(method, endpoint_url, headers=self.headers, json=data).json()
        oauthToken = response['oauthToken']
        ig.headers['Authorization'] = oauthToken['token_type'] + ' ' + oauthToken['access_token']
        ig.headers['IG-ACCOUNT-ID'] = response['accountId']

    def getWorkingOrders(self):
        self.headers['Version'] = '2'
        method = 'GET'
        url = '/workingorders'
        endpoint_url = ig.IG_ENDPOINT_URL
        endpoint_url += url
        response = self.session.request(method, endpoint_url, headers=self.headers).json()
        return response

    def getPrices(self, d_getPrices):
        self.headers['Version'] = '3'
        method = 'GET'
        url = '/prices'
        endpoint_url = ig.IG_ENDPOINT_URL
        endpoint_url += url
        endpoint_url += '/' + d_getPrices['epic'] + '?resolution=' + d_getPrices['resolution'] + '&from=' \
                        + d_getPrices['start_date'] + '&to=' + d_getPrices['end_date']
        response = self.session.request(method, endpoint_url, headers=self.headers).json()
        response.update(epic=d_getPrices['epic'], resolution=d_getPrices['resolution'])
        return response

    def getLatestPrices(self, d_getLatestPrice):
        self.headers['Version'] = '3'
        method = 'GET'
        url = '/prices'
        endpoint_url = ig.IG_ENDPOINT_URL
        endpoint_url += url
        endpoint_url += '/' + d_getLatestPrice['epic'] + '?resolution=' + d_getLatestPrice['resolution'] + '&max=2'  # hardcoded
        response = self.session.request(method, endpoint_url, headers=self.headers).json()
        response.update(epic=d_getLatestPrice['epic'], resolution=d_getLatestPrice['resolution'])
        return response

    def getWatchlists(self, d_getWatchLists):
        self.headers['Version'] = '1'
        method = 'GET'
        url = '/watchlists'
        endpoint_url = ig.IG_ENDPOINT_URL
        endpoint_url += url
        if not(d_getWatchLists is None):
            endpoint_url += '/' + d_getWatchLists['id']
        response = self.session.request(method, endpoint_url, headers=self.headers).json()
        return response

    def getMarkets(self, epic):
        self.headers['Version'] = '3'
        method = 'GET'
        url = '/markets'
        endpoint_url = ig.IG_ENDPOINT_URL
        endpoint_url += url
        if not(epic is None):
            endpoint_url += '/' + epic
        response = self.session.request(method, endpoint_url, headers=self.headers).json()
        return response

class TradingTools():
    def __init__(self):
        pass

    def raiseError(error_message):
        conn = cn.connect(user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD,
                          host=ig.MYSQL_HOST, database=ig.MYSQL_DATABASE)
        mycursor = conn.cursor(buffered=True)
        query = """
        insert into error_log (error_log_message) values (%s)
        """
        mycursor.execute(query, (error_message, ))
        conn.commit()
        print('RAISED ERROR: ', error_message)
        mycursor.close()
        conn.close()

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
        raw_datetime = datetime.strptime(time, source_time_format)
        mysql_datetime = raw_datetime.strftime(mysql_time_format)
        broker_datetime = raw_datetime.strftime(broker_time_format)
        return mysql_datetime if destination.upper() == 'DB' else broker_datetime
    
    @staticmethod
    def utcToLocal(utctime):
        from_zone = tz.tzutc()
        to_zone = tz.tzlocal()
        utctime = datetime.strptime(utctime, '%Y-%m-%d %H:%M:%S')
        # Tell the datetime object that it's in UTC time zone since
        # datetime objects are 'naive' by default
        utctime = utctime.replace(tzinfo=from_zone)
        # Convert time zone
        localtime = utctime.astimezone(to_zone)
        return localtime

    def datediff(self, date1, date2):
        diff = date2 - date1
        days, seconds = diff.days, diff.seconds
        hours = diff.total_seconds() / 3600
        minutes = (diff.days*1440 + diff.seconds/60)
        seconds = seconds % 60
        return hours, minutes, seconds

    def loadCurrency(self, d_loadCurrency):
        method = 'GET'
        url = '/latest'
        endpoint_url = ig.FIXER_ENDPOINT_URL
        endpoint_url += url
        endpoint_url += '?access_key=' + ig.FIXER_API_KEY + '&base=' + d_loadCurrency.get('base') + '&symbols='
        symbols = ','.join(d_loadCurrency.get('symbols'))
        endpoint_url += symbols
        session = requests.session()
        response = session.request(method, endpoint_url).json()
        return response

    def insertCurrency(self, d_insertCurrency):
        global conn, mycursor, query, i, epic, resolution
        try:
            conn = cn.connect(user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD,
                              host=ig.MYSQL_HOST, database=ig.MYSQL_DATABASE)
            mycursor = conn.cursor(buffered=True, dictionary=True)
            query = """
            truncate table currency
            """
            mycursor.execute(query)
            conn.commit()
            query = """
            insert into currency (currency_code, base_value, currency_effdatetime)
            select %(base)s, 1, %(currency_effdatetime)s from dual         
            where not exists (select 1 from currency c 
            where c.currency_code = %(base)s 
            and c.currency_effdatetime = %(currency_effdatetime)s)
            union
            select %(currency_code)s, %(base_value)s, %(currency_effdatetime)s from dual
            where not exists (select 1 from currency c 
            where c.currency_code = %(currency_code)s 
            and c.currency_effdatetime = %(currency_effdatetime)s)
            """
            utctime = datetime.utcfromtimestamp(d_insertCurrency.get('timestamp')).strftime('%Y-%m-%d %H:%M:%S')
            localtime = TradingTools.utcToLocal(utctime).strftime('%Y-%m-%d %H:%M:%S')
            l_rates = d_insertCurrency.get('rates').items()
            l_currency = []
            for t in l_rates:
                d_currency = dict(base=d_insertCurrency.get('base'), currency_code=t[0], base_value=t[1], currency_effdatetime=localtime)
                l_currency.append(d_currency)
            i = 0
            for l_symbol in l_currency:
                mycursor.execute(query, l_symbol)
                i += mycursor.rowcount
            conn.commit()
            print('CURRENCY EXCHANGE: ', i, 'records updated') if i > 0 \
                else print('CURRENCY EXCHANGE: Nothing to update')
            # UPDATE action table
            TradingTools.updateActionTable('load_currency_rates', None, None, localtime)
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
            error_message = inspect.currentframe().f_code.co_name + ': ' + str(e)
            TradingTools.raiseError(error_message)
        finally:
            mycursor.close()
            conn.close()

    def parsePrices(self, d_getPrice, response):
        l_prices = []
        for price in response['prices']:
            data = dict(epic=d_getPrice['epic'],
                        resolution=d_getPrice['resolution'],
                        snapshotTime=TradingTools.strToTime(price['snapshotTime'], 'DB'),
                        snapshotTimeUTC=TradingTools.strToTime(price['snapshotTimeUTC'], 'DB'),
                        openPrice_bid=price['openPrice']['bid'],
                        openPrice_ask=price['openPrice']['ask'],
                        openPrice_mid=round((price['openPrice']['bid'] + price['openPrice']['ask']) / 2, 8),
                        closePrice_bid=price['closePrice']['bid'],
                        closePrice_ask=price['closePrice']['ask'],
                        closePrice_mid=round((price['closePrice']['bid'] + price['closePrice']['ask']) / 2, 8),
                        highPrice_bid=price['highPrice']['bid'],
                        highPrice_ask=price['highPrice']['ask'],
                        highPrice_mid=round((price['highPrice']['bid'] + price['highPrice']['ask']) / 2, 8),
                        lowPrice_bid=price['lowPrice']['bid'],
                        lowPrice_ask=price['lowPrice']['ask'],
                        lowPrice_mid=round((price['lowPrice']['bid'] + price['lowPrice']['ask']) / 2, 8),
                        lastTradedVolume=price['lastTradedVolume']
                        )
            l_prices.append(data)
        return l_prices

    def parseWatchlists(self, l_watchlists):
        l_res_watchlists = []
        for l_watchlist in l_watchlists:
            d_watchlist = dict(epic=l_watchlist['instrument']['epic'],
                               name=l_watchlist['instrument']['name'],
                               forceOpenAllowed=l_watchlist['instrument']['forceOpenAllowed'],
                               stopsLimitsAllowed=l_watchlist['instrument']['stopsLimitsAllowed'],
                               lotSize=l_watchlist['instrument']['lotSize'],
                               unit=l_watchlist['instrument']['unit'],
                               type=l_watchlist['instrument']['type'],
                               marketId=l_watchlist['instrument']['marketId'],
                               currencyCode=l_watchlist['instrument']['currencies'][0]['code'],
                               currencySymbol=l_watchlist['instrument']['currencies'][0]['symbol'],
                               currencyBaseExchangeRate=l_watchlist['instrument']['currencies'][0]['baseExchangeRate'],
                               currencyExchangeRate=l_watchlist['instrument']['currencies'][0]['exchangeRate'],
                               marginDepositBands=l_watchlist['instrument']['marginDepositBands'][0]['margin'],
                               marginFactor=l_watchlist['instrument']['marginFactor'],
                               marginFactorUnit=l_watchlist['instrument']['marginFactorUnit'],
                               chartCode=l_watchlist['instrument']['chartCode'],
                               valueOfOnePip=l_watchlist['instrument']['valueOfOnePip'],
                               onePipMeans=l_watchlist['instrument']['onePipMeans'],
                               contractSize=l_watchlist['instrument']['contractSize'],
                               minStepDistanceUnit=l_watchlist['dealingRules']['minStepDistance']['unit'],
                               minStepDistanceValue=l_watchlist['dealingRules']['minStepDistance']['value'],
                               minDealSizeUnit=l_watchlist['dealingRules']['minDealSize']['unit'],
                               minDealSizeValue=l_watchlist['dealingRules']['minDealSize']['value'],
                               minGuaranteedSLUnit=l_watchlist['dealingRules']['minControlledRiskStopDistance']['unit'],
                               minGuaranteedSLValue=l_watchlist['dealingRules']['minControlledRiskStopDistance']['value'],
                               minNormalSLUnit=l_watchlist['dealingRules']['minNormalStopOrLimitDistance']['unit'],
                               minNormalSLValue=l_watchlist['dealingRules']['minNormalStopOrLimitDistance']['value'],
                               trailingStopsPreference=l_watchlist['dealingRules']['trailingStopsPreference'],
                               marketStatus=l_watchlist['snapshot']['marketStatus'],
                               decimalPlacesFactor=l_watchlist['snapshot']['decimalPlacesFactor'],
                               scalingFactor=l_watchlist['snapshot']['scalingFactor']
                               )
            l_res_watchlists.append(d_watchlist)
        return l_res_watchlists

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
            error_message = inspect.currentframe().f_code.co_name + ': ' + str(e)
            TradingTools.raiseError(error_message)
        finally:
            mycursor.close()
            conn.close()
        return rows

    @staticmethod
    def updateActionTable(action_name, action_value, action_message, action_datetime):
        global conn, mycursor, query
        try:
            conn = cn.connect(user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD,
                              host=ig.MYSQL_HOST, database=ig.MYSQL_DATABASE)
            mycursor = conn.cursor(buffered=True)
            query = """
             update action
             set action_datetime = action_datetime 
             """
            if not(action_value is None):
                query += """
                 , action_value = %(action_value)s
                """
            if not(action_message is None):
                query += """
                 , action_message = %(action_message)s
                """
            if not(action_datetime is None):
                query += """
                 , action_datetime = %(action_datetime)s
                """
            query += """
             where action_name = %(action_name)s
            """
            d_action = dict(action_name=action_name, action_value=action_value, action_message=action_message, action_datetime=action_datetime)
            mycursor.execute(query, d_action)
            conn.commit()
            if d_action.get('action_name') == 'batch_status':
                if d_action.get('action_value') == 'R':
                    print('****************** BATCH RUNNING ******************')
                    print('Start time: ', datetime.now())
                    print()
                elif d_action.get('action_value') == 'C':
                    print()
                    print('End time: ', datetime.now())
                    print('****************** BATCH COMPLETED ******************')
            else:
                print('ACTION: [', d_action.get('action_name'), '] = ', d_action.get('action_value'))
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
            error_message = inspect.currentframe().f_code.co_name + ': ' + str(e)
            TradingTools.raiseError(error_message)
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
            error_message = inspect.currentframe().f_code.co_name + ': ' + str(e)
            TradingTools.raiseError(error_message)
        finally:
            mycursor.close()
            conn.close()

    def insertWatchlists(self, l_parsed_watchlists):
        global conn, mycursor, query, i
        try:
            conn = cn.connect(user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD,
                              host=ig.MYSQL_HOST, database=ig.MYSQL_DATABASE)
            mycursor = conn.cursor(buffered=True, dictionary=True)
            query = """insert into watchlist (epic, name, forceOpenAllowed, stopsLimitsAllowed, lotSize, unit, type, marketId, currencyCode, currencySymbol, currencyBaseExchangeRate, currencyExchangeRate, marginDepositBands, marginFactor, marginFactorUnit, chartCode, valueOfOnePip, onePipMeans, contractSize, minStepDistanceUnit, minStepDistanceValue, minDealSizeUnit, minDealSizeValue, minGuaranteedSLUnit, minGuaranteedSLValue, minNormalSLUnit, minNormalSLValue, trailingStopsPreference, marketStatus, decimalPlacesFactor, scalingFactor) 
            select %(epic)s, %(name)s, %(forceOpenAllowed)s, %(stopsLimitsAllowed)s, %(lotSize)s, %(unit)s, %(type)s, %(marketId)s, %(currencyCode)s, %(currencySymbol)s, %(currencyBaseExchangeRate)s, %(currencyExchangeRate)s, %(marginDepositBands)s, %(marginFactor)s, %(marginFactorUnit)s, %(chartCode)s, %(valueOfOnePip)s, %(onePipMeans)s, %(contractSize)s, %(minStepDistanceUnit)s, %(minStepDistanceValue)s, %(minDealSizeUnit)s, %(minDealSizeValue)s, %(minGuaranteedSLUnit)s, %(minGuaranteedSLValue)s, %(minNormalSLUnit)s, %(minNormalSLValue)s, %(trailingStopsPreference)s, %(marketStatus)s, %(decimalPlacesFactor)s, %(scalingFactor)s
            from dual where not exists (select 1 from watchlist w where w.epic = %(epic)s) """
            i = 0
            for l_parsed_watchlist in l_parsed_watchlists:
                mycursor.execute(query, l_parsed_watchlist)
                i += mycursor.rowcount
            conn.commit()
            print('WATCHLIST: ', i, 'records inserted') if i > 0 \
                else print('WATCHLIST: Nothing to insert')
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
            error_message = inspect.currentframe().f_code.co_name + ': ' + str(e)
            TradingTools.raiseError(error_message)
        finally:
            mycursor.close()
            conn.close()

    def updateWatchlists(self, l_parsed_watchlists):
        global conn, mycursor, query, i
        try:
            conn = cn.connect(user=ig.MYSQL_USERNAME, password=ig.MYSQL_PASSWORD,
                              host=ig.MYSQL_HOST, database=ig.MYSQL_DATABASE)
            mycursor = conn.cursor(buffered=True, dictionary=True)
            query = """update watchlist w 
            set name  = %(name)s, forceOpenAllowed  = %(forceOpenAllowed)s, stopsLimitsAllowed  = %(stopsLimitsAllowed)s, lotSize  = %(lotSize)s, unit  = %(unit)s, type  = %(type)s, marketId  = %(marketId)s, currencyCode  = %(currencyCode)s, currencySymbol  = %(currencySymbol)s, currencyBaseExchangeRate  = %(currencyBaseExchangeRate)s, currencyExchangeRate  = %(currencyExchangeRate)s, marginDepositBands  = %(marginDepositBands)s, marginFactor  = %(marginFactor)s, marginFactorUnit  = %(marginFactorUnit)s, chartCode  = %(chartCode)s, valueOfOnePip  = %(valueOfOnePip)s, onePipMeans  = %(onePipMeans)s, contractSize  = %(contractSize)s, minStepDistanceUnit  = %(minStepDistanceUnit)s, minStepDistanceValue  = %(minStepDistanceValue)s, minDealSizeUnit  = %(minDealSizeUnit)s, minDealSizeValue  = %(minDealSizeValue)s, minGuaranteedSLUnit  = %(minGuaranteedSLUnit)s, minGuaranteedSLValue  = %(minGuaranteedSLValue)s, minNormalSLUnit  = %(minNormalSLUnit)s, minNormalSLValue  = %(minNormalSLValue)s, trailingStopsPreference  = %(trailingStopsPreference)s, marketStatus  = %(marketStatus)s, decimalPlacesFactor  = %(decimalPlacesFactor)s, scalingFactor  = %(scalingFactor)s
            where epic = %(epic)s
            """
            i = 0
            for l_parsed_watchlist in l_parsed_watchlists:
                mycursor.execute(query, l_parsed_watchlist)
                i += mycursor.rowcount
            conn.commit()
            print('WATCHLIST: ', i, 'records updated') if i > 0 \
                else print('WATCHLIST: Nothing to update')
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
            error_message = inspect.currentframe().f_code.co_name + ': ' + str(e)
            TradingTools.raiseError(error_message)
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
            error_message = inspect.currentframe().f_code.co_name + ': ' + str(e)
            TradingTools.raiseError(error_message)
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
            error_message = inspect.currentframe().f_code.co_name + ': ' + str(e)
            TradingTools.raiseError(error_message)
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
                    # hardcoded
                    # add EMA 22
                    df['ema_22'] = ta.EMA(df, timeperiod=22, price='close')
                    # add engulfing
                    df['cdl_engulfing'] = ta.CDLENGULFING(df['open'], df['high'], df['low'], df['close'])
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
                    SET pa.ema_22 = coalesce(t.ema_22, pa.ema_22),
                    pa.cdl_engulfing = coalesce(t.cdl_engulfing, pa.cdl_engulfing)
                    """
                    cnx.execute(query)
                    print('ANALYSIS [', d_updateAnalysisRow.get('epic'), '-', d_updateAnalysisRow.get('resolution'), ']: Updated')
        except (cn.Error, cn.Warning) as e:
            print('Something wrong with ', inspect.currentframe().f_code.co_name)
            print('Query = ', query)
            print('Error = ', e)
            error_message = inspect.currentframe().f_code.co_name + ': ' + str(e)
            TradingTools.raiseError(error_message)
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
            error_message = inspect.currentframe().f_code.co_name + ': ' + str(e)
            TradingTools.raiseError(error_message)
        finally:
            mycursor.close()
            conn.close()