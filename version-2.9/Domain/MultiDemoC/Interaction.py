 # -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:          		Interaction.py
 Model description:     <description>
 Authors:       		ASUS
 Organization:  		<your organization>
 Current date & time:   2016-10-14 09:13:57.868000
 License:       		GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message
import time


### Model class ----------------------------------------------------------------
class Interaction(DomainBehavior):
	''' DEVS Class for the model Interaction
	'''

	def __init__(self):
		''' Constructor.
		'''
		DomainBehavior.__init__(self)
		self.interactionQueue = None
		self.destinationToPort = {}
		self.msg = Message(None, None)
		self.initPhase('IDLE',0)
		self.count = 0

	def setInteraction (self, interactionQueue):
		self.interactionQueue = interactionQueue;
		# Build correspondence between Destination and Port number
		for o in self.OPorts :
			for dest in o.outLine :
				self.destinationToPort[dest.hostDEVS.getModelName()] = o 
				#print(dest.hostDEVS.getModelName() + ' --> ' + o.name)

	def extTransition(self, *args):
		''' DEVS external transition function. 
		'''
		return self.getState()

	def outputFnc(self):
		''' DEVS output function.
		'''
		if self.phaseIs('ACTIVE'):
			#print('Send msg to ADD_INTERCEPTOR Tm='+str(self.msg.time)+' Tc='+str(self.timeNext))
			#print(self.msg)
			return self.poke(self.destinationToPort[self.msg.value[0]], self.msg)
		return {}

	def intTransition(self):
		''' DEVS internal transition function.
		'''
		time.sleep(1.0)
		#print('INTERACTION check T=' + str(self.timeNext))
		if self.interactionQueue != None and not self.interactionQueue.empty():
			msg = self.interactionQueue.get()
			self.count+=1
			#print(msg)
			self.msg.value = [msg['destination'], self.count, msg['value']]
			self.msg.time  = self.timeNext
			self.holdIn('ACTIVE',0.0)
		else :
			#print('No msg')
			self.holdIn('WAIT',1.0)
		
		return self.getState()

	def timeAdvance(self):
		''' DEVS Time Advance function.
		'''
		return self.getSigma()

	def finish(self, msg):
		''' Additional function which is lunched just before the end of the simulation.
		'''
		pass

	def confTransition(self, inputs):
		'''DEFAULT Confluent Transition Function.
		'''
		self.state = self.intTransition()
		self.state = self.extTransition(inputs)
		return self.getState()
