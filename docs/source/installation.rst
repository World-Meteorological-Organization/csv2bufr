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

Additionally, the command line interface to csv2bufr requires:

* `click <https://pypi.org/project/click/>`_

All the above packages can be installed by running:

.. code-block:: bash

   pip install -r requirements.txt

Installation
************

Docker
------
The quickest way to install and run the software is via a Docker image containing all the required
libraries and Python modules:

.. code-block:: shell

   docker pull wmoim/csv2bufr

This installs a `Docker image <https://hub.docker.com/r/wmoim/csv2bufr>`_ based on Ubuntu and includes the ecCodes software library, dependencies noted above
and the csv2bufr module (including the command line interface).

Source
------

Alternatively, csv2bufr can be installed from source. First clone the repository and navigate to the cloned folder / directory:

.. code-block:: bash

   git clone https://github.com/World-Meteorological-Organization/csv2bufr.git -b dev
   cd csv2bufr

If running in a Docker environment, build the Docker image and run the container:

.. code-block:: bash

   docker build -t csv2bufr .
   docker run -it -v ${pwd}:/app csv2bufr
   cd /app

The above step can be skipped if not using Docker. Now install the module and test:

.. code-block:: bash

   python3 setup.py install
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