.. _mapping:

.. role:: redtext

BUFR template mapping
=====================

The mapping between the input CSV data and the output BUFR data is specified in a JSON file.
The csv2bufr module validates the mapping file against the schema shown at the bottom of this page prior to attempting the transformation to BUFR.
The schema version is taken from ``conformsTo``: if several supported versions are listed the highest is used,
and if none is listed the template is validated against ``csv2bufr-template-v3.json``.
The supported versions are ``csv2bufr-template-v2.json``, ``csv2bufr-template-v3.json`` and ``csv2bufr-template-v4.json``.
The schema specifies the following required properties:

- ``conformsTo`` - array (or string) containing the schema version identifier, e.g. ``"csv2bufr-template-v4.json"``
- ``metadata`` - object containing template metadata: ``label``, ``description``, ``version``, ``author``, ``editor``, ``dateCreated``, ``dateModified``, and ``id`` (UUID)
- ``inputDelayedDescriptorReplicationFactor`` - array of integers, values for the delayed descriptor replication factors to use
- ``inputShortDelayedDescriptorReplicationFactor`` - array of integers, values for the short delayed descriptor replication factors to use
- ``inputExtendedDelayedDescriptorReplicationFactor`` - array of integers, values for the extended delayed descriptor replication factors to use
- ``number_header_rows`` - integer, the number of header rows in the file before the first data, including the row with column names
- ``column_names_row`` - integer, the row number that gives the column names
- ``header`` - array of objects (see below), header section containing metadata
- ``data`` - array of objects (see below), section mapping from the CSV columns to the BUFR elements

The following properties are optional:

- ``wigos_station_identifier`` - either a constant WIGOS station identifier (e.g. ``const:0-20000-0-123``) or the column from the CSV file containing the WSI (e.g. ``data:WSI_column``). If omitted, the WSI is constructed from the individual WIGOS component fields (``#1#wigosIdentifierSeries``, ``#1#wigosIssuerOfIdentifier``, ``#1#wigosIssueNumber``, ``#1#wigosLocalIdentifierCharacter``) in the ``data`` section.
- ``delimiter`` - field separator character in the input CSV file; one of ``,`` (default), ``;``, ``|``, or tab
- ``quoting`` - CSV quoting mode; one of ``QUOTE_NONNUMERIC`` (default), ``QUOTE_ALL``, ``QUOTE_MINIMAL``, or ``QUOTE_NONE``
- ``quotechar`` - quote character used in the CSV file; default ``"``
- ``pack_subsets`` (v4) - boolean, default ``false``. Encode the rows of each station in the input file as the subsets of one
  BUFR message, instead of one message per row (see below).
- ``pack_multiple_stations`` (v4) - boolean, default ``false``. With ``pack_subsets``, encode the rows of all the stations in
  one message instead of one message per station.
- ``on_row_error`` (v4) - ``skip`` (default) or ``fail``. When ``pack_subsets`` is ``true``, what to do with a row that cannot be parsed:
  ``skip`` leaves the row out of its message and adds a warning, ``fail`` makes that message fail.

Packing rows as subsets (v4)
----------------------------

With ``"pack_subsets": true`` the whole input file is read first, and the rows of each station (WIGOS station identifier)
are encoded as one BUFR message with one subset per row. The file gives one result per station, in the order the stations
first appear, so the rows can be sorted by station or by date. For example, a file holding a month of daily values for one
station (DAYCLI) gives a single message.

With ``"pack_multiple_stations": true`` as well, all the rows of the file are encoded as one message, whatever the station.

- Each row must have a complete WIGOS station identifier (four non-empty parts) when packing by station. A row without one
  cannot be assigned to a station and is returned as a failed result of its own (``on_row_error`` does not apply).
- The Section 1 header values, including the typical date and time, are taken from the first row of the message.
- ``numberOfSubsets`` and ``compressedData`` are set by csv2bufr (and must not be in a v4 template): the message is
  compressed if it has more than one subset, and uncompressed otherwise.
- The replication factors in the template apply to every subset. Values that are arrays (``array:``) are not supported in the data section.
- Each result describes one message, with the same keys as a result without packing (a single row is a message
  with one subset). For a packed message:

  - ``_meta.id`` is ``WIGOS_<wigos_station_identifier>_<datetime>`` if the message has one station, otherwise ``BUFR_<md5>``;
  - ``_meta.geometry`` is a ``Point`` if all the subsets have the same location, otherwise a ``Polygon`` of the bounding
    box of the subset locations. If the locations cross the antimeridian (their longitude range is shorter through 180°
    than through 0°), the geometry is worked out separately for each side and combined, e.g. as a ``MultiPolygon``
    (as RFC 7946, section 3.1.9);
  - ``_meta.properties.datetime`` is the typical date and time from the Section 1 header;
  - ``_meta.properties.start_datetime`` and ``end_datetime`` are the earliest and latest times of the subsets, from their
    ``#1#year``, ``#1#month``, ``#1#day``, ``#1#hour``, ``#1#minute`` and ``#1#second`` elements. A missing hour, minute or
    second is taken as 0; a subset without a year, month or day (or with an invalid date) is left out.
    If no subset has a time, both are the typical date and time;
  - ``_meta.properties.wigos_station_identifier`` is the WIGOS station identifier if all the subsets are for one station
    (always the case unless ``pack_multiple_stations`` is set), otherwise ``null``;
  - ``_meta.properties.number_of_subsets`` is the number of subsets;
  - ``_meta.properties.geometry_index`` is only present if the message has more than one station. It lists one entry, or
    one for each side of the antimeridian, with its ``polygon``, bounding box ``bbox`` (``[west, south, east, north]``,
    west greater than east across the antimeridian, RFC 7946 section 5.2), ``start_datetime``, ``end_datetime``,
    ``subsets`` and ``wigos_station_identifiers``. The latter lists each station on that side, in the order they first
    appear, with its ``wigos_station_identifier``, ``geometry``, ``bbox``, ``start_datetime``, ``end_datetime`` and
    ``subsets``, e.g. to split the message into one per station. For example:

    .. code-block:: json

       "geometry_index": [
         {"polygon": {"type": "Polygon", "coordinates": [...]},
          "bbox": [10.0, 50.0, 12.0, 52.0],
          "start_datetime": "2021-11-01T00:00:00", "end_datetime": "2021-11-02T00:00:00",
          "subsets": [1, 2, 3],
          "wigos_station_identifiers": [
            {"wigos_station_identifier": "0-1-2-A",
             "geometry": {"type": "Point", "coordinates": [10.0, 50.0]},
             "bbox": [10.0, 50.0, 10.0, 50.0],
             "start_datetime": "2021-11-01T00:00:00", "end_datetime": "2021-11-02T00:00:00",
             "subsets": [1, 3]},
            {"wigos_station_identifier": "0-1-2-B",
             "geometry": {"type": "Point", "coordinates": [12.0, 52.0]},
             "bbox": [12.0, 52.0, 12.0, 52.0],
             "start_datetime": "2021-11-01T00:00:00", "end_datetime": "2021-11-01T00:00:00",
             "subsets": [2]}
          ]}
       ]

    ``subsets`` are the subset numbers in the message, from 1, so the subsets can be extracted with ecCodes, e.g.
    ``extractSubsetList``. (Times are ``datetime`` objects, shown here as strings.)
  - a failed result has the same keys, with ``start_datetime`` and ``end_datetime`` ``null`` and ``number_of_subsets`` 0.
    The ``wigos_station_identifier`` is kept if the rows are for one station;
  - the warnings in ``_meta.result`` start with the line number of the row in the file (e.g. ``row 5: ...``).
- Non-ASCII values are set to missing with a warning and the rest of the row is encoded, as without packing.
- ``pack_subsets`` is only applied to templates that conform to ``csv2bufr-template-v4.json``. For older templates it is ignored with a warning.

Template provenance (v4)
------------------------

A BUFR message, or an error in one, should be traceable to the exact template version that produced it.
Schema v4 adds two optional fields to ``metadata`` for this:

- ``references`` - array of the documents the template has been checked against, each with ``title`` (required), ``edition``, ``section`` and ``url``
- ``history`` - array with one entry per version, oldest first, each with ``version``, ``id``, ``date``, ``editor`` and ``changes`` (all required)
  and optionally ``references`` (array of strings naming the relevant sections)

The ``id`` is unique to the template **and** version: a new id is issued for every version and ids are never reused.

.. code-block:: json

   "metadata": {
       "label": "CLIMAT",
       "version": "1.1",
       "id": "c802d3c6-fc95-443d-96db-41ff373a90b2",
       "references": [
           {"title": "Manual on Codes (WMO-No. 306), Volume I.2",
            "edition": "2023",
            "section": "B/C30 - Regulations for reporting CLIMAT data in TDCF"}
       ],
       "history": [
           {"version": "1.0", "id": "99cad042-a73d-40a9-a646-cf140612394d",
            "date": "2025-07-09", "editor": "...", "changes": "Initial version."},
           {"version": "1.1", "id": "c802d3c6-fc95-443d-96db-41ff373a90b2",
            "date": "2026-10-07", "editor": "...",
            "changes": "Start of month fixed to day 1, 00:00.",
            "references": ["B/C30.1.1", "B/C30.2.1.2"]}
       ]
   }

(Other required ``metadata`` fields are omitted from the example.)

For v4 templates the following are checked, and a template that fails is rejected:

- ``id`` and the history ids are UUIDs, and ``dateCreated``, ``dateModified`` and the history dates are valid dates (``YYYY-MM-DD``).
- The last ``history`` entry has the same ``version`` and ``id`` as ``metadata``.
- The ``history`` ids are unique.

For v2 and v3 templates the formats are not checked, and the two ``history`` checks only log a warning.

Changes from v3:

- ``metadata.references`` and ``metadata.history`` added (optional).
- ``metadata.id`` uses the standard ``uuid`` format (v3 used ``uuid4``, which validators do not recognise) and formats are enforced.
- ``pack_subsets``, ``pack_multiple_stations`` and ``on_row_error`` added (optional).
- ``numberOfSubsets`` and ``compressedData`` must not be set in the ``header``: csv2bufr sets them
  (uncompressed for one subset, compressed for several).

See "Versions and provenance" in the
`csv2bufr-templates contributing guide <https://github.com/World-Meteorological-Organization/csv2bufr-templates/blob/main/docs/source/contributing.rst>`_
for how ids and history are maintained for the published templates.

The header and data sections contain arrays of ``bufr_element`` objects mapping to either the different fields
in the header sections of the BUFR message or to the data section respectively. More information is provided below.
In both cases the field ``eccodes_key`` from the ``bufr_element`` object is used to indicate the BUFR element mapped rather than the 6 digit  BUFR FXXYYY code.
The field ``value`` specifies where the data to encode comes from. This can be one of the following:

- ``data:`` the value is read from the named column in the CSV file (e.g. ``"data:temperature"``)
- ``const:`` a fixed constant value is used (e.g. ``"const:4"``)
- ``array:`` a comma-separated list of values is used as an array (e.g. ``"array:301150,301011,301012"``); used for ``unexpandedDescriptors`` in the header

For example, the code block below shows how the pressure reduced to mean sea level would be mapped from the column "mslp" in the CSV file
to the BUFR element indicated by the eccodes key "pressureReducedToMeanSeaLevel" (FXXYYY = 010051).

.. code-block:: json

   {
       "data":[
           {"eccodes_key": "pressureReducedToMeanSeaLevel", "value": "data:mslp"}
       ]
   }

The code block below gives examples for both constant values and a value read from the data file:

.. code-block:: json

   {
       "header":[
           {"eccodes_key": "dataCategory", "value": "const:0"}
       ],
       "data":[
           {"eccodes_key": "latitude", "value": "const:46.2234923"},
           {"eccodes_key": "longitude", "value": "const:6.1475485"},
           {"eccodes_key": "pressureReducedToMeanSeaLevel", "value": "data:mslp"},
       ]
   }

In this example, the ``dataCategory`` field in BUFR section 1 (see :ref:`bufr4`) is mapped to the constant value 0;
the ``latitude`` and ``longitude`` to the value specified;
and the ``pressureReducedToMeanSeaLevel`` to the data from the "mslp" column in the CSV file.

The keys used for the header elements are listed on the :ref:`bufr4` page, with the mandatory keys highlighted in red.
The list of keys can also be found at:

- `<https://confluence.ecmwf.int/display/ECC/BUFR+headers>`_

Similarly the keys for the different data elements can be found at:

- `<https://confluence.ecmwf.int/display/ECC/WMO%3D37+element+table>`_

input<Short|Extended>DelayedDescriptorReplicationFactor
-------------------------------------------------------
Due to the way that eccodes works any delayed replication factors need to be specified before encoding and included in the mapping file.
This currently limits the use of the delayed replication factors to static values for a given mapping. For example
every data file that uses a given mapping file has the same optional elements present or the same number of levels in an
atmospheric profile present.

For sequences that do not include delayed replications the :redtext:`inputDelayedDescriptorReplicationFactor` etc
must still be included but may be set to an empty array. e.g.

.. code-block:: json

   {
       "inputDelayedDescriptorReplicationFactor": [],
       "inputShortDelayedDescriptorReplicationFactor": [],
       "inputExtendedDelayedDescriptorReplicationFactor": []
   }



bufr_element
------------

Each item in the ``header`` and ``data`` arrays of the mapping template must conform with the definition of the ``bufr_element``
object specified in the schema shown below. This object contains an ``eccodes_key`` field specifying the BUFR element the data
are being mapped to as described above and up to 3 others pieces of information:

- the source of the data (``value``)
- valid range information (``valid_min``, ``valid_max``)
- simple scaling and offset parameters (``scale``, ``offset``)

Only one source can be mapped, if multiple sources are specified the validation of the mapping file by csv2bufr will fail.
As noted at the start of this page, the ``value`` field takes the form ``"<keyword>:<column|value>"``,
where ``<keyword>`` is one of ``data``, ``const``, or ``array`` as described above.

The ``valid_min`` and ``valid_max`` are optional and can be used to perform a basic quality control of numeric fields.
The values to use are specified in the same way as for the ``value`` element, with the values coming from either a
constant value or from the data file.
If these fields are specified the csv2bufr module checks the value extracted from the source to the indicated
valid minimum and maximum values. If outside of the range the value is set to missing. This check is applied before any
scaling of the data.

The ``scale`` and ``offset`` fields are conditionally optional, either both can be omitted or both can included.
Including only one will result in a failed validation of the mapping file. These allow simple unit conversions to be performed,
for example from degrees Celsius to Kelvin or from hectopascals to Pascals.
Again, the values are specified in the same way as for the other fields.
The scaled values are calculated as:

.. math::

   \mbox{scaled\_value} =
       \mbox{value} \times 10^{\mbox{scale}} + \mbox{offset}

The scaled value is then used to set the indicated BUFR element. For example:

.. code-block:: json

   {
       "data":[
           {
               "eccodes_key": "pressureReducedToMeanSeaLevel",
               "value": "data:mslp",
               "scale": "const:2",
               "offset": "const:0"
           }
       ]
   }

Would convert the value contained in the "mslp" column of the CSV file from hPa to Pa by multiplying by 100 and adding 0.

For each of the above elements (``value, valid_min, valid_max, scale, offset``) null values must be excluded from the mapping file.

An individual BUFR descriptor can occur multiple times within a single BUFR message.
To allow the indexing of the descriptors within a particular message, and the inclusions of multiple descriptors or keys with  the same name, eccodes prepends an index number to the eccodes_key.
For the first occurrence the index number can be omitted but for all other cases it should be included.
The index is indicated within the eccodes_key using ``#index#eccodes_key``, an example is given below.

.. code-block:: json

   {
       "data":[
           {
               "eccodes_key": "#1#pressureReducedToMeanSeaLevel",
               "value": "data:mslp",
               "scale": "const:2",
               "offset": "const:0"
           }
       ]
   }

Units
-----

It should be noted that the units of the data to be encoded into BUFR should match those specified in BUFR table B
(e.g. see `<https://confluence.ecmwf.int/display/ECC/WMO%3D37+element+table>`_), i.e.
Kelvin for temperatures, Pascals for pressure etc. Simple conversions between units are possible as specified above using
the ``scale`` and ``offset`` fields. Some additional examples are given below.

.. code-block:: json

   {
       "data":[
           {
               "eccodes_key": "airTemperature",
               "value": "data:AT-fahrenheit",
               "scale": "const:-0.25527",
               "offset": "const:255.37"
           },
           {
               "eccodes_key": "airTemperature",
               "value": "data:AT-celsius",
               "scale": "const:0",
               "offset": "const:273.15"
           },
           {
               "eccodes_key": "pressure",
               "value": "data:pressure-hPa",
               "scale": "const:2",
               "offset": "const:0"
           }
       ]
   }

Schema
------

.. literalinclude:: ../../csv2bufr/templates/resources/schema/csv2bufr-template-v4.json

Built in templates and search path
----------------------------------

Several preconfigured templates are available from the csv2bufr-templates repository:

- https://github.com/World-Meteorological-Organization/csv2bufr-templates

``csv2bufr`` searches for templates in the directory set by the ``CSV2BUFR_TEMPLATES`` environment variable
(or the current working directory if it is not set), then in ``/opt/csv2bufr/templates`` if that directory exists.

Templates are indexed by their ``metadata.id``. Directories are searched in the order above, and the files in each directory
in name order. If two files have the same id, the first found is used and a warning names both files.
A template with an empty id is not indexed.

A template can be requested (e.g. ``--bufr-template`` on the command line) by:

- its id, which returns exactly that version of the template. As each version has its own id, several versions can be installed side by side;
- its file name without the ``.json`` extension. If files with that name are found in more than one directory, the first is used and a warning lists them all;
- the path to the template file.

``csv2bufr mappings list`` shows the indexed templates, including their ``references`` and ``history``.