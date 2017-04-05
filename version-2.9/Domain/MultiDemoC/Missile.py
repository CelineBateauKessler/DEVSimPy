# -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:          Missile.py
 Model:         <describe model>
 Authors:       L. Capocchi (capocchi@univ-corse.fr)
 Organization:  SPE UMR 6134
 Date:          09.26.2016
 License:       GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message

from random import random, uniform
import math

markerMissileUpdate      = dict(symbol='circle', size='5', color='rgb(255,0,0)')
markerMissileIntercepted = dict(symbol='cross', size='10', color='rgb(255,0,0)')
markerMissileSuccessful  = dict(symbol='star', size='10', color='rgb(255,0,0)')

### Model class ----------------------------------------------------------------
class Missile(DomainBehavior):
	''' DEVS Class for Missile model
	'''

	def __init__(self, travelCount=10, killZone=2.0, spaceSize = 10):
		''' Constructor.
		'''
		DomainBehavior.__init__(self)

		### local copy
		self.travelcount = travelCount
		self.killZone = killZone
		self.spaceSize = spaceSize

		self.count = 0
		self.loc = (self.spaceSize*uniform(0,1),self.spaceSize*uniform(0,1))
		self.initPhase('Update', 1.0)

	def extTransition(self, *args):
		''' DEVS external transition function.
		'''

		###  Fire state transition functions
		if self.phaseIs('Update'):
			### adapted with PyPDEVS
			if hasattr(self, 'peek'):
				msg = self.peek(self.IPorts[0])
				msgs = [msg.value]
			else:
				inputs = args[0].get(self.IPorts[0])
				# inputs looks like this : [msg1, date1, msg2, date2, ..., msgN, dateN]
				# msg is a dict, date is a tuple
				msgs   = filter(lambda a: isinstance(a, dict), inputs)				

			### 'without reschedule' or 'eventually' used: not rescheduling events
			### Fire state and port specific external transition functions

			### for all messages
			for m in msgs: # val
				if m['status'] == 'outIntercept':
					x = m['x']
					y = m['y']
					dist = self.distance((x,y), self.loc)
					if dist < self.killZone:
						#print("*** Interception of " + self.name)
						self.holdIn('Intercept', 0.0)

		return self.state

	def distance(self,c1,c2):
		'''  Euclidean distance
		'''
		return sum([(x-y)**2 for (x,y) in zip(c1,c2)])**(0.5)

	def outputFnc(self):
		''' DEVS output function.
		'''
		output_port = self.OPorts[0]
		source = self.getBlockModel().label if hasattr(self, 'getBlockModel') else self.name
		
		if self.phaseIs('Update'):
			addon = 'Landed' if self.count == self.travelcount else "Update"
			#output_msg = Message(['outStateUpdate:'+label+":"+addon], self.timeNext)
			#output_msg = Message({'source':label, 'location':self.loc, 'status':addon}, self.timeNext)
			output_msg = Message({'source':source, 
								'x':self.loc[0], 'y':self.loc[1], 
								'keepXY':False,
								'marker':markerMissileUpdate,
								'status':addon,
								'label':'Missile'+addon}, 
								self.timeNext)
			return self.poke(output_port, output_msg)

		elif self.phaseIs('Intercept'):
			#output_msg = Message(['outStateUpdate:'+label+":"+"Intercepted"], self.timeNext)
			#output_msg = Message({'source':label, 'location':self.loc, 'status':'Intercepted'}, self.timeNext)
			output_msg = Message({'source':source, 
								'x':self.loc[0], 'y':self.loc[1], 
								'keepXY':True,
								'marker':markerMissileIntercepted,
								'status':'Intercepted',
								'label':'MissileIntercepted'}, 
								self.timeNext)
			return self.poke(output_port, output_msg)
		
		elif self.phaseIs('InTargetZone'):
			#output_msg = Message(['outStateUpdate:'+label+":"+"Intercepted"], self.timeNext)
			#output_msg = Message({'source':label, 'location':self.loc, 'status':'Intercepted'}, self.timeNext)
			output_msg = Message({'source':source, 
								'x':self.loc[0], 'y':self.loc[1], 
								'keepXY':True,
								'marker':markerMissileSuccessful,
								'status':'InTargetZone',
								'label':'MissileSuccessful'}, 
								self.timeNext)
			return self.poke(output_port, output_msg)

		else:
			return {}

	def intTransition(self):
		''' DEVS internal transition function.
		'''

		"""if self.phaseIs('Update'):
			self.holdIn('Repeat', 0.0)

			if self.count == self.travelcount:
				self.passivateIn('InTargetZone')

		elif self.phaseIs('Repeat'):
			self.holdIn('Update', 1.0)

			self.count += 1
			if self.count == self.travelcount:
				timeToEnterZone = random()
				if timeToEnterZone < 1:
					self.holdIn('Update', timeToEnterZone)

		elif self.phaseIs('Intercept'):
			self.passivate()"""
			
		if self.phaseIs('Update'):
			
			self.count += 1
			if self.count == self.travelcount:
				timeToEnterZone = random()
				#print('*** ' + self.name + ' in target zone ' + str(timeToEnterZone))
				self.holdIn('InTargetZone', timeToEnterZone)
			else:
				self.holdIn('Update', 1.0)

		elif self.phaseIs('InTargetZone'):
			self.passivate()			

		elif self.phaseIs('Intercept'):
			self.passivate()

		return self.state

	def timeAdvance(self):
		''' DEVS Time Advance function.
		'''
		return self.state['sigma']

	def confTransition(self, inputs):
		'''DEFAULT Confluent Transition Function.
		'''
		self.state = self.intTransition()
		self.state = self.extTransition(inputs)
		return self.state

	def finish(self, msg):
		''' Additional function which is lunched just before the end of the simulation.
		'''
		pass
