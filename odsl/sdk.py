import requests
from msal import PublicClientApplication
import json
from odsl import cache
from urllib.parse import quote


class ODSL:
    url = 'https://odsl.azurewebsites.net/api/'
    token = None
    cache = cache.TokenCacheAspect()
    app = PublicClientApplication(client_id='d3742f5f-3d4d-4565-a80a-ebdefaab8d08', authority="https://login.microsoft.com/common", token_cache=cache.getCache())
    
    def setStage(self, stage):
        if stage == 'dev':
            self.url = 'https://odsl-dev.azurewebsites.net/api/'
        if stage == 'local':
            self.url = 'http://localhost:7071/api/'
        if stage == 'prod':
            self.url = 'https://odsl.azurewebsites.net/api/'       
        
    def get(self, service, source, id):
        if self.token == None:
            print("Not logged in: call login() first")
            return
        headers = {'Authorization':'Bearer ' + self.token["access_token"]}
        eid = quote(id)
        r = requests.get(self.url + service + "/v1/" + source + "/" + eid, headers=headers)
        if r.status_code == 200:
            # x = json.loads(r.text, object_hook=lambda d: SimpleNamespace(**d))
            return r.json()
        return r.text
    
    def list(self, service, source='private', filter=None):
        if self.token == None:
            print("Not logged in: call login() first")
            return
        headers = {'Authorization':'Bearer ' + self.token["access_token"]}
        params = None
        if filter:
            params = filter
        r = requests.get(self.url + service + "/v1/" + source, headers=headers, params=params)
        if r.status_code == 200:
            return r.json()
        return r.text        

    def update(self, service, source, var, options=None):
        if self.token == None:
            print("Not logged in: call login() first")
            return
        headers = {'Authorization':'Bearer ' + self.token["access_token"]}        
        body = json.JSONEncoder().encode(o=var)
        r = requests.post(self.url + service, headers=headers, data=body)
        print(r.status_code)

    def login(self):
        accounts = self.app.get_accounts()
        if accounts:
            self.token = self.app.acquire_token_silent(["email", "profile", "openid", "offline_access", "api://opendatadsl/api_user"], account=accounts[0])
        else:
            self.token = self.app.acquire_token_interactive(["email", "profile", "openid", "offline_access", "api://opendatadsl/api_user"])
        if "access_token" in self.token:
            return
        print("Token acquisition failed: " + self.token["error_description"])

    def logout(self):
        self.token = None
        self.cache.logout()


