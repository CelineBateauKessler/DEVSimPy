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

    def __init__(self, agentId = '', modelFilename='', statesOfAgent={}, tasks=[], actions=[], isTopLevel=True, rewardMax=4, gamma=0.9, epsilon=0.1, alpha=0.1, penalty=0.1):
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
        self.tasks     = tasks

        self.globalDestinationStates = copy.deepcopy(self.agentStates)       
        for t in self.tasks:
            if 'ExitTo' in t:
                self.globalDestinationStates.append(t.split('ExitTo')[1])

        # Actions are the actions that can be applied to executing agents/environment
        # Actions depend on the current agent state
        self.actions   = actions

        # Rewards depend on the task
        self.rewardMax = rewardMax
                    
        self.reward = {}
        for s in self.globalDestinationStates :
            self.reward[s] = {}
            for t in self.tasks:
                if s == t.split('ExitTo')[1]:
                    self.reward[s][t] = self.rewardMax
                else :
                    self.reward[s][t] = 0.0
                #elif s in self.agentStates:
                #    self.reward[s][t] = 0.0
                #else : 
                #    self.reward[s][t] = - self.rewardMax
                    
        # Q value : expected utility of a given action A in a state S to achieve the goal defined by task T
        # Table of Q-values
        optimisticReward = self.gamma*self.rewardMax - self.penalty # expected best reward in a state next to the exit goal
        self.qValue = {}
        for t in self.tasks:
            self.qValue[t] = {}
            for s in self.agentStates:
                self.qValue[t][s] = {}
                for a in self.actions[s]:
                    self.qValue[t][s][a] = optimisticReward # Optimistic initial conditions to make the agent want to explore all space"""

        # Utility depends on the goal - computed when the goal is set
        self.utilityForGoal = {}
        
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
                self.qValue              = jsonData['qValue'] 
                for s in self.agentStates:
                    for a in self.actions[s]:
                        for s2 in self.nbTransition[s][a]:
                            self.destinationStates[s][a].append(s2)
                
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
                    self.task = 'NewEpisode'
                    self.currentState = None
                    self.nbStepsForTask = 0
                    self.msgForCurrentAgent = True
                    self.msgToCurrentAgent.value = [{'action' : 'NewEpisode'}]
                self.holdIn('REPORT',0)

            elif self.task == 'Idle' or self.task == 'NewEpisode' :
                
                if not self.isTopLevel :
                    # Report to Upper to get new task
                    #print('Report state and wait for new task')
                    self.nbStepsForTask = 0
                    self.msgForUpper = True
                    self.msgToUpper.value = [{'state' : self.stateToAgent[newState], 'goalFound':False}]
                else :
                    # Self define task
                    self.nbStepsForTask = 0
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
                #print(self.name + " --> " + self.OPorts[self.agentStates.index(self.currentState)+1].name + ' ' + str(self.msgToCurrentAgent))
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
        if len(self.goals) == 0:
            if os.path.exists(self.modelFilename):
                os.remove(self.modelFilename)
            with open(self.modelFilename, 'a') as f:
                f.write(json.dumps({'tasks'               : self.tasks,
                                    'nbSample'            : self.nbSample,
                                    'nbTransition'        : self.nbTransition,
                                    'cumulTransitionCost' : self.cumulTransitionCost,
                                    'qValue'              : self.qValue}))
        
    def confTransition(self, inputs):
        '''DEFAULT Confluent Transition Function.
        '''
        self.state = self.intTransition()
        self.state = self.extTransition(inputs)
        return self.getState()

    """def getTasks(self):
        return self.tasks"""
        
    def updateTransitionModel(self, newState, nbSteps):
        # Add the new state to the list of destination states if it is not already in the list        
        #if self.currentState != None      
        if newState not in self.destinationStates[self.currentState][self.action] :
            self.destinationStates[self.currentState][self.action].append(newState)
            self.nbTransition[self.currentState][self.action][newState] = 0
            self.cumulTransitionCost[self.currentState][self.action][newState] = 0

        # Increment transition counters used for probability assesment
        self.nbSample[self.currentState][self.action] += 1
        self.nbTransition[self.currentState][self.action][newState] += 1
        self.cumulTransitionCost[self.currentState][self.action][newState] += nbSteps

        """# Update list of tasks and reward table
        if newState not in self.globalDestinationStates :
            self.globalDestinationStates.append(newState)
            print(self.name + ' add task ExitTo'+newState)
            self.tasks.append('ExitTo'+newState)"""
                
        # Update Q-value
        self.updateQvalue(newState, nbSteps)
        
    def computeGoal(self, goalTable):
        for g in goalTable: # table contains list of goals from lower to upper level
            if g in self.agentStates:
                self.goal = g
                break
                

    """def selectLessExploredAction(self):
        minA = None
        minN = INFINITY

        for a in self.actions[self.currentState]:
            if self.nbSample[self.currentState][a] < minN :
                minA = a
                minN = self.nbSample[self.currentState][a]
        return minA"""
    
    def selectOptimalAction(self, utility):
        # Choose action maximizing utility (U(s,a)) 
        maxA = None
        maxU = -INFINITY
        
        for a in self.actions[self.currentState]:
            if utility[self.currentState][a] > maxU :
                maxA = a
                maxU = utility[self.currentState][a]
            
        return maxA

    def selectNextAction(self):
        if self.task == 'Explore':
            randomAction = random.randint(0, len(self.actions[self.currentState])-1)
            self.action = self.actions[self.currentState][randomAction]
            
        elif self.task == 'FindGoal':
            if self.currentState != self.goal:
                self.action = self.selectOptimalAction(self.utilityForGoal)
            elif not self.isLowerLevel :
                self.action = 'FindGoal'
            else :
                self.action = None
                
        else:
            self.action = self.selectOptimalAction(self.qValue[self.task])
            
    def updateQvalue(self, newState, nbSteps): # for inline learning 
        """
        origin state S1    = self.currentState
        applied action A1  = self.action
        resulting state S2 = newState
        reward depends on the task to complete and so does Q value
        """
        p = (self.name == 'A13')
        if p : print(self.currentState + ' -> ' + self.action + ' => ' + newState + ', cost=' + str(nbSteps))

        for t in self.tasks:
            if p : print(t)
            
            if self.currentState == t.split('ExitTo')[1]:
                self.qValue[t][self.currentState][self.action] = self.rewardMax
                
            else:
                qValue_S1_A1 = self.qValue[t][self.currentState][self.action]

                reward = self.reward[self.currentState][t] - self.penalty*nbSteps
                if p : print('   Reward=' + str(self.reward[self.currentState][t]))
                
                if newState in self.agentStates :
                    max_qValue_S2_A2 = -INFINITY
                    for a2 in self.actions[newState]:
                        qValue_S2_A2 = self.qValue[t][newState][a2]
                        if qValue_S2_A2 > max_qValue_S2_A2:
                            max_qValue_S2_A2 = qValue_S2_A2
                            
                else : # new State is a terminal state for this agent
                    max_qValue_S2_A2 = self.reward[newState][t]
                    
                if p : print('   maxQ(S2,a2)=' + str(max_qValue_S2_A2))
                new_qValue_S1_A1 = reward + self.gamma*max_qValue_S2_A2
                if p : print('   Q(s,a)=' + str(new_qValue_S1_A1))
                
                self.qValue[t][self.currentState][self.action] = qValue_S1_A1 + self.alpha*(new_qValue_S1_A1 - qValue_S1_A1)
                if p : print('   Q(s,a)filter=' + str(self.qValue[t][self.currentState][self.action]))

        if p : print(self.qValue['ExitToB3'][self.currentState])
            
    def computeOptimalStrategy(self, goal):
        # Compute optimal policy using value iteration algorithm = offline learning
        # Q[s,a] = R(s) + ∑s' P(s'|s,a).γ. maxa' Q[s',a'])
        
        # Init
        self.utilityForGoal = {}
        for s in self.agentStates:
            self.utilityForGoal[s] = {}
            for a in self.actions[s]:
                if s == goal:
                    self.utilityForGoal[s][a] = self.rewardMax
                else :            
                    self.utilityForGoal[s][a] = 0.0

        utilityNext = copy.deepcopy(self.utilityForGoal)

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
                                    QS2c = self.utilityForGoal[s2][c]
                                    if QS2c > maxQinS2 :
                                        maxQinS2 = QS2c
                            else:
                                maxQinS2 = -self.rewardMax
                            #print('        MaxQinS2=' + str(maxQinS2))
                            utilityNext[s][a] += probaSAS2 * self.gamma * (maxQinS2-self.penalty*float(self.cumulTransitionCost[s][a][s2])/float(self.nbTransition[s][a][s2]))
                        #print('        update Q for ' + t + ' : ' + str(utilityNext[s][a][t]))                                
                            
                    if abs(utilityNext[s][a] - self.utilityForGoal[s][a]) > delta :
                        delta = abs(utilityNext[s][a] - self.utilityForGoal[s][a])
                                
            self.utilityForGoal = copy.deepcopy(utilityNext)

        self.displayOptimalStrategy()

    def displayOptimalStrategy(self):
        print('*** '+self.name + ' / ' + self.goal + ' *************************************')
        for s in self.agentStates:
            #print('STATE=' + s)
            maxQState = - INFINITY
            for a in self.actions[s]:
                #print('   ' + a + ' -> ' +  str(self.qValue[s][a][t]) + ' nb=' + str(self.nbSample[s][a]))
                #print(self.nbTransition[s][a])
                #print(self.cumulTransitionCost[s][a])
                if self.utilityForGoal[s][a] > maxQState :
                    maxA = a
                    maxQState = self.utilityForGoal[s][a]
                    
            print('STATE=' + s + ' ==> ' + maxA )

    def displayTransitionModel(self):
        print('*** TRANSITION MODEL ****************************')
        print(self.globalDestinationStates)
        for s in self.agentStates:
            for a in self.actions[s]:
                print('STATE=' + s + '/' + a  + ' N=' + str(self.nbSample[s][a]))
                for s2 in self.destinationStates[s][a]:
                    print('   s2=' + s2 + ' n=' + str(self.nbTransition[s][a][s2]) + '/cost=' + str(self.cumulTransitionCost[s][a][s2]))

    def displayRewardModel(self):
        print('*** REWARD MODEL ********************************')  
        for t in self.tasks:
            print ('============== ' + t + ' ===================')
            for s in self.globalDestinationStates:
                print('STATE=' + s + ' ==> ' + str(self.reward[s][t]))
