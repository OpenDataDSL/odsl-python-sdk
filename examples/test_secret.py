import os

from dotenv import load_dotenv
from odsl import sdk

load_dotenv()
user=os.getenv('user')
apikey=os.getenv('apikey2')


odsl = sdk.ODSL()
odsl.setStage("dev")
odsl.loginWithSecret(os.getenv('tid'), os.getenv('appid'), os.getenv('secret'))
# odsl.loginWithAPIKey(user, apikey)

obj = odsl.get('object', 'public', '#ECB')
print(obj)
print(obj['description'])
