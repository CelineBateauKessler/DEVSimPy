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

### Model class ----------------------------------------------------------------
class Feudal_Agent(DomainBehavior):
    ''' DEVS Class for the model Markov_Agent
    '''

    def __init__(self, agentId = '',  statesOfAgent={}, tasks=[], actions=[], isTopLevel=True, nbSampleMin=5, gamma=0.9, epsilon=0.1, alpha=0.1):
        ''' Constructor.
        '''
        DomainBehavior.__init__(self)

        # Parameters
        self.gamma       = gamma
        self.epsilon     = epsilon
        self.nbSampleMin = nbSampleMin
        self.alpha       = alpha
        
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
        # external states will be added when they are reached
        #self.globalDestinationStates = copy.deepcopy(self.agentStates)
        # Reachable states according to state and action
        self.destinationStates = {}
        
        for s in self.agentStates:
            self.destinationStates[s] = {}
            for a in actions[s]:
                self.destinationStates[s][a] = []        

        # Tasks are goals set by a supervising agent
        # A task to learn is either       : "GoToStateSk" or "FindGoal"
        # Additional tasks for management : "Idle" or "NewEpisode"
        self.tasks     = tasks

        # Actions are the actions that can be applied to executing agents/environment
        # Actions may depend on the current agent state
        self.actions   = actions

        # Rewards depend on the task
        self.rewardMax = len(self.agentStates) # TBC
        
        self.globalDestinationStates = []
        for t in self.tasks: # external states will be added when they are reached TODO?
            goalState = t.split('GoTo')[1]
            if goalState not in self.globalDestinationStates:
                self.globalDestinationStates.append(goalState)
        self.reward = {}
        for s in self.globalDestinationStates :
            self.reward[s] = {}
            for t in self.tasks:
                if s == self.taskTerminalState(t):
                    self.reward[s][t] = self.rewardMax
                else:
                    self.reward[s][t] = 0.0
                
        # Q value : expected utility of a given action A in a state S to achieve the goal defined by task T
        # Table of Q-values
        self.qValue = {}
        for s in self.agentStates:
            self.qValue[s] = {}
            for a in self.actions[s]:
                self.qValue[s][a] = {}
                for t in self.tasks:
                    self.qValue[s][a][t] = self.rewardMax # Optimistic initial conditions to make the agent want to explore all space
            
        # Indicator Exploration completed
        self.explorationCompleted = False
            
        # Table of the number of samples collected for each (s,a) pair
        # This does not depend on the task
        self.nbSample = {}
        for s in self.agentStates:
            self.nbSample[s] = {}
            for a in self.actions[s]:
                self.nbSample[s][a] = 0

        self.nbTransition = {}
        self.transitionCost = {}
        for s in self.agentStates:
            self.nbTransition[s] = {}
            self.transitionCost[s] = {}
            for a in self.actions[s]:
                self.nbTransition[s][a] = {}
                self.transitionCost[s][a] = {}

        # State variables
        self.task           = 'Idle'
        self.previousState  = None
        self.nbStepsForTask = 0
        self.currentState   = None
        self.action         = None

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
            
    def extTransition(self, *args):
        ''' DEVS external transition function.
        '''
        self.isLowerLevel= (len(self.OPorts) == 2) # means that this agent commands directly the environment
        
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
                self.nbStepsForTask = 0
                self.msgForCurrentAgent = True
                self.msgToCurrentAgent.value = [{'action' : 'NewEpisode'}]
                self.holdIn('REPORT',0)
                
            elif msgFromUpper.value[0]['action'] == 'Idle':
                newState = msgFromUpper.value[0]['state']
                nbSteps  = msgFromUpper.value[0]['nbSteps']
                #print('Deactivate ' + self.name + ' in state ' + self.currentState)
                self.updateTransitionModel(newState, nbSteps)
                self.previousState = self.currentState
                self.task = 'Idle'
                self.nbStepsForTask = 0
                
                if not self.isLowerLevel :
                    self.msgForPreviousAgent = True
                    self.msgToPreviousAgent.value = [{'action' : 'Idle', 'state' : newState, 'nbSteps' : nbSteps}]
                    self.holdIn('REPORT',0)
                else :
                    self.holdIn('IDLE', INFINITY)
                
            else :
                self.task = msgFromUpper.value[0]['action']
                # New task
                self.nbStepsForTask = 0
                self.selectNextAction()
                self.msgForCurrentAgent = True
                self.msgToCurrentAgent.value = [{'action' : self.action}]
                self.holdIn('REPORT',0)

        # Receive message from Lower level
        # --------------------------------
        msgFromLower = self.peek(self.IPorts[1])
        
        if msgFromLower :
            #print(self.name + ' receives from lower :')
            #print(msgFromLower)
            newState       = msgFromLower.value[0]['state']
            nbSteps        = msgFromLower.value[0]['nbSteps']
                
            self.nbStepsForTask += nbSteps

            self.updateTransitionModel(newState, nbSteps)

            if newState != self.currentState and self.currentState != None and not self.isLowerLevel :
                # Signal state change to previously active lower agent
                #print('Deactivate ' + self.currentState)
                self.previousState = self.currentState
                self.msgForPreviousAgent = True
                self.msgToPreviousAgent.value = [{'action' : 'Idle', 'state': newState, 'nbSteps' : nbSteps}]
                self.holdIn('REPORT',0)
                
            self.currentState = newState

            # Goal searched and found!
            if newState == self.taskTerminalState(self.task) :
                #print(self.name + ' terminates ' + self.task + ' in state ' + newState)
                self.msgForUpper = True
                self.msgToUpper.value = [{'state' : self.stateToAgent[newState], 'nbSteps' : self.nbStepsForTask}]
                if self.isTopLevel :
                    # Start new Episode
                    self.task = 'NewEpisode'
                    self.nbStepsForTask = 0
                    self.msgForCurrentAgent = True
                    self.msgToCurrentAgent.value = [{'action' : 'NewEpisode'}]
                self.holdIn('REPORT',0)

            # Continue current task
            elif self.task != 'Idle' and self.task != 'NewEpisode' :
                # Select next action                    
                self.selectNextAction()
                #print('Next Action for ' + newState + ' is ' + self.action)
                self.msgForCurrentAgent = True
                self.msgToCurrentAgent.value = [{'action' : self.action}]
                self.holdIn('REPORT',0)

            else :
                # No task yet
                if not self.isTopLevel :
                    # Report to Upper to get new task
                    #print('Report state and wait for new task')
                    self.nbStepsForTask = 0
                    self.msgForUpper = True
                    self.msgToUpper.value = [{'state' : self.stateToAgent[newState], 'nbSteps' : nbSteps}]
                else :                                                
                    # Self define task # TODO
                    randomTask = random.randint(0, len(self.tasks)-1)
                    self.task = self.tasks[randomTask]
                    self.nbStepsForTask = 0
                    self.selectNextAction()
                    #print('START NEW SUP TASK = ' + self.action)
                    self.msgForCurrentAgent = True
                    self.msgToCurrentAgent.value = [{'action' : self.action}]                
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
            #print('msgForPreviousAgent from ' + self.name + ' to ' + self.previousState + ' / ' + str(len(self.OPorts)))
            self.msgToPreviousAgent.time = self.timeNext;
            #print(self.name + " --> " + self.OPorts[self.agentStates.index(self.previousState)+1].name + ' ' + str(self.msgToPreviousAgent))
            return self.poke(self.OPorts[self.agentStates.index(self.previousState)+1], self.msgToPreviousAgent)
            
        if self.msgForCurrentAgent :
            self.msgForCurrentAgent = False
            self.msgToCurrentAgent.time = self.timeNext;
            
            if self.currentState != None and not self.isLowerLevel :
                # agent does not command Environment
                #print(self.name + " --> " + self.OPorts[self.agentStates.index(self.currentState)+1].name + ' ' + str(self.msgToCurrentAgent))
                return self.poke(self.OPorts[self.agentStates.index(self.currentState)+1], self.msgToCurrentAgent)
            else:
                # Communication with the Environment or NewEpisode message
                #print(self.name + " --> " + self.OPorts[1].name +' ' + str(self.msgToCurrentAgent))
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
        print()
        print('*********************' + self.name + '*********************')
        self.displayOptimalStrategy()
        #self.displayTransitionModel()

    def confTransition(self, inputs):
        '''DEFAULT Confluent Transition Function.
        '''
        self.state = self.intTransition()
        self.state = self.extTransition(inputs)
        return self.getState()

    def updateTransitionModel(self, newState, nbSteps):
        # Add the new state to the list of destination states if it is not already in the list        
        #if self.currentState != None :
        if self.task != 'Idle' and self.task != 'NewEpisode':
            if newState not in self.destinationStates[self.currentState][self.action] :
                self.destinationStates[self.currentState][self.action].append(newState)
                self.nbTransition[self.currentState][self.action][newState] = 0
                self.transitionCost[self.currentState][self.action][newState] = 0
            
            if newState not in self.globalDestinationStates :
                self.globalDestinationStates.append(newState)

            # Increment transition counters used for probability assesment
            self.nbSample[self.currentState][self.action] += 1
            self.nbTransition[self.currentState][self.action][newState] += 1
            self.transitionCost[self.currentState][self.action][newState] += nbSteps

            # Update Q-value
            self.updateQvalue(newState, nbSteps)

    def taskTerminalState(self, task):
        if 'GoTo' in task:
            return task.split('GoTo')[1]
        else:
            return None

    def selectNextAction(self):
        # Choose action maximizing utility (Q(s,a)) unless some action has not been explored enough yet AI p 891
        # TODO indicate when all actions have been sufficiently tested
        maxA = 0
        maxQ = - INFINITY
        minA = 0
        minN = INFINITY
        
        for a in self.actions[self.currentState]:
            """if self.nbSample[self.currentState][a] < minN :
                minA = a
                minN = self.nbSample[self.currentState][a]"""
            if self.qValue[self.currentState][a][self.task] > maxQ :
                maxA = a
                maxQ = self.qValue[self.currentState][a][self.task]
            """if self.qValue[self.currentState][a][self.task] == maxQ and self.nbSample[self.currentState][a]<self.nbSample[self.currentState][maxA]:
                maxA = a
        #r = random.random()
        #if minN < self.nbSampleMin or r < 0.1:
        if minN < self.nbSampleMin:
            self.action = minA
        else:
            self.action = maxA"""
        self.action = maxA

    def updateQvalue(self, newState, nbSteps):
        """
        origin state S1    = self.currentState
        applied action A1  = self.action
        resulting state S2 = newState
        reward depends on the task to complete and so does Q value
        """
        for t in self.tasks:

            if self.currentState == self.taskTerminalState(t):
                self.qValue[self.currentState][self.action][t] = self.rewardMax
                
            else:
                qValue_S1_A1 = self.qValue[self.currentState][self.action][t]

                reward = self.reward[self.currentState][t] - 0.1*nbSteps

                if newState in self.agentStates :
                    max_qValue_S2_A2 = -INFINITY
                    for a2 in self.actions[newState]:
                        qValue_S2_A2 = self.qValue[newState][a2][t]
                        if qValue_S2_A2 > max_qValue_S2_A2:
                            max_qValue_S2_A2 = qValue_S2_A2
                            
                else : # new State is a terminal state for this agent
                    max_qValue_S2_A2 = self.reward[newState][t]
                        
                new_qValue_S1_A1 = reward + self.gamma*max_qValue_S2_A2
                
                self.qValue[self.currentState][self.action][t] = qValue_S1_A1 + self.alpha*(new_qValue_S1_A1 - qValue_S1_A1)
        
    """def computeOptimalStrategies(self):
        # Compute optimal policy using value iteration algorithm = offline learning
        # Q[s,a] = R(s) + ∑s' P(s'|s,a).γ. maxa' Q[s',a'])

        print ('computeOptimalStrategies for ' + self.name)
        print(self.tasks)
        print(self.reward)
        self.displayTransitionModel()

        self.explorationCompleted = True
        
        # Init
        qValue = copy.deepcopy(self.qValue)
        for s in self.agentStates:
            for a in self.actions[s]:                 
                # Add reward according to task 
                for t in self.tasks:
                    qValue[s][a][t] = self.reward[s][t] #- 0.1 * (float(transitionCost)/float(nbTransition)) TBC

        qValueNext = copy.deepcopy(qValue)

        delta = INFINITY
        nbIter = 0
        # Value iteration
        while delta > self.epsilon and nbIter < 10: #Repeat until convergence
            print('compute iter n=' + str(nbIter) + ' / delta = ' + str(delta))
            delta = 0.0
            nbIter +=1
            for s in self.agentStates:
                print('S='+s)
                for a in self.actions[s]:
                    print('  a='+a)
                    if self.nbSample[s][a] > 0:
                        if self.nbSample[s][a] < self.nbSampleMin:
                            self.explorationCompleted = False
                            
                        for s2 in self.destinationStates[s][a]:# possible s'
                            print('    S2='+s2)
                            probaSAS2 = float(self.nbTransition[s][a][s2]) / float(self.nbSample[s][a])                            
                            print('    P(S2|S,a)='+str(probaSAS2))

                            for t in self.tasks :
                                print('      task='+t)
                                if self.reward[s][t] > 0 : # Goal state for this task
                                    qValueNext[s][a][t] = self.reward[s][t]
                                else:
                                    qValueNext[s][a][t] = 0.0
                                    if self.reward[s2][t] > 0: # Goal state for this task
                                        maxQinS2 = self.reward[s2][t]
                                    elif s2 in self.agentStates : 
                                        maxQinS2 = -INFINITY
                                        for c in self.actions[s2]:
                                            QS2c = qValue[s2][c][t] -0.1*float(self.transitionCost[s][a][s2])/float(self.nbTransition[s][a][s2])
                                            if QS2c > maxQinS2 :
                                                maxQinS2 = QS2c
                                    else:
                                        maxQinS2 = -len(self.agentStates)
                                        
                                    print('        MaxQinS2=' + str(maxQinS2))
                                    qValueNext[s][a][t] += probaSAS2 * self.gamma * maxQinS2
                                    
                                print('        update Q for ' + t + ' : ' + str(qValueNext[s][a][t]))                                
                            
                                if abs(qValueNext[s][a][t] - qValue[s][a][t]) > delta :
                                    delta = abs(qValueNext[s][a][t] - qValue[s][a][t])
                                    #print('      delta='+str(delta))
                                
            qValue = copy.deepcopy(qValueNext)

        self.qValue = copy.deepcopy(qValue)
        #self.displayOptimalStrategy()
        print('delta=' + str(delta))
        print('nbIter=' + str(nbIter))"""

    def displayOptimalStrategy(self):
        print('*** Q VALUE *************************************')
        for t in self.tasks:
            print ('============== ' + t + ' ===================')
            for s in self.agentStates:
                print('STATE=' + s)
                maxQState = - INFINITY
                for a in self.actions[s]:
                    print('   ' + a + ' -> ' +  str(self.qValue[s][a][t]) + ' nb=' + str(self.nbSample[s][a]))
                    #print(self.nbTransition[s][a])
                    #print(self.transitionCost[s][a])
                    if self.qValue[s][a][t] > maxQState :
                        maxA = a
                        maxQState = self.qValue[s][a][t]
                        
                print('STATE=' + s + ' ==> ' + maxA )

    def displayTransitionModel(self):
        print('*** TRANSITION MODEL ****************************')
        print(self.globalDestinationStates)
        for s in self.agentStates:
            for a in self.actions[s]:
                print('STATE=' + s + '/' + a  + ' N=' + str(self.nbSample[s][a]))
                for s2 in self.destinationStates[s][a]:
                    print('   s2=' + s2 + ' n=' + str(self.nbTransition[s][a][s2]) + '/cost=' + str(self.transitionCost[s][a][s2]))

    def displayRewardModel(self):
        print('*** REWARD MODEL ********************************')  
        for t in self.tasks:
            print ('============== ' + t + ' ===================')
            for s in self.globalDestinationStates:
                print('STATE=' + s + ' ==> ' + str(self.reward[s][t]))
