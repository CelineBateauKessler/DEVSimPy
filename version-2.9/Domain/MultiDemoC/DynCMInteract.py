 
# -*- coding: utf-8 -*-
"""
-------------------------------------------------------------------------------
 Name:        DynCMInteract.py
 Model:       Dynamic coupled model composed by missiles, sensors, interceptors and messageCollector
 Authors:     L. Capocchi (capocchi@univ-corse.fr), J.F Santucci (santucci@univ-corse.fr)
 Date:     10-06-2016
-------------------------------------------------------------------------------
"""

from DomainInterface.DomainStructure import DomainStructure

from Domain.MultiDemoC import Missile, Sensor, Interceptor, Interaction, Ratio, AddInterceptor

from Domain.Collector import MessagesCollector, To_Disk

import os

#    ======================================================================    #
class DynCMInteract(DomainStructure):

	def __init__(self,  nbMissile=10, 
						nbInterceptor=10, 
						nbSensor=10, 
						missileTravelCount=10, 
						missileKillZone=2.0, 
						missileSpaceSize=10, 
						sensorExpectUpdateTime=2.0,
						timeStepAddInterceptor=10,
						plotlyKey='',
						plotlyUsername='',
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
		self.name = "DynCMInteract"
		### local copy
		self.nbInterceptor = nbInterceptor
		self.missileSpaceSize = missileSpaceSize

		### create interceptors AM
		for i in xrange(nbInterceptor):
			m = Interceptor.Interceptor(missileSpaceSize)
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

			"""if writeFiles:
				### create MessageColector am
				path = os.path.join(HOME_PATH, 'out', s.name)
				mc = MessagesCollector.MessagesCollector(fileName=path)
				mc.timeNext = mc.timeLast = mc.myTimeAdvance = 0.
				mc.addInPort()
				self.addSubModel(mc)			
				### coupling
				self.connectPorts(s.OPorts[0],mc.IPorts[0])"""

		### create Ratio AM
		self.ratio = Ratio.Ratio()
		self.ratio.name = 'Ratio'
		self.ratio.timeNext = self.ratio.timeLast = self.ratio.myTimeAdvance = 0.
		self.ratio.addInPort()
		self.ratio.addOutPort()
		self.ratio.addOutPort()
		self.models[self.ratio.name] = self.ratio			
		### adding
		self.addSubModel(self.ratio)

		### create AddInterceptor AM
		ai = AddInterceptor.AddInterceptor(timeStepAddInterceptor, nbInterceptor)
		ai.name = 'AddInterceptor'
		ai.timeNext = ai.timeLast = ai.myTimeAdvance = 0.
		ai.addInPort()
		ai.addOutPort()
		self.models[ai.name] = ai
		### adding
		self.addSubModel(ai)#TBC??
		
		### create User Interaction AM
		ui = Interaction.Interaction()
		ui.name = 'Interaction'
		ui.timeNext = ui.timeLast = ui.myTimeAdvance = 0.
		ui.addOutPort()
		self.models[ui.name] = ui
		### adding
		self.addSubModel(ui)
		### connect to AddInterceptor
		self.connectPorts(ui.OPorts[0],ai.IPorts[0])
			
		#self.connectPorts(ai.OPorts[0],tdi.IPorts[0])
		
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
		
		### connect all missiles and interceptors to the ratio model
		for missile in self.missile_list:
			self.connectPorts(missile.OPorts[0], self.ratio.IPorts[0])
		for interceptor in self.interceptor_list:
			self.connectPorts(interceptor.OPorts[0], self.ratio.IPorts[0])

		### connect the ratio model to the AddInterceptor AM
		#self.connectPorts(r.OPorts[0],ai.IPorts[0])

		if writeFiles:
			### create MissilePlotlyStream am --> too slow
			"""self.mps = MissilePlotlyStream.MissilePlotlyStream(fn='MissileDemo', key=plotlyKey, username=plotlyUsername, spaceSize=missileSpaceSize, killZone=missileKillZone)
			self.mps.name="MissilePlotlyStream"
			self.mps.timeNext = self.mps.timeLast = self.mps.myTimeAdvance = 0.
			self.mps.addInPort()
			self.addSubModel(self.mps)
			
			for interceptor in self.interceptor_list:
				self.connectPorts(interceptor.OPorts[0],self.mps.IPorts[0])
			for missile in self.missile_list:
				self.connectPorts(missile.OPorts[0],self.mps.IPorts[0])"""
				
			fn = os.path.join('/opt','src','mysite','static','yaml', 'RatioMissile')
			#print(fn)
			tdr = To_Disk.To_Disk(fn)
			tdr.name="Ratio_To_Disk"
			tdr.timeNext = tdr.timeLast = tdr.myTimeAdvance = 0.
			tdr.addInPort()
			tdr.addInPort()
			self.addSubModel(tdr)
			
			self.connectPorts(self.ratio.OPorts[0],tdr.IPorts[0])			
			self.connectPorts(self.ratio.OPorts[1],tdr.IPorts[1])
			"""fn = os.path.join(os.getcwd(),'InterceptorCount')
			print(fn)
			self.tdi = To_Disk.To_Disk(fn)
			self.tdi.name="Interceptor_To_Disk"
			self.tdi.timeNext = self.tdi.timeLast = self.tdi.myTimeAdvance = 0.
			self.tdi.addInPort()
			self.addSubModel(self.tdi)"""
			### connect the ratio model to a to_disk model
			
			

	def modelTransition(self, state):

		if 'ratio:status' in state and state['ratio:status'] == 'INIT':
			del state['ratio:status']

			return True

		elif 'add_interceptor:status'in state and state['add_interceptor:status'] == 'ADD_INTERCEPTOR':
			self.debugger('Interceptor %s added'%str(len(self.interceptor_list)+1))
			print('DYN_CM adds Interceptor')
			### add an interceptor and connect it to all missiles
			m = Interceptor.Interceptor(self.missileSpaceSize)
			m.name = ''.join([m.__class__.__name__,str(len(self.interceptor_list)+1)])
			m.timeNext = m.timeLast = m.myTimeAdvance = 0.
			m.addOutPort()
			self.addSubModel(m)
	
			self.interceptor_list.append(m)
			self.models[m.name] = m

			#self.connectPorts(m.OPorts[0],self.mps.IPorts[0])
			self.connectPorts(m.OPorts[0],self.ratio.IPorts[0])

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
		
