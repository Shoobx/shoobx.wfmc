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
import unittest
import zope.event
from zope.component import testing, provideAdapter
from zope.testing import doctest

from shoobx.wfmc import process

def tearDown(test):
    testing.tearDown(test)
    zope.event.subscribers.pop()

def setUp(test):
    testing.setUp(test)
    provideAdapter(process.PythonExpressionEvaluator)

def test_suite():
    return unittest.TestSuite((
            doctest.DocFileSuite(
                'integration.txt', setUp=setUp, tearDown=tearDown),
            ))
