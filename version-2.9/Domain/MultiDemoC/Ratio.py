# -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:          		Ratio.py
 Model description:     output the ratio between the number of intercepte missiles and the number of missiles
 Authors:       		capocchi_l.UDCPP
 Organization:  		UMR SPE 6134
 Current date & time:   2016-10-11 09:22:56.829000
 License:       		GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message

### Model class ----------------------------------------------------------------
class Ratio(DomainBehavior):
	''' DEVS Class for the model Ratio
	'''

	def __init__(self):
		''' Constructor.
		
			@param timeStepInterceptor
		'''
		DomainBehavior.__init__(self)

		### buffer that contain key as sensor_id and value True if intercepted
		self.missiles = {}
		self.interceptors = {}

		### intercepted missiles / total number of missiles
		self.ratioM = 0.0
		### total number of interceptors / intercepted missiles
		self.ratioI = 1.0

		### output msg
		self.msg = Message(None, None)

		self.initPhase('INIT',0.0)

	def extTransition(self, *args):
		''' DEVS external transition function.
		'''
		port = self.IPorts[0]

		### get input message
		if hasattr(self, 'peek'):
			msgs = [self.peek(port).value]
			np = port.myID
		else:
			inputs = args[0].get(port)
			msgs = filter(lambda a: isinstance(a, dict), inputs)
			np=port.port_id

		if msgs:
			### loop for bag taking only the message value (tuple is time info)
			for m in msgs:
				#print(m)
				if 'Missile' in m['source'] :
					self.missiles[m['source']] = m['status']
					
				if 'Interceptor' in m['source'] :
					self.interceptors[m['source']] = m['status']
					
			### number of detected missiles
			nbInterceptedMissiles = len(filter(lambda a: a=='Intercepted', self.missiles.values()))
			### total number of missiles
			nbMissiles = float(len(self.missiles))
			### ratio calculation
			self.ratioM = nbInterceptedMissiles/nbMissiles
			
			### number of interceptors
			nbInterceptors = float(len(self.interceptors))
			### ratio calculation
			if nbInterceptors > 0 :
				self.ratioI=nbInterceptedMissiles/nbInterceptors
			else :
				self.ratioI=0.0

			### generate output immediately
			self.holdIn('ACTIVE_M',0.0)
			
		return self.getState()

	def outputFnc(self):
		''' DEVS output function.
		'''
		### send output only for ACTIVE phase
		if self.phaseIs('ACTIVE_M'):
			#print('ratioM='+str(self.ratioM))
			self.msg.value = [self.ratioM]
			#self.msg.value= {'ratioMissileInterceptedvsTotal':self.ratioM}
			self.msg.time = self.timeNext
			return self.poke(self.OPorts[0], self.msg)
		elif self.phaseIs('ACTIVE_I'):
			#print('ratioI='+str(self.ratioI))
			self.msg.value = [self.ratioI]
			#self.msg.value={'ratioInterceptorInterceptingvsTotal':self.ratioI}
			self.msg.time = self.timeNext
			return self.poke(self.OPorts[1], self.msg)
		else:
			return {}

	def intTransition(self):
		''' DEVS internal transition function.
		'''
		### INIT phase to instanciate all models from dynamic coupled model (see modelTransition below)
		if self.phaseIs('INIT'):
			self.holdIn('INIT_CM', 0.0)
		elif self.phaseIs('INIT_CM'):
			self.passivateIn('WAIT')
		else:
			if self.phaseIs('ACTIVE_M'):
				self.holdIn('ACTIVE_I', 0.0)
			elif self.phaseIs('ACTIVE_I'):
				self.passivateIn('WAIT')
			if self.ratioM == 1.0:
				### if the ratio is reached, passivate.
				self.passivateIn('ALL_DETECTED')
		#print(self.state)
		return self.getState()

	def timeAdvance(self):
		''' DEVS Time Advance function.
		'''
		return self.getSigma()

	def finish(self, msg):
		''' Additional function which is lunched just before the end of the simulation.
		'''
		#if self.phaseIs('ADD_INTERCEPTOR'):
		#	print "Despite of the %s added interceptors,\n the missiles were not reached."%self.interceptor_cpt

	def confTransition(self, inputs):
		'''DEFAULT Confluent Transition Function.
		'''
		self.state = self.intTransition()
		self.state = self.extTransition(inputs)
		return self.getState()

	def modelTransition(self, state):
		''' Notify parent of structural change
		'''
		### notify the parent coupled model that 
		### it must instantiated all atomic models 
		### (missiles, sensors, interceptors, etc)
		if self.phaseIs('INIT_CM'):
			state['ratio:status'] = 'INIT'
			return True
		### notify the parent coupled model that 
		### it must instantiated an interceptor
		#elif self.phaseIs('ADD_INTERCEPTOR'):
		#	state['ratio:status'] = 'ADD_INTERCEPTOR'
		#	print self.timeNext
		#	self.interceptor_cpt+=1
		#	return True
		elif self.phaseIs('ALL_DETECTED'):
			state['ratio:status'] = 'ALL_DETECTED'
			return True
		else:
			return False
