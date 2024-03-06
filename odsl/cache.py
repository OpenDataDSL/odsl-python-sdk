import os
import msal
import atexit

class TokenCacheAspect:
    filedir = os.path.expanduser('~') + "/AppData/Roaming/ODSL/"
    filename = filedir + ".odsl"
    data = None
    cache = msal.SerializableTokenCache()
    
    def __init__(self):
        self.cache.deserialize(open(self.filename, "r").read())
        atexit.register(lambda:
            open(self.filename, "w").write(self.cache.serialize()))
        
    def getCache(self):
        return self.cache
    
    def logout(self):
        os.remove(self.filename)