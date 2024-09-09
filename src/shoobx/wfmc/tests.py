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
"""Test hookup
"""
from __future__ import print_function
import doctest
import os
import unittest
import zope.event
import zope.interface

from zope.component import testing, provideAdapter
from shoobx.wfmc import interfaces, process


def tearDown(test):
    testing.tearDown(test)
    if zope.event.subscribers:
        zope.event.subscribers.pop()


def setUp(test):
    test.globs['this_directory'] = os.path.dirname(__file__)
    testing.setUp(test)
    provideAdapter(process.PythonExpressionEvaluator)


@zope.interface.implementer(
    interfaces.IAbortWorkItem, interfaces.IRevertableWorkItem)
class WorkItemStub(object):

    def __init__(self, participant, process, activity):
        self.participant = participant
        self.process = process
        self.activity = activity

    def start(self, args):
        self.args = args
        print('Workitem %i for activity %r started.' % (
            self.id, self.activity.definition.id))

    def abort(self):
        print('Workitem %i for activity %r aborted.' % (
            self.id, self.activity.definition.id))

    def revert(self):
        print('Workitem %i for activity %r reverted.' % (
            self.id, self.activity.definition.id))


def test_multiple_input_parameters():
    """
    We'll create a very simple process that inputs two variables and
    has a single activity that just outputs them.

    >>> from shoobx.wfmc import process
    >>> pd = process.ProcessDefinition('sample')
    >>> from zope import component, interface

    >>> pdfactory = process.StaticProcessDefinitionFactory()
    >>> zope.component.provideUtility(pdfactory)
    >>> pdfactory.register(pd)

    >>> pd.defineParameters(
    ...     process.InputParameter('x'),
    ...     process.InputParameter('y'),
    ...     )

    >>> pd.defineActivities(
    ...    eek = process.ActivityDefinition(),
    ...    ook = process.ActivityDefinition(),
    ...    )

    >>> pd.defineTransitions(process.TransitionDefinition('eek', 'ook'))

    >>> pd.defineApplications(
    ...     eek = process.Application(
    ...         process.InputParameter('x'),
    ...         process.InputParameter('y'),
    ...         )
    ...     )

    >>> pd.activities['eek'].addApplication('eek', ['x', 'y'])

    >>> from shoobx.wfmc import interfaces

    >>> @zope.interface.implementer(interfaces.IParticipant)
    ... class Participant(object):
    ...     zope.component.adapts(interfaces.IActivity)
    ...
    ...     def __init__(self, activity, process):
    ...         self.activity = activity

    >>> from shoobx.wfmc.attributeintegration import AttributeIntegration
    >>> integration = AttributeIntegration()
    >>> pd.integration = integration

    >>> integration.Participant = Participant


    >>> @interface.implementer(interfaces.IWorkItem)
    ... class Eek:
    ...     component.adapts(interfaces.IParticipant)
    ...
    ...     def __init__(self, participant, process, activity):
    ...         self.participant = participant
    ...
    ...     def start(self, args):
    ...         x = args['x']; y=args['y']
    ...         print(x, y)


    >>> integration.eekWorkItem = Eek

    >>> proc = pd()
    >>> proc.start(99, 42)
    99 42
    """

def test_literal_input_parameters():
    """
    We'll create a very simple process that inputs two variables and
    has a single activity that just outputs them.

    The first variable will be a normal Input variable, the second
    will be a literal input variable

    The first variable will return the actual value, the second
    will be the literal value "y", representing the expression definition

    >>> from shoobx.wfmc import process
    >>> pd = process.ProcessDefinition('sample')
    >>> from zope import component, interface

    >>> pdfactory = process.StaticProcessDefinitionFactory()
    >>> zope.component.provideUtility(pdfactory)
    >>> pdfactory.register(pd)

    >>> pd.defineParameters(
    ...     process.InputParameter('x'),
    ...     process.LiteralInputParameter('y'),
    ...     )

    >>> pd.defineActivities(
    ...    eek = process.ActivityDefinition(),
    ...    ook = process.ActivityDefinition(),
    ...    )

    >>> pd.defineTransitions(process.TransitionDefinition('eek', 'ook'))

    >>> pd.defineApplications(
    ...     eek = process.Application(
    ...         process.InputParameter('x'),
    ...         process.LiteralInputParameter('y'),
    ...         )
    ...     )

    >>> pd.activities['eek'].addApplication('eek', ['x', 'y'])

    >>> from shoobx.wfmc import interfaces

    >>> @zope.interface.implementer(interfaces.IParticipant)
    ... class Participant(object):
    ...     zope.component.adapts(interfaces.IActivity)
    ...
    ...     def __init__(self, activity, process):
    ...         self.activity = activity

    >>> from shoobx.wfmc.attributeintegration import AttributeIntegration
    >>> integration = AttributeIntegration()
    >>> pd.integration = integration

    >>> integration.Participant = Participant


    >>> @interface.implementer(interfaces.IWorkItem)
    ... class Eek:
    ...     component.adapts(interfaces.IParticipant)
    ...
    ...     def __init__(self, participant, process, activity):
    ...         self.participant = participant
    ...
    ...     def start(self, args):
    ...         x = args['x']; y=args['y']
    ...         print(x, y)


    >>> integration.eekWorkItem = Eek

    >>> proc = pd()
    >>> proc.start(99, 42)
    99 y
    """

def test_pickling():
    """
    >>> from shoobx.wfmc import process
    >>> pd = process.ProcessDefinition('sample')
    >>> from zope import component, interface

    >>> pdfactory = process.StaticProcessDefinitionFactory()
    >>> zope.component.provideUtility(pdfactory)
    >>> pdfactory.register(pd)

    >>> pd.defineActivities(
    ...    eek = process.ActivityDefinition(),
    ...    ook = process.ActivityDefinition(),
    ...    )

    >>> pd.defineTransitions(process.TransitionDefinition('eek', 'ook'))

    >>> pd.defineApplications(
    ...     eek = process.Application(
    ...         process.InputParameter('x'),
    ...         process.InputParameter('y'),
    ...         )
    ...     )

    >>> pd.activities['eek'].addApplication('eek', ['x', 'y'])


    >>> proc = pd()

    >>> import pickle
    >>> s = pickle.dumps(proc)
    """

def test_inputoutput():
    """

    >>> from shoobx.wfmc import process
    >>> pd = process.ProcessDefinition('sample')
    >>> from zope import component, interface

    >>> pdfactory = process.StaticProcessDefinitionFactory()
    >>> zope.component.provideUtility(pdfactory)
    >>> pdfactory.register(pd)

    >>> pd.defineParameters(
    ...     process.InputParameter('x'),
    ...     )

    >>> pd.defineActivities(
    ...    eek = process.ActivityDefinition(),
    ...    ook = process.ActivityDefinition(),
    ...    )

    >>> pd.defineTransitions(process.TransitionDefinition('eek', 'ook'))

    >>> pd.defineApplications(
    ...     eek = process.Application(
    ...         process.InputOutputParameter('x'),
    ...         )
    ...     )

    >>> pd.activities['eek'].addApplication('eek', ['x'])

    >>> class Participant(object):
    ...     def __init__(self, activity, process):
    ...         self.activity = activity

    >>> from shoobx.wfmc.attributeintegration import AttributeIntegration
    >>> integration = AttributeIntegration()
    >>> pd.integration = integration

    >>> integration.Participant = Participant

    >>> class Eek:
    ...     def __init__(self, participant, process, activity):
    ...         self.participant = participant
    ...
    ...     def start(self, args):
    ...         x = args['x']
    ...         self.participant.activity.workItemFinished(self, {'x': x+1 })


    >>> integration.eekWorkItem = Eek

    >>> proc = pd()
    >>> proc.start(1)
    >>> proc.workflowRelevantData.x
    2
    """

def test_wrong_number_process_args_error_message():
    """

    >>> from shoobx.wfmc import process
    >>> pd = process.ProcessDefinition('sample')
    >>> from zope import component, interface

    >>> pdfactory = process.StaticProcessDefinitionFactory()
    >>> zope.component.provideUtility(pdfactory)
    >>> pdfactory.register(pd)

    >>> pd.defineActivities(
    ...    eek = process.ActivityDefinition(),
    ...    ook = process.ActivityDefinition(),
    ...    )
    >>> pd.defineTransitions(process.TransitionDefinition('eek', 'ook'))

    >>> proc = pd()
    >>> proc.start(1)
    Traceback (most recent call last):
    ...
    TypeError: Too many arguments. Expected 0. got 1
    """

def test_process_abort():
    """
    >>> from shoobx.wfmc import process
    >>> pd = process.ProcessDefinition('sample')
    >>> from zope import component, interface

    >>> pdfactory = process.StaticProcessDefinitionFactory()
    >>> zope.component.provideUtility(pdfactory)
    >>> pdfactory.register(pd)

    >>> pd.defineActivities(
    ...    eek = process.ActivityDefinition(),
    ...    ook = process.ActivityDefinition(),
    ...    )

    >>> pd.defineTransitions(process.TransitionDefinition('eek', 'ook'))

    >>> pd.defineApplications(
    ...     eek = process.Application(
    ...         process.InputParameter('x'),
    ...         process.InputParameter('y'),
    ...         ),
    ...     ook = process.Application()
    ...     )

    >>> pd.activities['eek'].addApplication('eek', ['x', 'y'])
    >>> pd.activities['ook'].addApplication('ook')

    >>> from shoobx.wfmc.attributeintegration import AttributeIntegration
    >>> integration = AttributeIntegration()
    >>> integration.eekWorkItem = WorkItemStub
    >>> integration.ookWorkItem = WorkItemStub
    >>> integration.Participant = process.Participant
    >>> pd.integration = integration

    >>> proc = pd()
    >>> proc.workflowRelevantData.x = 1
    >>> proc.workflowRelevantData.y = 2

    >>> proc.start()
    Workitem 1 for activity 'eek' started.

    >>> proc.activities[1].workItemFinished(proc.activities[1].workitems[1][0])
    Workitem 1 for activity 'ook' started.

    >>> proc.abort()
    Workitem 1 for activity 'ook' aborted.
    Workitem 1 for activity 'eek' reverted.
    """


def test_getValidOutgoingTransitions():
    """

    >>> from shoobx.wfmc import process
    >>> pd = process.ProcessDefinition('sample')
    >>> from zope import component, interface

    >>> pdfactory = process.StaticProcessDefinitionFactory()
    >>> zope.component.provideUtility(pdfactory)
    >>> pdfactory.register(pd)

    >>> pd.defineActivities(
    ...    eek = process.ActivityDefinition(),
    ...    ook = process.ActivityDefinition(),
    ...    )
    >>> pd.defineTransitions(process.TransitionDefinition('eek', 'ook'))

    >>> proc = pd()
    >>> process.getValidOutgoingTransitions(proc, pd.activities['eek'])
    [TransitionDefinition(from='eek', to='ook')]
    """


def test_getValidOutgoingTransitions_custom_checker():
    """

    >>> from shoobx.wfmc import process
    >>> pd = process.ProcessDefinition('sample')
    >>> from zope import component, interface

    >>> pdfactory = process.StaticProcessDefinitionFactory()
    >>> zope.component.provideUtility(pdfactory)
    >>> pdfactory.register(pd)

    >>> pd.defineActivities(
    ...    eek = process.ActivityDefinition(),
    ...    ook = process.ActivityDefinition(),
    ...    )
    >>> def raiseCondition(data):
    ...     raise Exception()
    >>> pd.defineTransitions(process.TransitionDefinition('eek', 'ook',
    ...                      condition=raiseCondition))
    >>> proc = pd()
    >>> process.getValidOutgoingTransitions(proc, pd.activities['eek'])
    Traceback (most recent call last):
      ...
        raise Exception()
    Exception

    >>> def swallowExceptionsChecker(transition):
    ...     try:
    ...         transition.condition(proc)
    ...     except:
    ...         return [transition]
    ...     return []
    ...

    >>> process.getValidOutgoingTransitions(
    ...     proc, pd.activities['eek'], checker=swallowExceptionsChecker)
    [TransitionDefinition(from='eek', to='ook')]

    """


def test_evaluateInputs():
    """

    >>> from shoobx.wfmc import process
    >>> from shoobx.wfmc import interfaces
    >>> from zope.component import provideAdapter

    >>> provideAdapter(process.PythonExpressionEvaluator)
    >>> pd = process.ProcessDefinition('sample')
    >>> proc = process.Process(pd, None)
    >>> evaluator = interfaces.IPythonExpressionEvaluator(proc)
    >>> inp1 = process.InputParameter('p1')
    >>> inp2 = process.InputParameter('p2')
    >>> formal = (inp1, inp2)
    >>> actual = ('unknown', 'True')

    # Use strict=False to allow including valid inputs.
    >>> process.evaluateInputs(
    ...     proc,
    ...     formal,
    ...     actual,
    ...     evaluator,
    ...     strict=False,
    ... )
    [('p2', True)]

    # Use strict=True to not allow any inputs if any fails.
    >>> process.evaluateInputs(
    ...     proc,
    ...     formal,
    ...     actual,
    ...     evaluator,
    ...     strict=True,
    ... )
    Traceback (most recent call last):
    ...
    shoobx.wfmc.interfaces.EvaluateException: unknown
    """


def test_getInitialDataFieldsValues():
    """

    >>> from shoobx.wfmc import process
    >>> from shoobx.wfmc import interfaces
    >>> from zope.component import provideAdapter

    >>> provideAdapter(process.PythonExpressionEvaluator)
    >>> pd = process.ProcessDefinition('sample')
    >>> proc = process.Process(pd, None)
    >>> evaluator = interfaces.IPythonExpressionEvaluator(proc)
    >>> p1 = process.InputParameter('p1')
    >>> p2 = process.InputParameter('p2')
    >>> p3 = process.InputParameter('p3')
    >>> p2.initialValue = "10"
    >>> p3.initialValue = "True"
    >>> datafields = {'p1': p1, 'p2': p2, 'p3': p3}
    >>> vals = process.getInitialDataFieldsValues(datafields, evaluator)
    >>> vals['p1']  # None

    >>> vals['p2']
    10
    >>> vals['p3']
    True
    """


def test_suite():
    suite = unittest.TestSuite()
    for doctestfile in ['README.txt', 'xpdl.txt',
                        'xpdl-2.1.txt', 'subflow.txt',
                        'deadline.txt']:
        suite.addTest(doctest.DocFileSuite(
            doctestfile,
            setUp=setUp, tearDown=tearDown,
            optionflags=doctest.NORMALIZE_WHITESPACE | doctest.REPORT_NDIFF))
    suite.addTest(doctest.DocTestSuite(
        setUp=setUp, tearDown=testing.tearDown))
    return suite
