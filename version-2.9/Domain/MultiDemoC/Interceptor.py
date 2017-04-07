# -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:          Interceptor.py
 Model:         <describe model>
 Authors:       L. Capocchi (capocchi@univ-corse.fr), J.F Santucci (santucci@univ-corse.fr)
 Organization:  UMR CNRS 6134
 Date:         09.26.2016
 License:      GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message

from random import random,uniform

markerInterceptorFlying  = dict(symbol='circle', size='5', color='rgb(0,255,0)')
markerInterceptorExploded = dict(symbol='star', size='10', color='rgb(0,255,0)')

### Model class ----------------------------------------------------------------
class Interceptor(DomainBehavior):
	''' DEVS Class for Interceptor model
	'''

	def __init__(self, spaceSize = 10):
		''' Constructor.
		'''
		DomainBehavior.__init__(self)

		self.spaceSize = spaceSize
		self.msg = Message(None, None)
		self.interceptLocation = (self.spaceSize*uniform(0,1), self.spaceSize*uniform(0,1))
		self.initPhase('Update', 1.0)

	def outputFnc(self):
		''' DEVS output function.
		'''

		if self.phaseIs('Update'):
			status = 'Update'
			marker = markerInterceptorFlying
		else :
			status = 'outIntercept' # = Exploded
			marker = markerInterceptorExploded
			
		label = self.getBlockModel().label if hasattr(self, 'getBlockModel') else self.name
		#self.msg = Message({'source':label, 'location':self.interceptLocation, 'status':status}, self.timeNext)
		self.msg = Message({'source':label, 
						'x':self.interceptLocation[0], 'y':self.interceptLocation[1], 
						'keepXY':(status!='Update'),
						'marker':marker,
						'status':status,
						'label':'Interceptors'+status}, 
						self.timeNext)
		return self.poke(self.OPorts[0], self.msg)
		#else:			return {}

	def intTransition(self):
		''' DEVS internal transition function.
		'''
		if self.phaseIs('Update'):
 			timeToIntercept = 15.*random()
 			#print 'timeToIntercept', timeToIntercept
 			if timeToIntercept < 1:
 				self.holdIn('Repeat', timeToIntercept)
 			else:
 				self.holdIn('Update', 1.0)

 		elif self.phaseIs('Repeat'):
 			self.passivateIn('Expended')

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
