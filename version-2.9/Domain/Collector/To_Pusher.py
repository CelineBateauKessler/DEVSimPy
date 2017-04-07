# -*- coding: utf-8 -*-

"""
Name : To_Pusher.py
Brief descritpion : Atomic Model pushing results to a web socket
Author(s) : Celine KESSLER
Version :  2.0
Last modified : 12/05/2016
GENERAL NOTES AND REMARKS:
GLOBAL VARIABLES AND FUNCTIONS:
"""

### just for python 2.5
from __future__ import with_statement

from QuickScope import *

import random
from decimal import *
import os 
from datetime import datetime
import pusher
import json

#  ================================================================    #
class To_Pusher(QuickScope):
	"""	Atomic Model writing on the disk.
	"""

	###
	def __init__(self, app_id='178867', key='c2d255356f53779e6020', secret='9d41a54d45d25274df63', pusherChannel='mySimu'):
		""" Constructor.

			@param app_id  : PUSHER identifier
			@param key     : PUSHER key
			@param secret  : PUSHER secret key--> from PUSHER subscription
			@param channel : PUSHER channel identifier
			@param event   : PUSHER event identifier

		"""
		QuickScope.__init__(self)

		#decimal precision
		getcontext().prec = 6

		### last time value for delete engine
		'''self.last_time_value = {}
		self.buffer = {}'''

		### Interface with the web socket broker : Pusher
		self.app_id = app_id
		self.key = key
		self.secret = secret
		self.pusher = pusher.Pusher(app_id=self.app_id,key=self.key,secret=self.secret,ssl=True,port=443)
		#self.pusher_data = []
		#self.push_time = datetime.today()
		self.pusherChannel = pusherChannel
		self.event = 'output'

		print(self.pusherChannel)
		print(self.event)
	###
	def extTransition(self, *args):
		"""
		"""
		
		for port in self.IPorts:
			
			msgs = []
			
			# Get label
			#############
			# If the port has been given a name then use it as port Label
			# otherwise use the name of the first source connected to this port
			# Then if the message has a label use it
			# otherwise use the port Label
			if 'port' not in port.name :
				# this means that the port has been given a specific name by the modeler
				# then use this name
				portLabel = port.name
			else :
				# If several sources are connected to 1 port
				# the label will be the name of the first source
				if hasattr(self, 'peek'):
					portLabel = port.inLine[0].host.name 
				else: # PyPDEVS
					portLabel = port.inLine[0].hostDEVS.name
				
			if hasattr(self, 'peek'):
				msg  = self.peek(port)
				msgs =[{'label': portLabel, 
						'result':{'time': msg.time, 'value':msg.value}}] 
				if isinstance(msg.value, dict) and msg.value.has_key('label'):
					msgs[len(msgs)-1]['label'] = msg.value['label']
				#msgsVal  = [msg.value[0]]
				#msgsTime = [msg.time] 
				
			else: #PyPDEVS adaptation
				""" inputs is an array looking like that :
				[value1, (time1, counter1), value2, (time2, counter2), ... ,valueN, (timeN, counterN)]
				"""
				inputs = args[0].get(port)
				#print (inputs)
				
				if inputs :
					isValue = True
					for input in inputs:
						if isValue:
							try:
								value = input[0]
							except:
								value = input
						else:
							time = input[0]
							msgs.append({'label':portLabel, 
						    	       'result':{'time': time, 'value':value}}) 
							if isinstance(value, dict) and value.has_key('label'):
								msgs[len(msgs)-1]['label'] = value['label'] 
						isValue = not isValue 
					
				"""if inputs:
					msgsVal  = filter(lambda a: isinstance(a, dict), inputs)
					msgsTime = filter(lambda a: isinstance(a, tuple), inputs)"""
			
			if len(msgs) > 0:
				#print('TO PUSHER :')
				#print(msgs)
				self.pusher.trigger(self.pusherChannel, self.event, json.dumps(msgs))
			#self.pusher_data.append({'label': str(t), 'value':str(v)})
			
			#self.last_time_value[fn] = t
			#self.buffer[fn] = v"""

		self.state["sigma"] = 0
		return self.state

	def intTransition(self):
	    """now = datetime.today()
	    if (len(self.pusher_data) == 50) or (now - self.push_time).seconds >= 1:
			self.pusher.trigger(self.channel, self.event, json.dumps(self.pusher_data))
			print('PUSH')
			del self.pusher_data[:]
			self.push_time = now
	    self.state["status"] = 'IDLE'"""
	    self.state["sigma"] = INFINITY
	    return self.state

	def finish(self, msg):
		#self.pusher.trigger(self.channel, self.event, json.dumps(self.pusher_data))
		pass
	###
	def __str__(self):return "To_Pusher"
