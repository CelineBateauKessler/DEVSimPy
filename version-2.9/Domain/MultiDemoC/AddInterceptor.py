# -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:          		AddInterceptor.py
 Model description:     Add interceptor to intercept missiles
 Authors:       		capocchi_l.UDCPP
 Organization:  		SPE UMR CNRS 6134
 Current date & time:   2016-10-14 07:47:17.387000
 License:       		GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message

### Model class ----------------------------------------------------------------
class AddInterceptor(DomainBehavior):
	''' DEVS Class for the model AddInterceptor
	'''

	def __init__(self, timeStepAddInterceptor=10, initNbInterceptor=0.0):
		''' Constructor.
			
			@param timeStepAddInterceptor: 
			@patam initNbInterceptor: number of interceptors at the begining of simulation 
		'''
		DomainBehavior.__init__(self)

		### local copy
		self.timeStepAddInterceptor = timeStepAddInterceptor
		self.initNbInterceptor = initNbInterceptor

		### number of added interceptor
		self.interceptor_cpt = 0

		self.msg = Message(None,None)

		#self.initPhase('ADD_INTERCEPTOR',timeStepAddInterceptor)
		self.initPhase('IDLE',INFINITY)

	def extTransition(self, *args):
		''' DEVS external transition function.
		'''

		### adapted with PyPDEVS
		if hasattr(self, 'peek'):
			msg = self.peek(self.IPorts[0])
			ratio = msg.value[0]
		else:
			inputs = args[0].get(self.IPorts[0])
			#msgs = inputs.get(self.IPorts[0])
			#ratio = msgs[0][0]

		"""if self.phaseIs('ADD_INTERCEPTOR') and ratio < 1.0:
			self.holdIn('ADD_INTERCEPTOR', self.state['sigma']-self.elapsed)
		else:
			self.passivate()"""
		self.interceptor_cpt +=1
		#print("ADD_INTERCEPTOR receives msg T=" + str(self.timeNext))
		self.holdIn('ADD_INTERCEPTOR', 0)

		return self.getState()

	def outputFnc(self):
		''' DEVS output function.
		'''	
		### Never called?
		if self.phaseIs('ADD_INTERCEPTOR'):
			self.msg.value = [self.initNbInterceptor+self.interceptor_cpt]
			self.msg.time = self.timeNext
			return self.poke(self.OPorts[0], self.msg) 
		else:
			return {}

	def intTransition(self):
		''' DEVS internal transition function.
		'''
		#self.initPhase('ADD_INTERCEPTOR',self.timeStepAddInterceptor)
		#self.interceptor_cpt+=1
		### Never called?
		self.holdIn('IDLE', INFINITY)
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

	def modelTransition(self, state):
		''' modelTransition method will be called at every step
			in simulated time on every model that transitioned
			in order to notify parent of structural change.
			Dynamic structure is possible for both Classic and Parallel DEVS,
			but only for local simulation.
		'''

		# Notify parent of structural change
		"""if self.state['sigma']-self.elapsed <= 0.0:
			state['add_interceptor:status'] = 'ADD_INTERCEPTOR'
			return True
		else:
			return False"""
		if self.phaseIs('ADD_INTERCEPTOR'):
			state['add_interceptor:status'] = 'ADD_INTERCEPTOR'
			return True
		else:
			return False
