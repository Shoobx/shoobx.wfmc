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
"""Integration Components
"""
from zope import component, interface
from shoobx.wfmc import interfaces

interface.moduleProvides(interfaces.IIntegration)


def createParticipant(activity, process, performer):
    participant = component.queryAdapter(
        activity, interfaces.IParticipant,
        process.definition.id + '.' + performer)

    if participant is None:
        participant = component.getAdapter(
            activity, interfaces.IParticipant, '.' + performer)

    return participant


def createWorkItem(participant, process, activity, application):

    workitem = component.queryAdapter(
        participant, interfaces.IWorkItem,
        process.definition.id + '.' + application)
    if workitem is None:
        workitem = component.getAdapter(
            participant, interfaces.IWorkItem, '.' + application)

    return workitem
