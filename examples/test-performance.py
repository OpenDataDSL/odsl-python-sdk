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


def performance_stats(service, source, id, params, iterations):
	quantiles = [0.5, 0.9, 0.95, 0.99]
	measurements = []

	for x in range(iterations):
		start = time.time()
		obj = odsl.get(service, source, id, params)
		# print(obj)
		end = time.time()
		measurements.append(end - start)

	stats = np.array(measurements)
	print("Mean: ", np.mean(stats))
	print("Min: ", np.min(stats))
	print("Max: ", np.max(stats))
	print("Percentiles: ", np.percentile(stats, quantiles))

performance_stats('object', 'public', '#ECB', None, 100)

