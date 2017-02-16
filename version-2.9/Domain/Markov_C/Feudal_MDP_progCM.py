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
ALPHA         = 0.1

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
              
              'A4' : ['c16', 'c17', 'c24', 'c25'],
              'A5' : ['c18', 'c19', 'c26', 'c27'],
              'A6' : ['c20', 'c21', 'c28', 'c29'],
              'A7' : ['c22', 'c23', 'c30', 'c31'],
              
              'A8' : ['c32', 'c33', 'c40', 'c41'],
              'A9' : ['c34', 'c35', 'c42', 'c43'],
              'A10' : ['c36', 'c37', 'c44', 'c45'],
              'A11' : ['c38', 'c39', 'c46', 'c47'],
              
              'A12' : ['c48', 'c49', 'c56', 'c57'],
              'A13' : ['c50', 'c51', 'c58', 'c59'],
              'A14' : ['c52', 'c53', 'c60', 'c61'],
              'A15' : ['c54', 'c55', 'c62', 'c63']
              }

LEVEL2_8x8 = {'B0' : ['A0', 'A1', 'A4', 'A5'],
              'B1' : ['A2', 'A3', 'A6', 'A7'],
              'B2' : ['A8', 'A9', 'A12', 'A13'],
              'B3' : ['A10', 'A11', 'A14', 'A15']}

LEVEL3_8x8 = {'SUP' : ['B0', 'B1', 'B2', 'B3']}

GRID_8x8_EXIT = {'A0' : ['A1', 'A4'],
                 'A1' : ['A0', 'A5', 'B1'],
                 'A2' : ['A3', 'A6', 'B0'],
                 'A3' : ['A2', 'A7'],

                 'A4' : ['A0', 'A5', 'B2'],
                 'A5' : ['A1', 'A4', 'B1', 'B2'],
                 'A6' : ['A2', 'A7', 'B0', 'B3'],
                 'A7' : ['A3', 'A6', 'B3'],
                 
                 'A8' : ['A9', 'A12', 'B0'],
                 'A9' : ['A8', 'A13', 'B0', 'B3'],
                 'A10' : ['A11', 'A14', 'B1', 'B2'],
                 'A11' : ['A10', 'A15', 'B1'],
                 
                 'A12' : ['A8', 'A13'],
                 'A13' : ['A9', 'A12', 'B3'],
                 'A14' : ['A10', 'A15', 'B2'],
                 'A15' : ['A11', 'A14'],
    
                 'B0' : ['B1', 'B2'],
                 'B1' : ['B0', 'B3'],
                 'B2' : ['B0', 'B3'],
                 'B3' : ['B1', 'B2'],
                 
                 'SUP': []}

GRID_8x8= {'sizeX' : 8,
           'sizeY' : 8,
           'forbidden' : [],
           'goal' : [[7,7]],
           'levels' : {'level1' : LEVEL1_8x8,
                       'level2' : LEVEL2_8x8,
                       'level3' : LEVEL3_8x8},
           'exits' : GRID_8x8_EXIT}


# 8x8 grid ------------------------------------------------------------

### Model class ----------------------------------------------------------------
class Feudal_MDP_progCM(Master):
    ''' DEVS Class for the feudal MDP
    '''

    def __init__(self, gridName='8x8'):
        ''' Constructor.
        '''
        Master.__init__(self)

        if gridName == '4x4':
            grid  = GRID_4x4
        elif gridName == '8x8':
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
                
                agent = Feudal_Agent.Feudal_Agent(a, grid['levels'][level], tasks, actions, isTopLevel, NB_SAMPLE_MIN, GAMMA, EPSILON, ALPHA);
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

