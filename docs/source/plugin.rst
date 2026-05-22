.. _plugin:

pygeoapi plugin
===============
Overview
********

csv2bufr also provides a custom `pygeoapi <https://pygeoapi.io>`_ processing plugin, providing
csv2bufr functionality via OGC API - Processes.

Installation
************

To integrate this plugin in pygeoapi:

- ensure csv2bufr and its dependencies are installed into the pygeoapi deployment environment
- add the processes to the pygeoapi configuration as follows:

.. code-block:: yaml

    csv2bufr-transform:
        type: process
        processor:
            name: csv2bufr.pygeoapi_plugin.csv2bufrProcessor

- regenerate the pygeoapi OpenAPI configuration

.. code-block:: bash

    pygeoapi openapi generate $PYGEOAPI_CONFIG --output-file $PYGEOAPI_OPENAPI

- restart pygeoapi

Usage
*****

The resulting processes will be available at the following endpoints:

* ``/processes/csv2bufr-transform``

Note that pygeoapi's OpenAPI/Swagger interface (at ``/openapi``) also
provides a developer-friendly interface to test and run requests