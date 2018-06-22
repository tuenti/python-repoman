Repoman
=======

Repoman is a python library designed to automate repository operations
in release processes.

It provides a unified API to work with different SCMs, and the
mechanisms to quickly have ready and clean working copies. It currently
supports git and mercurial.

There are some basic concepts that are needed to start working with
Repoman:

-  A ``Repository`` is an instance with the usual operations of a SCM.
-  A ``Depot`` contains a repository, and the operations to interact
   with Repoman managers.
-  A ``DepotManager`` provides ``Depots`` with an specific code, each
   ``DepotManager`` is intended to manage ``Depots`` of the same
   project.
-  Each ``Depot`` is locked to the task that requests it to the manager
   and belongs to this task till it's freed.

But the best way to see how it works is with an example:

.. code:: python

    from repoman import depot_manager

    repo_kind = 'git'
    repo_url = 'https://github.com/tuenti/python-repoman.git'

    manager = depot_manager.DepotManager(repo_kind=repo_kind)

    depot = manager.give_me_depot('task_id', 'Owner task name')

    try:
        depot.request_refresh({ repo_url: ['master'] })

        # Do work...
        depot.repository.tag('example')
        # ...

        # If you were going to continue the task in other process,
        # it needs to receive the path of the depot to request it
        depot = manager.give_me_depot_from_path(depot.path)
        assert 'example' in depot.repository.tags()

    finally:
        # And when the repository is not needed anymore, free its depot
        manager.free_depot(depot, 'task_id')

You can know more by looking to the examples in the ``doc/examples``
directory, and to the full `API reference`_.

==============  ===============  =========  ============
VERSION         DOWNLOADS        TESTS      COVERAGE
==============  ===============  =========  ============
|pip version|   |pip downloads|  |travis|   |coveralls|
==============  ===============  =========  ============


Installation
------------

Repoman is intended to be used as part of a more complex release
automation infrastructure, it requires a quite specific set of
dependencies, see ``Requirements`` section to know more about this.

To install it in your development environment, you can use pip:

::

    pip install -e git+https://github.com/tuenti/python-repoman.git@v0.6#egg=repoman

To install it in your production environment, it's recommended to
generate your own packages, usual tools can be used for that, e.g:

::

    python setup.py bdist_egg

Requirements
------------

Repoman should play well with any Linux distribution with Python >= 3.4,
it's daily used in Debian, and has been also tested in Ubuntu and
Fedora.

As a general rule, ``pip install -r requirements.txt`` is able to
install everything, but some things need to be taken into account.

``mercurial`` > 2.1 is also required, as well as ``python-hglib``, the
version specified in the ``requirements.txt`` file should be fine.

Some Dockerfiles are provided in the ``docker`` directory that can serve
as examples about how to prepare an environment to work with repoman in
different distributions.

Credits & Contact
-----------------

Repoman was created by `Tuenti Technologies S.L.`_. You can follow
Tuenti engineering team on Twitter `@tuentieng`_.

License
-------

Repoman is available under the Apache License, Version 2.0. See LICENSE
file for more info.

.. |travis| image:: https://travis-ci.org/tuenti/python-repoman.png?branch=master
  :target: `Travis`_
  :alt: Travis results

.. |coveralls| image:: https://coveralls.io/repos/tuenti/python-repoman/badge.png
  :target: `Coveralls`_
  :alt: Coveralls results_

.. |pip version| image:: https://pypip.in/v/repoman-scm/badge.png
    :target: https://pypi.python.org/pypi/repoman-scm
    :alt: Latest PyPI version

.. |pip downloads| image:: https://pypip.in/d/repoman-scm/badge.png
    :target: https://pypi.python.org/pypi/repoman-scm
    :alt: Number of PyPI downloads


.. _`API reference`: http://tuenti.github.io/python-repoman
.. _Travis: https://travis-ci.org/tuenti/python-repoman
.. _Coveralls: https://coveralls.io/r/tuenti/python-repoman
.. _`@tuentieng`: http://twitter.com/tuentieng
.. _`Tuenti Technologies S.L.`: http://github.com/tuenti
