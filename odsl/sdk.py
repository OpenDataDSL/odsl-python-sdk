import requests
from msal import PublicClientApplication, ConfidentialClientApplication
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
        
    def get(self, service, source, id, params=None):
        if self.token == None:
            print("Not logged in: call login() first")
            return
        headers = {'Authorization':'Bearer ' + self.token["access_token"]}
        eid = quote(id)
        r = requests.get(self.url + service + "/v1/" + source + "/" + eid, headers=headers, params=params)
        if r.status_code == 200:
            return r.json()
        return r.text
    
    def function(self, service, name, id=None, params=None):
        if self.token == None:
            print("Not logged in: call login() first")
            return
        headers = {'Authorization':'Bearer ' + self.token["access_token"]}
        if params == None:
            params = {'_function':name}
        else:
            params['_function'] = name
        url = self.url + service + "/v1"
        if id != None:
            source = 'private'
            if id.startswith('#'):
                source = 'public'
            eid = quote(id)
            url = url + "/" + source + "/" + eid
            print(url)
        r = requests.get(url, headers=headers, params=params)
        if r.status_code == 200:
            return r.json()
        return r.text
    
    def list(self, service, source='private', params=None):
        if self.token == None:
            print("Not logged in: call login() first")
            return
        headers = {'Authorization':'Bearer ' + self.token["access_token"]}
        r = requests.get(self.url + service + "/v1/" + source, headers=headers, params=params)
        if r.status_code == 200:
            return r.json()
        return r.text        

    def update(self, service, source, var, params=None):
        if self.token == None:
            print("Not logged in: call login() first")
            return
        headers = {'Authorization':'Bearer ' + self.token["access_token"]}        
        body = json.JSONEncoder().encode(o=var)
        r = requests.post(self.url + service, headers=headers, data=body, params=params)
        print(r.status_code)

    def login(self):
        accounts = self.app.get_accounts()
        s = ["api://opendatadsl/api_user"]
        if accounts:
            self.token = self.app.acquire_token_silent(scopes=s, account=accounts[0])
        else:
            self.token = self.app.acquire_token_interactive(scopes=s)
        if "access_token" in self.token:
            return
        print("Token acquisition failed: " + self.token["error_description"])
        
    def loginWithSecret(self, tenant, clientId, secret):
        authority = "https://login.microsoft.com/" + tenant
        s = ["api://opendatadsl/.default"]
        ccapp = ConfidentialClientApplication(client_id=clientId, client_credential=secret, authority=authority)
        self.token = ccapp.acquire_token_for_client(scopes=s)
        if "access_token" in self.token:
            return
        print("Token acquisition failed: " + self.token["error_description"])

    def logout(self):
        self.token = None
        self.cache.logout()


