# -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:          Sensor.py
 Model:         <describe model>
 Authors:       L. Capocchi (capocchi@univ-corse.fr)
 Organization:  SPE UMR CNRS 6134
 Date:          09.26.2016
 License:       GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message

### Model class ----------------------------------------------------------------
class Sensor(DomainBehavior):
	''' DEVS Class for Sensor model
	'''

	def __init__(self, expectUpdateTime=2):
		''' Constructor.
		'''
		DomainBehavior.__init__(self)

		### local copy
		self.expectUpdateTime = expectUpdateTime

		### init the phase
		self.initPhase('GetUpdate', self.expectUpdateTime)
		self.sensorId = 'SensorUnknown'   
		self.missileId= 'MissileUnknown'
		self.missileStatus=None

	def extTransition(self, *args):
		''' DEVS external transition function.
		'''
		self.sensorId = self.getBlockModel().label if hasattr(self, 'getBlockModel') else self.name  
		id_label = self.sensorId.split('_')[-1] 
		self.missileId= 'Missile_'+id_label		

		#print('*** MSG FOR SENSOR_'+id_label+' ***')
		if hasattr(self, 'peek'):
			msg = self.peek(self.IPorts[0])
			if msg.value['source']==self.missileId:
				self.missileStatus = msg.value['status']
		else:
			inputs = args[0].get(self.IPorts[0])
			# inputs looks like this : [msg1, date1, msg2, date2, ..., msgN, dateN]
			msgs   = filter(lambda a: isinstance(a, dict), inputs)
			# message is a dict, date is a tuple
			# Keep only missile information corresponding to the missile tracked by this sensor
			for m in msgs:
				if m['source']==self.missileId:
					self.missileStatus = m['status']

		return self.state

	def outputFnc(self):
		''' DEVS output function.
		'''
		if self.missileStatus != None:
			return self.poke(self.OPorts[0],
							 Message({'source':self.sensorId,'missile':self.missileId, 'status':self.missileStatus}, self.timeNext))
		else:
			return{}

	def intTransition(self):
		''' DEVS internal transition function.
		'''

		self.holdIn('GetUpdate', self.expectUpdateTime)

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
