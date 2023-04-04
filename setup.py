##############################################################################
#
# Copyright (c) 2007 Zope Corporation and Contributors.
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
"""Setup for shoobx.wfmc package
"""
import os
from setuptools import setup, find_packages

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(name='shoobx.wfmc',
      version='4.3.1',
      author='Zope Corporation and Contributors',
      author_email='zope3-dev@zope.org',
      description="Workflow-Management Coalition Workflow Engine",
      long_description=(
          read('README.rst')
          + '\n\n' +
          'Detailed Documentation\n' +
          '++++++++++++++++++++++\n\n'
          + '\n\n' +
          read('src', 'shoobx', 'wfmc', 'README.txt')
          + '\n\n' +
          read('src', 'shoobx', 'wfmc', 'xpdl.txt')
          + '\n\n' +
          read('CHANGES.rst')
          ),
      keywords = "bpmn wfmc xpdl workflow engine",
      classifiers = [
          'Development Status :: 5 - Production/Stable',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: Zope Public License',
          'Programming Language :: Python',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.7',
          'Programming Language :: Python :: 3.8',
          'Programming Language :: Python :: 3.9',
          'Programming Language :: Python :: 3.10',
          'Programming Language :: Python :: 3.11',
          'Programming Language :: Python :: Implementation :: CPython',
          'Natural Language :: English',
          'Operating System :: OS Independent'],
      url='http://pypi.python.org/pypi/shoobx.wfmc',
      license='ZPL 2.1',
      packages=find_packages('src'),
      package_dir = {'': 'src'},
      namespace_packages=['shoobx'],
      extras_require = dict(
          test=[
            'coverage',
            'zope.testing',
            'zope.testrunner',
            ]),
      install_requires=['setuptools',
                        'zope.component',
                        'persistent',
                        'zope.cachedescriptors'],
      include_package_data = True,
      zip_safe = False,
      )
