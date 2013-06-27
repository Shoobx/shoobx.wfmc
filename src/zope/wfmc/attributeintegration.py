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


$Id$
"""

from zope.wfmc import interfaces
from zope import interface


class AttributeIntegration:
    """Integration component that uses simple attributes

    Subclasses provide attributes with suffices Participant or Application to
    provide participant and application factories of a given name.
    """

    interface.implements(interfaces.IIntegration)

    def createParticipant(self, activity, process, performer):
        factory = getattr(self, performer + 'Participant')
        return factory(activity, process)

    def createWorkItem(self, participant, process, activity, application):
        factory = getattr(self, application + 'WorkItem')
        return factory(participant, process, activity)
