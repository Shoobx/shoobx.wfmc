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
"""Attribute-based integration components
"""
from shoobx.wfmc import interfaces, process
from zope import interface


@interface.implementer(interfaces.IIntegration)
class AttributeIntegration:
    """Integration component that uses simple attributes

    Subclasses provide attributes with suffices Participant or Application to
    provide participant and application factories of a given name.
    """

    def createParticipant(self, activity, proc, performer):
        factory = getattr(self, performer + 'Participant')
        return factory(activity, proc)

    def createWorkItem(self, participant, proc, activity, application):
        factory = getattr(self, application + 'WorkItem')
        return factory(participant, proc, activity)

    def createScriptWorkItem(self, proc, activity, code):
        return process.ScriptWorkItem(proc, activity, code)

    def createSubflowWorkItem(self, proc, activity, subflow, execution):
        return process.SubflowWorkItem(proc, activity, subflow, execution)
