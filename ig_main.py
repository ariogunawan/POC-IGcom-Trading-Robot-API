from ig_class import IGWrapper, TradingTools
from datetime import datetime
from decimal import Decimal

trade = IGWrapper()
util = TradingTools()

# SELECT action table from db
d_action_table = util.selectActionTable()
# PARSE action table into dictionary
d_action_names = util.parseActionTable(d_action_table)

# CHECK batch section
if d_action_names['batch_status'].get('action_value') != 'C':
    print('Process halted! Batch Status = ', d_action_names['batch_status'].get('action_value'))
    exit()
else:
    util.updateActionTable('batch_status', 'R', None, None)

# LOAD currency rates for today section
currency_datediff = util.datediff(d_action_names['load_currency_rates'].get('action_datetime'), datetime.now())
if d_action_names['load_currency_rates'].get('action_value') == 'Y' \
        and currency_datediff[0] >= int(d_action_names['load_currency_rates'].get('action_message')):
    d_loadCurrency = dict(base='EUR', symbols=['USD', 'AUD', 'JPY', 'GBP', 'XAU', 'NZD', 'CHF', 'CAD', 'IDR'])
    d_insertCurrency = (util.loadCurrency(d_loadCurrency))
    util.insertCurrency(d_insertCurrency)

# INSERT & UPDATE Watchlists
if d_action_names['update_watchlists'].get('action_value') == 'Y':
    d_getWatchlists = trade.getWatchlists(None).get('watchlists')
    for d_getWatchlist in d_getWatchlists:
        if d_getWatchlist.get('name') == 'My Watchlist':
            break
    d_markets = trade.getWatchlists(d_getWatchlist).get('markets')
    l_markets = []
    for d_market in d_markets:
        l_markets.append(trade.getMarkets(d_market.get('epic')))
    # PARSE Watchlists
    l_parsed_watchlists = util.parseWatchlists(l_markets)
    # INSERT Watchlists into db
    util.insertWatchlists(l_parsed_watchlists)
    # UPDATE Watchlists
    util.updateWatchlists(l_parsed_watchlists)

# UPDATE price section
if d_action_names['update_price'].get('action_value') == 'Y':
    # SELECT latest prices from database
    d_selectLatestPrices = dict()
    res_latest_db_prices = util.selectLatestPrices(d_selectLatestPrices)
    # GET last available prices from the broker
    res_latest_broker_prices = []
    for res_latest_db_price in res_latest_db_prices:
        res_latest_broker_prices.append(trade.getLatestPrices(res_latest_db_price))
    d_getPrices = []
    for res_latest_broker_price, res_latest_db_price in zip(res_latest_broker_prices, res_latest_db_prices):
        if res_latest_db_price.get('epic') == res_latest_broker_price.get('epic') \
                and res_latest_db_price.get('resolution') == res_latest_broker_price.get('resolution'):
            d_getPrice = res_latest_db_price
            d_getPrice.update(
                end_date=util.strToTime(res_latest_broker_price['prices'][0].get('snapshotTime'), 'Broker'))
            d_getPrices.append(d_getPrice)
    # PARSE prices from broker to be inserted into db
    for d_getPrice in d_getPrices:
        inputParsePrices = trade.getPrices(d_getPrice)
        l_prices = util.parsePrices(d_getPrice, inputParsePrices)
        # INSERT prices into db
        util.insertPrices(l_prices)

# UPDATE indicator and analysis table
if d_action_names['update_analysis'].get('action_value') == 'Y':
    # SELECT missing analysis
    res_missing_items = util.selectMissingAnalysis(None)
    # UPDATE analysis table
    util.updateAnalysisTable(res_missing_items)

# CHECK robot trading
if d_action_names['robot_trading'].get('action_value') == 'Y':
    # Number of open positions
    l_entry_configurations = []
    for d_entry_configuration in util.selectEntryConfiguration():
        for d_watchlist in util.loadWatchlists():
            if d_entry_configuration['epic'] == d_watchlist['epic']:
                d_entry_configuration['watchlist'] = d_watchlist
                l_entry_configurations.append(d_entry_configuration)
    # Get last positions
    d_tradePositions = trade.getPositions()
    # ENTRY!
    for d_entry_configuration in l_entry_configurations:
        d_entry_variables = trade.setEntryVariables(trade.getPositions(), trade.getAccounts())
        # Find last position for each epic
        d_entry_configuration['last_open_position'] = None
        if d_entry_variables['open_position'] > 0:
            l_latestPositions = util.getLatestPositions(d_tradePositions)
            for d_latestPosition in l_latestPositions:
                if d_latestPosition['epic'] == d_entry_configuration['epic']:
                    diff = datetime.utcnow() - d_latestPosition['createdDateUTC']
                    days, seconds = diff.days, diff.seconds
                    hours = days * 24 + seconds // 3600
                    minutes = (seconds % 3600) // 60
                    if minutes < d_entry_configuration['delay_minute']:
                        d_entry_configuration['last_open_position'] = 'Failed'
        # Make decision based on environment
        d_trade_decision = util.tradeDecision(d_entry_variables, d_entry_configuration)
        # Find entry point pattern
        d_trade_decision['resolution'] = 'MINUTE_5'
        d_trade_decision['limit'] = 15
        d_trade_strategy = util.tradeStrategy(d_trade_decision)
        if d_trade_strategy['finalResult'] == 'Passed':
            d_createPosition = dict(epic=d_trade_decision['epic'],
                                    expiry='-',
                                    direction=d_trade_strategy['orderType'],
                                    size=float(d_trade_decision['entry_size']),
                                    orderType='MARKET',
                                    timeInForce=None,
                                    level=None,
                                    guaranteedStop=False,
                                    stopLevel=None,
                                    stopDistance=d_trade_decision['stop_loss'],
                                    trailingStop=None,
                                    trailingStopIncrement=None,
                                    forceOpen=True,
                                    limitLevel=None,
                                    limitDistance=d_trade_decision['take_profit'],
                                    quoteId=None,
                                    currencyCode=d_trade_decision['currency_code'])
            d_position = trade.createPosition(d_createPosition)
            if not(d_position is None):
                print('POSITION', '[', d_trade_decision['epic'], ']: ', d_trade_strategy['orderType'], ' - ', d_position['dealReference'])

# CLEAN UP
if d_action_names['truncate_old_data'].get('action_value') == 'Y':
    util.deletePrices(d_action_names['truncate_old_data'].get('action_message'))
# EXIT
util.updateActionTable('batch_status', 'C', None, None)
