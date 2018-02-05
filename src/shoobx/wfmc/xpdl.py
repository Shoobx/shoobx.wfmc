##############################################################################
#
# Copyright (c) 2004 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""XPDL reader for process definitions
"""
from __future__ import absolute_import
import logging
import sys
import xml.sax
import xml.sax.xmlreader
import xml.sax.handler

import shoobx.wfmc.process
from zope import interface
from shoobx.wfmc import interfaces
import six

xpdlns10 = "http://www.wfmc.org/2002/XPDL1.0"
xpdlns21 = "http://www.wfmc.org/2008/XPDL2.1"

RAISE_ON_DUPLICATE_ERROR = False

log = logging.getLogger(__name__)


class HandlerError(Exception):

    def __init__(self, orig, tag, locator):
        self.orig = orig
        self.tag = tag
        self.xml = locator.getSystemId()
        self.line = locator.getLineNumber()

    def __repr__(self):
        return ('%r\nFile "%s", line %s. in %s'
                % (self.orig, self.xml, self.line, self.tag))

    def __str__(self):
        return ('%s\nFile "%s", line %s. in %s'
                % (self.orig, self.xml, self.line, self.tag))

    def __call__(self):
        return self


class Package(dict):

    def __init__(self):
        self.applications = {}
        self.participants = {}
        self.pools = {}
        self.script = None
        self.parseErrors = []

    def defineApplications(self, **applications):
        for id, application in applications.items():
            application.id = id
            self.applications[id] = application

    def definePools(self, **pools):
        for id, pool in pools.items():
            pool.id = id
            self.pools[id] = pool

    def defineParticipants(self, **participants):
        for id, participant in participants.items():
            participant.id = id
            self.participants[id] = participant

    def addScript(self, script):
        self.script = script


@interface.implementer(interfaces.IPoolDefinition)
class PoolDefinition:

    def __init__(self, name=None, process_def=None):
        self.__name__ = name
        self.process_def = process_def
        self.lanes = {}

    def defineLanes(self, **lanes):
        for id, lane in lanes.items():
            lane.id = id
            self.lanes[id] = lane

    def __repr__(self):
        return "Pool(%r, %r)" % (self.__name__, self.process_def)


@interface.implementer(interfaces.ILaneDefinition)
class LaneDefinition:

    def __init__(self, name=None):
        self.__name__ = name
        self.performers = ()

    def definePerformer(self, performer):
        self.performers += (performer,)

    def __repr__(self):
        return "Lane(%r)" % (self.__name__, )


class DeadlineDefinition(object):
    def __init__(self, duration, act_def, exceptionName=None,
                 execution='SYNCHR'):
        self.duration = duration
        self.exceptionName = exceptionName
        self.execution = execution

        # The definition ID must be the list index, since there is no other
        # uniquely identifying information (0 for the first, etc.)
        self.id = len(act_def.deadlines)
        if self.id > 0:
            raise NotImplementedError(
                'Current implementation only supports one deadline per activity'
            )
        act_def.deadlines.append(self)


class XPDLHandler(xml.sax.handler.ContentHandler):

    start_handlers = {}
    end_handlers = {}
    text = u''

    ProcessDefinitionFactory = shoobx.wfmc.process.ProcessDefinition
    PoolDefinitionFactory = PoolDefinition
    LaneDefinitionFactory = LaneDefinition
    ParticipantFactory = shoobx.wfmc.process.Participant
    DataFieldFactory = shoobx.wfmc.process.DataField
    ApplicationFactory = shoobx.wfmc.process.Application
    ActivityDefinitionFactory = shoobx.wfmc.process.ActivityDefinition
    TransitionDefinitionFactory = shoobx.wfmc.process.TransitionDefinition
    TextCondition = shoobx.wfmc.process.TextCondition
    DeadlineDefinitionFactory = DeadlineDefinition

    def __init__(self, package):
        self.package = package
        self.stack = []
        self.textstack = []

    @property
    def text(self):
        return self.textstack[-1]

    def startElementNS(self, name, qname, attrs):
        handler = self.start_handlers.get(name)
        if handler:
            try:
                result = handler(self, attrs)
            except:
                six.reraise(HandlerError(sys.exc_info()[1], name[1], self.locator
                    ), None, sys.exc_info()[2])
        else:
            result = None

        if result is None:
            # Just dup the top of the stack
            result = self.stack[-1]

        self.stack.append(result)
        self.textstack.append(u'')

    def endElementNS(self, name, qname):
        last = self.stack.pop()
        handler = self.end_handlers.get(name)
        if handler:
            try:
                handler(self, last)
            except:
                six.reraise(HandlerError(sys.exc_info()[1], name[1], self.locator
                    ), None, sys.exc_info()[2])

        self.textstack.pop()

    def characters(self, text):
        self.textstack[-1] += text

    def setDocumentLocator(self, locator):
        self.locator = locator

    ######################################################################
    # Application handlers

    # Pointless container elements that we want to "ignore" by having them
    # dup their containers:
    def Package(self, attrs):
        package = self.package
        package.id = attrs[(None, 'Id')]
        package.__name__ = attrs.get((None, 'Name'))
        return package
    start_handlers[(xpdlns10, 'Package')] = Package
    start_handlers[(xpdlns21, 'Package')] = Package

    def WorkflowProcess(self, attrs):
        id = attrs[(None, 'Id')]
        process = self.ProcessDefinitionFactory(id)
        process.__name__ = attrs.get((None, 'Name'))

        # Copy package data:
        process.defineApplications(**self.package.applications)
        process.defineParticipants(**self.package.participants)

        self.package[id] = process
        return process
    start_handlers[(xpdlns10, 'WorkflowProcess')] = WorkflowProcess
    start_handlers[(xpdlns21, 'WorkflowProcess')] = WorkflowProcess

    parameter_types = {
        'IN': shoobx.wfmc.process.InputParameter,
        'OUT': shoobx.wfmc.process.OutputParameter,
        'INOUT': shoobx.wfmc.process.InputOutputParameter,
        }

    def FormalParameter(self, attrs):
        mode = attrs.get((None, 'Mode'), 'IN')
        id = attrs[(None, 'Id')]
        parameter = self.parameter_types[mode](id)
        self.stack[-1].defineParameters(parameter)
        return parameter
    start_handlers[(xpdlns10, 'FormalParameter')] = FormalParameter
    start_handlers[(xpdlns21, 'FormalParameter')] = FormalParameter

    def Pool(self, attrs):
        id = attrs[(None, 'Id')]
        name = attrs.get((None, 'Name'))
        process_def = attrs.get((None, 'Process'))
        pool = self.PoolDefinitionFactory(name, process_def)
        self.stack[-1].definePools(**{str(id): pool})
        return pool
    start_handlers[(xpdlns10, 'Pool')] = Pool
    start_handlers[(xpdlns21, 'Pool')] = Pool

    def Lane(self, attrs):
        id = attrs[(None, 'Id')]
        name = attrs.get((None, 'Name'))
        lane = self.LaneDefinitionFactory(name)
        self.stack[-1].defineLanes(**{str(id): lane})
        return lane
    start_handlers[(xpdlns10, 'Lane')] = Lane
    start_handlers[(xpdlns21, 'Lane')] = Lane

    def Participant(self, attrs):
        id = attrs[(None, 'Id')]
        name = attrs.get((None, 'Name'))
        participant = self.ParticipantFactory(name)
        self.stack[-1].defineParticipants(**{str(id): participant})
        return participant
    start_handlers[(xpdlns10, 'Participant')] = Participant
    start_handlers[(xpdlns21, 'Participant')] = Participant

    def ParticipantType(self, attrs):
        tp = attrs.get((None, 'Type'))
        participant = self.stack[-1]
        participant.type = tp
        return participant
    start_handlers[(xpdlns10, 'ParticipantType')] = ParticipantType
    start_handlers[(xpdlns21, 'ParticipantType')] = ParticipantType

    def DataField(self, attrs):
        id = attrs[(None, 'Id')]
        name = attrs.get((None, 'Name'))
        datafield = self.DataFieldFactory(id, name)
        self.stack[-1].defineDataFields(**{str(id): datafield})
        return datafield
    start_handlers[(xpdlns10, 'DataField')] = DataField
    start_handlers[(xpdlns21, 'DataField')] = DataField

    def initialValue(self, datafield):
        self.stack[-1].initialValue = self.text.strip()
    end_handlers[(xpdlns10, 'InitialValue')] = initialValue
    end_handlers[(xpdlns21, 'InitialValue')] = initialValue

    def Application(self, attrs):
        id = attrs[(None, 'Id')]
        name = attrs.get((None, 'Name'))
        app = self.ApplicationFactory()
        app.id = id
        if name:
            app.__name__ = name
        return app
    start_handlers[(xpdlns10, 'Application')] = Application
    start_handlers[(xpdlns21, 'Application')] = Application

    def application(self, app):
        self.stack[-1].defineApplications(**{str(app.id): app})
    end_handlers[(xpdlns10, 'Application')] = application
    end_handlers[(xpdlns21, 'Application')] = application

    def description(self, ignored):
        if self.stack[-1] is not None:
            self.stack[-1].description = self.text
    end_handlers[(xpdlns10, 'Description')] = description
    end_handlers[(xpdlns21, 'Description')] = description

    ######################################################################
    # Activity definitions

    def ActivitySet(self, attrs):
        raise NotImplementedError("ActivitySet")
    end_handlers[(xpdlns10, 'ActivitySet')] = ActivitySet
    end_handlers[(xpdlns21, 'ActivitySet')] = ActivitySet

    def Activity(self, attrs):
        id = attrs[(None, 'Id')]
        name = attrs.get((None, 'Name'))
        activity = self.ActivityDefinitionFactory(name)
        activity.id = id
        self.stack[-1].defineActivities(**{str(id): activity})
        return activity
    start_handlers[(xpdlns10, 'Activity')] = Activity
    start_handlers[(xpdlns21, 'Activity')] = Activity

    def startTool(self, attrs):
        return Tool(attrs[(None, 'Id')])
    start_handlers[(xpdlns10, 'Tool')] = startTool
    start_handlers[(xpdlns21, 'TaskApplication')] = startTool

    def endTool(self, tool):
        self.stack[-1].addApplication(tool.id, tool.parameters)
    end_handlers[(xpdlns10, 'Tool')] = endTool
    end_handlers[(xpdlns21, 'TaskApplication')] = endTool

    def SubFlow(self, attrs):
        return SubFlow(attrs[(None, 'Id')], attrs.get((None, 'Execution')))
    start_handlers[(xpdlns10, 'SubFlow')] = SubFlow
    start_handlers[(xpdlns21, 'SubFlow')] = SubFlow

    def subflow(self, subflow):
        self.stack[-1].addSubflow(subflow.id, subflow.execution,
                                  subflow.parameters)
    end_handlers[(xpdlns10, 'SubFlow')] = subflow
    end_handlers[(xpdlns21, 'SubFlow')] = subflow

    def script(self, script):
        self.stack[-1].addScript(self.text)
    end_handlers[(xpdlns10, 'Script')] = script
    end_handlers[(xpdlns21, 'Script')] = script

    def StartEvent(self, attrs):
        ad = self.stack[-1]
        assert isinstance(ad, shoobx.wfmc.process.ActivityDefinition)
        ad.event = interfaces.START_EVENT
    start_handlers[(xpdlns10, 'StartEvent')] = StartEvent
    start_handlers[(xpdlns21, 'StartEvent')] = StartEvent

    def EndEvent(self, attrs):
        ad = self.stack[-1]
        assert isinstance(ad, shoobx.wfmc.process.ActivityDefinition)
        ad.event = interfaces.END_EVENT
    start_handlers[(xpdlns10, 'EndEvent')] = EndEvent
    start_handlers[(xpdlns21, 'EndEvent')] = EndEvent

    def actualparameter(self, ignored):
        self.stack[-1].parameters += (self.text,)
    end_handlers[(xpdlns10, 'ActualParameter')] = actualparameter
    end_handlers[(xpdlns21, 'ActualParameter')] = actualparameter

    def performer(self, ignored):
        activity_or_lane = self.stack[-1]
        activity_or_lane.definePerformer(self.text.strip())
    end_handlers[(xpdlns10, 'Performer')] = performer
    end_handlers[(xpdlns21, 'Performer')] = performer

    def startDeadline(self, attrs):
        execution = attrs.get((None, u'Execution')) or u'SYNCHR'
        actdef = self.stack[-1]
        self.DeadlineDefinitionFactory(
            None, actdef, exceptionName=None, execution=execution)
    start_handlers[(xpdlns10, 'Deadline')] = startDeadline
    start_handlers[(xpdlns21, 'Deadline')] = startDeadline

    def deadlineDuration(self, actdef):
        duration = self.text.strip()
        actdef.deadlines[-1].duration = duration
    end_handlers[(xpdlns10, 'DeadlineDuration')] = deadlineDuration
    end_handlers[(xpdlns21, 'DeadlineDuration')] = deadlineDuration

    def exceptionName(self, actdef):
        exceptionName = self.text.strip()
        actdef.deadlines[-1].exceptionName = exceptionName
    end_handlers[(xpdlns10, 'exceptionName')] = exceptionName
    end_handlers[(xpdlns21, 'exceptionName')] = exceptionName

    def Join(self, attrs):
        Type = attrs.get((None, 'Type'))
        if Type in (u'AND', u'Parallel'):
            self.stack[-1].andJoin(True)
    start_handlers[(xpdlns10, 'Join')] = Join
    start_handlers[(xpdlns21, 'Join')] = Join

    def Split(self, attrs):
        Type = attrs.get((None, 'Type'))
        if Type in (u'AND', u'Parallel'):
            self.stack[-1].andSplit(True)
    start_handlers[(xpdlns10, 'Split')] = Split
    start_handlers[(xpdlns21, 'Split')] = Split

    def TransitionRef(self, attrs):
        Id = attrs.get((None, 'Id'))
        self.stack[-1].addOutgoing(Id)
    start_handlers[(xpdlns10, 'TransitionRef')] = TransitionRef
    start_handlers[(xpdlns21, 'TransitionRef')] = TransitionRef

    # Activity definitions
    ######################################################################
    def Transition(self, attrs):
        id = attrs[(None, 'Id')]
        name = attrs.get((None, 'Name'))
        from_ = attrs.get((None, 'From'))
        to = attrs.get((None, 'To'))
        transition = self.TransitionDefinitionFactory(from_, to)
        transition.id = id
        transition.__name__ = name
        return transition
    start_handlers[(xpdlns10, 'Transition')] = Transition
    start_handlers[(xpdlns21, 'Transition')] = Transition

    def transition(self, transition):
        self.stack[-1].defineTransitions(transition)
    end_handlers[(xpdlns10, 'Transition')] = transition
    end_handlers[(xpdlns21, 'Transition')] = transition

    def startCondition(self, attrs):
        tp = attrs.get((None, 'Type'), 'CONDITION')
        transdef = self.stack[-1]
        assert isinstance(transdef, self.TransitionDefinitionFactory)

        transdef.type = tp
        condition = self.TextCondition(tp)
        return condition
    start_handlers[(xpdlns10, 'Condition')] = startCondition
    start_handlers[(xpdlns21, 'Condition')] = startCondition

    def endCondition(self, condition):
        assert isinstance(self.stack[-1],
                          self.TransitionDefinitionFactory)

        text = self.text
        condition.set_source('(%s)' % text)
        self.stack[-1].condition = condition
    end_handlers[(xpdlns10, 'Condition')] = endCondition
    end_handlers[(xpdlns21, 'Condition')] = endCondition

    def ExtendedAttributes(self, attrs):
        parent = self.stack[-1]
        if interfaces.IExtendedAttributesContainer.providedBy(parent):
            return parent.attributes

        return {}  # dummy dict that will be discarded
    start_handlers[(xpdlns10, 'ExtendedAttributes')] = ExtendedAttributes
    start_handlers[(xpdlns21, 'ExtendedAttributes')] = ExtendedAttributes

    def ExtendedAttribute(self, attrs):
        container = self.stack[-1]
        name = attrs[(None, 'Name')]
        value = attrs.get((None, 'Value'))
        if name in container:
            msg = (u"The Name '{}' is already used, uniqueness violated, "
                   u"value: '{}' see: {}.".format(
                    name, value, self.package.id))
            if RAISE_ON_DUPLICATE_ERROR:
                raise KeyError(msg)
            self.package.parseErrors.append(msg)

        container[name] = value
        return container, name
    start_handlers[(xpdlns10, 'ExtendedAttribute')] = ExtendedAttribute
    start_handlers[(xpdlns21, 'ExtendedAttribute')] = ExtendedAttribute

    def extendedAttribute(self, info):
        container, name = info
        if container[name] is None:
            container[name] = self.text.strip()
    end_handlers[(xpdlns10, 'ExtendedAttribute')] = extendedAttribute
    end_handlers[(xpdlns21, 'ExtendedAttribute')] = extendedAttribute


class Tool(object):
    parameters = ()

    def __init__(self, id):
        self.id = id


class SubFlow(object):
    parameters = ()
    execution = interfaces.SYNCHRONOUS

    def __init__(self, id, execution=None):
        self.id = id
        if execution is not None:
            self.execution = execution


def read(file):
    src = xml.sax.xmlreader.InputSource(getattr(file, 'name', '<string>'))
    src.setByteStream(file)
    parser = xml.sax.make_parser()
    package = Package()
    parser.setContentHandler(XPDLHandler(package))
    parser.setFeature(xml.sax.handler.feature_namespaces, True)
    parser.parse(src)
    return package
