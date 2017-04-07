# -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:              Grid_Env_1Agent.py
 Model description:     Model a grid environment for a Markov Decision Process
                        Only 1 agent can interact with the environment.
                        The environnement is a grid.
                        It receives an action as input and returns the resulting position
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
import os

ACTIONS = ['north', 'east', 'south', 'west']

### Model class ----------------------------------------------------------------
class Grid_Env_1Agent(DomainBehavior):
    ''' DEVS Class for the model Markov_Env
    '''

    def __init__(self, maxX=8, maxY=8, forbidden=['c18','c19','c20','c28','c36','c44','c52','c51','c50'], goal='c34'):
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
            pos = self.stateToPosition(c)
            self.cellIsForbidden[pos[0]][pos[1]] = True

        # Visits Counter
        self.counter = []
        for x in range(self.maxX):
            self.counter.append([])
            for y in range(self.maxY):
                self.counter[x].append({'visit' : 0, 'start' : 0})

        # Terminal cells
        self.goal = goal

        # State
        self.currentPosition = None

        self.msgToAgent      = Message (None, None)

        self.initPhase('IDLE', INFINITY)

    def extTransition(self, *args):
        ''' DEVS external transition function.
        '''
        msg = self.peek(self.IPorts[0])
        #print(msg)
        requested_action = msg.value[0]['action']

        if requested_action == "Idle":
            newPosition = self.currentPosition

        elif requested_action == "NewEpisode":
            newPosition = [random.randint(0, self.maxX - 1), random.randint(0, self.maxY - 1)]
            #newPosition = [3,5]
            while not self.positionIsAllowed(newPosition):
                newPosition = [random.randint(0, self.maxX - 1), random.randint(0, self.maxY - 1)]
            self.counter[newPosition[0]][newPosition[1]]['start'] += 1
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
            self.counter[newPosition[0]][newPosition[1]]['visit'] += 1

        newState = self.positionToState(newPosition)
        self.msgToAgent.value = [{'state'  : newState,
                                  'isGoal' : (newState == self.goal)}]

        self.currentPosition = newPosition

        self.holdIn('MOVE',1)

        return self.getState()

    def outputFnc(self):
        ''' DEVS output function.
        '''
        self.msgToAgent.time = self.timeNext
        #print("   ENV ==> " + self.OPorts[0].name + ' ' + str(self.msgToAgent))
        return self.poke(self.OPorts[0], self.msgToAgent)


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
        with open('Env.txt', 'w') as f:
            f.write('id Nb_start Nb_visit \n')
            for x in range(self.maxX):
                for y in range(self.maxY):
                    f.write(str(self.positionToState([x,y])) + ' ' + str(self.counter[x][y]['start'])
                    + ' ' + str(self.counter[x][y]['visit']) + '\n')


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
