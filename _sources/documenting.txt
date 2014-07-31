How to generate this documentation
==================================

There are two useful commands to generate this documentation:

Updating the in-code documentation
----------------------------------

After modifying the current in-code documentation, it is necessary to update the
generated documentation::

    $ sphinx-apidoc repoman -o doc/source -f


This command will parse the source code and generate a ``.rst`` file with all
the documentation inside it. This will prepare it for the next step.

Please, **avoid adding these files to the repository**. Unfortunately, they
should be placed among the other documentation files.

Notice you only need to execute this once after modifying the source code.


Generate the final HTML
-----------------------

In order to generate the final documentation, you can trust on ``setuptools``::

    $ python setup.py build_sphinx

This command will leave the documentation at doc/build/html directory.

This command should be executed after updating the in-code documentation
or whenever you modify any other ``.rst`` file.


About the documentation style
-----------------------------

Documentation configures `Sphinx <http://http://sphinx-doc.org/>`_ to use the
*bootstrap* theme, but it requires the ``pip`` package
**sphinx-bootstrap-theme**. If it is not found, it will use a default theme
("nature", maybe).
