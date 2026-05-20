###############################################################################
#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#
###############################################################################
import logging
from pygeoapi.process.base import BaseProcessor

from csv2bufr import transform

LOGGER = logging.getLogger(__name__)

PROCESS_METADATA = {
    "version": "0.1.0",
    "id": "csv2bufr-transform",
    "title": {"en": "csv2bufr"},
    "description": {"en": "Process to convert CSV data to BUFR"},  # noqa
    "keywords": [],
    "links": [{
        "type": "text/html",
        "rel": "about",
        "title": "information",
        "href": "https://example.org/process",
        "hreflang": "en-US",
    }],
    'jobControlOptions': ['sync-execute', 'async-execute'],
    "inputs": {
        "data": {
            "title": "CSV Data",
            "description": "Input CSV file contents as string.",  # noqa
            "minOccurs": 1,
            "maxOccurs": 1,
            "metadata": None,
            "keywords": [],
        },
        "mapping": {
            "title": "BUFR Mapping",
            "description": "JSON file describing BUFR mapping.",  # noqa
            "schema": {"type": "string"},
            "minOccurs": 1,
            "maxOccurs": 1,
            "metadata": None,
            "keywords": [],
        },
    },
    "outputs": {
        "messages": {
            "title": "BUFR encoded data in base64",  # noqa
            "schema": {"type": "array"},
            "description": "One result per line in input data"  # noqa
        }
    },
    "example": {
        "inputs": {
            "data":"wsi,year,month,day,hour,minute,latitude,longitude,slp,mslp,ppp,a,brmh\\\n0-20000-0-06700,2022,2,10,6,0,46.2475,6.12774,978.3,1029.9,-0.4,8,412.3",  # noqa
            "mapping": '''{
                "inputDelayedDescriptorReplicationFactor": [],
                "inputShortDelayedDescriptorReplicationFactor": [],
                "inputExtendedDelayedDescriptorReplicationFactor": [],
                "wigos_station_identifier": "data:wsi",
                "number_header_rows": 1,
                "column_names_row": 1,
                "QUOTING": "QUOTE_NONE"
                "header": [
                    {"eccodes_key": "edition", "value": "const:4"},
                    {"eccodes_key": "masterTableNumber", "value": "const:0"},
                    {"eccodes_key": "updateSequenceNumber", "value": "const:0"},
                    {"eccodes_key": "dataCategory", "value": "const:0"},
                    {"eccodes_key": "internationalDataSubCategory", "value": "const:6"},
                    {"eccodes_key": "masterTablesVersionNumber", "value": "const:36"},
                    {"eccodes_key": "typicalYear", "value": "data:year"},
                    {"eccodes_key": "typicalMonth", "value": "data:month"},
                    {"eccodes_key": "typicalDay", "value": "data:day"},
                    {"eccodes_key": "typicalHour", "value": "data:hour"},
                    {"eccodes_key": "typicalMinute", "value": "data:minute"},
                    {"eccodes_key": "numberOfSubsets", "value": "const:1"},
                    {"eccodes_key": "observedData", "value": "const:1"},
                    {"eccodes_key": "compressedData", "value": "const:0"},
                    {"eccodes_key": "unexpandedDescriptors", "value": "array: 301150, 301011, 301012, 301021, 7031, 302001"}
                ],
                "data": [
                    {"eccodes_key": "#1#wigosIdentifierSeries", "value": "metadata:wsi_series", "valid_min": "const:0", "valid_max": "const:0"},
                    {"eccodes_key": "#1#wigosIssuerOfIdentifier", "value": "metadata:wsi_issuer", "valid_min": "const:0", "valid_max": "const:65534"},
                    {"eccodes_key": "#1#wigosIssueNumber", "value": "metadata:wsi_issue_number", "valid_min": "const:0", "valid_max": "const:65534"},
                    {"eccodes_key": "#1#wigosLocalIdentifierCharacter", "value": "metadata:wsi_local"},
                    {"eccodes_key": "#1#year", "value": "data:year", "valid_min": "const:2022", "valid_max": "const:2025"},
                    {"eccodes_key": "#1#month", "value": "data:month", "valid_min": "const:1", "valid_max": "const:12"},
                    {"eccodes_key": "#1#day", "value": "data:day", "valid_min": "const:1", "valid_max": "const:31"},
                    {"eccodes_key": "#1#hour", "value": "data:hour", "valid_min": "const:0", "valid_max": "const:23"},
                    {"eccodes_key": "#1#minute", "value": "data:minute", "valid_min": "const:0", "valid_max": "const:59"},
                    {"eccodes_key": "#1#latitude", "value": "data:latitude", "valid_min": "const:-90.0", "valid_max": "const:90.0"},
                    {"eccodes_key": "#1#longitude", "value": "data:longitude", "valid_min": "const:-180.0", "valid_max": "const:180.0"},
                    {"eccodes_key": "#1#heightOfBarometerAboveMeanSeaLevel", "value": "data:brmh", "valid_min": "const:-400.0", "valid_max": "const:12707.0"},
                    {"eccodes_key": "#1#nonCoordinatePressure", "value": "data:slp", "valid_min": "const:0", "valid_max": "const:163820", "scale": "const:2", "offset": "const:0"},
                    {"eccodes_key": "#1#pressureReducedToMeanSeaLevel", "value": "data:mslp", "valid_min": "const:0", "valid_max": "const:163820", "scale": "const:2", "offset": "const:0"},
                    {"eccodes_key": "#1#3HourPressureChange", "value": "data:ppp", "valid_min": "const:-5000", "valid_max": "const:5220", "scale": "const:2", "offset": "const:0"},
                    {"eccodes_key": "#1#characteristicOfPressureTendency", "value": "data:a", "valid_min": "const:0", "valid_max": "const:14"}
                ]
            }'''  # noqa
        },
        "output": {"messages": []}
    },
}


class csv2bufrProcessor(BaseProcessor):
    def __init__(self, processor_def):
        """
        Initialize object
        :param processor_def: provider definition
        :returns: pygeoapi.process.csv2bufr.csv2bufr
        """

        super().__init__(processor_def, PROCESS_METADATA)

    def execute(self, data):
        """
        This method is invoked by pygeoapi when this class is set as a
        `process` type resource in pygeoapi config file.

        :param data: It is the value of `inputs` passed in payload. e.g.
        {
            "inputs": {
                "data": "csv data to encode",
                "mappings": "csv2bufr mapping json file"
            }
        }

        :return: media_type, json
        """

        mimetype = "application/json"
        try:
            bufr_generator = transform(data["data"], data["mapping"])
            # transform returns a generator, we need to iterate over
            # and add to single output object
            bufr = []
            for result in bufr_generator:
                bufr.append(result)

            output = {"messages": bufr}

            LOGGER.error(output)
        except Exception as e:
            LOGGER.exception(e)
            output = {"messages": None}
        return mimetype, output

    def __repr__(self):
        return "<csv2bufr> {}".format(self.name)
