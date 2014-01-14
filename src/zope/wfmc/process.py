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
import persistent
import zope.cachedescriptors.property
import zope.event
from collections import OrderedDict
from zope import component, interface

from zope.wfmc import interfaces

def always_true(data):
    return True

class TransitionDefinition(object):

    interface.implements(interfaces.ITransitionDefinition)

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
        return "TransitionDefinition(from=%r, to=%r)" %(self.from_, self.to)


class ProcessDefinition(object):

    interface.implements(interfaces.IProcessDefinition)

    TransitionDefinitionFactory = TransitionDefinition

    def __init__(self, id, integration=None):
        self.id = id
        self.integration = integration
        self.activities = {}
        self.transitions = []
        self.applications = {}
        self.participants = {}
        self.datafields = {}
        self.parameters = ()
        self.attributes = OrderedDict()
        self.description = None

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

class ActivityDefinition(object):

    interface.implements(interfaces.IActivityDefinition,
                         interfaces.IExtendedAttributesContainer)

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
                            %(actual, formal, app, app.id))
        self.applications += ((application, formal, tuple(actual)), )

    def addSubFlow(self, subflow, execution, actual=()):
        # Lookup of formal parameters must be delayed, since the subflow might
        # not yet be loaded.
        self.subflows += ((subflow, execution, None, tuple(actual)), )

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
        return "<ActivityDefinition %r>" %self.__name__


class Activity(persistent.Persistent):

    interface.implements(interfaces.IActivity)

    def __init__(self, process, definition):
        self.process = process
        self.activity_definition_identifier = definition.id
        self.workitems = None
        self.finishedWorkitems = {}

    def createWorkItems(self):
        integration = self.process.definition.integration
        definition = self.definition
        participant = None
        workitems = {}

        if definition.applications or definition.subflows or definition.scripts:

            participant = integration.createParticipant(
                self, self.process, definition.performer)

            i = 0

            # Instantiate Applications
            for application, formal, actual in definition.applications:
                workitem = integration.createWorkItem(
                    participant, self.process, self, application)
                i += 1
                workitem.id = i
                workitems[i] = workitem, application, formal, actual

            # Instantiate Subflows
            for subflow, execution, formal, actual in definition.subflows:
                workitem = integration.createSubFlowWorkItem(
                    self.process, self, subflow, execution)
                i += 1
                workitem.id = i
                workitems[i] = workitem, subflow, formal, actual

            # Script
            for code in definition.scripts:
                workitem = integration.createScriptWorkItem(
                    self.process, self, code)
                i += 1
                workitem.id = i
                workitems[i] = workitem, "__script__", (), ()

        self.workitems = workitems

    def definition(self):
        return self.process.definition.activities[
            self.activity_definition_identifier]
    definition = property(definition)

    incoming = ()
    def start(self, transition):
        # Start the activity, if we've had enough incoming transitions

        definition = self.definition

        if definition.andJoinSetting:
            if transition in self.incoming:
                raise interfaces.ProcessError(
                    "Repeated incoming %s with id='%s' "
                    "while waiting for and completion"
                    %(transition, transition.id))
            self.incoming += (transition, )

            if len(self.incoming) < len(definition.incoming):
                return # not enough incoming yet

        zope.event.notify(ActivityStarted(self))

        if self.workitems:
            evaluator = interfaces.IPythonExpressionEvaluator(self.process)
            for workitem, app, formal, actual in self.workitems.values():
                args = []
                for parameter, name in zip(formal, actual):
                    if parameter.input:
                        __traceback_info__ = (
                            workitem, self.activity_definition_identifier,
                            parameter)
                        value = evaluator.evaluate(name)
                        args.append(value)

                __traceback_info__ = (self.activity_definition_identifier,
                                      workitem, args)
                workitem.start(*args)

        else:
            # Since we don't have any work items, we're done
            self.finish()

    def workItemDiscardard(self, work_item):
        self.workitems.pop(work_item.id)
        self._p_changed = True
        if not self.workitems:
            self.finish()

    def workItemFinished(self, work_item, *results):
        unused, app, formal, actual = entry = self.workitems.pop(work_item.id)
        self.finishedWorkitems[work_item.id] = entry
        self._p_changed = True
        res = results
        outputs = [(param, name) for param, name in zip(formal, actual)
                   if param.output]
        if len(res) != len(outputs):
            formalnames = tuple([p.__name__ for p, a in outputs])
            raise TypeError("Not enough parameters returned by work "
                            "item. Expected: %s, got: %s" % (formalnames,
                                                             results))

        for parameter, name in zip(formal, actual):
            if parameter.output:
                v = res[0]
                res = res[1:]
                setattr(self.process.workflowRelevantData, name, v)

        if res:
            raise TypeError("Too many results")

        zope.event.notify(WorkItemFinished(
            work_item, app, actual, results))

        if not self.workitems:
            self.finish()

    def finish(self):
        zope.event.notify(ActivityFinished(self))

        transitions = getValidOutgoingTransitions(self.process, self.definition)

        self.process.transition(self, transitions)

    def abort(self):
        # Abort all workitems.
        for workitem, app, formal, actual in self.workitems.values():
            if interfaces.IAbortWorkItem.providedBy(workitem):
                workitem.abort()
                zope.event.notify(WorkItemAborted(workitem, app, actual))
        # Remove itself from the process activities list.
        del self.process.activities[self.id]
        zope.event.notify(ActivityAborted(self))

    def revert(self):
        # Revert all finished workitems.
        for workitem, app, formal, actual in self.finishedWorkitems.values():
            if interfaces.IRevertableWorkItem.providedBy(workitem):
                workitem.revert()

    def __repr__(self):
        return "Activity(%r)" % (
            self.process.process_definition_identifier + '.' +
            self.activity_definition_identifier
            )


class WorkflowData(persistent.Persistent):
    """Container for workflow-relevant and application-relevant data
    """


class Process(persistent.Persistent):

    interface.implements(interfaces.IProcess)

    ActivityFactory = Activity
    WorkflowDataFactory = WorkflowData

    def __init__(self, definition, start, context=None):
        self.process_definition_identifier = definition.id
        self.context = context
        self.activities = {}
        self.finishedActivities = {}
        self.nextActivityId = 0
        self.workflowRelevantData = self.WorkflowDataFactory()
        self.applicationRelevantData = self.WorkflowDataFactory()

    @property
    def startTransition(self):
        return self.definition._start

    @property
    def definition(self):
        return component.getUtility(
            interfaces.IProcessDefinition,
            self.process_definition_identifier,
            )

    def start(self, *arguments):
        if self.activities:
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
                pass
            else:
                __traceback_info__ = (self, args, definition.parameters)
                raise ValueError(
                    'Insufficient arguments passed to process.')
            setattr(data, parameter.__name__, arg)
        if args:
            raise TypeError("Too many arguments. Expected %s. got %s" %
                            (len(inputparams), len(arguments)))

        zope.event.notify(ProcessStarted(self))
        self.transition(None, (self.startTransition, ))

    def outputs(self):
        outputs = []
        for parameter in self.definition.parameters:
            if parameter.output:
                outputs.append(
                    getattr(self.workflowRelevantData,
                            parameter.__name__))

        return outputs

    def _finish(self):
        zope.event.notify(ProcessFinished(self))

    def abort(self):
        for idx, activity in self.activities.items():
            activity.abort()
        for idx, activity in self.finishedActivities.items():
            activity.revert()
        zope.event.notify(ProcessAborted(self))

    def transition(self, activity, transitions):
        if transitions:
            definition = self.definition

            for transition in transitions:
                activity_definition = definition.activities[transition.to]
                next = None
                if activity_definition.andJoinSetting:
                    # If it's an and-join, we want only one.
                    for i, a in self.activities.items():
                        if a.activity_definition_identifier == transition.to:
                            # we already have the activity -- use it
                            next = a
                            break

                if next is None:
                    next = self.ActivityFactory(self, activity_definition)
                    next.createWorkItems()
                    self.nextActivityId += 1
                    next.id = self.nextActivityId

                zope.event.notify(Transition(activity, next))
                self.activities[next.id] = next
                next.start(transition)

        if activity is not None:
            del self.activities[activity.id]
            self.finishedActivities[activity.id] = activity
            if not self.activities:
                self._finish()

        self._p_changed = True

    def __repr__(self):
        return "Process(%r)" % self.process_definition_identifier


class ProcessStarted:
    interface.implements(interfaces.IProcessStarted)

    def __init__(self, process):
        self.process = process

    def __repr__(self):
        return "ProcessStarted(%r)" % self.process

class ProcessFinished:
    interface.implements(interfaces.IProcessFinished)

    def __init__(self, process):
        self.process = process

    def __repr__(self):
        return "ProcessFinished(%r)" % self.process

class ProcessAborted:
    interface.implements(interfaces.IProcessAborted)

    def __init__(self, process):
        self.process = process

    def __repr__(self):
        return "ProcessAborted(%r)" % self.process


def getValidOutgoingTransitions(process, activity_definition, strict=True):
    """Return list of valid outgoing transitions from given activity_definition
    in given process.

    Valid outgoing transitions are transitions having conditions that are
    evaluating to True (or "otherwise" transitions if all conditions are
    False).

    If any exception is raised during evaluation of condition expressions,
    it will be rerised only if ``strict`` parameter is True. Otherwise, the
    condition will be treated as False.
    """
    transitions = []
    otherwises = []

    for transition in activity_definition.outgoing:
        if transition.otherwise:
            # do not consider 'otherwise' transitions just yet
            otherwises.append(transition)
            continue
        try:
            active = transition.condition(process)
        except:
            if strict:
                raise
            else:
                active = False
        if active:
            transitions.append(transition)
            if not activity_definition.andSplitSetting:
                break  # xor split, want first one

    if not transitions:
        # no condition was met, choose 'otherwise' transitions
        return otherwises
    return transitions


class ScriptWorkItem(object):
    "Executes the script and stores all changed workflow-relevant attributes."

    def __init__(self, process, activity, code):
        self.process = process
        self.activity = activity
        self.code = code

    def execute(self):
        evaluator = interfaces.IPythonExpressionEvaluator(self.process)
        evaluator.execute(self.code)

    def start(self):
        self.execute()
        self.finish()

    def finish(self):
        self.activity.workItemFinished(self)


class WorkItemFinished(object):

    def __init__(self, workitem, application, parameters, results):
        self.workitem =  workitem
        self.application = application
        self.parameters = parameters
        self.results = results

    def __repr__(self):
        return "WorkItemFinished(%r)" % self.application

class WorkItemAborted:

    def __init__(self, workitem, application, parameters):
        self.workitem =  workitem
        self.application = application
        self.parameters = parameters

    def __repr__(self):
        return "WorkItemAborted(%r)" % self.application

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

class Parameter(object):

    interface.implements(interfaces.IParameterDefinition)

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

class Application:

    interface.implements(interfaces.IApplicationDefinition)

    def __init__(self, *parameters):
        self.parameters = parameters

    def defineParameters(self, *parameters):
        self.parameters += parameters

    def __repr__(self):
        input = u', '.join([param.__name__ for param in self.parameters
                           if param.input == True])
        output = u', '.join([param.__name__ for param in self.parameters
                           if param.output == True])
        return "<Application %r: (%s) --> (%s)>" % (self.id, input, output)


class Participant:

    interface.implements(interfaces.IParticipantDefinition)

    def __init__(self, name=None, type=None):
        self.__name__ = name
        self.type = type
        self.description = None

    def __repr__(self):
        return "Participant(%r, %r)" % (self.__name__, self.type)


class DataField:

    interface.implements(interfaces.IDataFieldDefinition)

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


class PythonExpressionEvaluator(object):
    """Simple Python Expression Evaluator.

    This evaluator only produces a limited namespace and does not use a safe
    Python engine.
    """
    interface.implements(interfaces.IPythonExpressionEvaluator)
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
        exec code in ALLOWED_BUILTINS, result
        for name, value in result:
            pass
