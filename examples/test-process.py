import asyncio
import os

from dotenv import load_dotenv
from odsl import process
from odsl import sdk

load_dotenv()
user=os.getenv('user')
apikey=os.getenv('apikey')
task=os.getenv('task')

odsl = sdk.ODSL()
odsl.setStage("local")
odsl.loginWithAPIKey(user,apikey)

async def run():
	t = odsl.get('process-task', None, task)
	print(t)
	if t is not None:
		p = odsl.get('process', None, t['name'])
		if p is not None:
			print(p)
			odsl_process = process.TASK(p, t)
			await odsl_process.startProcess()
			await odsl_process.startPhase("EXTRACT")
			await odsl_process.logMessage("Extracting data from ???")
			await odsl_process.endPhase("success", "Completed Extraction")
			await odsl_process.endProcess("success", "Completed Successfully")

asyncio.run(run())
print("Finished Process Task")
print("-----------------------")