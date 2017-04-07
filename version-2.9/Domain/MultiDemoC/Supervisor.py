# -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:          Supervisor.py
 Model:         <describe model>
 Authors:       L. Capocchi (capocchi@univ-corse.fr)
 Organization:  UMR CNRS 6134
 Date:          10-05-2016
 License:       GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message

import MultiDemo
#from Domain.MultiDemo import Missile, Sensor, Interceptor
from Domain.Collector import MessagesCollector

import os

### Model class ----------------------------------------------------------------
class Supervisor(DomainBehavior):
	''' DEVS Class for Supervisor model
	'''

	def __init__(self, nbMissile = 10, nbInterceptor=10, nbSensor=10, missileTravelCount=10, missileKillZone=2.0, missileSpaceSize=10, sensorExpectUpdateTime=2.0):
		''' Constructor.
		'''
		DomainBehavior.__init__(self)

		assert(nbMissile==nbSensor)

		### lcoal copy
		self.nbMissile = nbMissile
		self.nbInterceptor=nbInterceptor
		self.nbSensor=nbSensor
		self.missileTravelCount = missileTravelCount
		self.missileKillZone=missileKillZone
		self.missileSpaceSize=missileSpaceSize
		self.sensorExpectUpdateTime=sensorExpectUpdateTime

		self.initPhase('CreateModels', 0.0)

	def extTransition(self, inputs=None):
		''' DEVS external transition function.
		'''
		return self.state

	def outputFnc(self):
		''' DEVS output function.
		'''
		
		if self.phaseIs('ACTIVE'):
			return self.poke(self.OPorts[0], Message({}, self.timeNext))
		else:
			return {}

	def intTransition(self):
		''' DEVS internal transition function.
		'''

		### adapted with PyPDEVS
		if hasattr(self, 'peek'):
			mv = self.OPorts[0].outLine[0].host
		else:
			mv = self.OPorts[0].outLine[0].hostDEVS
			#mv = self.parent
			if hasattr(mv, 'fullName'): del mv.fullName

		### create interceptor am
		for i in xrange(self.nbInterceptor):
			m = Interceptor.Interceptor()

			m.name = ''.join([m.__class__.__name__,str(i)])
			m.timeNext = m.timeLast = m.myTimeAdvance = 0.
			m.addOutPort()
			mv.addSubModel(m)

		### create missile am
		for i in xrange(self.nbMissile):
			m = Missile.Missile(self.missileTravelCount, self.missileKillZone, self.missileSpaceSize)

			m.name = '_'.join([m.__class__.__name__,str(i)])
			m.timeNext = m.timeLast = m.myTimeAdvance = 0.
			m.addInPort()
			m.addOutPort()
			mv.addSubModel(m)
		
		### create sensor am
		for i in range(self.nbSensor):
			s = Sensor.Sensor(self.sensorExpectUpdateTime)

			s.name = s.__class__.__name__+'_'+str(i)
			s.timeNext = s.timeLast = s.myTimeAdvance = 0.
			s.addInPort()
			s.addOutPort()

			### create MessageColector am
			path = os.path.join(os.getcwd(), s.name)
			mc = MessagesCollector.MessagesCollector(fileName=path)
			mc.timeNext = mc.timeLast = mc.myTimeAdvance = 0.
			mc.addInPort()

			### adding
			mv.addSubModel(s)
			mv.addSubModel(mc)

			### coupling
			mv.connectPorts(s.OPorts[0],mc.IPorts[0])

		### coupling
		interceptor_list = filter(lambda model: isinstance(model, Interceptor.Interceptor), mv.componentSet)
		missile_list = filter(lambda model: isinstance(model, Missile.Missile), mv.componentSet)	
		sensor_list = filter(lambda model: isinstance(model, Sensor.Sensor), mv.componentSet)
		
		for interceptor in interceptor_list:
			for missile in missile_list:
				mv.connectPorts(interceptor.OPorts[0],missile.IPorts[0])

		for missile in missile_list:
			for sensor in sensor_list:
				mv.connectPorts(missile.OPorts[0],sensor.IPorts[0])

			### coupling with mv
			mv.connectPorts(missile.OPorts[0], mv.OPorts[0])

		### change state
		if self.phaseIs('CreateModels'):
			self.holdIn('ACTIVE', 0.5)
		else:
			self.passivate()

		return self.state

	def timeAdvance(self):
		''' DEVS Time Advance function.
		'''
		return self.state['sigma']

	def finish(self, msg):
		''' Additional function which is lunched just before the end of the simulation.
		'''
		pass

	def confTransition(self, inputs):
		'''DEFAULT Confluent Transition Function.
		'''
		self.state = self.intTransition()
		self.state = self.extTransition(inputs)
		return self.state

	def modelTransition(self, state):
		''' modelTransition method will be called at every step
			in simulated time on every model that transitioned
			in order to notify parent of structural change.
			Dynamic structure is possible for both Classic and Parallel DEVS,
			but only for local simulation.
		'''
		# Notify parent of structural change
		state['status'] = 'Active'
		return True
