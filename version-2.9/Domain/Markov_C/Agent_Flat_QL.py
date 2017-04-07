 # -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:              Agent_Flat_QL.py
 Model description: Agent explores the environment to compute the Q-value for each state to get an optimal strategy
 Authors:           C. Kessler
 Organization:      UDCPP
 Date & time:       2017-04-04 14:03:16.377000
 License:           GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message
import random
import copy

### Model class ----------------------------------------------------------------
class Agent_Flat_QL(DomainBehavior):
    ''' DEVS Class for the model Markov_Agent
    '''

    def __init__(self, gamma=0.9, epsilon=0.1, alpha=0.1):
        ''' Constructor.
        '''
        DomainBehavior.__init__(self)

        # Parameters
        self.gamma       = gamma
        self.epsilon     = epsilon
        self.alpha       = alpha

        self.agentStates = []
        for i in range(64):
            state = 'c'+str(i)
            self.agentStates.append(state)

        # Reachable states according to state and action
        self.destinationStates = {}

        # Actions
        self.actions   = ['N','E','S','W']

        # Rewards depend on the task
        self.rewardMax = 4

        # Q value : expected utility of a given action A in a state S to achieve the goal defined by task T
        # Table of Q-values
        self.qValue = {}
        for s in self.agentStates:
            self.qValue[s] = {}
            for a in self.actions:
                self.qValue[s][a] = self.rewardMax # Optimistic initial conditions to make the agent want to explore all space

        # State variables
        self.currentState   = None
        self.action         = 'NewEpisode'
        self.episodeStartTime = 0
        self.meanEpisodeLength = 0
        self.nbEpisodes       = 0
        self.msgToEnv       = Message(None,None)

        self.msgToEnv.value = [{'action' : 'NewEpisode'}]
        self.initPhase('REPORT',0)

        self.fEpisode = open('episodes_flat.txt', 'w')
        self.fEpisode.write ('StartCell StartTime Length MeanLength \n')
        self.fPolicy  = open('policy_flat.txt', 'w')

    def extTransition(self, *args):
        ''' DEVS external transition function.
        '''
        # Receive message from Environment
        # --------------------------------
        msgFromEnv = self.peek(self.IPorts[0])

        if msgFromEnv :
            #print(self.name + ' receives from lower :')
            #print(msgFromEnv)
            newState  = msgFromEnv.value[0]['state']
            isGoal    = msgFromEnv.value[0]['isGoal']

            if self.action != 'NewEpisode':
                self.updateQvalue(newState, isGoal)
            else:
                self.episodeStartCell = newState

            self.currentState = newState

            # Goal searched and found!
            episodeLength = msgFromEnv.time - self.episodeStartTime
            if isGoal:# or (msgFromEnv.time < 2000 and episodeLength > 100):

                if self.nbEpisodes == 0 : #msgFromEnv.time < 2000:
                    self.meanEpisodeLength = episodeLength
                else:
                    self.meanEpisodeLength = self.meanEpisodeLength + 0.1*(episodeLength-self.meanEpisodeLength)
                self.fEpisode.write(
                    self.episodeStartCell +
                    ' ' + str(self.episodeStartTime) +
                    ' '+ str(episodeLength)+
                    ' ' + str(self.meanEpisodeLength) + '\n')
                self.action = 'NewEpisode'
                self.msgToEnv.value = [{'action' : self.action}]
                self.nbEpisodes += 1
                self.episodeStartTime = msgFromEnv.time
                self.currentState = None
                self.holdIn('REPORT',0)

            # Continue current task
            else:
                # Select next action
                self.selectNextAction()
                #print('Next Action for ' + newState + ' is ' + self.action)
                self.msgToEnv.value = [{'action' : self.action}]
                self.holdIn('REPORT',0)

        return self.getState()

    def outputFnc(self):
        ''' DEVS output function.
        '''
        self.msgToEnv.time = self.timeNext;
        return self.poke(self.OPorts[0], self.msgToEnv)

    def intTransition(self ):
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
        self.displayOptimalStrategy()
        self.fEpisode.write('nb Episodes = ' + str(self.nbEpisodes))
        self.fEpisode.close()

    def confTransition(self, inputs):
        '''DEFAULT Confluent Transition Function.
        '''
        self.state = self.intTransition()
        self.state = self.extTransition(inputs)
        return self.getState()

    def selectNextAction(self):
        # Choose action maximizing utility (Q(s,a)) unless some action has not been explored enough yet AI p 891
        # TODO indicate when all actions have been sufficiently tested
        maxA = 0
        maxQ = 0.0

        for a in self.actions:
            if self.qValue[self.currentState][a] > maxQ :
                maxA = a
                maxQ = self.qValue[self.currentState][a]
            """if self.qValue[self.currentState][a][self.task] == maxQ and self.nbSample[self.currentState][a]<self.nbSample[self.currentState][maxA]:
                maxA = a
        #r = random.random()
        #if minN < self.nbSampleMin or r < 0.1:
        if minN < self.nbSampleMin:
            self.action = minA
        else:
            self.action = maxA"""
        self.action = maxA

    def updateQvalue(self, newState, isGoal):
        """
        origin state S1    = self.currentState
        applied action A1  = self.action
        resulting state S2 = newState
        reward depends on the task to complete and so does Q value
        """
        #print(self.currentState)
        #print(self.action)
        qValue_S1_A1 = self.qValue[self.currentState][self.action]

        if isGoal:
            max_qValue_S2_A2 = self.rewardMax
        else:
            max_qValue_S2_A2 = 0.0
            for a2 in self.actions:
                qValue_S2_A2 = self.qValue[newState][a2]
                if qValue_S2_A2 > max_qValue_S2_A2:
                    max_qValue_S2_A2 = qValue_S2_A2

        new_qValue_S1_A1 = self.gamma*max_qValue_S2_A2

        self.qValue[self.currentState][self.action] = qValue_S1_A1 + self.alpha*(new_qValue_S1_A1 - qValue_S1_A1)

    def displayOptimalStrategy(self):

        for s in self.agentStates:
            maxQState = - INFINITY
            for a in self.actions:
                #print('   ' + a + ' -> ' +  str(self.qValue[s][a][t]) + ' nb=' + str(self.nbSample[s][a]))
                #print(self.nbTransition[s][a])
                #print(self.transitionCost[s][a])
                if self.qValue[s][a] > maxQState :
                    maxA = a
                    maxQState = self.qValue[s][a]

            self.fPolicy.write('STATE=' + s + ' ==> ' + maxA+'\n')# + ' Q='+ str(self.qValue[s])+'\n')
        self.fPolicy.close()
