# -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:          		MM1.py
 Model description:     Model of a M/M/1 queueing system
                        M/M/1 means that :
                        - Inter-arrival times of customers follows exponential law
                        - service times follows exponential law
                        - there is 1 server
						Also called a Birth-Death process
 Authors:       		C. Kessler
 Organization:  		UDCPP
 Current date & time:   2017-01-04 10:53:04.882000
 License:       		GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message
import random
import math

TAU_MAX = 100
TAU_RES = 0.01

### Model class ----------------------------------------------------------------
class MM1(DomainBehavior):
	''' DEVS Class for the model MM1
	'''

	def __init__(self, arrivalMeanTime = 2.0, serviceMeanTime = 1.0):
		''' Constructor.
		'''
		DomainBehavior.__init__(self) 

		self.initPhase('IDLE',0)

		self.arrivalMeanTime = arrivalMeanTime
		self.serviceMeanTime = serviceMeanTime
		self.queueLength     = 0
		self.msg             = Message(None, None)

		print('Arrival Mean Time = ' + str(self.arrivalMeanTime))
		print('Service Mean Time = ' + str(self.serviceMeanTime))

		# Mean values
		self.nbTransitions   = 0
		self.nbIncrease      = 0
		self.queueLengthSum  = 0
		self.tauIncreaseSum  = 0
		self.tauDecreaseSum  = 0

		# Affichage loi de tau Increase 
		self.repTauInc       = []
		for i in range(int(TAU_MAX/TAU_RES)) :
			self.repTauInc.append(0);
		

	def extTransition(self, *args):
		''' DEVS external transition function.
		'''
		return self.getState()

	def outputFnc(self):
		''' DEVS output function.
		'''
		return self.poke(self.OPorts[0], Message([self.queueLength], self.timeNext))

	def intTransition(self):
		''' DEVS internal transition function.
		'''
		self.nbTransitions += 1
		
		# Gillepsie Stochastic Simulation Algorithm (SSA, Gillepsie 1976)
		#****************************************************************
                # Sum rates of all possible transactions
                arrivalRate = 1.0/float(self.arrivalMeanTime)
                serviceRate = 1.0/float(self.serviceMeanTime)
                rate = arrivalRate
                if self.queueLength > 0 :
                        rate += serviceRate
                # Simulate time to next transition using exponential law with preceding rate
		tau = random.expovariate(rate)
		# Select between possible transitions
		r = random.uniform(0, rate)
		if (r <= arrivalRate) :
			self.holdIn('INCREASE', tau)
			self.nbIncrease  += 1
			self.queueLength += 1
		else :
			self.holdIn('DECREASE', tau)
			self.queueLength -= 1

		"""# First Reaction method
		#****************************************************************
		# If a customer arrives, queue length increases by 1
		# tauIncrease simulates the time till next arrival with an exponential probability distribution
		tauIncrease = random.expovariate(1.0/float(self.arrivalMeanTime))
		self.tauIncreaseSum += tauIncrease

		iTau = int(math.floor(tauIncrease/TAU_RES))
		if iTau < int(float(TAU_MAX)/float(TAU_RES)) :
			self.repTauInc[iTau] += 1
		
		# If a customer is served, queue length decreases by 1
		# tauDecrease simulates the time till next customer is served with an exponential probability distribution
		tauDecrease = random.expovariate(1.0/float(self.serviceMeanTime))
		self.tauDecreaseSum += tauDecrease
		if self.queueLength == 0 or tauIncrease < tauDecrease :
		#if tauIncrease < tauDecrease :
			self.holdIn('INCREASE', tauIncrease)
			self.nbIncrease  += 1
			self.queueLength += 1
		else :
			self.holdIn('DECREASE', tauDecrease)
			self.queueLength -= 1"""
		
		self.queueLengthSum  += self.queueLength

		#print('---------------------------')
		#print(self.timeNext)
		#print('tauInc = ' + str(tauIncrease))
		#print('tauDec = ' + str(tauDecrease))
		#print('r = ' + str(r))
		#print('--> ' + self.state['status'])
		#print('queue = ' + str(self.queueLength))
		#print('nbInc = ' + str(self.nbIncrease) + ' / ' +str(self.nbTransitions))

		return self.getState()

	def timeAdvance(self):
		''' DEVS Time Advance function.
		'''
		return self.getSigma()

	def finish(self, msg):
		''' Additional function which is lunched just before the end of the simulation.
		'''
		#for i in range(int(TAU_MAX/TAU_RES)):
		#	print (str(float(i)*TAU_RES) + ' ; ' + str(self.repTauInc[i]))
		print('Mean value of TAU INCREASE         = ' + str(float(self.tauIncreaseSum)/float(self.nbTransitions)))
		print('Mean value of TAU DECREASE         = ' + str(float(self.tauDecreaseSum)/float(self.nbTransitions)))
		print('Mean time between transitions      = ' + str(float(self.timeNext)/float(self.nbTransitions)))
		print('Percentage of INCREASE transitions = ' + str(float(self.nbIncrease)/float(self.nbTransitions)))
		print('Mean Value of QUEUE LENGTH         = ' + str(float(self.queueLengthSum)/float(self.nbTransitions)))
		print('Total number of transitions        = ' + str(self.nbTransitions))
		
		
		pass

	def confTransition(self, inputs):
		'''DEFAULT Confluent Transition Function.
		'''
		self.state = self.intTransition()
		self.state = self.extTransition(inputs)
		return self.getState()
