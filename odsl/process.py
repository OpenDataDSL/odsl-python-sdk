import os
import json
import datetime
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus import ServiceBusMessage

class TASK:
	def __init__(self, process, task, odsl=None):
		"""process = the process record, task = the process task record,
		odsl = optional sdk.ODSL client: everything it does is then linked to this run (provenance trace)"""
		self.process = process
		self.task = task
		# Provenance: the trace this run belongs to (passed on by whatever started it), else the run itself
		self.trace = task.get('trace') or task['_id']
		if odsl is not None:
			odsl.setTrace(self.trace, process['name'], task['_id'], self.ondate())
		self.started = False
		self.inphase = False
		self.sb_client = ServiceBusClient.from_connection_string(os.environ["ODSL_SB_CPM"], logging_enable=True)
		self.queue_name = os.environ['ODSL_STAGE'] + "/process-execution"

	def ondate(self):
		"""The date this run loads data for: the task input called ondate (any case), or None"""
		inp = self.task.get('input')
		if isinstance(inp, dict):
			for k, v in inp.items():
				if k.lower() == 'ondate' and v:
					return str(v)[:10]
		return None

	async def startProcess(self):
		if not self.started:
			self.started = True
			print("Starting process for task " + self.task['_id'])
			message = ProcessMessage(self.process, self.task)
			message.setStatus("start")
			message.setMessage("Initialising Process")
			await self.updateProcess(message)

	async def endProcess(self, status, mess):
		message = ProcessMessage(self.process, self.task)
		message.setStatus(status)
		message.setMessage(mess)
		await self.updateProcess(message)
  
	async def startPhase(self, name):
		self.phase = ProcessMessage(self.process, self.task)
		self.phase.setStatus("running")
		self.phase.setMessage("Initialising Phase: " + name)
		self.phase.setPhase(name)
		await self.updateProcess(self.phase)
		self.inphase = True
   
	async def endPhase(self, status, mess):
		self.phase.data['timestamp'] = datetime.datetime.now().isoformat()
		self.phase.setStatus(status)
		self.phase.setMessage(mess)
		level = "fatal" if status == "failed" else "info"
		lm = datetime.datetime.now().isoformat() + "[UTC] " + level + " " + mess
		self.phase.log.append(lm)
		await self.updateProcess(self.phase)
		self.inphase = False

	async def logMessage(self, level, mess):
		lm = datetime.datetime.now().isoformat() + "[UTC] " + level + " " + mess
		self.phase.log.append(lm)
		if level == "WARNING" or level == "SEVERE":
			self.phase.warnings.append(lm)
		await self.updateProcess(self.phase)

	async def updateProcess(self, message):
		sbm = ServiceBusMessage(message.toJson())
		sbm.application_properties = dict()
		sbm.application_properties['tenantid'] = self.task['tid']
		sbm.application_properties['environment'] = self.task['environment']
		sbm.application_properties['trace'] = message.data['trace']
		sender = self.sb_client.get_queue_sender(queue_name=self.queue_name)
		async with sender:
			await sender.send_messages(sbm)
		message.log.clear()
		message.warnings.clear()

class ProcessMessage:
	def __init__(self, process, task):
		self.log = []
		self.warnings = []
		self.data = dict()
		self.data['timestamp'] = datetime.datetime.now().isoformat()
		self.data['type'] = "ProcessMessage"
		self.data['id'] = task['_id']
		self.data['tenantid'] = task['tid']
		self.data['service'] = process['service']
		self.data['name'] = process['name']
		self.data['stage'] = os.environ['ODSL_STAGE']
		self.data['environment'] = task['environment']
		self.data['trigger'] = task['trigger']
		self.data['triggerTime'] = task['triggerTime']
		self.data['reason'] = task['reason']
		self.data['trace'] = task.get('trace') or task['_id']
		self.data['log'] = self.log
		self.data['warnings'] = self.warnings

	def toJson(self):
		return json.dumps(self.data)

	def setStatus(self, status):
		self.data['status'] = status

	def setMessage(self, message):
		self.data['message'] = message

	def setPhase(self, name):
		self.data['phase'] = name
