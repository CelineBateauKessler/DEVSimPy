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

from Domain.Markov_C import Grid_Env_Multiple_Agents, Feudal_Agent_with_Goal

import copy


EPSILON    = 0.1
ALPHA      = 0.1
# These 3 last parameters are connected
REWARD_MAX = 4 # Depends on the mean number of steps to exit a state - connected to penalty
GAMMA      = 0.8 # The closer to 1, the more future rewards are taken into account, if too high, the process does not find the shortest way
#PENALTY    = 1.0 #

# Utility of action South in cell c50 for task Exit to B3
# U(c50,South) = Reward - penaltyForStep + gamma*(Sum(P(S2|c50,South)*Max(a2)U(S2,a2))
# U(c50,South) = 0 - penalty + gamma*(0.8*MaxU(c51) + 0.1*MaxU(c42) + 0.1*MaxU(c58))
#              = 0 - penalty + gamma*(0.8*RewardMax + ...)


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

GRID_4x4= {'sizeX' : 4,
           'sizeY' : 4,
           'forbidden' : [],
           'levels' : {'level1' : LEVEL1_4x4,
                       'level2' : LEVEL2_4x4}}

# 8x8 grid with 3 levels of agents ------------------------------------------------------------
# Cell id:
#   0   8  16  24  32  40  48  56
#   1   9  17  25  33  41  49  57
#   2  10  18  26  34  42  50  58
#   3  11  19  27  35  43  51  59
#   4  12  20  28  36  44  52  60
#   5  13  21  29  37  45  53  61
#   6  14  22  30  38  46  54  62
#   7  15  23  31  39  47  55  63
#
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

GRID_8x8= {'sizeX' : 8,
           'sizeY' : 8,
           'forbidden' : [[2,2],[2,3],[2,4],[3,4],[4,4],[5,4],[6,4],[6,3],[6,2]], # U-shape wall
           'levels' : {'level1' : {'subset' : LEVEL1_8x8, 'exploreDuration' : 0},
                       'level2' : {'subset' : LEVEL2_8x8, 'exploreDuration' : 1500},
                       'level3' : {'subset' : LEVEL3_8x8, 'exploreDuration' : 2500}}}

# 8x8 grid with 2 levels of agents ------------------------------------------------------------
LEVEL1_8x8b = {'B0' : ['c0', 'c1', 'c8', 'c9', 'c16', 'c17', 'c24', 'c25', 'c2', 'c3', 'c10', 'c11', 'c18', 'c19', 'c26', 'c27'],
              'B1' : ['c4', 'c5', 'c12', 'c13', 'c6', 'c7', 'c14', 'c15', 'c20', 'c21', 'c28', 'c29', 'c22', 'c23', 'c30', 'c31'],
              'B2' : ['c32', 'c33', 'c40', 'c41', 'c34', 'c35', 'c42', 'c43','c48', 'c49', 'c56', 'c57', 'c50', 'c51', 'c58', 'c59'],
              'B3' : ['c36', 'c37', 'c44', 'c45', 'c38', 'c39', 'c46', 'c47', 'c52', 'c53', 'c60', 'c61', 'c54', 'c55', 'c62', 'c63']}

LEVEL2_8x8b = {'SUP' : ['B0', 'B1', 'B2', 'B3']}

GRID_8x8b= {'sizeX' : 8,
           'sizeY' : 8,
           'forbidden' : [[2,2],[2,3],[2,4],[3,4],[4,4],[5,4],[6,4],[6,3],[6,2]], # U-shape wall
           'levels' : {'level1' : {'subset' : LEVEL1_8x8b, 'exploreDuration' : 0},
                       'level2' : {'subset' : LEVEL2_8x8b, 'exploreDuration' : 2000}}}


# 8x8 grid ------------------------------------------------------------

### Model class ----------------------------------------------------------------
class Feudal_MDP_with_Goal_progCM(Master):
    ''' DEVS Class for the feudal MDP
    '''

    def __init__(self, gridName='8x8', goal='c12'):
        ''' Constructor.
        '''
        Master.__init__(self)

        if gridName == '4x4':
            grid  = GRID_4x4
        elif gridName == '8x8':
            grid = GRID_8x8
        elif gridName == '8x8b':
            grid = GRID_8x8b
        else:
            grid = None

        # Pre-compute some correspondance tables
        L1agents = []
        L0stateToL1Agents = {}
        for a in grid['levels']['level1']['subset']:
            L1agents.append(a)
            for s in grid['levels']['level1']['subset'][a]:
                L0stateToL1Agents[s] = a

        #print(L1agents)
        #print(L0stateToL1Agents)

        # Turn cell goal as state goal
        goalTable = [goal]
        for level in grid['levels']:
            for s in grid['levels'][level]['subset']:
                if goal in grid['levels'][level]['subset'][s]:
                    goalTable.append(s)
                    goal = s
        print(goalTable)

        # Environment
        env = Grid_Env_Multiple_Agents.Grid_Env_Multiple_Agents(grid['sizeX'], grid['sizeY'], grid['forbidden'], L1agents, L0stateToL1Agents)
        env.name = "ENV"
        env.timeNext = env.elapsed = 0
        self.addSubModel(env)
        env.addInPort("FromAgents")

        # Create agents from bottom to top
        self.agents = {}
        actions = {}
        rewardMax  = REWARD_MAX

        lowerLevel = None
        for level in grid['levels']:
            print(level)
            self.agents[level] = {}

            for a in grid['levels'][level]['subset']:
                # Create agent
                print('Create ' + a)
                isTopLevel = (len(grid['levels'][level]['subset']) == 1)
                #print('States:')
                states = grid['levels'][level]['subset'][a]
                #print(states)

                #print('Actions')
                actions = {}
                if lowerLevel == None:
                    for s in states:
                        actions[s] = ['N','E','S','W']
                else:
                    for s in states:
                        actions[s] = []

                modelFilename = "TransitionModel_"+gridName+"_"+a+".json"
                agent = Feudal_Agent_with_Goal.Feudal_Agent_with_Goal(a, modelFilename, grid['levels'][level]['subset'], actions, isTopLevel, lowerLevel == None, rewardMax, GAMMA, EPSILON, ALPHA, grid['levels'][level]['exploreDuration'])
                agent.name = a
                agent.timeNext = agent.elapsed = 0
                self.addSubModel(agent)
                self.agents[level][a] = agent

                if isTopLevel and goal != None:
                    agent.setGoal(goalTable)

                # Create ports for future connections with upper level
                agent.addInPort("FromUpper") # port 0
                agent.addOutPort("ToUpper") # port 0

                # Connect to lower level
                if lowerLevel == None:
                    # Connect to Environment
                    env.addOutPort("To"+a)
                    agent.addInPort("FromENV") # port 1
                    agent.addOutPort("ToENV") # port 1
                    agentIndex = grid['levels'][level]['subset'].keys().index(a)
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
            #rewardMax *= len(grid['levels'][level])
