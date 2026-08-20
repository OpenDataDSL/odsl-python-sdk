import time
import os
import numpy as np
from odsl import sdk
from dotenv import load_dotenv

load_dotenv()
tid=os.getenv('tid')
appid=os.getenv('appid')
secret=os.getenv('secret')

# Login using app and secret
odsl = sdk.ODSL()
odsl.loginWithSecret(tid, appid, secret)

# by eventtime and isp
events = odsl.list('event', 'public', {'_filter':'{"$and": [{"event": "#TENNET.EL.BID_PRICE_LADDER.15MIN:MERIT_ORDER"}, {"eventtime": "2025-01-04T23:00:00Z"}, {"isp": 1}]}'})
print(events)

# by eventtime, isp and volume
events = odsl.list('event', 'public', {'_filter':'{"$and": [{"event": "#TENNET.EL.BID_PRICE_LADDER.15MIN:MERIT_ORDER"}, {"eventtime": "2025-01-04T23:00:00Z"}, {"isp": 1}, {"capacity_threshold": 10}]}'})
print(events)

# by eventtime, hourmin
events = odsl.list('event', 'public', {'_filter':'{"$and": [{"event": "#TENNET.EL.BID_PRICE_LADDER.15MIN:MERIT_ORDER"}, {"eventtime": "2025-01-04T23:00:00Z"}, {"hourmin": "00:00"}]}'})
print(events)

# by starttime range
print(odsl.headers('event', 'public', {'_limit':-1, '_filter':'{"$and": [{"event": "#TENNET.EL.BID_PRICE_LADDER.15MIN:MERIT_ORDER"}, {"eventstart": {"$gte": "2025-01-04T21:00:00Z", "$lte":"2025-01-04T23:45:00Z"}}]}'}))
events = odsl.list('event', 'public', {'_limit':-1, '_filter':'{"$and": [{"event": "#TENNET.EL.BID_PRICE_LADDER.15MIN:MERIT_ORDER"}, {"eventstart": {"$gte": "2025-01-04T21:00:00Z", "$lte":"2025-01-04T23:45:00Z"}}]}'})
for e in events:
	print(e["eventstart"])


# Get multiple timeseries
mts = odsl.list('data', 'all', {'_id':'EEX.EM.DE.T3PA.SPOT:AUC_PRICE,EEX.EM.EU.EAA3.SPOT:AUC_PRICE'})
print(mts)


abn = odsl.list('object', 'public', {'source':'ECB'})
for a in abn:
    print(a['_id'])

obj = odsl.get('object', 'public', '#ECB')
print(obj['description'])
ts = odsl.get('data', 'public', '#ABN_FX.EURUSD:SPOT', {'_range':'from(2024-07-01)'})
print(ts)

# # Get a curve

id = '#AEMO.EL.AU.NEM.NSW1.FORECAST:DEMAND:2024-07-15'
curve = odsl.get('data', 'public', id)
for c in curve['contracts']:
	print(c['tenor'] + " - " + str(c['value']))

# # Test functions
print('Function')
f = odsl.function('calendar', 'holiday-report', None, {'_id':'#HENG', 'start':'2024-01-01', 'end': '2024-12-31'})
print(f)

f = odsl.function('calendar', 'holidays', '#HENG')
print(f)

