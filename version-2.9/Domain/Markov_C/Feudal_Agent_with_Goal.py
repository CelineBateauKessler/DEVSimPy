 # -*- coding: utf-8 -*-

"""
-------------------------------------------------------------------------------
 Name:              Feudal_Agent.py
 Model description: Agent explores the environment to get knowledge of the transition and reward model
                    and computes the Q-value for each state to get an optimal strategy
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

    def __init__(self, agentId = '', modelFilename='', statesOfAgent={}, primitiveActions=[], isTopLevel=True, isLowerLevel=False, rewardMax=4, gamma=0.9, epsilon=0.1, alpha=0.1, learningDuration=0):
        ''' Constructor.
        '''
        DomainBehavior.__init__(self)

        # Parameters
        self.gamma       = gamma
        self.epsilon     = epsilon
        self.alpha       = alpha

        ### states handled by this agent
        self.agentId       = agentId
        self.isTopLevel    = isTopLevel
        self.isLowerLevel  = isLowerLevel
        self.agentStates   = statesOfAgent[agentId]

        self.threshold = learningDuration
        # under thisthreshold, the agent is only allowed to use the Explore action
        self.explorationEpisodeMaxLength = 3*len(self.agentStates)

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

        # Actions are the actions that can be applied to executing agents/environment
        # Actions depend on the current agent state
        if self.isLowerLevel:
            self.actions   = primitiveActions
            self.firstAction = 0 # primitive actions
        else:
            self.actions = {}
            for s in self.agentStates:
                self.actions[s] = ['FindGoal', 'Explore']
            self.firstAction = 2

        for s in self.agentStates:
            self.destinationStates[s] = {}
            for a in self.actions[s][self.firstAction:]:
                self.destinationStates[s][a] = []

        # Tasks are goals outside the states handled by the agent "ExitToState??"
        # Additional generic tasks for management are not stored in self.tasks : "Idle" or "NewEpisode" or "FindGoal"
        self.tasks     = []

        # Rewards depend on the task
        self.rewardMax = rewardMax

        # Q value : expected utility of a given action A in a state S to achieve the goal defined by task T
        # Table of Q-values
        self.optimisticReward = self.gamma*self.rewardMax # expected best reward in a state next to the exit goal
        self.qValue = {}

        # Utility depends on the goal - computed when the goal is set
        self.utilityForGoal = {}

        # Table of the number of samples collected for each (s,a) pair
        # This does not depend on the task
        self.nbSample = {}
        for s in self.agentStates:
            self.nbSample[s] = {}
            for a in self.actions[s][self.firstAction:]:
                self.nbSample[s][a] = 0

        self.nbTransition = {}
        self.cumulTransitionCost = {}
        for s in self.agentStates:
            self.nbTransition[s] = {}
            self.cumulTransitionCost[s] = {}
            for a in self.actions[s][self.firstAction:]:
                self.nbTransition[s][a] = {}
                self.cumulTransitionCost[s][a] = {}

        # Read learned data if exist :
        self.modelFilename = modelFilename
        if os.path.exists(self.modelFilename): # TODO
            with open(self.modelFilename, 'r') as f:
                jsonData = json.load(f)
                #print(jsonData)
                self.tasks               = jsonData['tasks']
                self.actions             = jsonData['actions']
                self.destinationStates   = jsonData['destinationStates']
                self.nbSample            = jsonData['nbSample']
                self.nbTransition        = jsonData['nbTransition']
                self.cumulTransitionCost = jsonData['cumulTransitionCost']
                self.qValue              = jsonData['qValue']
                self.threshold = 0 # learning done

        elif self.modelFilename != '':
            print("WARNING : Model " + self.modelFilename + " not found")

        #print(self.nbTransition)

        # State variables
        self.goals          = [] # same goal seen from different levels
        self.goal           = None
        #self.lowerLevelGoal = None
        self.task           = 'Idle'
        self.previousState  = None
        self.currentState   = None
        self.action         = None
        self.actionStartTime  = 0

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
            self.nbEpisodes = 0
            self.episodeStartTime = 0
            self.episodeStartState = ''
            self.meanEpisodeLength = 0
            self.fEpisode = open('episodes_HRL.txt', 'w')
            self.fEpisode.write ('StartCell StartTime Length MeanLength \n')
        else:
            self.initPhase('IDLE',INFINITY)

    def setGoal(self, goals):
        if self.isTopLevel:
            self.goals = goals
            self.computeGoal(self.goals)

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
                if self.action == 'Idle': # goal found situation
                    self.task = 'Idle'
                    self.msgForUpper = True
                    self.msgToUpper.value = [{'state' : self.stateToAgent[self.currentState], 'goalFound' : True}]
                else:
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
                if goalFound : print('!!! GOAL !!!')

            if self.task != 'Idle' and self.task != 'NewEpisode' and self.action != 'FindGoal' and self.currentState != None:
                self.updateTransitionModel(newState, (msgFromLower.time - self.actionStartTime))

            if newState != self.currentState and self.currentState != None and not self.isLowerLevel :
                # Signal state change to previously active lower agent
                #print('Deactivate lower ' + self.currentState)
                self.previousState = self.currentState
                self.msgForPreviousAgent = True
                self.msgToPreviousAgent.value = [{'action' : 'Idle', 'state': newState}]
                self.holdIn('REPORT',0)

            self.currentState = newState

            # Final Goal found!
            if goalFound:
                if not self.isTopLevel:
                    # Report success
                    self.currentState = None
                    self.task = 'Idle'
                    self.msgForUpper = True
                    self.msgToUpper.value = [{'state' : self.stateToAgent[newState], 'goalFound' : True}]
                else :
                    # Start new Episode
                    episodeLength = msgFromLower.time - self.episodeStartTime
                    if self.meanEpisodeLength == 0 and (self.episodeStartTime > self.threshold): #initialization
                        self.meanEpisodeLength = episodeLength
                    elif (self.episodeStartTime > self.threshold):
                        self.meanEpisodeLength = self.meanEpisodeLength + 0.02*(episodeLength-self.meanEpisodeLength)
                    self.fEpisode.write(
                        self.episodeStartState +
                        ' ' + str(self.episodeStartTime) +
                        ' '+ str(episodeLength)+
                        ' ' + str(self.meanEpisodeLength) + '\n')
                    self.task = 'NewEpisode'
                    self.nbEpisodes +=1
                    self.episodeStartTime = msgFromLower.time
                    self.currentState = None
                    self.msgForCurrentAgent = True
                    self.msgToCurrentAgent.value = [{'action' : 'NewEpisode'}]
                self.holdIn('REPORT',0)

            elif self.task == 'Idle' or self.task == 'NewEpisode' :

                if not self.isTopLevel :
                    # Report to Upper to get new task
                    #print('Report state and wait for new task')
                    self.msgForUpper = True
                    self.msgToUpper.value = [{'state' : self.stateToAgent[newState], 'goalFound':False}]
                else :
                    # Self define task
                    self.task = 'FindGoal'
                    self.computeOptimalStrategy(self.goal)
                    self.selectNextAction()
                    #print('START = ' + self.action)
                    self.msgForCurrentAgent = True
                    self.msgToCurrentAgent.value = [{'action' : self.action, 'goals' : self.goals}]

                self.holdIn('REPORT',0)

            # Continue current task
            else : #(self.task != 'Idle' and self.task != 'NewEpisode'):
                # Select next action
                if self.isTopLevel and (msgFromLower.time < self.threshold) and (msgFromLower.time - self.episodeStartTime)> self.explorationEpisodeMaxLength:

                    self.fEpisode.write(
                        self.episodeStartState +
                        ' ' + str(self.episodeStartTime) +
                        ' '+ str(msgFromLower.time - self.episodeStartTime)+
                        ' ' + str(0.0) + '\n')
                    self.task = 'NewEpisode'
                    self.nbEpisodes +=1
                    self.episodeStartTime = msgFromLower.time
                    self.currentState = None
                    self.msgForCurrentAgent = True
                    self.msgToCurrentAgent.value = [{'action' : 'NewEpisode'}]
                else:
                    self.selectNextAction()
                    #print('Next Action for ' + newState + ' is ' + self.action)
                    self.msgForCurrentAgent = True
                    self.msgToCurrentAgent.value = [{'action' : self.action, 'goals' : self.goals}]
                self.holdIn('REPORT',0)

            self.actionStartTime = msgFromLower.time

        return self.getState()

    def outputFnc(self):
        ''' DEVS output function.
        '''
        #print("OUT " + self.name + " MSGS for Upper/Previous/current=" + str(self.msgForUpper) + '/'+ str(self.msgForPreviousAgent) + '/' + str(self.msgForCurrentAgent))
        if self.msgForUpper:
            self.msgForUpper = False
            self.msgToUpper.time = self.timeNext;
            #print(self.name + " --^ " + self.OPorts[0].name + ' ' + str(self.msgToUpper))
            return self.poke(self.OPorts[0], self.msgToUpper )

        if self.msgForPreviousAgent :
            self.msgForPreviousAgent = False
            self.msgToPreviousAgent.time = self.timeNext;
            #print(self.name + " ->- " + self.OPorts[self.agentStates.index(self.previousState)+1].name + ' ' + str(self.msgToPreviousAgent))
            return self.poke(self.OPorts[self.agentStates.index(self.previousState)+1], self.msgToPreviousAgent)

        if self.msgForCurrentAgent :
            self.msgForCurrentAgent = False
            self.msgToCurrentAgent.time = self.timeNext;

            if self.currentState != None and not self.isLowerLevel :
                # agent does not command Environment
                #print(self.name + " ==> " + self.OPorts[self.agentStates.index(self.currentState)+1].name + ' ' + str(self.msgToCurrentAgent))
                return self.poke(self.OPorts[self.agentStates.index(self.currentState)+1], self.msgToCurrentAgent)
            else:
                # Communication with the Environment or NewEpisode message
                #print(self.name + " ==> " + self.OPorts[1].name +' ' + str(self.msgToCurrentAgent))
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
        with open(self.modelFilename, 'w') as f:
            f.write(json.dumps({'tasks'               : self.tasks,
                                'actions'             : self.actions,
                                'destinationStates'   : self.destinationStates,
                                'nbSample'            : self.nbSample,
                                'nbTransition'        : self.nbTransition,
                                'cumulTransitionCost' : self.cumulTransitionCost,
                                'qValue'              : self.qValue}))


        print(self.name)
        #print(self.tasks)
        #print(self.optimisticReward)
        #self.displayTransitionModel()
        if self.utilityForGoal != {}:
            self.displayStrategy('goal', self.utilityForGoal);

        for t in self.tasks:
            if 'ExitTo' in t:
                self.displayStrategy(t,self.qValue[t])

        if self.isTopLevel:
            self.fEpisode.close()

    def confTransition(self, inputs):
        '''DEFAULT Confluent Transition Function.
        '''
        self.state = self.intTransition()
        self.state = self.extTransition(inputs)
        return self.getState()

    def updateTransitionModel(self, newState, nbSteps):
        if self.action != 'Explore' and self.action != 'FindGoal':
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
                self.qValue[task] = {}
                #print(self.name + ' adds task ' + task)
                for s in self.agentStates:
                    self.qValue[task][s] = {}
                    for a in self.actions[s][self.firstAction:]:
                        self.qValue[task][s][a] = self.optimisticReward

        # Update list of actions (that can be given to the sub-agent (lower level agent))
        if newState != self.currentState and not self.isLowerLevel:
            action = 'ExitTo'+newState
            if action not in self.actions[self.currentState]:
                #print(self.name + ' adds action ' +action + ' for agent ' + self.currentState)
                """self.actions[self.currentState].append(action)
                self.destinationStates[self.currentState][action] = []
                self.nbSample[self.currentState][action] = 0
                self.nbTransition[self.currentState][action] = {}
                self.cumulTransitionCost[self.currentState][action] = {}
                for t in self.tasks:
                    self.qValue[t][self.currentState][action] = self.optimisticReward
                if self.goal != None:
                    self.computeOptimalStrategy(self.goal)"""
                self.actions[self.currentState].append(action)
                self.destinationStates[self.currentState][action] = [newState]
                self.nbSample[self.currentState][action] = 1
                self.nbTransition[self.currentState][action] = {}
                self.nbTransition[self.currentState][action][newState] = 1
                self.cumulTransitionCost[self.currentState][action] = {}
                self.cumulTransitionCost[self.currentState][action][newState] = nbSteps
                for t in self.tasks:
                    self.qValue[t][self.currentState][action] = self.optimisticReward
                if self.goal != None:
                    self.computeOptimalStrategy(self.goal)

        # Update Q-value
        if self.action != 'Explore' and self.action != 'FindGoal':
            self.updateQvalue(newState, nbSteps)

    def computeGoal(self, goalTable):
        self.goal = None
        for g in goalTable: # table contains list of goals from lower to upper level
            if g in self.agentStates:
                self.goal = g
                break

    def selectOptimalAction(self, utility):
        # Choose action maximizing utility (U(s,a))
        maxA = 'Explore' # default action
        maxU = 0.0#-INFINITY
        for a in self.actions[self.currentState][self.firstAction:]:
            if utility[self.currentState][a] > maxU :
                maxA = a
                maxU = utility[self.currentState][a]
        return maxA

    def selectRandomAction(self):
        randomAction = random.randint(self.firstAction, len(self.actions[self.currentState])-1)
        return self.actions[self.currentState][randomAction]

    def selectNextAction(self):
        print('************** agent=' + self.name+ ' task=' + self.task+' S=' + self.currentState)
        if self.goal != None : print('goal  ='+ self.goal)

        if self.timeLast <= self.threshold and not self.isLowerLevel:
            self.action = 'Explore'

        elif self.task == 'Explore':
            self.action = self.selectRandomAction()

        elif self.task == 'FindGoal':
            if self.currentState != self.goal:
                """print('utilityForGoal')
                print(self.utilityForGoal)
                print('actions')
                print(self.actions)"""
                self.action = self.selectOptimalAction(self.utilityForGoal)
                if self.action == 'Explore' and self.isLowerLevel:
                    self.action = self.selectRandomAction()

            elif not self.isLowerLevel :
                self.action = 'FindGoal'
            else :
                print(self.name + ' : Goal found - nothing to do !')
                self.action = 'Idle'

        else:
            """print('Qvalue for task')
            print(self.qValue[self.task])
            if (self.timeLast < 1000 and not self.isLowerLevel) :
                self.action = 'Explore'
            else :"""

            #print(self.qValue[self.task])
            self.action = self.selectOptimalAction(self.qValue[self.task])
            """r = random.random()
            if r<= self.epsilon or (self.action == 'Explore' and self.isLowerLevel):
                self.action = self.selectRandomAction()"""
        print('--> ' + self.action)

    def updateQvalue(self, newState, nbSteps): # for inline learning
        """
        origin state S1    = self.currentState
        applied action A1  = self.action
        resulting state S2 = newState
        reward depends on the task to complete and so does Q value
        """
        p = False#self.name == 'B2'
        if p : print("QQQQQ " + self.currentState + ' -> ' + self.action + ' => ' + newState + ', cost=' + str(nbSteps))

        if p : print(self.tasks)
        for t in self.tasks:
            if p : print(t)

            goal = t.split('ExitTo')[1]

            qValue_S1_A1 = self.qValue[t][self.currentState][self.action]

            if newState in self.agentStates :
                max_qValue_S2_A2 = 0.0#-INFINITY
                if p : print('qValueS2')
                if p : print(self.qValue[t][newState])
                for a2 in self.actions[newState][self.firstAction:]:
                    qValue_S2_A2 = self.qValue[t][newState][a2]
                    if qValue_S2_A2 > max_qValue_S2_A2:
                        max_qValue_S2_A2 = qValue_S2_A2

            else : # new State is a terminal state for this agent
                if newState == goal:
                    max_qValue_S2_A2 = self.rewardMax
                else:
                    max_qValue_S2_A2 = 0.0

            if p : print('   maxQ(S2,a2)=' + str(max_qValue_S2_A2))
            new_qValue_S1_A1 = (self.gamma**nbSteps)*max_qValue_S2_A2
            if p : print('   Q(s,a)=' + str(new_qValue_S1_A1))

            alpha = 10.0/(50.0+self.nbSample[self.currentState][self.action])
            self.qValue[t][self.currentState][self.action] = qValue_S1_A1 + alpha*(new_qValue_S1_A1 - qValue_S1_A1)
            if p : print('   Q(s,a)filter=' + str(self.qValue[t][self.currentState][self.action]))

    def computeOptimalStrategy(self, goal):
        # Compute optimal policy using value iteration algorithm = offline learning
        # Q[s,a] = R(s) + ∑s' P(s'|s,a).γ. maxa' Q[s',a'])
        p = False#self.name == 'B2'
        # Init
        self.utilityForGoal = {}
        for s in self.agentStates:
            self.utilityForGoal[s] = {}
            for a in self.actions[s][self.firstAction:]:
                if s == goal:
                    self.utilityForGoal[s][a] = self.rewardMax
                else :
                    self.utilityForGoal[s][a] = 0.0

        utilityNext = copy.deepcopy(self.utilityForGoal)

        delta = INFINITY
        nbIter = 0
        deltaThreshold = self.epsilon * (1.0 - self.gamma) / self.gamma

        if p :
            print(self.nbSample)
            print(self.nbTransition)
            print(self.cumulTransitionCost)

        # Value iteration
        while delta > deltaThreshold : #Repeat until convergence
            #print('compute iter n=' + str(nbIter) + ' / delta = ' + str(delta))
            delta = 0.0
            nbIter +=1
            for s in self.agentStates:
                if p :print('S='+s)
                for a in self.actions[s][self.firstAction:]:
                    if p:print('  a='+a)
                    if s == goal:
                        utilityNext[s][a] = self.rewardMax
                    else :
                        utilityNext[s][a] = 0.0
                        for s2 in self.destinationStates[s][a]:# possible s'
                            if p : print('    S2='+s2)
                            probaSAS2 = float(self.nbTransition[s][a][s2]) / float(self.nbSample[s][a])
                            if p : print('    P(S2|S,a)='+str(probaSAS2))
                            if s2 in self.agentStates:
                                maxQinS2 = 0.0#-INFINITY
                                for c in self.actions[s2][self.firstAction:]:
                                    QS2c = self.utilityForGoal[s2][c]
                                    if QS2c > maxQinS2 :
                                        maxQinS2 = QS2c
                            else:
                                maxQinS2 = 0.0#-self.rewardMax
                            if p : print('        MaxQinS2=' + str(maxQinS2))
                            meanN = float(self.cumulTransitionCost[s][a][s2])/float(self.nbTransition[s][a][s2])
                            utilityNext[s][a] += probaSAS2 * (self.gamma**meanN) * maxQinS2
                        if p : print('     update V : ' + str(utilityNext[s][a]))

                    if abs(utilityNext[s][a] - self.utilityForGoal[s][a]) > delta :
                        delta = abs(utilityNext[s][a] - self.utilityForGoal[s][a])

            self.utilityForGoal = copy.deepcopy(utilityNext)

        self.displayStrategy('goal', self.utilityForGoal)

    def displayStrategy(self, task,  utility):
        print('*** '+ self.name + ' ' + task + ' *************************************')
        for s in self.agentStates:
            #print('STATE=' + s)
            maxA = 'None'
            maxQState = - INFINITY
            for a in self.actions[s][self.firstAction:]:
                #print('   ' + a + ' -> ' +  str(self.qValue[s][a][t]) + ' nb=' + str(self.nbSample[s][a]))
                #print(self.nbTransition[s][a])
                #print(self.cumulTransitionCost[s][a])
                if utility[s][a] > maxQState :
                    maxA = a
                    maxQState = utility[s][a]

            if maxA!= None : print('STATE=' + s + ' ==> ' + maxA+ ' Q=' + str(utility[s]))

    def displayTransitionModel(self):
        print('*** TRANSITION MODEL ****************************')
        for s in self.agentStates:
            for a in self.actions[s][self.firstAction:]:
                print('STATE=' + s + '/' + a  + ' N=' + str(self.nbSample[s][a]))
                for s2 in self.destinationStates[s][a]:
                    print('   s2=' + s2 + ' n=' + str(self.nbTransition[s][a][s2]) + '/cost=' + str(self.cumulTransitionCost[s][a][s2]))
