import pandas as pd
import os
from odsl import sdk
from dotenv import load_dotenv
import datetime

load_dotenv()
user=os.getenv('user')
apikey=os.getenv('apikey')

odsl = sdk.ODSL()
odsl.setStage("local")
odsl.loginWithAPIKey(user,apikey)

# 15 Minutely aggregation
limit=100000
skip=0
match="{'$match':{'event':'#TENNET.EL.BALANCING:DELTA_PRICES','eventstart':{'$gte':'2024-12-31T23:00:00'}}}"
group="{'$group':{'_id':{'$dateTrunc':{'date':'$eventstart','unit':'minute','binSize':15}},'MID_PRICE':{'$avg':'$MID_PRICE'},'PICASSO_OUT':{'$sum':'$PICASSO_OUT'}}}"
sort="{'$sort':{'_id':1}}"
pipeline="[" + match + "," + group + "," + sort + "]"

print(datetime.datetime.now().time())
data=odsl.list('event','public',{'_aggregate':pipeline,'_limit':limit,'_skip':skip})
print(datetime.datetime.now().time())
print("Got " + str(len(data)) + " rows")
more = len(data) == limit

while more:
	skip += 100000
	print(datetime.datetime.now().time())
	dtmp=odsl.list('event','public',{'_aggregate':pipeline,'_limit':limit,'_skip':skip})
	print(datetime.datetime.now().time())
	print("Got " + str(len(dtmp)) + " rows")
	data += dtmp
	more = len(dtmp) == limit

df = pd.DataFrame(data)
df.set_index('_id', inplace=True)
df.index = [f"{dt}T00:00:00" if len(dt) == 10 else dt for dt in df.index]
df.index = pd.to_datetime(df.index, utc=True).tz_convert('Europe/Amsterdam').tz_localize(None)

print(df.info())
print(df.head())