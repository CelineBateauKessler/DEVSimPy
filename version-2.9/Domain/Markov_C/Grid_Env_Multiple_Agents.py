# -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:              Grid_Env_Multiple_Agents.py
 Model description:     Model a grid environment for a Markov Decision Process
                        Several agents can interact with the environment.
                        The environnement is a grid.
                        It receives a position and an action as inputs and returns the resulting position
 Authors:           C. Kessler
 Organization:      UDCPP
 Current date & time:   2017-02-12 14:02:54.868000
 License:           GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message
import random
import math

ACTIONS = ['north', 'east', 'south', 'west']

### Model class ----------------------------------------------------------------
class Grid_Env_Multiple_Agents(DomainBehavior):
    ''' DEVS Class for the model Markov_Env
    '''

    def __init__(self, maxX=4, maxY=4, forbidden=[], goals=[], agents=[], stateToAgent={}):
        ''' Constructor.
        '''
        DomainBehavior.__init__(self)

        # Grid 4x3 :
        #     0    1    2    3
        #   ---------------------
        # 0 |    |    |    | +1 |
        #   ---------------------
        # 1 |    |xxxx|    | -1 |
        #   ---------------------
        # 2 |    |    |    |    |
        #   ---------------------
        

        # Cell (0,3) gives reward +1
        # Cell (1,3) gives reward -1
        # Cell (1,1) cannot be entered

        # Actions : Go North/South/West/East
        # Action result : 80% OK, 20% on orthogonal sides
        # eg : Go North results in : 80% North, 10%East, 10%West
        # If the move is not possible, then the agent remains on the same cell

        self.maxX = maxX;
        self.maxY = maxY;

        # Forbidden cells
        self.cellIsForbidden = []
        for x in range(self.maxX):
            self.cellIsForbidden.append([])
            for y in range(self.maxY):
                self.cellIsForbidden[x].append(False)
        for c in forbidden :
            self.cellIsForbidden[c[0]][c[1]] = True

        # Terminal cells
        self.cellIsGoal = []
        for x in range(self.maxX):
            self.cellIsGoal.append([])
            for y in range(self.maxY):
                self.cellIsGoal[x].append(False)
        for c in goals :
            self.cellIsGoal[c[0]][c[1]] = True

        # State to Agent correspondence table
        self.agents = agents
        self.stateToAgent = stateToAgent
         
        self.activeAgent     = None
        self.currentPosition = None
        self.msgToAgent      = Message (None, None)

        self.initPhase('IDLE',INFINITY)

    def extTransition(self, *args):
        ''' DEVS external transition function.
        '''                    
        msg = self.peek(self.IPorts[0])
        
        requested_action = msg.value[0]['action']
        
        if requested_action == "Idle":
            return self.getState()
        
        elif requested_action == "NewEpisode":
            newPosition = [random.randint(0, self.maxX - 1), random.randint(0, self.maxY - 1)]
            
        else:
            #position        = self.stateToPosition(msg.value[0]['state'])
            # Action performed is non deterministic
            r = random.random()
            if r<= 0.8 :
                effective_action = requested_action
            elif r <=0.9 :
                effective_action = self.turnRight(requested_action)
            else :
                effective_action = self.turnLeft(requested_action)

            # Move agent according to effective action
            newPosition = self.move(self.currentPosition, effective_action)

        self.msgToAgent.value = [{'state'  : self.positionToState(newPosition),
                                  #'isGoal' : self.cellIsGoal[newPosition[0]][newPosition[1]],
                                  'nbSteps' : 1}]

        self.currentPosition = newPosition
        
        self.holdIn('MOVE',1)

        return self.getState()

    def outputFnc(self):
        ''' DEVS output function.
        '''
        self.msgToAgent.time = self.timeNext
        activeAgent = self.stateToAgent[self.positionToState(self.currentPosition)]
        #print("**** ENV ==> " + self.OPorts[self.agents.index(activeAgent)].name + ' ' + str(self.msgToAgent))
        return self.poke(self.OPorts[self.agents.index(activeAgent)], self.msgToAgent)


    def intTransition(self):
        ''' DEVS internal transition function.
        '''
        self.holdIn('IDLE',INFINITY)
            
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

    def turnRight(self, action):
        return {'N' : 'E',
                'E' : 'S',
                'S' : 'W',
                'W' : 'N'} [action]

    def turnLeft(self, action):
        return {'N' : 'W',
                'E' : 'N',
                'S' : 'E',
                'W' : 'S'} [action]

    def move(self, pos, action):
        #print('MOVE ' + str(pos) + ' ' + action)
        
        newPosition = [pos[0], pos[1]]

        if action == 'N':
            newPosition[1] -= 1
        elif action == 'S':
            newPosition[1] += 1
        elif action == 'E':
            newPosition[0] += 1
        else : #action == 'west'
            newPosition[0] -= 1 

        if self.positionIsAllowed(newPosition):
            #print(newPosition)
            return newPosition
        else:
            return pos

    def positionIsAllowed(self, pos):
        if pos[0]<0 or pos[0]>=self.maxX : return False
        if pos[1]<0 or pos[1]>=self.maxY : return False
        if self.cellIsForbidden[pos[0]][pos[1]] : return False
        return True

    def positionToState (self, pos):
        stateId = pos[0]*self.maxY + pos[1]
        return 'c'+str(stateId)

    def stateToPosition (self, state):
        stateId = int(state.split('c')[1])
        x = math.floor(stateId / self.maxY)
        y = stateId - x*self.maxY
        return [int(x),int(y)]
