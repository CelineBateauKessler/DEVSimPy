# -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:          MissilePlotlyStream.py
 Model:         Plot input data as a graph for plot.ly (https://plot.ly/)
 Authors:       L. Capocchi (capocchi@univ-corse.fr)
 Organization:  UMR CNRS 6134
 Date:          04/11/2016
 License:       GPL V3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message

import plotly.plotly as py
import plotly.graph_objs as go  
import plotly.tools as tls 
import time

# Patch TIC : 
#  TIC server antivirus does not send any data through a persistent HTTP request
#  until the request is closed. 
CT_MAX_DELAY = 1.0; # seconds, should be less than 1minute or stream will be closed by server
markerMissileFlying      = dict(symbol='circle', size='10', color='rgb(255,0,0)')
markerMissileIntercepted = dict(symbol='circle', size='15', color='rgb(255,255,255)')
markerMissileLanded      = dict(symbol='circle', size='20', color='rgb(255,0,0)')

markerInterceptorFlying  = dict(symbol='star', size='10', color='rgb(0,255,0)')
markerInterceptorSuccess = dict(symbol='star', size='20', color='rgb(0,0,255)')
markerInterceptorFailure = dict(symbol='star', size='10', color='rgb(255,255,255)')
### Model class ----------------------------------------------------------------
class MissilePlotlyStream(DomainBehavior):
	''' DEVS Class for PlotlyStream model
	'''

	def __init__(self, fn='test', key='', username='', plotUrl='', spaceSize=10, killZone=2):
		''' Constructor.

			fn (string) -- the name that will be associated with this figure
			fileopt ('new' | 'overwrite' | 'extend' | 'append') -- 'new' creates a
				'new': create a new, unique url for this plot
				'overwrite': overwrite the file associated with `filename` with this
				'extend': add additional numbers (data) to existing traces
				'append': add additional traces to existing data lists
			world_readable (default=True) -- make this figure private/public
			auto_open (default=True) -- Toggle browser options
				True: open this plot in a new browser tab
				False: do not open plot in the browser, but do return the unique url
			sharing ('public' | 'private' | 'sharing') -- Toggle who can view this graph
				- 'public': Anyone can view this graph. It will appear in your profile 
					and can appear in search engines. You do not need to be 
					logged in to Plotly to view this chart.
				- 'private': Only you can view this plot. It will not appear in the
					Plotly feed, your profile, or search engines. You must be
					logged in to Plotly to view this graph. You can privately
					share this graph with other Plotly users in your online
					Plotly account and they will need to be logged in to
					view this plot.
				- 'secret': Anyone with this secret link can view this chart. It will
					not appear in the Plotly feed, your profile, or search
					engines. If it is embedded inside a webpage or an IPython
					notebook, anybody who is viewing that page will be able to
					view the graph. You do not need to be logged in to view
					this plot.
		'''
		DomainBehavior.__init__(self)
		
		if key == '' or username == '':
			key = '475knde90n'
			username = 'cebeka'
			
		py.sign_in(username, key)
		#tls.set_credentials_file(username=username, api_key=key)
		#stream_tokens = tls.get_credentials_file()['stream_ids']
		#tokenI = stream_tokens[-2]   # I'm getting my stream tokens from the end to ensure I'm not reusing tokens
		#tokenM = stream_tokens[-1] 
		tokenI = 'rrbzcid5ty'
		tokenM = 'te8csiqys2'
			


		spacePlotWidth = 500
		missileKillZonePlotRadius = spacePlotWidth * killZone / spaceSize

		traceInterceptor = go.Scatter(
			x=[],
			y=[],
			mode='markers',
			stream=dict(token=tokenI),
			name="Interceptors",
			marker = dict(
				symbol = 'star',
        		size = 20
    		)
		)

		traceMissile = go.Scatter(
			x=[],
			y=[],
			mode='markers',
			stream=dict(token=tokenM),
			name="Missiles",
			marker = dict(
				symbol = 'circle',
        		size = 10
        	 )
		)

		layout= go.Layout(
			xaxis = {'range': [0, spaceSize]},
			yaxis = {'range': [0, spaceSize]},
			width  = spacePlotWidth,
			height = spacePlotWidth,
			showlegend=False
		) 

		fig = go.Figure(data=[traceInterceptor, traceMissile], layout=layout)
		self.plotUrl = py.plot(fig, filename=fn, auto_open=False, sharing='public', fileopt='new')
		#self.plotUrl='https://upload.wikimedia.org/wikipedia/en/0/0a/Gallery_of_Plotly_Graphs.png'
		print(self.plotUrl)
		# Interceptor stream
		self.interceptors={}
		self.sI = py.Stream(tokenI)
		self.sInb = 0
		self.sI.open()
		#Missile stream
		self.missiles={}
		self.sM = py.Stream(tokenM)
		self.sMnb = 0
		self.sM.open()		
		
		### patch TIC
		#############
		self.sTime = time.time()
		
		self.state = {	'status': 'IDLE', 'sigma':INFINITY}

	def extTransition(self, *args):
		''' DEVS external transition function.
		'''
		### adapted with PyPDEVS
		if hasattr(self, 'peek'):
			msg = self.peek(self.IPorts[0])
			#val = msg.value
			msgs = [msg.value]
		else:
			inputs = args[0].get(self.IPorts[0])
			# inputs looks like this : [msg1, date1, msg2, date2, ..., msgN, dateN]
			# msg is a dict, date is a tuple
			msgs = filter(lambda a: isinstance(a, dict), inputs)

		### for all messages
		for m in msgs:
			#print('*** MSG FOR PLOTLY ***')
			#print(m)
			if 'Missile' in m['source']:
				change = False
				if m['source'] not in self.missiles.keys():
					change = True
				elif m['status'] != self.missiles[m['source']]['status']:
					change = True
					
				if change:
					if m['status'] == 'Update':
						marker = markerMissileFlying# = 'rgb(255, 144, 14)'#yellow?
					elif m['status'] == 'Landed':
						marker = markerMissileLanded#color = 'rgb(255, 65, 54)'#red?
					else:#Intercepted
						marker = markerMissileIntercepted#color = 'rgb(44, 160, 101)'#green?
					self.sMnb+=1 
					#self.sM.write(dict(x=m['location'][0], y=m['location'][1], marker=marker))
					self.sM.write(dict(x=m['x'][0], y=m['y'][1], marker=marker))
				
			if 'Interceptor' in m['source']:
				change = False
				if m['source'] not in self.interceptors.keys():
					change = True
				elif m['status'] != self.interceptors[m['source']]['status']:
					change = True
					
				if change:
					if m['status'] == 'outIntercept':
						marker = markerInterceptorSuccess#color = 'rgb(93, 164, 214)'#blue?
					elif m['status'] == 'Update':
						marker = markerInterceptorFlying#color = 'rgb(255, 144, 14)'#yellow?
					else:
						marker = markerInterceptorFailure
					self.sInb+=1
					#self.sI.write(dict(x=m['location'][0], y=m['location'][1], marker=marker))
					self.sI.write(dict(x=m['x'][0], y=m['y'][1], marker=marker))

		self.state['sigma'] = 0
		return self.state

	def outputFnc(self):
		''' DEVS output function.
		'''
		return {}

	def intTransition(self):
		''' DEVS internal transition function.
		'''
		#patch TIC
		now = time.time()
		#if (self.sNbData >= 100) or (now - self.sTime >= CT_MAX_DELAY):
		if (now - self.sTime >= CT_MAX_DELAY):
			print(">> send to plotly")
			print(self.sInb)
			print(self.sMnb)
			if self.sInb > 0:
				self.sI.close();
				self.sI.open();
				self.sInb=0
			if self.sMnb>0:
				self.sM.close();
				self.sM.open();
				self.sMnb=0
			self.sTime = now
		
		self.state["sigma"] = INFINITY
		return self.state

	def timeAdvance(self):
		''' DEVS Time Advance function.
		'''
		return self.state['sigma']

	def finish(self, msg):
		''' Additional function which is lunched just before the end of the simulation.
		'''
		self.sI.close()
		self.sM.close()
