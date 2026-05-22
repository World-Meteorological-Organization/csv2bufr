.. _quickstart:

Quick start
===========

The csv2bufr Python module contains both a command line interface and an API to convert data
stored in a CSV file to the WMO BUFR data format.
For example, the command line interface reads in data from a CSV file, converts it to BUFR and writes out the data to the specified directory. e.g.:

.. code-block:: shell

   csv2bufr data transform <my-csv-file.csv> \
       --bufr-template <csv-to-bufr-mapping.json> \
       --output-dir <output-directory-path>

This command is explained in more detail below.

Command line interface
**********************

The following example transforms the data in file ``my-csv-file.csv`` to BUFR using template ``csv-to-bufr-mapping.json``
and writes the output to directory ``output-directory-path``:

.. code-block:: shell

   csv2bufr data transform <my-csv-file.csv> \
       --bufr-template <csv-to-bufr-mapping.json> \
       --output-dir <output-directory-path>

The command is built on the `Python Click module <https://click.palletsprojects.com/en/8.0.x/>`_ and is formed of
three components (``csv2bufr data transform``), 1 arguments and 2 mandatory options (specified by --).
The argument specifies the file to process of the data being processed.
The options specify various configuration files to use.

#. ``my-csv-file.csv``: argument specifying the CSV data file to process
#. ``--bufr-template csv-to-bufr-mapping.json``: option followed by the bufr mapping template to use
#. ``--output-dir output-directory-path``: option followed by the directory to write BUFR files to. Output filenames are derived from the WIGOS station identifier and observation timestamp, e.g. ``WIGOS_0-20000-0-06700_20220210T060000.bufr4``.

The output BUFR files can be validated using a tool such as the `ECMWF BUFR validator <https://apps.ecmwf.int/codes/bufr/validator/>`_.

Input CSV file
--------------

Currently, a single station per file is supported with each row treated as a separate record and one BUFR file per record created.
The format of the input CSV file has a few requirements:

- A comma (i.e. ``,``) must be used as the delimiter.
- Strings must be quoted.
- Missing values must be encoded as "None".
- The final row in the file must contain data and not be a new line.
- The timestamp of the records must be separated into components, i.e. year, month, day etc must each be in a separate column.
- The date/time elements should be in Universal Time Coordinated (UTC).
- The file must contain the WIGOS station identifier

WIGOS Station Identifier
------------------------

Each station must have a WIGOS Station Identifier. More information can be found in the
`Guide to the WMO Integrated Observing System <https://library.wmo.int/doc_num.php?explnum_id=10962>`_,
section 2 (WMO-No. 1165).

BUFR mapping template (``--bufr-template``)
-------------------------------------------

The mapping from CSV to BUFR is specified in a JSON file (see the :ref:`BUFR template mapping page <mapping>`).

API
***

The command line interface uses the ``transform`` function from the csv2bufr module. This can be used directly, e.g.:

.. code-block:: python

   # import modules
   import json
   from csv2bufr import transform

   # load data from file
   with open("my-csv-file.csv") as fh:
       data = fh.read()

   # load mapping
   with open("csv-to-bufr-mapping.json") as fh:
       mapping = json.load(fh)

   # call transform function
   result = transform(data, mapping)

   # iterate over items
   for item in result:
       # get id and phenomenon time to use in output filename
       wsid = item["_meta"]["properties"]["wigos_station_identifier"]  # WIGOS station ID
       geometry = item["_meta"]["geometry"]  # GeoJSON geometry object
       timestamp = item["_meta"]["properties"]["datetime"]  # phenomenonTime as datetime object
       timestamp = timestamp.strftime("%Y%m%dT%H%MZ")  # convert to string
       # set filename
       output_file = f"{wsid}_{timestamp}.bufr4"
       # save to file
       with open(output_file, "wb") as fh:  # note binary write mode
           fh.write(item["bufr4"])

The ``transform`` function returns an iterator that can be used to iterate over each line in the data file.
Each item returned contains a dictionary with the following elements:

- ``item["bufr4"]`` binary BUFR data
- ``item["_meta"]`` GeoJSON dictionary containing metadata elements
- ``item["_meta"]["id"]`` identifier for result (set combination of ``wigos_station_identifier`` and ``datetime``)
- ``item["_meta"]["geometry"]`` GeoJSON geometry object of location of data
- ``item["_meta"]["properties"]`` key/value pairs of properties/attributes
- ``item["_meta"]["properties"]["md5"]`` the md5 checksum of the encoded BUFR data
- ``item["_meta"]["properties"]["wigos_station_identifier"]`` WIGOS station identifier
- ``item["_meta"]["properties"]["datetime"]`` characteristic date of data contained in result (from BUFR)
- ``item["_meta"]["properties"]["originating_centre"]`` originating centre for data (from BUFR)
- ``item["_meta"]["properties"]["data_category"]`` data category (from BUFR)
- ``item["_meta"]["result"]`` encoding status dictionary
- ``item["_meta"]["result"]["code"]`` 1 if encoding succeeded, 0 if it failed
- ``item["_meta"]["result"]["errors"]`` list of error messages (empty on success)
- ``item["_meta"]["result"]["warnings"]`` list of non-fatal warnings (e.g. values set to missing due to failed validation)
