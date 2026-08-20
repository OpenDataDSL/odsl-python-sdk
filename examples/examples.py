import pandas as pd
import os
from odsl import sdk
from dotenv import load_dotenv

load_dotenv()
user=os.getenv('user')
apikey=os.getenv('apikey')

odsl = sdk.ODSL()
odsl.loginWithAPIKey(user,apikey)

# Get EUR/GBP Spot FX rate from ECB
ts = odsl.get('data', 'public', '#ECB_FX.EURGBP:SPOT', {'_range': 'from(2026-01-01)'})
df = pd.DataFrame(ts['data'], columns=['time', 'value'])
print(df)

# Get a curve
curve = odsl.get('data', 'public', '#ECB_IR.ESTR.EURO_SHORT_TERM_RATE:RATE:2026-05-26')
df_curve = pd.DataFrame(curve['contracts'], columns=['tenor', 'value'])
print(df_curve)

