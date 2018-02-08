##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.0 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Processes
"""
import logging
import threading
import persistent
import datetime
from datetime import timedelta
import zope.cachedescriptors.property
import zope.event
from collections import OrderedDict
from zope import component, interface

from shoobx.wfmc import interfaces

log = logging.getLogger(__name__)

WFRD_PREFIX = "WFRD_REVERT_"
DEL_MARKER = "WFRD_DEL_MARK_"


def always_true(data):
    return True


def defaultDeadlineTimer(process, deadline):
    timestamp = deadline.deadline_time
    timer = threading.Timer(
        (timestamp - datetime.datetime.now()).seconds,
        process.deadlinePassedHandler,
        args=[deadline]
    )
    deadline.deadlineTimer = timer
    timer.start()


def defaultDeadlineCanceller(process, deadline):
    if deadline.deadlineTimer:
        deadline.deadlineTimer.cancel()


@interface.implementer(interfaces.IProcessDefinitionFactory)
class StaticProcessDefinitionFactory(object):

    def __init__(self):
        self.definitions = {}

    def get(self, name):
        """See IProcessDefinitionFactory.get()
        """
        return self.definitions.get(name)

    def register(self, pd):
        self.definitions[pd.id] = pd


@interface.implementer(interfaces.ITransitionDefinition)
class TransitionDefinition(object):

    def __init__(self, from_, to, condition=always_true, id=None,
                 __name__=None, otherwise=False):
        self.id = id
        self.from_ = from_
        self.to = to
        self.condition = condition
        self.__name__ = __name__
        self.description = None
        self.type = 'OTHERWISE' if otherwise else 'CONDITION'

    @property
    def otherwise(self):
        return self.type in ('OTHERWISE', )

    def __repr__(self):
        return "TransitionDefinition(from=%r, to=%r)" % (self.from_, self.to)


@interface.implementer(interfaces.IProcessDefinition)
class ProcessDefinition(object):

    TransitionDefinitionFactory = TransitionDefinition

    def __init__(self, id, integration=None):
        self.id = id
        self.name = id
        self.integration = integration
        self.activities = {}
        self.transitions = []
        self.applications = {}
        self.participants = {}
        self.datafields = {}
        self.parameters = ()
        self.attributes = OrderedDict()
        self.description = None

    def getAllActivities(self):
        """
        Gets all activities, including subflows
        """
        result = self.activities.copy()
        for idx, act in self.activities.items():
            if act.subflows:
                sf = self.obtainSubflow(act)
                result.update(sf.definition.getAllActivities())
        return result

    def obtainSubflow(self, activityDefinition):
        """ Make a subflow stub from the subflows of `activityDefinition`
        """
        if activityDefinition.subflows:
            subflow_name, execution, actual = activityDefinition.subflows[0]
            subflow_pd = getProcessDefinition(subflow_name)
            return subflow_pd(factory=Process)

    def __repr__(self):
        return "ProcessDefinition(%r)" % self.id

    def defineActivities(self, **activities):
        self._dirty()
        for id, activity in activities.items():
            activity.id = id
            if activity.__name__ is None:
                activity.__name__ = self.id + '.' + id
            activity.process = self
            self.activities[id] = activity

    def defineTransitions(self, *transitions):
        self._dirty()
        self.transitions.extend(transitions)

        # Compute activity transitions based on transition data:
        activities = self.activities
        for transition in transitions:
            activities[transition.from_].transitionOutgoing(transition)
            activities[transition.to].incoming += (transition, )

    def defineApplications(self, **applications):
        for id, application in applications.items():
            application.id = id
            self.applications[id] = application

    def defineParticipants(self, **participants):
        for id, participant in participants.items():
            participant.id = id
            self.participants[id] = participant

    def defineDataFields(self, **datafields):
        for id, datafield in datafields.items():
            datafield.id = id
            self.datafields[id] = datafield

    def defineParameters(self, *parameters):
        self.parameters += parameters

    def _start(self):
        # Return an initial transition

        activities = self.activities

        # Find the start, making sure that there is one and that there
        # aren't any activities with no transitions:
        start = ()
        for aid, activity in activities.items():
            if not activity.incoming:
                start += ((aid, activity), )
                if not activity.outgoing:
                    raise interfaces.InvalidProcessDefinition(
                        "Activity %s has no transitions" %aid)

        if len(start) != 1:
            if start:
                raise interfaces.InvalidProcessDefinition(
                    "Multiple start activities",
                    [id for (id, a) in start]
                    )
            else:
                raise interfaces.InvalidProcessDefinition(
                    "No start activities")

        return self.TransitionDefinitionFactory(None, start[0][0])

    _start = zope.cachedescriptors.property.Lazy(_start)

    def __call__(self, context=None, factory=None):
        if factory is None:
            factory = Process
        return factory(self, self._start, context)

    def _dirty(self):
        try:
            del self._start
        except AttributeError:
            pass


@interface.implementer(interfaces.IActivityDefinition,
                         interfaces.IExtendedAttributesContainer)
class ActivityDefinition(object):

    performer = ''
    process = None

    def __init__(self, __name__=None):
        self.__name__ = __name__
        self.incoming = self.outgoing = ()
        self.transition_outgoing = self.explicit_outgoing = ()
        self.applications = ()
        self.subflows = ()
        self.scripts = ()
        self.andJoinSetting = self.andSplitSetting = False
        self.description = None
        self.attributes = OrderedDict()
        self.event = None
        self.deadlines = []

    def andSplit(self, setting):
        self.andSplitSetting = setting

    def andJoin(self, setting):
        self.andJoinSetting = setting

    def addApplication(self, application, actual=()):
        app = self.process.applications[application]
        formal = app.parameters
        if len(formal) != len(actual):
            raise TypeError("Wrong number of parameters => "
                            "Actual=%s, Formal=%s for Application %s with id=%s"
                            % (actual, formal, app, app.id))
        self.applications += ((application, formal, tuple(actual)), )

    def addSubflow(self, subflow, execution, parameters):
        # Lookup of formal parameters must be delayed, since the subflow might
        # not yet be loaded.
        self.subflows += ((subflow, execution, parameters),)

    def addScript(self, code):
        self.scripts += (code,)

    def definePerformer(self, performer):
        self.performer = performer

    def addOutgoing(self, transition_id):
        self.explicit_outgoing += (transition_id,)
        self.computeOutgoing()

    def transitionOutgoing(self, transition):
        self.transition_outgoing += (transition,)
        self.computeOutgoing()

    def computeOutgoing(self):
        if self.explicit_outgoing:
            transitions = dict([(t.id, t) for t in self.transition_outgoing])
            self.outgoing = ()
            for tid in self.explicit_outgoing:
                transition = transitions.get(tid)
                if transition is not None:
                    self.outgoing += (transition,)
        else:
            self.outgoing = self.transition_outgoing

    def __repr__(self):
        return "<ActivityDefinition %r>" % self.__name__


class Deadline(object):
    def __init__(self, activity, deadline_time, deadlinedef):
        self.activity = activity
        self.deadline_time = deadline_time
        self.definition = deadlinedef
        if deadlinedef.execution != u'SYNCHR':
            raise NotImplementedError('Only Synchronous (SYNCHR) deadlines '
                                      'are supported at this point.')


@interface.implementer(interfaces.IActivity)
class Activity(persistent.Persistent):
    DeadlineFactory = Deadline

    incoming = ()
    deadlineTimer = None
    now = datetime.datetime.now

    def __init__(self, process, definition):
        self.process = process
        self.activity_definition_identifier = definition.id
        self.workitems = {}
        self.finishedWorkitems = {}
        self.workitemIdSequence = Sequence()
        self.active = True

        # Didn't want to change the getter, but do want it set from the
        # constructor
        self._definition = definition

        self.id = self.process.activityIdSequence.next()

        self.deadlines = []
        for deadlinedef in self.definition.deadlines:
            evaluator = interfaces.IPythonExpressionEvaluator(self.process)
            if not deadlinedef.duration:
                log.warn('There is an empty deadline time in '
                          '{} for activity {}.'.format(process, definition.id))
                continue
            try:
                evaled = evaluator.evaluate(deadlinedef.duration,
                                            {'timedelta': timedelta,
                                             'datetime': datetime})
            except Exception as e:
                raise RuntimeError(
                    'Evaluating the deadline duration failed '
                    'for activity {}. Error: {}'.format(definition.id, e))

            if evaled is None:
                log.warn('There is an empty deadline time in '
                          '{} for activity {}.'.format(process, definition.id))
                continue

            if isinstance(evaled, timedelta):
                deadline_time = self.now() + evaled
            elif isinstance(evaled, datetime.datetime):
                deadline_time = evaled
            elif isinstance(evaled, int):
                deadline_time = self.now() + \
                    timedelta(seconds=evaled)
            else:
                raise ValueError(
                    'Deadline time was not a timedelta, datetime, or integer '
                    'number of seconds.\n{}'.format(evaled)
                )

            deadline = self.DeadlineFactory(self, deadline_time, deadlinedef)
            self.deadlines.append(deadline)
            self.process.deadlineTimer(deadline)

        self.activity_definition_identifier_path = \
            calculateActivityStackPath(self)
        self.createWorkItems()

    def getExecutionStack(self):
        """Return list of subflow activities that eventually started the
        process of current activity.

        The first activity returned by this function will belong to the main
        process.
        """
        act = self
        stack = []
        while act.process.starterActivityId:
            act = self.process.activities[act.process.starterActivityId]
            stack.append(act)
        stack.reverse()
        return stack

    def createWorkItems(self):
        workitems = {}

        if self.definition.applications:
            workitems = self.createApplicationWorkItems()
        elif self.definition.subflows:
            workitems = self.createSubflowWorkItems()
        elif self.definition.scripts:
            workitems = self.createScriptWorkItems()

        for workitem, application, formal, actual in workitems:
            self.addWorkItem(workitem, application, formal, actual)

    def addWorkItem(self, workitem, application, formal, actual):
        nextid = self.workitemIdSequence.next()
        workitem.id = nextid
        self.workitems[nextid] = (workitem, application, formal, actual)

    def createApplicationWorkItems(self):
        integration = self.process.definition.integration

        participant = integration.createParticipant(
            self, self.process, self.definition.performer)
        # Instantiate Applications
        for application, formal, actual in self.definition.applications:
            workitem = integration.createWorkItem(
                participant, self.process, self, application)
            yield workitem, application, formal, actual

    def definition(self):
        try:
            return self.process.definition.activities[
                self.activity_definition_identifier]
        except KeyError:
            return self._definition
    definition = property(definition)

    def createScriptWorkItems(self):
        integration = self.process.definition.integration

        for code in self.definition.scripts:
            workitem = integration.createScriptWorkItem(
                self.process, self, code)
            yield workitem, "__script__", (), ()

    def createSubflowWorkItems(self):
        integration = self.process.definition.integration

        # Instantiate Subflows
        for subflow, execution, actual in self.definition.subflows:
            # Figre out formal parameters. At this point, process definition
            # has to be available.
            subflow_pd = self.process.getSubflowProcessDefinition(subflow)
            formal = subflow_pd.parameters

            workitem = integration.createSubflowWorkItem(
                self.process, self, subflow, execution)
            yield workitem, subflow, formal, actual

    def start(self, transition):
        # Start the activity, if we've had enough incoming transitions

        definition = self.definition
        if definition.andJoinSetting:
            if transition in self.incoming:
                raise interfaces.ProcessError(
                    "Repeated incoming %s with id='%s' "
                    "while waiting for and completion"
                    % (transition, transition.id))
            self.incoming += (transition, )
            if len(self.incoming) < len(definition.incoming):
                # Tells us whether or not we need to wait
                # for enough transitions at an add-joint, specifically for
                # the case where we revert back through the joint and want to
                # move forward through it again, and don't expect the other
                # transition to happen again
                return  # not enough incoming yet

        zope.event.notify(ActivityStarted(self))

        if self.workitems:
            evaluator = getEvaluator(self.process)
            workitems = list(self.workitems.values())
            # We need the list() here to make a copy to
            # loop over, as we modify self.workitems in the loop.
            for workitem, app, formal, actual in list(self.workitems.values()):
                __traceback_info__ = (
                    workitem, self.activity_definition_identifier)

                inputs = evaluateInputs(self.process, formal, actual, evaluator)
                args = {n: a for n, a in inputs}

                __traceback_info__ = (self.activity_definition_identifier,
                                      workitem, args)

                zope.event.notify(WorkItemStarting(workitem, app, actual))
                workitem.start(args)
                zope.event.notify(WorkItemStarted(workitem, app, actual))

        else:
            # Since we don't have any work items, we're done
            self.finish()

    def workItemDiscarded(self, work_item):
        unused, app, formal, actual = self.workitems.pop(work_item.id)
        self._p_changed = True
        zope.event.notify(WorkItemDiscarded(work_item, app, actual))

        if not self.workitems:
            self.finish()

    def workItemFinished(self, work_item, results=None):
        try:
            unused, app, formal, actual = entry = \
                self.workitems.pop(work_item.id)
        except KeyError:
            raise KeyError(
                'Tried to pop workitem id:{} from the workitems dict of {}. '
                'Maybe it is already finished: {}'.format(
                    work_item.id, self, self.finishedWorkitems))
        self.finishedWorkitems[work_item.id] = entry
        self._p_changed = True
        args = results
        if not results:
            args = {}

        res = []

        for parameter, name in zip(formal, actual):
            if parameter.output:
                __traceback_info__ = args, parameter
                v = args.get(parameter.__name__)
                res.append(v)

                if not name:
                    log.warning("Output parameter {param} of {activity} "
                                "is not bound to workflow variables".format(
                                    param=parameter, activity=self))
                    continue

                # Remember the old value to restore in case of revert
                try:
                    old_val = getattr(self.process.workflowRelevantData, name)
                except AttributeError:
                    old_val = DEL_MARKER
                if v != old_val:
                    setattr(self.process.applicationRelevantData,
                            WFRD_PREFIX+str(self.id)+"_"+name,
                            old_val)
                setattr(self.process.workflowRelevantData, name, v)

        zope.event.notify(WorkItemFinished(
            work_item, app, actual, res))

        if not self.workitems:
            self.finish()

    def finish(self):
        self.active = False
        zope.event.notify(ActivityFinished(self))

        transitions = getValidOutgoingTransitions(self.process, self.definition)

        self.process.transition(self, transitions)
        for deadline in self.deadlines:
            self.process.deadlineCanceller(deadline)

    def abort(self, cancelDeadlineTimer=True):
        if cancelDeadlineTimer:
            self.cancelDeadlines()

        self.active = False

        # Abort all workitems. We need the list() here to make a copy to
        # loop over, as we modify self.workitems in the loop.
        for workitem, app, formal, actual in list(self.workitems.values()):
            if interfaces.IAbortWorkItem.providedBy(workitem):
                workitem.abort()
                zope.event.notify(WorkItemAborted(workitem, app, actual))
            else:
                # Just discard the workitem (we cannot abort it)
                zope.event.notify(WorkItemDiscarded(workitem, app, actual))
            del self.workitems[workitem.id]
        zope.event.notify(ActivityAborted(self))

    def restoreWFRD(self):
        wf_revert_names = [name for name in dir(self.process.applicationRelevantData)
                           if name.startswith(WFRD_PREFIX+str(self.id)+"_")]
        for name in wf_revert_names:
            old_val = getattr(self.process.applicationRelevantData, name)
            wfname = name.lstrip(WFRD_PREFIX+str(self.id)+"_")
            if old_val == DEL_MARKER:
                delattr(self.process.workflowRelevantData, wfname)
            else:
                setattr(self.process.workflowRelevantData, wfname, old_val)

    def cancelDeadlines(self):
        for deadline in self.deadlines:
            self.process.deadlineCanceller(deadline)

    def revert(self, cancelDeadlineTimer=True):

        reverted_workitems = []
        # Revert all finished workitems.
        for workitem, app, formal, actual in self.finishedWorkitems.values():
            if interfaces.IRevertableWorkItem.providedBy(workitem):
                workitem.revert()
                reverted_workitems.append(workitem)

        # Restore workflowRelevantData
        self.restoreWFRD()

        if cancelDeadlineTimer:
            self.cancelDeadlines()

        zope.event.notify(ActivityReverted(self))

        return reverted_workitems

    def __repr__(self):
        return "Activity(%r)" % (
            self.process.process_definition_identifier + '.' +
            self.activity_definition_identifier
            )


class WorkflowData(persistent.Persistent):
    """Container for workflow-relevant and application-relevant data
    """


class Sequence(object):
    counter = 0

    def __init__(self, counter=0):
        self.counter = counter

    def next(self):
        self.counter += 1
        return self.counter

    def current(self):
        return self.counter


@interface.implementer(interfaces.IActivityContainer)
class ActivityContainer(dict):

    def getActive(self):
        return [a for a in self.values() if a.active]

    def getFinished(self):
        return [a for a in self.values() if not a.active]


@interface.implementer(interfaces.IProcess)
class Process(persistent.Persistent):

    ActivityFactory = Activity
    WorkflowDataFactory = WorkflowData

    isStarted = False
    isFinished = False
    isAborted = False
    starterActivityId = None
    starterWorkitemId = None
    execution = interfaces.SYNCHRONOUS
    asyncflowId = None

    deadlineTimer = defaultDeadlineTimer
    deadlineCanceller = defaultDeadlineCanceller

    def __init__(self, definition, start, context=None):
        self.process_definition_identifier = definition.id
        self.context = context
        self._definition = definition
        self.activities = ActivityContainer()
        self.activityIdSequence = Sequence()
        self.asyncflowIdSequence = Sequence()
        self.workflowRelevantData = self.WorkflowDataFactory()
        self.applicationRelevantData = self.WorkflowDataFactory()
        self.subflows = []

    @property
    def startTransition(self):
        return self.definition._start

    @property
    def definition(self):
        try:
            return getProcessDefinition(self.process_definition_identifier)
        except zope.component.interfaces.ComponentLookupError:
            return self._definition

    def start(self, *arguments):
        if self.isStarted:
            raise TypeError("Already started")

        definition = self.definition
        data = self.workflowRelevantData
        evaluator = interfaces.IPythonExpressionEvaluator(self)

        # Assign data defaults.
        for id, datafield in definition.datafields.items():
            val = None
            if datafield.initialValue:
                val = evaluator.evaluate(datafield.initialValue)
            setattr(data, id, val)

        # Now apply input parameters on top of the defaults.
        args = arguments
        inputparams = [p for p in definition.parameters if p.input]
        for parameter in inputparams:
            if args:
                arg, args = args[0], args[1:]
            elif parameter.initialValue is not None:
                arg = evaluator.evaluate(parameter.initialValue)
            else:
                __traceback_info__ = (self, args, definition.parameters)
                raise ValueError(
                    'Insufficient arguments passed to process.')
            setattr(data, parameter.__name__, arg)
        if args:
            raise TypeError("Too many arguments. Expected %s. got %s" %
                            (len(inputparams), len(arguments)))

        if self.execution == interfaces.ASYNCHRONOUS:
            # Asynchronous processes gets their own asyncflowId
            self.asyncflowId = self.asyncflowIdSequence.next()

        self.isStarted = True
        zope.event.notify(ProcessStarted(self))
        self.transition(None, (self.startTransition, ))

    def outputs(self):
        outputs = {}
        evaluator = interfaces.IPythonExpressionEvaluator(self)
        for parameter in self.definition.parameters:
            if parameter.output:
                if hasattr(self.workflowRelevantData, parameter.__name__):
                    value = getattr(self.workflowRelevantData,
                                    parameter.__name__)
                elif parameter.initialValue is not None:
                    value = evaluator.evaluate(parameter.initialValue)
                else:
                    __traceback_info__ = (self, parameter)
                    raise ValueError('Process finished, and there is an output '
                                     'parameter with no value in workflow vars '
                                     'and no initial value.')
                outputs[parameter.__name__] = value

        return outputs

    def _finish(self):
        self.isFinished = True
        if self.starterActivityId:
            if self.execution == interfaces.ASYNCHRONOUS:
                # Starter activity was already finished, since this process is
                # asynchronous
                return
            # Subflow finished, continue with main flow
            starter = self.activities[self.starterActivityId]
            wi, _, _, _ = starter.workitems[self.starterWorkitemId]
            starter.workItemFinished(wi, self.outputs())
        else:
            self._terminateAsyncflows()
            zope.event.notify(ProcessFinished(self))

    def _terminateAsyncflows(self):
        for act in self.activities.getActive():
            if act.process.asyncflowId is None:
                # This is activity from main process, don't touch it
                continue

            self.throwException(act)

    def abort(self):
        allActivities = self.activities.values()
        for activity in sorted(allActivities,
                               key=Process.chronological_key,
                               reverse=True):
            if activity.active:
                activity.abort()
            else:
                activity.revert()
            del self.activities[activity.id]
        self.isAborted = True
        zope.event.notify(ProcessAborted(self))

    def transition(self, activity, transitions):
        if transitions:
            definition = self.definition

            for transition in transitions:
                activity_definition = definition.activities[transition.to]
                next = None
                if activity_definition.andJoinSetting:
                    # If it's an and-join, we want only one.
                    for a in self.activities.getActive():
                        if a.process is not activity.process:
                            continue
                        if a.activity_definition_identifier == transition.to:
                            # we already have the activity -- use it
                            next = a
                            break

                if next is None:
                    next = self.ActivityFactory(self, activity_definition)

                zope.event.notify(Transition(activity, next))
                self.activities[next.id] = next
                next.start(transition)
        else:
            self._finish()

        self._p_changed = True

    def __repr__(self):
        return "Process(%r)" % self.process_definition_identifier

    def getSubflowProcessDefinition(self, subflow_pd_name):
        return getProcessDefinition(subflow_pd_name)

    def initSubflow(self, subflow_pd_name, starter_activity_id,
                    starter_workitem_id,
                    execution=interfaces.SYNCHRONOUS,
                    proc_factory=None):
        subflow_pd = self.getSubflowProcessDefinition(subflow_pd_name)
        subflow = subflow_pd(self.context, factory=proc_factory)
        subflow.activities = self.activities
        subflow.activityIdSequence = self.activityIdSequence
        subflow.subflows = self.subflows

        subflow.starterActivityId = starter_activity_id
        subflow.starterWorkitemId = starter_workitem_id
        subflow.execution = execution
        subflow.asyncflowIdSequence = self.asyncflowIdSequence

        subflow.asyncflowId = self.asyncflowId

        self.subflows.append(subflow)
        return subflow

    @staticmethod
    def chronological_key(activity):
        """
        Returns the key for sorting activities chronologically in a list
        """
        return activity.id

    def throwException(self, activity):
        """Throw process exception

        We abort the activity and follow exception route
        """
        activity.abort()

        transitions = getValidOutgoingTransitions(
            self, activity.definition,
            exception=True
        )

        activity.process.transition(activity, transitions)

    def deadlinePassedHandler(self, deadline):
        # TODO: Is this threadsafe?
        if deadline.definition.execution != u'SYNCHR':
            raise NotImplementedError('Only Synchronous (SYNCHR) deadlines are '
                                      'supported at this piont.')
        activity = deadline.activity
        activity.abort(cancelDeadlineTimer=False)
        transitions = getValidOutgoingTransitions(
            self, activity.definition,
            exception=True
        )

        # activity.process, since self could be parent flow and we need local
        # flow in case of subflow
        activity.process.transition(activity, transitions)


@interface.implementer(interfaces.IProcessStarted)
class ProcessStarted:

    def __init__(self, process):
        self.process = process

    def __repr__(self):
        return "ProcessStarted(%r)" % self.process


@interface.implementer(interfaces.IProcessFinished)
class ProcessFinished:

    def __init__(self, process):
        self.process = process

    def __repr__(self):
        return "ProcessFinished(%r)" % self.process


@interface.implementer(interfaces.IProcessAborted)
class ProcessAborted:

    def __init__(self, process):
        self.process = process

    def __repr__(self):
        return "ProcessAborted(%r)" % self.process


def getEvaluator(process):
    """Return expression evaluator object for given proceess"""
    return interfaces.IPythonExpressionEvaluator(process)


def evaluateInputs(process, formal, actual, evaluator, strict=True):
    """Evaluate input parameters for the process or activity

    Return list of pairs: (name, value) for each input parameter
    """
    args = []
    for parameter, expr in zip(formal, actual):
        if parameter.input:
            if expr is u'':
                expr = getattr(parameter, 'initialValue', '')
            __traceback_info__ = (parameter, expr)
            try:
                value = evaluator.evaluate(expr)
            except:
                if strict:
                    raise
                else:
                    continue
            args.append((parameter.__name__, value))

    return args


def getValidOutgoingTransitions(process, activity_definition, exception=False,
                                checker=None):
    """Return list of valid outgoing transitions from given activity_definition
    in given process.

    Valid outgoing transitions are transitions having conditions that are
    evaluating to True (or "otherwise" transitions if all conditions are
    False).

    If any exception is raised during evaluation of condition expressions,
    it will be rerised only if ``strict`` parameter is True. Otherwise, the
    condition will be treated as False.

    A custom checker can be passed in if the caller wants more control over
    what gets raised during evaluation of the condition. The checker should
    take a transition and return a boolean if the transition is available.
    """
    def defaultChecker(transition):
        return transition.condition(process)

    if checker is None:
        checker = defaultChecker
    transitions = []
    otherwises = []

    if exception:
        # TODO: Need support for exception Name specification
        for transition in activity_definition.outgoing:
            if transition.type == u'DEFAULTEXCEPTION':
                return [transition]
        else:
            raise interfaces.ProcessError(
                'The activity_definition {} exited with an exception, but no '
                'exception transition was found.'.format(activity_definition)
            )

    for transition in activity_definition.outgoing:
        if transition.otherwise:
            # do not consider 'otherwise' transitions just yet
            otherwises.append(transition)
            continue
        if checker(transition):
            transitions.append(transition)
            if not activity_definition.andSplitSetting:
                break  # xor split, want first one

    if not transitions:
        # no condition was met, choose 'otherwise' transitions
        transitions = otherwises

    return transitions


@zope.interface.implementer(interfaces.IWorkItem)
class ScriptWorkItem(object):
    """Executes the script and stores all changed workflow-relevant
    attributes."""

    def __init__(self, process, activity, code):
        self.process = process
        self.activity = activity
        self.code = code

    def execute(self):
        evaluator = interfaces.IPythonExpressionEvaluator(self.process)
        evaluator.execute(self.code)

    def start(self, args):
        self.execute()
        self.finish()

    def finish(self):
        self.activity.workItemFinished(self)


@zope.interface.implementer(interfaces.IWorkItem)
class SubflowWorkItem(object):
    processFactory = None

    def __init__(self, process, activity, subflow, execution):
        self.process = process
        self.activity = activity
        self.subflow = subflow
        self.execution = execution

    def start(self, args):
        subproc = self.process.initSubflow(self.subflow,
                                           self.activity.id, self.id,
                                           proc_factory=self.processFactory,
                                           execution=self.execution)
        pd = subproc.definition
        tupArgs = [args.get(p.__name__, None) for p in pd.parameters if p.input]
        subproc.start(*tupArgs)

        if self.execution == interfaces.ASYNCHRONOUS:
            self.activity.workItemFinished(self)


class WorkItemFinished(object):

    def __init__(self, workitem, application, parameters, results):
        self.workitem = workitem
        self.application = application
        self.parameters = parameters
        self.results = results

    def __repr__(self):
        return "WorkItemFinished(%r)" % self.application


class WorkItemStarting(object):
    """Event emitted just before starting workitem
    """
    def __init__(self, workitem, application, parameters):
        self.workitem = workitem
        self.application = application
        self.parameters = parameters

    def __repr__(self):
        return "WorkItemStarting(%r)" % self.application


class WorkItemStarted(object):
    """Event emitted just after starting a workitem"""
    def __init__(self, workitem, application, parameters):
        self.workitem = workitem
        self.application = application
        self.parameters = parameters

    def __repr__(self):
        return "WorkItemStarted(%r)" % self.application


class WorkItemAborted:

    def __init__(self, workitem, application, parameters):
        self.workitem = workitem
        self.application = application
        self.parameters = parameters

    def __repr__(self):
        return "WorkItemAborted(%r)" % self.application


class WorkItemDiscarded(object):
    def __init__(self, workitem, application, parameters):
        self.workitem = workitem
        self.application = application
        self.parameters = parameters

    def __repr__(self):
        return "WorkItemDiscarded(%r)" % self.application


class Transition:

    def __init__(self, from_, to):
        self.from_ = from_
        self.to = to

    def __repr__(self):
        return "Transition(%r, %r)" % (self.from_, self.to)


class TextCondition:

    def __init__(self, type='CONDITION', source=''):
        self.type = type
        self.otherwise = type in ('OTHERWISE', )

        if source:
            self.set_source(source)

    def set_source(self, source):
        self.source = source
        # make sure that we can compile the source
        compile(source, '<string>', 'eval')

    def __getstate__(self):
        return {'source': self.source,
                'type': self.type}

    def __call__(self, process, data={}):
        evaluator = interfaces.IPythonExpressionEvaluator(process)
        return evaluator.evaluate(self.source, data)


class ActivityFinished:

    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):
        return "ActivityFinished(%r)" % self.activity


class ActivityReverted:

    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):
        return "ActivityReverted(%r)" % self.activity


class ActivityAborted:

    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):
        return "ActivityAborted(%r)" % self.activity


class ActivityStarted:

    def __init__(self, activity):
        self.activity = activity

    def __repr__(self):
        return "ActivityStarted(%r)" % self.activity


@interface.implementer(interfaces.IParameterDefinition)
class Parameter(object):

    input = output = False
    initialValue = None

    def __init__(self, name):
        self.__name__ = name

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.__name__)


class OutputParameter(Parameter):
    output = True


class InputParameter(Parameter):
    input = True

class InputOutputParameter(InputParameter, OutputParameter):

    pass

@interface.implementer(interfaces.IApplicationDefinition,
                         interfaces.IExtendedAttributesContainer)
class Application:

    def __init__(self, *parameters):
        self.parameters = parameters
        self.attributes = OrderedDict()

    def defineParameters(self, *parameters):
        self.parameters += parameters

    def __repr__(self):
        input = u', '.join([param.__name__ for param in self.parameters
                           if param.input == True])
        output = u', '.join([param.__name__ for param in self.parameters
                           if param.output == True])
        return "<Application %r: (%s) --> (%s)>" % (self.id, input, output)


@interface.implementer(interfaces.IParticipantDefinition,
                         interfaces.IExtendedAttributesContainer)
class Participant:

    def __init__(self, name=None, type=None):
        self.__name__ = name
        self.type = type
        self.description = None
        self.attributes = OrderedDict()

    def __repr__(self):
        return "Participant(%r, %r)" % (self.__name__, self.type)


@interface.implementer(interfaces.IDataFieldDefinition)
class DataField:

    def __init__(self, name=None, title=None, initialValue=None):
        self.__name__ = name
        self.title = title
        self.initialValue = initialValue

    def __repr__(self):
        return "DataField(%r, %r, %r)" % (
            self.__name__, self.title, self.initialValue)


ALLOWED_BUILTIN_NAMES = ['True', 'False', 'None']
ALLOWED_BUILTINS = {k: v for k, v in __builtins__.items()
                    if k in ALLOWED_BUILTIN_NAMES}


@interface.implementer(interfaces.IPythonExpressionEvaluator)
class PythonExpressionEvaluator(object):
    """Simple Python Expression Evaluator.

    This evaluator only produces a limited namespace and does not use a safe
    Python engine.
    """
    component.adapts(interfaces.IProcess)

    def __init__(self, process):
        self.process = process

    def evaluate(self, expr, locals={}):
        __traceback_info__ = (expr, locals)
        ns = {'context': self.process.context}
        ns.update(vars(self.process.workflowRelevantData))
        ns.update(vars(self.process.applicationRelevantData))
        ns.update(locals)
        return eval(expr, ALLOWED_BUILTINS, ns)

    def execute(self, code, locals={}):
        __traceback_info__ = (code, locals)
        ns = {'context': self.process.context}
        ns.update(vars(self.process.workflowRelevantData))
        ns.update(vars(self.process.applicationRelevantData))
        ns.update(locals)
        ns.update(ALLOWED_BUILTINS)
        result = {}
        exec(code, ALLOWED_BUILTINS, result)
        for name, value in result:
            pass


def getProcessDefinition(name):
    """Return process definition with given name"""
    factory = component.getUtility(interfaces.IProcessDefinitionFactory)
    pd = factory.get(name)
    if pd is None:
        raise RuntimeError("Process with name %s is not found" % name)
    return pd


def getActivityStackPath(activity_defs):
    """Return path of activity definition stack (as a string)
    """
    return "/".join("%s@%s" % (ad.process.id, ad.id) for ad in activity_defs)


def calculateActivityStackPath(activity):
    if activity.definition is None:
        return None
    stack = activity.getExecutionStack()
    ads = [a.definition for a in stack if a.definition]
    ads.append(activity.definition)
    return getActivityStackPath(ads)
