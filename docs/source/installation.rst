.. _installation:

Installation
============
Dependencies
************

The csv2bufr module relies on the `ecCodes <https://confluence.ecmwf.int/display/ECC>`_ software library to perform
the BUFR encoding. This needs to be installed prior to installing any of the Python packages, instructions can
be found on the ecCodes documentation pages: `https://confluence.ecmwf.int/display/ECC <https://confluence.ecmwf.int/display/ECC>`_.

The following Python packages are required by the csv2bufr module:

* `eccodes <https://pypi.org/project/eccodes/>`__ (NOTE: this is separate from the ecCodes library)
* `jsonschema <https://pypi.org/project/jsonschema/>`_

Additionally, the command line interface to csv2bufr requires:

* `click <https://pypi.org/project/click/>`_

These are installed automatically when installing csv2bufr via pip.

Installation
************

PyPI (recommended)
------------------

The simplest way to install csv2bufr is from `PyPI <https://pypi.org/project/csv2bufr/>`_:

.. code-block:: bash

   pip install csv2bufr

This will automatically install all required Python dependencies. The ecCodes software library
must be installed separately beforehand (see Dependencies above).

Docker
------

A Docker image is available that bundles the ecCodes library, all Python dependencies and
csv2bufr itself:

.. code-block:: shell

   docker pull wmoim/csv2bufr

See the `Docker Hub page <https://hub.docker.com/r/wmoim/csv2bufr>`_ for further details.

Source (development)
--------------------

To install directly from source (e.g. to contribute or test unreleased changes), clone the
repository and install with pip:

.. code-block:: bash

   git clone https://github.com/World-Meteorological-Organization/csv2bufr.git
   cd csv2bufr
   pip install .

Released source archives are also available from the
`GitHub releases page <https://github.com/World-Meteorological-Organization/csv2bufr/releases>`_.

To verify the installation:

.. code-block:: bash

   csv2bufr --help

The following output should be shown:

.. code-block:: bash

   Usage: csv2bufr [OPTIONS] COMMAND [ARGS]...

     csv2bufr

   Options:
     --version  Show the version and exit.
     --help     Show this message and exit.

   Commands:
     data      data workflows
     mappings  stored mappings

Environment variables
*********************
Three environment variables are defined and can be used to set the originating centre and
sub centre of the generated BUFR files and the system search path used to find BUFR mapping templates(see
:ref:`BUFR template page <mapping>`)

- ``BUFR_ORIGINATING_CENTRE``: Specifies the originating centre of the BUFR data, Common Code Table C-11, defaults to BUFR missing value.
- ``BUFR_ORIGINATING_SUBCENTRE``: Specifies the originating sub centre of the BUFR data, Common Code Table C-12, defaults to BUFR missing value.
- ``BUFR_TABLE_VERSION``: Default BUFR table version number to use if not specified in mapping template, defaults to 41.
- ``CSV2BUFR_MISSING_VALUE``: Value used to indicate missing value in csv input file if not in ("NA", "NaN", "NAN", "None", "", None).
- ``CSV2BUFR_NULLIFY_INVALID``: True|False. If True invalid values are set to missing (with warning), otherwise error raised. Defaults to True if not set.
- ``CSV2BUFR_TEMPLATES``: Path to search for BUFR templates, defaults to current directory ("./"). Paths are searched in order of ``CSV2BUFR_TEMPLATES`` and then ``/opt/csv2bufr/templates`` (if exists).

Note: the ``BUFR_ORIGINATING_CENTRE`` and ``BUFR_ORIGINATING_SUBCENTRE`` are only used if missing from the
specified :ref:`mapping file <mapping>`.