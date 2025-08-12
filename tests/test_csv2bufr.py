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

import csv
import os
import threading

from io import StringIO
import logging

from eccodes import (codes_bufr_new_from_samples, codes_release)
import pytest

from csv2bufr import (apply_scaling, validate_value,
                      transform, SUCCESS, _warnings_global)

import csv2bufr.templates as c2bt

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel("DEBUG")

# set up warnings dict
tidx = f"t-{threading.get_ident()}"
_warnings_global[tidx] = []


# test data
@pytest.fixture
def mapping_dict():
    return {
        "conformsTo": ["csv2bufr-template-v2.json"],
        "metadata": {
            "label": "pytest",
            "description": "pytest template",
            "version": "2",
            "author": "David I. Berry",
            "editor": "",
            "dateCreated": "2023-09-01",
            "dateModified": "2024-01-12",
            "id": "eb37ac4f-13ce-4254-b372-5c1d097ea857"
        },
        "inputShortDelayedDescriptorReplicationFactor": [],
        "inputDelayedDescriptorReplicationFactor": [],
        "inputExtendedDelayedDescriptorReplicationFactor": [],
        "wigos_station_identifier": "const:0-1-2-ABCD",
        "number_header_rows": 1,
        "column_names_row": 1,
        "header": [
            {"eccodes_key": "edition", "value": "const:4"},  # noqa
            {"eccodes_key": "masterTableNumber", "value": "const:0"},  # noqa
            {"eccodes_key": "bufrHeaderCentre", "value": "const:0"},  # noqa
            {"eccodes_key": "bufrHeaderSubCentre", "value": "const:0"},  # noqa
            {"eccodes_key": "updateSequenceNumber", "value": "const:0"},  # noqa
            {"eccodes_key": "dataCategory", "value": "const:0"},  # noqa
            {"eccodes_key": "internationalDataSubCategory", "value": "const:6"},  # noqa
            {"eccodes_key": "masterTablesVersionNumber", "value":  "const:36"},  # noqa
            {"eccodes_key": "numberOfSubsets", "value":  "const:1"},  # noqa
            {"eccodes_key": "observedData", "value":  "const:1"},  # noqa
            {"eccodes_key": "compressedData", "value":  "const:0"},  # noqa
            {"eccodes_key": "typicalYear", "value": "data:year"},  # noqa
            {"eccodes_key": "typicalMonth", "value": "data:month"},  # noqa
            {"eccodes_key": "typicalDay", "value": "data:day"},  # noqa
            {"eccodes_key": "typicalHour", "value": "data:hour"},  # noqa
            {"eccodes_key": "typicalMinute", "value": "data:minute"},  # noqa
            {"eccodes_key": "unexpandedDescriptors","value": "array:301021, 301011, 301012, 10051, 12101"}  # noqa
        ],
        "data": [
            {"eccodes_key": "#1#year", "value": "data:year"},  # noqa
            {"eccodes_key": "#1#month", "value": "data:month"},  # noqa
            {"eccodes_key": "#1#day", "value": "data:day"},  # noqa
            {"eccodes_key": "#1#hour", "value": "data:hour"},  # noqa
            {"eccodes_key": "#1#minute", "value": "data:minute"},  # noqa
            {"eccodes_key": "#1#latitude", "value": "data:latitude"},  # noqa
            {"eccodes_key": "#1#longitude", "value": "data:longitude"},  # noqa
            {"eccodes_key": "#1#pressureReducedToMeanSeaLevel", "value": "data:pressure"},  # noqa
            {"eccodes_key": "#1#airTemperature", "value": "data:air_temperature"}  # noqa
        ]
    }


@pytest.fixture
def data_dict():
    return {
        "air_temperature": 290.31,
        "pressure": 100130,
        "latitude": 55.154,
        "longitude": 0.0,
        "year": 2021,
        "month": 11,
        "day": 18,
        "hour": 18,
        "minute": 0
    }


@pytest.fixture
def data_to_encode():
    return {
        "edition": 4,
        "masterTableNumber": 0,
        "bufrHeaderCentre": 0,
        "bufrHeaderSubCentre": 0,
        "updateSequenceNumber": 0,
        "section1Flags": 0,
        "dataCategory": 0,
        "internationalDataSubCategory": 6,
        "masterTablesVersionNumber": 36,
        "numberOfSubsets": 1,
        "observedData": 1,
        "compressedData": 0,
        "typicalYear": 2021.0,
        "typicalMonth": 11.0,
        "typicalDay": 18.0,
        "typicalHour": 18.0,
        "typicalMinute": 0.0,
        "unexpandedDescriptors": [
            301021,
            301011,
            301012,
            10051,
            12101
        ],
        "#1#year": 2021.0,
        "#1#month": 11.0,
        "#1#day": 18.0,
        "#1#hour": 18.0,
        "#1#minute": 0.0,
        "#1#latitude": 55.154,
        "#1#longitude": 0.0,
        "#1#pressureReducedToMeanSeaLevel": 100130.0,
        "#1#airTemperature": 290.31
    }


@pytest.fixture
def wsi():
    return "0-1-2-ABCD"


# test to check whether eccodes is installed
def test_eccodes():
    # call to eccodes library to test if accessible
    bufr_msg = codes_bufr_new_from_samples('BUFR4')
    # call to release the BUFR message
    codes_release(bufr_msg)
    assert True


# test to check validate_mapping is not broken
def test_validate_mapping_pass(mapping_dict):
    success = c2bt.validate_template(mapping_dict)
    assert success == SUCCESS


# test to check validate_mapping fails when we expect it to
def test_validate_mapping_fail():
    # not sure on this one, do we need this test and if so have many
    # different exceptions do we want to test?
    test_data = {
        "inputDelayedDescriptorReplicationFactor": [],
        "header": [],
        "data": [
            {"eccodes_key": "abc", "value": 1, "offset": 1},  # noqa
            {"eccodes_key": "def", "value": "col1", "valid-min": 0, "valid-max": 10},  # noqa
            {"eccodes_key": "ghi", "value": "col2", "valid-min": 250.0, "valid-max": 350.0, "scale": 0.0, "offset":  273.15},  # noqa
            {"eccodes_key": "jkl", "value": "col3", "valid-min": 90000.0, "valid-max": 120000.0, "scale": 2.0, "offset": 0.0}  # noqa
        ]
    }
    try:
        success = c2bt.validate_template(test_data)
    except Exception:
        success = False
    assert success != SUCCESS


# test to make sure apply_scaling works as expected
def test_apply_scaling():
    scale = 1
    offset = 20.0
    test_value = 10.0
    assert 120.0 == apply_scaling(test_value, scale, offset)


# test to check that valid_value works
def test_validate_value_pass():
    input_value = 10.0
    try:
        value = validate_value("test value", input_value, 0.0, 100.0, False)
    except Exception:
        assert False
    assert value == input_value


# test to check that valid_value fails when we expect it to
def test_validate_value_fail():
    input_value = 10.0
    try:
        _ = validate_value("test value", input_value, 0.0, 9.9, False)
    except Exception:
        return
    assert False


# test to check that valid_value returns null value when we expect it to
def test_validate_value_nullify():
    input_value = 10.0
    tid = f"t-{threading.get_ident()}"
    if tid not in _warnings_global:
        _warnings_global[tid] = []
    try:
        value = validate_value("test value", input_value, 0.0, 9.9, True)
    except Exception:
        assert False
    assert value is None
    del _warnings_global[tid]


# check that test transform works
def test_transform(data_dict, mapping_dict):
    # create CSV
    output = StringIO()
    writer = csv.DictWriter(output, quoting=csv.QUOTE_NONNUMERIC,
                            fieldnames=data_dict.keys())
    writer.writeheader()
    writer.writerow(data_dict)
    data = output.getvalue()

    result = transform(data, mapping_dict)

    for item in result:
        assert isinstance(item, dict)
        assert "_meta" in item

        item_meta_keys = ['geometry', 'id', 'properties', 'result']

        item_meta_properties_keys = ['data_category', 'datetime',
                                     'md5', 'originating_centre',
                                     'wigos_station_identifier']

        assert sorted(item["_meta"].keys()) == item_meta_keys
        assert sorted(item["_meta"]["properties"].keys()) == item_meta_properties_keys  # noqa
        assert item["_meta"]["properties"]["md5"] == "981938dbd97be3e5adc8e7b1c6eb642c"  # noqa


def test_templates():
    tmpl = c2bt.load_template('21327aac-46a6-437d-ae81-7a16a637dd2c')
    assert tmpl is not None
    # check header centre and sub centre set to env
    ocset = False
    ocenv = os.environ.get('BUFR_ORIGINATING_CENTRE', 65535)
    oscset = False
    oscenv = os.environ.get('BUFR_ORIGINATING_SUBCENTRE', 65535)
    LOGGER.warning((tmpl['header']))
    for hidx in range(len(tmpl['header'])):
        LOGGER.warning(tmpl['header'][hidx]['eccodes_key'])
        if tmpl['header'][hidx]['eccodes_key'] == 'bufrHeaderCentre':
            assert tmpl['header'][hidx]['value'] == f"const:{ocenv}"
            ocset = True
        if tmpl['header'][hidx]['eccodes_key'] == 'bufrHeaderSubCentre':
            assert tmpl['header'][hidx]['value'] == f"const:{oscenv}"
            oscset = True
    assert ocset
    assert oscset


def test_load_template_by_name():
    tmpl = c2bt.load_template('aws-template')
    assert tmpl is not None
