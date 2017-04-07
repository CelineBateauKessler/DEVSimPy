
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------
 Name:        DynCM.py
 Model:       Dynamic coupled model composed by missiles, sensors, interceptors and messageCollector
 Authors:     L. Capocchi (capocchi@univ-corse.fr), J.F Santucci (santucci@univ-corse.fr)
 Date:     10-06-2016
-------------------------------------------------------------------------------
"""

from DomainInterface.DomainStructure import DomainStructure

from Domain.MultiDemo import Missile, Sensor, Interceptor

### depend on the import order when DEVSimPy is starting
try:
	import Ratio, AddInterceptor
except:
	pass

from Domain.Collector import MessagesCollector, To_Disk

import os

#    ======================================================================    #
class DynCM(DomainStructure):

	def __init__(self,  nbMissile=10, 
						nbInterceptor=10, 
						nbSensor=10, 
						missileTravelCount=10, 
						missileKillZone=2.0, 
						missileSpaceSize=10, 
						sensorExpectUpdateTime=2.0,
						timeStepAddInterceptor=10,
						writeFiles=True):
		'''
			@param nbMissile: number of missiles
			@param nbInterceptor: number of intercepctors
			@param nbSensor: number of sensors
			@param missileTravelCount: number of simulation time step to land a missile
			@param missileKillZone: zone to kill a missile
			@param missileSpaceSize: zone to randomly generate missile position
			@param sensorExpectUpdateTime: step time to update the sensor
			@param timeStepAddInterceptor: simulation time step to add an intercpetor
			@param writeFiles: if True, files are generated into the out directory of DEVSimPy
		'''
		DomainStructure.__init__(self)

		self.models = {}

		### local copy
		self.nbInterceptor = nbInterceptor

		### create interceptors AM
		for i in xrange(nbInterceptor):
			m = Interceptor.Interceptor()
			m.name = ''.join([m.__class__.__name__,str(i)])
			m.timeNext = m.timeLast = m.myTimeAdvance = 0.
			m.addOutPort()
			self.addSubModel(m)

			self.models[m.name] = m

		### create missile am
		for i in xrange(nbMissile):
			m = Missile.Missile(missileTravelCount, missileKillZone, missileSpaceSize)
			m.name = '_'.join([m.__class__.__name__,str(i)])
			m.timeNext = m.timeLast = m.myTimeAdvance = 0.
			m.addInPort()
			m.addOutPort()
			self.addSubModel(m)

			self.models[m.name] = m
			
		### create sensor am
		for i in xrange(nbSensor):
			s = Sensor.Sensor(sensorExpectUpdateTime)
			s.name = '_'.join([s.__class__.__name__,str(i)])
			s.timeNext = s.timeLast = s.myTimeAdvance = 0.
			s.addInPort()
			s.addOutPort()
			self.addSubModel(s)

			self.models[s.name] = s

			if writeFiles:
				### create MessageColector am
				path = os.path.join(HOME_PATH, 'out', s.name)
				mc = MessagesCollector.MessagesCollector(fileName=path)
				mc.timeNext = mc.timeLast = mc.myTimeAdvance = 0.
				mc.addInPort()
				self.addSubModel(mc)
			
				### coupling
				self.connectPorts(s.OPorts[0],mc.IPorts[0])

		### create Ratio AM
		r = Ratio.Ratio()
		r.name = 'Ratio'
		r.timeNext = r.timeLast = r.myTimeAdvance = 0.
		r.addInPort()
		r.addOutPort()
		self.models[r.name] = r
			
		### adding
		self.addSubModel(r)

		### create AddInterceptor AM
		ai = AddInterceptor.AddInterceptor(timeStepAddInterceptor, nbInterceptor)
		ai.name = 'AddInterceptor'
		ai.timeNext = ai.timeLast = ai.myTimeAdvance = 0.
		ai.addInPort()
		ai.addOutPort()
		self.models[ai.name] = ai
			
		### adding
		self.addSubModel(ai)

		if writeFiles:
			### create To_Disk am
			path = os.path.join(HOME_PATH, 'out', r.name)
			td = To_Disk.To_Disk(fileName=path)
			td.timeNext = td.timeLast = td.myTimeAdvance = 0.
			td.addInPort()
			self.addSubModel(td)

#		ps = PlotlyStream.PlotlyStream('testMultiDemo3','zc6s6ehtub', 'pbumoo52sn','capocchi')
#		ps.timeNext = ps.timeLast = ps.myTimeAdvance = 0.
#		ps.addInPort()
#		self.addSubModel(ps)
			
#		self.connectPorts(r.OPorts[0],ps.IPorts[0])
		
		### lists of AM models
		self.interceptor_list = filter(lambda model: isinstance(model, Interceptor.Interceptor), self.componentSet)
		self.missile_list = filter(lambda model: isinstance(model, Missile.Missile), self.componentSet)	
		self.sensor_list = filter(lambda model: isinstance(model, Sensor.Sensor), self.componentSet)
		
		### connect all interceptors to all missiles
		for interceptor in self.interceptor_list:
			for missile in self.missile_list:
				self.connectPorts(interceptor.OPorts[0],missile.IPorts[0])

		### connect all missiles to all sensors
		for missile in self.missile_list:
			for sensor in self.sensor_list:
				self.connectPorts(missile.OPorts[0], sensor.IPorts[0])
		
		### connect all sensors to the ratio model
		for sensor in self.sensor_list:
			self.connectPorts(sensor.OPorts[0], r.IPorts[0])

		### connect the ratio model to the AddInterceptor AM
		self.connectPorts(r.OPorts[0],ai.IPorts[0])

		if writeFiles:
			### connect the ratio model to a to_disk model
			self.connectPorts(r.OPorts[0],td.IPorts[0])

	def modelTransition(self, state):

		print('--------------------')
		print(state)
		print(self.timeNext)
		if 'ratio:status' in state and state['ratio:status'] == 'INIT':
			### connect the ratio model to input of all included To_Disk model
			to_disk_list = filter(lambda a: hasattr(a, 'getBlockModel') and 'To_Disk' in a.getBlockModel().label,self.componentSet)
			if to_disk_list != []:
				for to_disk in to_disk_list:
					if 'Ratio' in to_disk.name:
						self.connectPorts(self.models['Ratio'].OPorts[0],to_disk.IPorts[0])
					elif 'Interceptor' in to_disk.name:
						self.connectPorts(self.models['AddInterceptor'].OPorts[0],to_disk.IPorts[0])

			del state['ratio:status']

			return True

		elif 'add_interceptor:status'in state and state['add_interceptor:status'] == 'ADD_INTERCEPTOR':
			#self.debugger('Interceptor %s added'%str(len(self.interceptor_list)+1))
			print('DYNCM Interceptor added T='+str(self.timeNext))
			### add an interceptor and connect it to all missiles
			m = Interceptor.Interceptor()
			m.name = ''.join([m.__class__.__name__,str(len(self.interceptor_list)+1)])
			m.timeNext = m.timeLast = m.myTimeAdvance = 0.
			m.addOutPort()
			self.addSubModel(m)
	
			self.interceptor_list.append(m)
			self.models[m.name] = m

			for missile in self.missile_list:
				self.connectPorts(m.OPorts[0],missile.IPorts[0])

			del state['add_interceptor:status']

			return True

		elif 'ratio:status' in state and state['ratio:status'] == 'ALL_DETECTED':
			print "Report:"
			print "%i missiles detected!"%len(self.missile_list)
			print "%i initial interceptor"%self.nbInterceptor
			print "%i interceptor added during the simulation"%(len(self.interceptor_list)-self.nbInterceptor)
			return True

		else:
			return False
		
