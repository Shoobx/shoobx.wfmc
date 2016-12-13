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
"""Workflow-integration interfaces
"""
__docformat__ = "reStructuredText"

from zope import interface
from zope.interface.common import mapping

SYNCHRONOUS = 'SYNCHR'
ASYNCHRONOUS = 'ASYNCHR'

START_EVENT = "start"
END_EVENT = "end"


class IExtendedAttributesContainer(interface.Interface):
    """Container for extended attributes"""
    attributes = interface.Attribute("Extended attribute dictionary")


class IIntegration(interface.Interface):
    """Integration of a workflow definition with an application environment

    ``IIntegration`` objects provide methods for integrating workflow
    process definition with an application environment.
    """

    def createParticipant(activity, process, performer):
        """Create a participant for an activity

        The process id and especially the performer (id) are used to
        select an appropriate participant type.
        """

    def createWorkItem(participant, process, activity, application):
        """Create a work item for the given participant

        The process id and especially the application (id) are used to
        select an appropriate work-item type.
        """

    def createSubflowWorkItem(process, activity, subflow, execution):
        """Create a subflow work item.

        The subflow id is used to lookup the sub-process to be executed.
        """

    def createScriptWorkItem(process, activity, code):
        """Create a script work item.

        The workitem for the given code of the script is created. The task of
        the integration is to provide the proper execution environment for the
        script.
        """


class IProcessDefinition(IExtendedAttributesContainer):
    """Process definition

    A process definition defines a particular workflow and define the control
    and flow of the work. You can think of them as the workflow blueprint.
    """

    id = interface.Attribute("Process-definition identifier")
    name = interface.Attribute("Process-definition name (as specified in XPDL)")

    __name__ = interface.Attribute("Name")

    description = interface.Attribute("Description")

    integration = interface.Attribute(
        """Environment-integration component

        The integration component is used to hook up a process
        definition with an application environment.

        This is an ``IIntegration``.
        """
        )

    participants = interface.Attribute(
        """Process participants

        This is a mapping from participant id to participant definition
        """
        )

    activities = interface.Attribute(
        """Process activities

        This is a mapping from activity id to activity definition
        """
        )

    applications = interface.Attribute(
        """Process applications

        This is a mapping from application id to application definition
        """
        )

    def defineActivities(**activities):
        """Add activity definitions to the collection of defined activities

        Activity definitions are supplied as keyword arguments.  The
        keywords provide activity identifiers.  The values are
        IActivityDefinition objects.

        """

    def defineTransitions(*transitions):
        """Add transition definitions

        The transitions are ITransition objects.
        """

    def defineParticipants(**participants):
        """Declare participants

        The participants are provided as keyword arguments.
        Participant identifiers are supplied as the keywords and the
        definitions are supplied as values.  The definitions are
        IParticipantDefinition objects.
        """

    def defineApplications(**applications):
        """Declare applications

        The applications are provided as keyword arguments.
        Application identifiers are supplied as the keywords and the
        definitions are supplied as values.  The definitions are
        IApplicationDefinition objects.
        """

    def defineParameters(*parameters):
        """Declate process parameters

        Input parameters are set as workflow-relevant data.  Output
        parameters are passed from workflow-relevant data to the
        processFinished method of process-instances process contexts.

        """


class IProcessDefinitionFactory(interface.Interface):
    """Object to manufacture IProcessDefinition objects by process definition
    name
    """
    def get(name):
        """Return process definition by given name

        Return None if process definition cannot be found by given name
        """


class IActivityDefinition(interface.Interface):
    """Activity definition
    """

    id = interface.Attribute("Activity identifier")

    __name__ = interface.Attribute("Activity Name")

    description = interface.Attribute("Description")

    def addApplication(id, *parameters):
        """Declare that the activity uses the identified application

        The application identifier must match an application declared
        for the process.

        Parameter definitions can be given as positional arguments.
        The parameter definition directions must match those given in
        the application definition.
        """

    def definePerformer(performer):
        """Set the activity performer

        The argument must be the identifier of a participant defined
        for the enclosing process.
        """

    def setAndSplit(setting):
        """Provide an and-split setting

        If the setting is true, then the activity will use an "and" split.
        """

    def setAndJoin(setting):
        """Provide an and-join setting

        If the setting is true, then the activity will use an "and" join.
        """

class ITransitionDefinition(interface.Interface):
    """Transition definition
    """
    id = interface.Attribute("Transition identifier")

    __name__ = interface.Attribute(
        "Transition name, Text used to identify the Transition.")

    description = interface.Attribute("Description")

    from_ = interface.Attribute(
        "Determines the FROM source of a Transition. (Activity Identifier)")

    to = interface.Attribute(
        "Determines the TO target of a Transition (Activity Identifier)")

    condition = interface.Attribute(
        "A Transition condition expression based on relevant data field.")


class IProcess(interface.Interface):
    """Process instance
    """

    definition = interface.Attribute("Process definition")

    workflowRelevantData = interface.Attribute(
        """Workflow-relevant data

        Object with attributes containing data used in conditions and
        to pass data as parameters between applications
        """
        )

    applicationRelevantData = interface.Attribute(
        """Application-relevant data

        Object with attributes containing data used to pass data as
        shared data for applications

        """
        )

    activities = interface.Attribute(
        """Instance of IActivityContainer.

        Provides access to all activities, created for process (both finished
        and active).
        """
        )

    def deadlineTimer(deadline):
        """A function that will time the event of the deadline. it should call
        process.deadlinePassedHandler when the timestamp has passed. This
        function is meant to be over-written in different implementations of
        the engine.
        """

    def deadlineCanceller(deadine):
        """Cancels the deadline timer created by deadlineTimer. This method
        is called on activity.finish calls, as well as activity.revert.
        """

    def start(*arguments):
        """Start the process with the given parameters.
        """

    def abort():
        """Abort the process.

        All current activities should be properly aborted as well.
        """


class IProcessContext(interface.Interface):
    """Object that can receive process results.
    """

    def processFinished(process, *results):
        """Receive notification of process completion, with results
        """


class IActivityContainer(mapping.IMapping):
    """Container for process activities

    A mapping of activity id to activity object. Also provides convenience
    methods to filter activities.
    """

    def getActive():
        """Return list of active (not finished) activities
        """

    def getFinished():
        """Return list of all finished activities
        """



class IActivity(interface.Interface):
    """Activity instance
    """

    id = interface.Attribute(
        """Activity identifier

        This identifier is set by the process instance

        """)

    definition = interface.Attribute("Activity definition")

    active = interface.Attribute(
        "True when activity is active, False when finished")

    def start(transition):
        """Start an activity originating from the given transition.

        If we do not have enough incoming transitions yet (via a parallel
        gateway for example), then wait for more transitions.
        """

    def finish():
        """Finish the activity."""

    def abort():
        """Abort the activity.

        Aborting activities can be used as part of aborting the process or to
        intervene in a process manually, for example to correct a previous
        mistake.

        Contrary to finish(), when aborting an activity no result is
        produced. Also, all workitems are aborted at this time as well.

        Important: Aborting activities can leave your process in a state where
        is cannot properly finish anymore!
        """

    def revert():
        """Revert any effects of the activity.

        This method is used when the process is aborted manually.

        Returns a list of workitems that were aborted.
        """

    def workItemFinished(work_item, *results):
        """Notify the activity that the work item has been completed.
        """


class IApplicationDefinition(interface.Interface):
    """Application definition
    """

    __name__ = interface.Attribute("Name")

    description = interface.Attribute("Description")

    parameters = interface.Attribute(
        "A sequence of parameter definitions")


class IParameterDefinition(interface.Interface):
    """Parameter definition
    """

    name = interface.Attribute("Parameter name")

    input = interface.Attribute("Is this an input parameter?")

    output = interface.Attribute("Is this an output parameter?")


class IPoolDefinition(interface.Interface):
    """Pool definition
    """

    name = interface.Attribute("Pool name")

    process_def = interface.Attribute(
        "Process definition ID, to which the pool belongs")

    lanes = interface.Attribute("Lanes of the pool")


class ILaneDefinition(interface.Interface):
    """Lane definition
    """

    id = interface.Attribute("Lane id")

    name = interface.Attribute("Lane name")

    performers = interface.Attribute("Performers for the lane")


class IParticipantDefinition(interface.Interface):
    """Participant definition
    """


class IParticipant(interface.Interface):
    """Workflow participant
    """

    __name__ = interface.Attribute("Name")

    description = interface.Attribute("Description")


class IDataFieldDefinition(interface.Interface):
    """Participant definition
    """


class IWorkItem(interface.Interface):
    """Work item
    """

    id = interface.Attribute(
        """Item identifier

        This identifier is set by the activity instance

        """)

    def start(arguments):
        """Start the work.
        """


class IAbortWorkItem(IWorkItem):
    """A work item that can be aborted."""

    def abort():
        """Abort the work.
        """


class IRevertableWorkItem(IWorkItem):
    """A work item whose work can be reverted."""

    def revert():
        """Undo the work done by the workitem.
        """


class InvalidProcessDefinition(Exception):
    """A process definition isn't valid in some way.
    """


class ProcessError(Exception):
    """An error occurred in execution of a process.
    """


class IProcessStarted(interface.Interface):
    """A process has begun executing.
    """

    process = interface.Attribute("The process")


class IProcessFinished(interface.Interface):
    """A process has finished executing.
    """

    process = interface.Attribute("The process")


class IProcessAborted(interface.Interface):
    """A process has been aborted.
    """

    process = interface.Attribute("The process")


class IPythonExpressionEvaluator(interface.Interface):
    """Python Expression Evaluator

    A component that evaluates Python expressions in the context of a
    process.

    It is the responsibility of this component to create the necessary
    namespace. At least the attributes of the workflow-relevant data must be
    made available.
    """

    def evaluate(expr, locals):
        """Evaluate the python expression.

        `locals` is a mapping containing additional namesapce attributes.

        Returns the result of the expression.
        """
