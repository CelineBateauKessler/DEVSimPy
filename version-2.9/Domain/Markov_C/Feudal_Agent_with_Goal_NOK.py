 # -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:              Feudal_Agent.py
 Model description: Agent explores the environment to get knowledge of the transition and reward model
                    and computes the expected cumulated reward for each state to get an optimal strategy
 Authors:           C. Kessler
 Organization:      UDCPP
 Date & time:       2017-01-31 14:03:16.377000
 License:           GPL v3.0
-------------------------------------------------------------------------------
"""

### Specific import ------------------------------------------------------------
from DomainInterface.DomainBehavior import DomainBehavior
from DomainInterface.Object import Message
import random
import copy
import os
import json

### Model class ----------------------------------------------------------------
class Feudal_Agent_with_Goal(DomainBehavior):
    ''' DEVS Class for the model Markov_Agent
    '''

    def __init__(self, agentId = '', modelFilename='', statesOfAgent={}, actions=[], isTopLevel=True, rewardMax=4, gamma=0.9, epsilon=0.1, alpha=0.1, penalty=0.1):
        ''' Constructor.
        '''
        DomainBehavior.__init__(self)

        # Parameters
        self.gamma       = gamma
        self.epsilon     = epsilon
        self.alpha       = alpha
        self.penalty     = penalty

        ### states handled by this agent
        self.agentId       = agentId
        self.isTopLevel    = isTopLevel
        self.isLowerLevel  = False # computed according to number of Ouput ports after ports have been programmatically added
        self.agentStates   = statesOfAgent[agentId]

        self.stateToAgent  = {}
        for a in statesOfAgent :
            for s in statesOfAgent[a] :
                self.stateToAgent[s] = a

        ### states reachable by a transition, might be out of the scope of this agent
        ### the set of destination states is initialized with the set of states handled by this agent
        # agent states (s1, s2, s3, s4)
        # and external Communicating states (SA, SB, SC, SD) for the grid MDP
        # -------------------------------------------
        # |             |             |             |
        # |      X      |     SA      |      X      |
        # |             |             |             |
        # -------------------------------------------
        # |             |  s1  |  s2  |             |
        # |     SB      |-------------|     SC      |
        # |             |  s3  |  s4  |             |
        # -------------------------------------------
        # |             |             |             |
        # |      X      |     SD      |       X     |
        # |             |             |             |
        # -------------------------------------------
        #
        # Reachable states according to state and action
        # added when met or read from model file
        self.destinationStates = {}
        for s in self.agentStates:
            self.destinationStates[s] = {}
            for a in actions[s]:
                self.destinationStates[s][a] = []

        # Tasks are goals outside the states handled by the agent "ExitToState??"
        # Additional generic tasks for management are not stored in self.tasks : "Idle" or "NewEpisode" or "FindGoal"
        self.tasks     = ['FindGoal']#tasks

        # Actions are the actions that can be applied to executing agents/environment
        # Actions depend on the current agent state
        self.actions   = actions

        # Rewards depend on the task
        self.rewardMax = rewardMax

        # Table of the number of samples collected for each (s,a) pair
        # This does not depend on the task
        self.nbSample = {}
        for s in self.agentStates:
            self.nbSample[s] = {}
            for a in self.actions[s]:
                self.nbSample[s][a] = 0

        self.nbTransition = {}
        self.cumulTransitionCost = {}
        for s in self.agentStates:
            self.nbTransition[s] = {}
            self.cumulTransitionCost[s] = {}
            for a in self.actions[s]:
                self.nbTransition[s][a] = {}
                self.cumulTransitionCost[s][a] = {}

        # Utility - for all predefined tasks
        self.utility = {}
        for t in self.tasks:
            self.utility[t] = {}
            for s in self.agentStates:
                self.utility[t][s] = {}
                for a in self.actions[s]:
                    self.utility[t][s][a] = 0.0 # Optimistic initial conditions to make the agent want to explore all space"""

        # Read learned data if exist :
        self.modelFilename = modelFilename
        if os.path.exists(self.modelFilename):
            with open(self.modelFilename, 'r') as f:
                jsonData = json.load(f)
                #print(jsonData)
                self.tasks               = jsonData['tasks']
                self.nbSample            = jsonData['nbSample']
                self.nbTransition        = jsonData['nbTransition']
                self.cumulTransitionCost = jsonData['cumulTransitionCost']
                self.utility             = jsonData['utility']
                for s in self.agentStates:
                    for a in self.actions[s]:
                        for s2 in self.nbTransition[s][a]:
                            self.destinationStates[s][a].append(s2)
            for t in self.tasks:
                if 'ExitTo' in t:
                    goal = t.split('ExitTo')[1]
                    self.computeOptimalStrategy(self.utility[t], goal)

        elif self.modelFilename != '':
            print("WARNING : Model " + self.modelFilename + " not found")

        # State variables
        self.goals          = [] # same goal seen from different levels
        self.goal           = None
        #self.lowerLevelGoal = None
        self.task           = 'Idle'
        self.previousState  = None
        self.currentState   = None
        self.action         = None
        self.actionStartTime  = 0
        self.episodeStartTime = 0

        self.msgForUpper         = False
        self.msgToUpper          = Message(None,None)
        self.msgForPreviousAgent = False
        self.msgToPreviousAgent  = Message(None,None)
        self.msgForCurrentAgent  = False
        self.msgToCurrentAgent   = Message(None,None)

        if isTopLevel:
            self.msgForCurrentAgent = True
            self.msgToCurrentAgent.value = [{'action' : 'NewEpisode'}]
            self.initPhase('REPORT',0)
        else:
            self.initPhase('IDLE',INFINITY)

    def setGoal(self, goals):
        if self.isTopLevel:
            self.goals = goals

    def extTransition(self, *args):
        ''' DEVS external transition function.
        '''
        self.isLowerLevel= (len(self.OPorts) == 2) # means that this agent commands directly the environment
        #print(self.name + ' T=' + str(self.task) + ' S=' + str(self.currentState) + ' A=' + str(self.action))
        # Receive message from Upper level
        # --------------------------------
        msgFromUpper = self.peek(self.IPorts[0])

        if msgFromUpper :
            #print(self.name + ' receives from upper :')
            #print(msgFromUpper)
            self.msgForLower = True
            if msgFromUpper.value[0]['action'] == 'NewEpisode':
                #print('NewEpisode')
                self.task = 'NewEpisode'
                self.currentState = None
                self.action = None
                self.msgForCurrentAgent = True
                self.msgToCurrentAgent.value = [{'action' : 'NewEpisode'}]
                self.holdIn('REPORT',0)

            elif msgFromUpper.value[0]['action'] == 'Idle':
                newState = msgFromUpper.value[0]['state']
                #nbSteps  = msgFromUpper.value[0]['nbSteps']
                if self.task != 'Idle' and self.task != 'NewEpisode' and self.action != 'FindGoal':
                    #print('Deactivate ' + self.name + ' in state ' + self.currentState)
                    self.updateTransitionModel(newState, (msgFromUpper.time - self.actionStartTime))
                    self.previousState = self.currentState
                    self.currentState = None
                self.task = 'Idle'

                if self.previousState != None and not self.isLowerLevel :
                    self.msgForPreviousAgent = True
                    self.msgToPreviousAgent.value = [{'action' : 'Idle', 'state' : newState}]
                    self.holdIn('REPORT',0)
                else :
                    self.holdIn('IDLE', INFINITY)

            else :
                self.task  = msgFromUpper.value[0]['action']
                self.goals = msgFromUpper.value[0]['goals']

                if self.task == 'FindGoal':
                    self.computeGoal(self.goals)
                    self.computeOptimalStrategy(self.goal)
                    #print(self.name + ' computes optimal strategy for goal ' + self.goal)

                # New task - new action
                self.actionStartTime = msgFromUpper.time
                self.selectNextAction()
                self.msgForCurrentAgent = True
                self.msgToCurrentAgent.value = [{'action' : self.action, 'goals' : self.goals}]
                self.holdIn('REPORT',0)

        # Receive message from Lower level
        # --------------------------------
        msgFromLower = self.peek(self.IPorts[1])

        if msgFromLower :
            #print(self.name + ' receives from lower :')
            #print(msgFromLower)
            newState  = msgFromLower.value[0]['state']
            #nbSteps   = msgFromLower.value[0]['nbSteps']

            if 'goalFound' in msgFromLower.value[0]:
                goalFound = msgFromLower.value[0]['goalFound']
            else : # message from Environment
                goalFound = (newState == self.goal)
                #if goalFound : print('!!! GOOOOAAAAL !!!')

            if self.task != 'Idle' and self.task != 'NewEpisode' and self.action != 'FindGoal' and self.currentState != None:
                self.updateTransitionModel(newState, (msgFromLower.time - self.actionStartTime))

            self.actionStartTime = msgFromLower.time

            if newState != self.currentState and self.currentState != None and not self.isLowerLevel :
                # Signal state change to previously active lower agent
                # This agent can be told to go to this new state
                self.previousState = self.currentState
                self.msgForPreviousAgent = True
                self.msgToPreviousAgent.value = [{'action' : 'Idle', 'state': newState}]
                self.holdIn('REPORT',0)

            self.currentState = newState

            # Final Goal found!
            if goalFound or (self.isTopLevel and (msgFromLower.time - self.episodeStartTime) > 20):
                if not self.isTopLevel:
                    # Report success
                    self.currentState = None
                    self.task = 'Idle'
                    self.msgForUpper = True
                    self.msgToUpper.value = [{'state' : self.stateToAgent[newState], 'goalFound' : True}]
                else :
                    # Start new Episode
                    self.task = 'NewEpisode'
                    print('NEW EPISODE ' + str(msgFromLower.time))
                    self.episodeStartTime = msgFromLower.time
                    self.currentState = None
                    self.msgForCurrentAgent = True
                    self.msgToCurrentAgent.value = [{'action' : 'NewEpisode'}]
                self.holdIn('REPORT',0)

            elif self.task == 'Idle' or self.task == 'NewEpisode' :
                if self.task=='NewEpisode' :print('starting state = ' + self.currentState)
                if not self.isTopLevel :
                    # Report to Upper to get new task
                    #print('Report state and wait for new task')
                    self.msgForUpper = True
                    self.msgToUpper.value = [{'state' : self.stateToAgent[newState], 'goalFound':False}]
                else :
                    # Self define task
                    if len(self.goals) == 0:
                        self.task = 'Explore'
                    else :
                        self.task = 'FindGoal'
                        self.computeGoal(self.goals)
                        self.computeOptimalStrategy(self.goal)
                        #print(self.name + ' commands ' + self.task)

                    self.selectNextAction()
                    #print('START = ' + self.action)
                    self.msgForCurrentAgent = True
                    self.msgToCurrentAgent.value = [{'action' : self.action, 'goals' : self.goals}]

                self.holdIn('REPORT',0)

            # Continue current task
            else : #(self.task != 'Idle' and self.task != 'NewEpisode'):
                # Select next action
                self.selectNextAction()
                #print('Next Action for ' + newState + ' is ' + self.action)
                self.msgForCurrentAgent = True
                self.msgToCurrentAgent.value = [{'action' : self.action, 'goals' : self.goals}]
                self.holdIn('REPORT',0)

        return self.getState()

    def outputFnc(self):
        ''' DEVS output function.
        '''
        #print("MSGS for Upper/Previous/current=" + str(self.msgForUpper) + '/'+ str(self.msgForPreviousAgent) + '/' + str(self.msgForCurrentAgent))
        if self.msgForUpper:
            self.msgForUpper = False
            self.msgToUpper.time = self.timeNext;
            #print(self.name + " --> " + self.OPorts[0].name + ' ' + str(self.msgToUpper))
            return self.poke(self.OPorts[0], self.msgToUpper )

        if self.msgForPreviousAgent :
            self.msgForPreviousAgent = False
            self.msgToPreviousAgent.time = self.timeNext;
            #print(self.name + " --> " + self.OPorts[self.agentStates.index(self.previousState)+1].name + ' ' + str(self.msgToPreviousAgent))
            return self.poke(self.OPorts[self.agentStates.index(self.previousState)+1], self.msgToPreviousAgent)

        if self.msgForCurrentAgent :
            self.msgForCurrentAgent = False
            self.msgToCurrentAgent.time = self.timeNext;

            if self.currentState != None and not self.isLowerLevel :
                # agent does not command Environment
                print(self.name + " --> " + self.currentState + ' ' + str(self.msgToCurrentAgent))
                return self.poke(self.OPorts[self.agentStates.index(self.currentState)+1], self.msgToCurrentAgent)
            else:
                # Communication with the Environment or NewEpisode message
                print(self.name + " --> " + self.OPorts[1].name +' ' + str(self.msgToCurrentAgent))
                return self.poke(self.OPorts[1], self.msgToCurrentAgent)

    def intTransition(self ):
        ''' DEVS internal transition function.
        '''
        if self.msgForUpper or self.msgForPreviousAgent or self.msgForCurrentAgent :
            self.holdIn('REPORT',0)
        else:
            self.holdIn('IDLE',INFINITY)
        return self.getState()

    def timeAdvance(self):
        ''' DEVS Time Advance function.
        '''
        return self.getSigma()

    def finish(self, msg):
        ''' Additional function which is lunched just before the end of the simulation.
        '''
        """if len(self.goals) == 0:
            if os.path.exists(self.modelFilename):
                os.remove(self.modelFilename)
            with open(self.modelFilename, 'a') as f:
                f.write(json.dumps({'tasks'               : self.tasks,
                                    'nbSample'            : self.nbSample,
                                    'nbTransition'        : self.nbTransition,
                                    'cumulTransitionCost' : self.cumulTransitionCost,
                                    'utility'             : self.utility}))"""

        self.displayTransitionModel()

        for t in self.tasks:
            if 'ExitTo' in t :
                goal = t.split('ExitTo')[1]
                #self.computeOptimalStrategy(goal)
                self.displayOptimalStrategy(t)


    def confTransition(self, inputs):
        '''DEFAULT Confluent Transition Function.
        '''
        self.state = self.intTransition()
        self.state = self.extTransition(inputs)
        return self.getState()

    def updateTransitionModel(self, newState, nbSteps):

        #if self.action != 'Explore':
        # Add the new state to the list of destination states if it is not already in the list
        if newState not in self.destinationStates[self.currentState][self.action]:
            self.destinationStates[self.currentState][self.action].append(newState)
            self.nbTransition[self.currentState][self.action][newState] = 0
            self.cumulTransitionCost[self.currentState][self.action][newState] = 0

        # Increment transition counters used for probability assesment
        self.nbSample[self.currentState][self.action] += 1
        self.nbTransition[self.currentState][self.action][newState] += 1
        self.cumulTransitionCost[self.currentState][self.action][newState] += nbSteps

        # Update list of tasks (that can be given to the agent)
        if newState not in self.agentStates :
            task = 'ExitTo'+newState
            if task not in self.tasks:
                self.tasks.append(task)
                self.utility[task] = {}
                #print(self.name + ' adds task ' + task)
            self.computeOptimalStrategy(task)

        # Update list of actions (that can be given to the sub-agent (lower level agent))
        if newState != self.currentState and not self.isLowerLevel:
            action = 'ExitTo'+newState
            if action not in self.actions[self.currentState]:
                #print(self.name + ' adds action ' +action + ' for agent ' + self.currentState)
                self.actions[self.currentState].append(action)
                self.destinationStates[self.currentState][action] = []
                self.nbSample[self.currentState][action] = 0
                self.nbTransition[self.currentState][action] = {}
                self.cumulTransitionCost[self.currentState][action] = {}
                for t in self.tasks:
                    self.computeOptimalStrategy(t)

    def computeGoal(self, goalTable):
        for g in goalTable: # table contains list of goals from lower to upper level
            if g in self.agentStates:
                self.goal = g
                break

    def selectOptimalAction(self):
        # Choose action maximizing utility (U(s,a))
        maxA = 'Explore'
        maxU = -INFINITY

        for a in self.actions[self.currentState]:
            if a != 'Explore' and a != 'FindGoal' and self.utility[self.task][self.currentState][a] > maxU :
                maxA = a
                maxU = self.utility[self.task][self.currentState][a]
        return maxA

    """def selectLessExploredAction(self):
        # Choose action maximizing utility (U(s,a))
        minA = 'Explore'
        if 'Explore' in self.actions[self.currentState]:
            minE = self.nbSample[self.currentState][minA]
        else:
            minE = INFINITY
        for a in self.actions[self.currentState]:
            if a != 'Explore' and a != 'FindGoal' and self.nbSample[self.currentState][a] < minE :
                minA = a
                minE = self.nbSample[self.currentState][a]
        return minA"""

    def selectNextAction(self):
        keepExploring = self.timeLast < 1000
        """for a in self.actions[self.currentState]:
            if  a!= 'FindGoal' and self.nbSample[self.currentState][a] < 5 :
                keepExploring = True"""

        if keepExploring and not self.isLowerLevel:
            self.action = 'Explore'

        elif self.task == 'Explore':
            randomAction = random.randint(0, len(self.actions[self.currentState])-2) # Avoid FindGoal
            self.action = self.actions[self.currentState][randomAction+1]
            #self.action = self.selectLessExploredAction() --> NOK : leads to do endless round trips (A->B->A->B->A->B...)

        elif self.task == 'FindGoal':
            if self.currentState != self.goal:
                self.action = self.selectOptimalAction()
            elif not self.isLowerLevel :
                self.action = 'FindGoal'
            else :
                self.action = None

        else:
            self.action = self.selectOptimalAction()

    def computeOptimalStrategy(self, task):
        # Compute optimal policy using value iteration algorithm = offline learning
        # U[s,a] = R(s) + ∑s' P(s'|s,a).γ. maxa' U[s',a'])

        # Initialization
        if 'ExitTo' in task:
            goal = task.split('ExitTo')[1]
        elif task=='FindGoal':
            goal = self.goal
        else:
            return

        utility = {}
        for s in self.agentStates:
            utility[s] = {}
            for a in self.actions[s]:
                if s == goal:
                    utility[s][a] = self.rewardMax
                else :
                    utility[s][a] = 0.0

        utilityNext = copy.deepcopy(utility)
        delta = INFINITY
        nbIter = 0
        deltaThreshold = self.epsilon * (1.0 - self.gamma) / self.gamma

        #print(self.nbSample)
        #print(self.nbTransition)
        #print(self.cumulTransitionCost)

        # Value iteration
        while delta > deltaThreshold : #Repeat until convergence
            #print('compute iter n=' + str(nbIter) + ' / delta = ' + str(delta))
            delta = 0.0
            nbIter +=1
            for s in self.agentStates:
                #print('S='+s)
                for a in self.actions[s]:
                    #print('  a='+a)
                    if s == goal:
                        utilityNext[s][a] = self.rewardMax
                    else :
                        utilityNext[s][a] = 0.0
                        for s2 in self.destinationStates[s][a]:# possible s'
                            #print('    S2='+s2)
                            probaSAS2 = float(self.nbTransition[s][a][s2]) / float(self.nbSample[s][a])
                            #print('    P(S2|S,a)='+str(probaSAS2))
                            if s2 in self.agentStates:
                                maxQinS2 = -INFINITY
                                for c in self.actions[s2]:
                                    QS2c = utility[s2][c]
                                    if QS2c > maxQinS2 :
                                        maxQinS2 = QS2c
                            else:
                                if s2 == goal:
                                    maxQinS2 = self.rewardMax
                                else:
                                    maxQinS2 = 0.0 #-self.rewardMax
                            #print('        MaxQinS2=' + str(maxQinS2))
                            utilityNext[s][a] += probaSAS2 * self.gamma * (maxQinS2-self.penalty*float(self.cumulTransitionCost[s][a][s2])/float(self.nbTransition[s][a][s2]))
                            # SMDP --> Use gamma ^N
                        #print('        update Q for ' + t + ' : ' + str(utilityNext[s][a][t]))

                    if abs(utilityNext[s][a] - utility[s][a]) > delta :
                        delta = abs(utilityNext[s][a] - utility[s][a])

            utility = copy.deepcopy(utilityNext)

        self.utility[task] = copy.deepcopy(utility)
        #self.displayOptimalStrategy(utility)

    def displayOptimalStrategy(self, task):
        print('*** UTILITY '+self.name + ' / ' + task + ' *************************************')

        for s in self.agentStates:
            #print('STATE=' + s)
            maxA = 'Explore'
            maxQState = - INFINITY
            for a in self.actions[s]:
                #print('   ' + a + ' -> ' +  str(self.utility[s][a][t]) + ' nb=' + str(self.nbSample[s][a]))
                #print(self.nbTransition[s][a])
                #print(self.cumulTransitionCost[s][a])
                if a != 'FindGoal' and a != 'Explore' and self.utility[task][s][a] > maxQState :
                    maxA = a
                    maxQState = self.utility[task][s][a]

            print('STATE=' + s + ' ==> ' + maxA + ' / ' + str(maxQState))

    def displayTransitionModel(self):
        print('*** TRANSITION MODEL '+ self.name +'****************************')
        print(self.tasks)
        print(self.actions)
        print(self.nbSample)
        for s in self.agentStates:
            for a in self.actions[s]:
                print('STATE=' + s + '/' + a  + ' N=' + str(self.nbSample[s][a]))
                for s2 in self.destinationStates[s][a]:
                    print('   s2=' + s2 + ' n=' + str(self.nbTransition[s][a][s2]) + '/cost=' + str(self.cumulTransitionCost[s][a][s2]))
