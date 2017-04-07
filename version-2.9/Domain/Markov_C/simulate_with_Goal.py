# -*- coding: utf-8 -*-

from __future__ import with_statement

import os
import sys
import __builtin__
import threading
import time
import traceback

__version__ = '2.9'

ABS_HOME_PATH = os.path.abspath(os.path.dirname(sys.argv[0]))

### specific builtin variables. (dont modify the defautls value. If you want to change it, go tot the PreferencesGUI from devsimpy interface.)
builtin_dict = {'SPLASH_PNG': os.path.join(ABS_HOME_PATH, 'splash', 'splash.png'),
                'DEVSIMPY_PNG': 'iconDEVSimPy.png', # png file for devsimpy icon
                'HOME_PATH': ABS_HOME_PATH,
                'ICON_PATH': os.path.join(ABS_HOME_PATH, 'icons'),
                'ICON_PATH_16_16': os.path.join(ABS_HOME_PATH, 'icons', '16x16'),
                'SIMULATION_SUCCESS_SOUND_PATH': os.path.join(ABS_HOME_PATH,'sounds', 'Simulation-Success.wav'),
                'SIMULATION_ERROR_SOUND_PATH': os.path.join(ABS_HOME_PATH,'sounds', 'Simulation-Error.wav'),
                'DOMAIN_PATH': os.path.join(ABS_HOME_PATH, 'Domain'), # path of local lib directory
                'NB_OPENED_FILE': 5, # number of recent files
                'NB_HISTORY_UNDO': 5, # number of undo
                'OUT_DIR': 'out', # name of local output directory (composed by all .dat, .txt files)
                'PLUGINS_PATH': os.path.join(ABS_HOME_PATH, 'plugins'), # path of plug-ins directory
                'FONT_SIZE': 12, # Block font size
                'LOCAL_EDITOR': True, # for the use of local editor
                'LOG_FILE': os.devnull, # log file (null by default)
                'DEFAULT_SIM_STRATEGY': 'bag-based', #choose the default simulation strategy for PyDEVS
                'PYDEVS_SIM_STRATEGY_DICT' : {'original':'SimStrategy1', 'bag-based':'SimStrategy2', 'direct-coupling':'SimStrategy3'}, # list of available simulation strategy for PyDEVS package
                                'PYPDEVS_SIM_STRATEGY_DICT' : {'classic':'SimStrategy4', 'distributed':'SimStrategy5', 'parallel':'SimStrategy6'}, # list of available simulation strategy for PyPDEVS package
                'HELP_PATH' : os.path.join('doc', 'html'), # path of help directory
                'NTL' : False, # No Time Limit for the simulation
                'DYNAMIC_STRUCTURE' : True, #Dynamic structure for PyPDEVS simulation
                'TRANSPARENCY' : True, # Transparancy for DetachedFrame
                'DEFAULT_PLOT_DYN_FREQ' : 100, # frequence of dynamic plot of QuickScope (to avoid overhead),
                'DEFAULT_DEVS_DIRNAME':'PyDEVS', # default DEVS Kernel directory
                'DEVS_DIR_PATH_DICT':{'PyDEVS':os.path.join(ABS_HOME_PATH,'DEVSKernel','PyDEVS'),
                                    'PyPDEVS_221':os.path.join(ABS_HOME_PATH,'DEVSKernel','PyPDEVS','pypdevs221' ,'src'),
                                    'PyPDEVS':os.path.join(ABS_HOME_PATH,'DEVSKernel','PyPDEVS','old')},
                'GUI_FLAG' : False,
                'INFINITY' : float('inf')
                }

# Sets the homepath variable to the directory where your application is located (sys.argv[0]).
__builtin__.__dict__.update(builtin_dict)

from Patterns.Strategy import *
#print __builtin__.__dict__

def simulator_factory(model, strategy, prof, ntl, verbose, dynamic_structure_flag):
    """ Preventing direct creation for Simulator
        disallow direct access to the classes
    """

    ### find the correct simulator module depending on the
    for pydevs_dir, filename in __builtin__.__dict__['DEVS_DIR_PATH_DICT'].items():
        if pydevs_dir == __builtin__.__dict__['DEFAULT_DEVS_DIRNAME']:
            from DEVSKernel.PyDEVS.simulator import Simulator as BaseSimulator

    class Simulator(BaseSimulator):
        """
        """
        ###
        def __init__(self, model):
            """Constructor.
            """
            BaseSimulator.__init__(self, model)

            self.model = model
            self.__algorithm = SimStrategy1(self)

        def simulate(self, T = sys.maxint):
            return self.__algorithm.simulate(T)

        def getMaster(self):
            return self.model

        def setMaster(self, model):
            self.model = model

        def setAlgorithm(self, s):
            self.__algorithm = s

        def getAlgorithm(self):
            return self.__algorithm

    class SimulationThread(threading.Thread, Simulator):
        """
            Thread for DEVS simulation task
        """

        def __init__(self, model = None, strategy = '', prof = False, ntl = False, verbose=False, dynamic_structure_flag=False):
            """ Constructor.
            """
            threading.Thread.__init__(self)
            Simulator.__init__(self, model)

            ### local copy
            self.strategy = strategy
            self.prof = prof
            self.ntl = ntl
            self.verbose = verbose
            self.dynamic_structure_flag = dynamic_structure_flag

            self.end_flag = False
            self.thread_suspend = False
            self.sleep_time = 0.0
            self.thread_sleep = False
            self.cpu_time = -1

            self.start()

        def run(self):
            """ Run thread
            """
            ### define the simulation strategy
            args = {'simulator':self}
            ### TODO: isinstance(self, PyDEVSSimulator)
            if DEFAULT_DEVS_DIRNAME == "PyDEVS":
                cls_str = eval(PYDEVS_SIM_STRATEGY_DICT[self.strategy])
            else:
                cls_str = eval(PYPDEVS_SIM_STRATEGY_DICT[self.strategy])

            self.setAlgorithm(apply(cls_str, (), args))

            while not self.end_flag:
                ### traceback exception engine for .py file
                try:
                    self.simulate(self.model.FINAL_TIME)
                except Exception, info:
                    self.terminate(error=True, msg=sys.exc_info())

        def terminate(self, error = False, msg = None):
            """ Thread termination routine
                param error: False if thread is terminate without error
                param msg: message to submit
            """

            if not self.end_flag:
                if error:

                    ###for traceback
                    etype = msg[0]
                    evalue = msg[1]
                    etb = traceback.extract_tb(msg[2])
                    sys.stderr.write('Error in routine: your routine here\n')
                    sys.stderr.write('Error Type: ' + str(etype) + '\n')
                    sys.stderr.write('Error Value: ' + str(evalue) + '\n')
                    sys.stderr.write('Traceback: ' + str(etb) + '\n')

                else:
                    for m in filter(lambda a: hasattr(a, 'finish'), self.model.componentSet):
                        ### call finished method
                        m.finish(None)

            self.end_flag = True

        def set_sleep(self, sleeptime):
            self.thread_sleep = True
            self._sleeptime = sleeptime

        def suspend(self):

            #main_thread = threading.currentThread()
            #for t in threading.enumerate():
            #   t.thread_suspend = True

            self.thread_suspend = True

        def resume_thread(self):
            self.thread_suspend = False

    return SimulationThread(model, strategy, prof, ntl, verbose, dynamic_structure_flag)
    
class runSimulation:
    """
    """

    def __init__(self, master, time):
        """ Constructor.
        """

        # local copy
        self.master = master
        self.time = time

        ### No time limit simulation (defined in the builtin dico from .devsimpy file)
        self.ntl = False

        # simulator strategy
        self.selected_strategy = DEFAULT_SIM_STRATEGY
        self.dynamic_structure_flag = __builtin__.__dict__['DYNAMIC_STRUCTURE']

        ### profiling simulation with hotshot
        self.prof = False

        self.verbose = False

        # definition du thread, du timer et du compteur pour les % de simulation
        self.thread = None
        self.count = 10.0
        self.stdioWin = None

    ###
    def Run(self):
        """ run simulation
        """

        assert(self.master is not None)
                 
        #print __builtin__.__dict__
        if self.master:
            self.master.FINAL_TIME = float(self.time)
            self.thread = simulator_factory(self.master, self.selected_strategy, self.prof, self.ntl, self.verbose, self.dynamic_structure_flag)

            return self.thread  

#-------------------------------------------------------------------
if __name__ == '__main__':

    """
    import argparse
    parser = argparse.ArgumentParser(description="simulate a model")
    # required filename
    parser.add_argument("masterName", help="name of master model")
    # optional simulation_time for simulation
    parser.add_argument("simulation_time", nargs='?', help="simulation time [inf|ntl]", default=10)
    # optional kernel for simulation kernel
    parser.add_argument("-kernel", help="simulation kernel [pyDEVS|PyPDEVS]", type=str, default="pyDEVS")
    
    args = parser.parse_args()"""

    """if args.kernel:
        if 'PyPDEVS' in args.kernel:
            __builtin__.__dict__['DEFAULT_DEVS_DIRNAME'] = 'PyPDEVS_221'
            __builtin__.__dict__['DEFAULT_SIM_STRATEGY'] = 'parallel'"""

    gridName = sys.argv[1]
    duration = sys.argv[2]
    if len(sys.argv)==4:
        goal = sys.argv[3]
    else:
        goal=None
         
    from Domain.Markov_C import Feudal_MDP_with_Goal_progCM
    devs = Feudal_MDP_with_Goal_progCM.Feudal_MDP_with_Goal_progCM(gridName, goal)

    if isinstance(duration, str):
        duration = float(duration)

    sim = runSimulation(devs, duration)
    startTime = time.time()
    thread = sim.Run()
    
    

