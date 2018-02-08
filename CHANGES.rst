=======
CHANGES
=======

4.1.1 (2018-02-08)
------------------

- More Python 3 compatibility.


4.1.0 (2018-02-06)
------------------

- Python 3 support.


4.0.4 (2017-11-01)
------------------

- Make the `now` function pluggable.


4.0.3 (2017-06-20)
------------------

- Nothing changed yet.


4.0.2 (2017-05-25)
------------------

- Update and improve Trove classifiers.


4.0.1 (2017-05-25)
------------------

- Fix small ReST issues, so that PyPI description will render.


4.0.0 (2017-05-25)
------------------

- Renamed from `zope.wfmc` to `shoobx.wfmc`.

- Added support for community CI and coverage tools.

- Raise an exception on duplicate `ExtendedAttribute` `Name` in a single
  `ExtendedAttributes` container

- Use IProcessDefinitionFactory to retrieve process definitions instead of
  named utilities. This additional layer of indirection allows to generate
  definitions dynamically.

- Support for synchronious and asynchronous execution of WFMC subflows.
  Subflows are executed   as part of main process, however have their separate
  state (workflow variables).

- The simplistic Python ``evaluate(expr, locals)`` function has been replaced
  by the `PythonExpressionEvaluator` component, which is an adapter from
  `IProcess` to `IPythonExpressionEvaluator`. The evaluation locals namespace
  is automatically filled with workflow- and application-relevant data
  attributes, the context of the process and the passed in locals variable.

  All calls of `evaluate()` have been updated to use the adapter.

  This change allows for easy replacement of the evaluation engine to hook up
  a safe Python engine (i.e. RestrictedPython) and to provide more namespace
  entries.

- Transition conditions can now be evaluated in the larger context of a
  process, instead of just the workflow-relevant data. Thus their calling
  signature changed from `condition(data)` to `condition(process, data)`.

- `TextCondition` has been changed to use the `PythonExpressionEvaluator`
  component. Also, the compile optimization has been removed, since the
  expression evalautor can do this more effectively.

- Support for aborting processes and activities.

  * Work items can be abortable by implementing ``IAbortWorkItem``.

  * Work items can be cleaned up, if they implement ``ICleanupWorkItem``.

  * Activities keep track of finished work items.

  * Activities can clean themselves up by cleaning up work items.

  * Processes keep track of finished activities.

  * When processes are aborted, the following is done:

    + All activities are aborted.

    + All finished activities are cleaned up.

	+ isAborted flag is set on a process.

- Support for reading XPDL-2.1 added

- Added reading Pools and Lanes from XPDL


3.5.0 (2009-07-24)
------------------

- Update tests to latest package versions.


3.4.0 (2007-11-02)
------------------

- Initial release independent of the main Zope tree.
