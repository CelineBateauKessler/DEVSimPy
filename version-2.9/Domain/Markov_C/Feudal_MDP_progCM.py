 # -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:              Feudal_MDP_progCM.py
 Model description: Hierarchical feudal MDP coupled model built programmatically   and computes the Q-value for each state to get an optimal strategy
 Authors:           C. Kessler
 Organization:      UDCPP
 Date & time:       2017-02-13 14:03:16.377000
 License:           GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.MasterModel import Master
from DomainInterface.Object import Message

from Domain.Markov_C import Grid_Env_Multiple_Agents, Feudal_Agent

NB_SAMPLE_MIN = 5
GAMMA         = 0.5
EPSILON       = 0.1

# 4x4 grid ------------------------------------------------------------

# States hierarchy
#   0 |  4 |  8 | 12
# ----+----+----+----
#   1 |  5 |  9 | 13
# ----+----+----+----
#   2 |  6 | 10 | 14
# ----+----+----+----
#   3 |  7 | 11 | 15

#          |     
#     A0   |    A2
#          |  
# ----+----+----+----
#          |     
#     A1   |    A3
#          |  

LEVEL1_4x4 = {'A0' : ['c0', 'c1', 'c4', 'c5'],
              'A1' : ['c2', 'c3', 'c6', 'c7'],
              'A2' : ['c8', 'c9', 'c12', 'c13'],
              'A3' : ['c10', 'c11', 'c14', 'c15']}

LEVEL2_4x4 = {'SUP' : ['A0', 'A1', 'A2', 'A3']}

LEVEL1_4x4_EXIT = {'A0' : ['A1', 'A2'],
                   'A1' : ['A0', 'A3'],
                   'A2' : ['A0', 'A3'],
                   'A3' : ['A1', 'A2'],
                   'SUP': []}

GRID_4x4= {'sizeX' : 4,
           'sizeY' : 4,
           'forbidden' : [],
           'goal' : [[3,3]],
           'levels' : {'level1' : LEVEL1_4x4,
                       'level2' : LEVEL2_4x4},
           'exits'  : LEVEL1_4x4_EXIT}

# 8x8 grid ------------------------------------------------------------

LEVEL1_8x8 = {'A0' : ['c0', 'c1', 'c8', 'c9'],
              'A1' : ['c2', 'c3', 'c10', 'c11'],
              'A2' : ['c4', 'c5', 'c12', 'c13'],
              'A3' : ['c6', 'c7', 'c14', 'c15'],
              'A4' : ['c6', 'c7', 'c14', 'c15'],
              'A5' : ['c6', 'c7', 'c14', 'c15'],
              'A6' : ['c6', 'c7', 'c14', 'c15'],
              'A7' : ['c6', 'c7', 'c14', 'c15'],
              'A8' : ['c6', 'c7', 'c14', 'c15'],
              'A9' : ['c6', 'c7', 'c14', 'c15'],
              'A10' : ['c6', 'c7', 'c14', 'c15'],
              'A11' : ['c6', 'c7', 'c14', 'c15'],
              'A12' : ['c6', 'c7', 'c14', 'c15'],
              'A13' : ['c6', 'c7', 'c14', 'c15'],
              'A14' : ['c6', 'c7', 'c14', 'c15'],
              'A15' : ['c6', 'c7', 'c14', 'c15']
              }

LEVEL2_8x8 = {'BO' : ['A0', 'A1', 'A4', 'A5'],
              'B1' : ['A2', 'A3', 'A6', 'A7'],
              'B2' : ['A8', 'A9', 'A12', 'A13'],
              'B3' : ['A10', 'A11', 'A14', 'A15']}

LEVEL3_8x8 = {'SUP' : ['B0', 'B1', 'B2', 'B3']}

GRID_8x8= {'sixeX' : 8,
           'sizeY' : 8,
           'forbidden' : [],
           'goal' : [[7,7]],
           'levels' : {'level1' : LEVEL1_8x8,
                       'level2' : LEVEL2_8x8,
                       'level3' : LEVEL3_8x8}}


# 8x8 grid ------------------------------------------------------------

### Model class ----------------------------------------------------------------
class Feudal_MDP_progCM(Master):
    ''' DEVS Class for the feudal MDP
    '''

    def __init__(self, gridName='4x4', nbSampleMin=5, gamma=0.9, epsilon=0.1):
        ''' Constructor.
        '''
        Master.__init__(self)

        if gridName == '4x4':
            grid  = GRID_4x4
        elif gridName == '4x4':
            grid = GRID_8x8
        else:
            grid = None
            
        # Pre-compute some correspondance tables
        L1agents = []
        L0stateToL1Agents = {}
        for a in grid['levels']['level1']:
            L1agents.append(a)
            for s in grid['levels']['level1'][a]:
                L0stateToL1Agents[s] = a

        print(L1agents)
        print(L0stateToL1Agents)

        # Environment
        env = Grid_Env_Multiple_Agents.Grid_Env_Multiple_Agents(grid['sizeX'], grid['sizeY'], grid['forbidden'], grid['goal'], L1agents, L0stateToL1Agents)
        env.name = "ENV"
        env.timeNext = env.elapsed = 0
        self.addSubModel(env)
        env.addInPort("FromAgent")
        
        # Create agents from bottom to top
        self.agents = {}

        lowerLevel = None
        for level in grid['levels']:
            print(level)
            self.agents[level] = {}
            
            for a in grid['levels'][level]:
                # Create agent
                print('Create ' + a)
                isTopLevel = (len(grid['levels'][level]) == 1)
                print('States:')
                states = grid['levels'][level][a]
                print(states)
                print('Tasks:')
                tasks = []
                for s in states:
                    tasks.append('GoTo'+s)
                for s in grid['exits'][a]:
                    tasks.append('GoTo'+s)
                print(tasks)
                print('Actions')
                actions = {}
                if lowerLevel == None:
                    for s in states:
                        actions[s] = ['N','E','S','W']
                else:                   
                    for s in states:
                        actions[s] = []
                        for s2 in grid['exits'][s]:
                            actions[s].append('GoTo'+s2)
                print(actions)
                
                agent = Feudal_Agent.Feudal_Agent(a, grid['levels'][level], tasks, actions, isTopLevel, NB_SAMPLE_MIN, GAMMA, EPSILON);
                agent.name = a
                agent.timeNext = agent.elapsed = 0
                self.addSubModel(agent)
                self.agents[level][a] = agent

                # Create ports for future connections with upper level
                agent.addInPort("FromUpper") # port 0
                agent.addOutPort("ToUpper") # port 0
                
                # Connect to lower level
                if lowerLevel == None:
                    # Connect to Environment
                    env.addOutPort("To"+a)
                    agent.addInPort("FromENV") # port 1
                    agent.addOutPort("ToENV") # port 1
                    agentIndex = grid['levels'][level].keys().index(a)
                    self.connectPorts(env.OPorts[agentIndex], agent.IPorts[1])
                    self.connectPorts(agent.OPorts[1], env.IPorts[0])
                else :
                    # Connect to lower agents
                    agent.addInPort("FromAgent") # port 1
                    for a2 in states:
                        agent.addOutPort("To"+a2) # port a2index + 1
                        self.connectPorts(agent.OPorts[states.index(a2)+1], self.agents[lowerLevel][a2].IPorts[0])
                        self.connectPorts(self.agents[lowerLevel][a2].OPorts[0], agent.IPorts[1])
                
            lowerLevel = level

