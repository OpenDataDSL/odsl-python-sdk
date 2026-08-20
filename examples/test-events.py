import pandas as pd
import os
from odsl import sdk
from dotenv import load_dotenv
import datetime
import time
import json

load_dotenv()
user=os.getenv('user')
apikey=os.getenv('apikey')

odsl = sdk.ODSL()
odsl.loginWithAPIKey(user,apikey)

def send_odsl_request(odsl, event, start, end, project):
	range={'$gte':start, '$lt':end}    
	filter="{'event':'" + event + "','eventstart':" + json.dumps(range) + "}"
	sort="{'eventstart':1}"
	limit=100000
	skip=0
	data=[]
	more=True

	while more:
		success=False
		while success==False:
			try:
				print(datetime.datetime.now().time())
				dtmp=odsl.list('event','public',{'_filter':filter,'_sort':sort,'_limit':limit,'_skip':skip,'_project':json.dumps(project)})
				print("Got " + str(len(dtmp)) + " rows")
				print(datetime.datetime.now().time())
				data += dtmp
				skip += limit
				more = len(dtmp) == limit
				success=True
			except:
				success=False
				print("Failed - retrying")
				time.sleep(5)
    
    # Create the dataframe
	if len(data) > 0:
		df = pd.DataFrame(data)
		df.set_index('eventstart', inplace=True)
		df.index = [f"{dt}T00:00:00" if len(dt) == 10 else dt for dt in df.index]
		df.index = pd.to_datetime(df.index, utc=True).tz_convert('Europe/Amsterdam').tz_localize(None)
		return df
	return pd.DataFrame()

def send_odsl_aggregate(odsl, event, start, end, project, minutes):
	range={'$gte':start, '$lt':end}    
	filter="{'event':'" + event + "','eventstart':" + json.dumps(range) + "}"
	match="{'$match':" + filter + "}"
	fields={'_id':{'$dateTrunc': {'date':'$eventstart','unit':'minute','binSize':minutes}}}
	for x in project:
		fields[x] = project[x]
	group=json.dumps({'$group':fields})
	sort="{'$sort':{'_id':1}}"
	pipeline="[" + match + "," + group + "," + sort + "]"
	limit=100000
	skip=0
	data=[]
	more=True

	while more:
		success=False
		while success==False:
			try:
				print(datetime.datetime.now().time())
				dtmp=odsl.list('event','public',{'_aggregate':pipeline,'_limit':limit,'_skip':skip})
				print("Got " + str(len(dtmp)) + " rows")
				print(datetime.datetime.now().time())
				data += dtmp
				skip += limit
				more = len(dtmp) == limit
				success=True
			except:
				success=False
				print("Failed - retrying")
				time.sleep(5)
    
    # Create the dataframe
	if len(data) > 0:
		df = pd.DataFrame(data)
		df.set_index('_id', inplace=True)
		df.index = [f"{dt}T00:00:00" if len(dt) == 10 else dt for dt in df.index]
		df.index = pd.to_datetime(df.index, utc=True).tz_convert('Europe/Amsterdam').tz_localize(None)
		return df
	return pd.DataFrame()


# Raw minutely data retrieval example
project={'_id':0,'eventstart':1,'MIN_PRICE':1,'MAX_PRICE':1,'MID_PRICE':1,'DOWNWARD_DISPATCH':1,'UPWARD_DISPATCH':1,'RESERVE_DOWNWARD_DISPATCH':1,'RESERVE_UPWARD_DISPATCH':1,'PICASSO_IN':1,'PICASSO_OUT':1}
df = send_odsl_request(odsl, '#TENNET.EL.BALANCING:DELTA_PRICES', '2024-12-31T23:00:00', '2025-08-26T23:00:00', project)

# 15min Aggregation example
# project={'MID_PRICE':{'$avg':'$MID_PRICE'},'PICASSO_OUT':{'$sum':'$PICASSO_OUT'}}
# df = send_odsl_aggregate(odsl, '#TENNET.EL.BALANCING:DELTA_PRICES', '2024-12-31T23:00:00', '2025-08-26T23:00:00', project, 15)

print(df.info())
print(df.head())


