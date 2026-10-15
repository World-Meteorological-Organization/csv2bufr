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

import asyncio
import contextvars
import csv
import os

from io import StringIO
from unittest import mock
import logging

from eccodes import (codes_bufr_new_from_samples, codes_release,
                     codes_new_from_message, codes_set, codes_get,
                     codes_get_array, CODES_MISSING_DOUBLE)
import pytest

import csv2bufr
from csv2bufr import (apply_scaling, validate_value, transform, SUCCESS)

import csv2bufr.templates as c2bt

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel("DEBUG")


# test data
@pytest.fixture
def mapping_dict():
    return {
        "conformsTo": ["csv2bufr-template-v3.json"],
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
    try:
        value = validate_value("test value", input_value, 0.0, 9.9, True)
    except Exception:
        assert False
    assert value is None


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


def to_csv(rows):
    output = StringIO()
    writer = csv.DictWriter(output, quoting=csv.QUOTE_NONNUMERIC,
                            fieldnames=rows[0].keys())
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def decode_values(bufr, key):
    msg = codes_new_from_message(bufr)
    try:
        codes_set(msg, "unpack", 1)
        return (codes_get(msg, "numberOfSubsets"),
                codes_get(msg, "compressedData"),
                list(codes_get_array(msg, key)))
    finally:
        codes_release(msg)


# MISSING without CSV2BUFR_MISSING_VALUE
DEFAULT_MISSING = ["NA", "NaN", "NAN", "None", "", None]


@pytest.mark.parametrize("value, expected", [
    (None, True), ("", True), ("NA", True), ("NaN", True), ("None", True),
    (float("nan"), True),
    (-999, True), (-999.0, True), ("-999", True), ("-999.0", True),
    (-99, False), ("-99", False), (0, False), ("abc", False),
    ("nan", False)
])
def test_is_missing(value, expected):
    # as if CSV2BUFR_MISSING_VALUE=-999
    with mock.patch.object(csv2bufr, "MISSING", DEFAULT_MISSING + ["-999"]):
        assert csv2bufr._is_missing(value) is expected


def test_is_missing_without_missing_value():
    with mock.patch.object(csv2bufr, "MISSING", DEFAULT_MISSING):
        assert not csv2bufr._is_missing(-999)
        assert not csv2bufr._is_missing("-999")


def test_transform_unquoted_nan_is_missing(data_dict, mapping_dict):
    # with QUOTE_NONNUMERIC, unquoted values are read as floats, so NaN in
    # the file is read as a float NaN
    data_dict["air_temperature"] = float("nan")
    data = to_csv([data_dict])
    assert data.splitlines()[1].startswith("nan,")  # unquoted
    results = list(transform(data, mapping_dict))
    assert results[0]["bufr4"] is not None
    _, _, temps = decode_values(results[0]["bufr4"], "#1#airTemperature")
    assert temps == [CODES_MISSING_DOUBLE]


def test_transform_pack_failure_reported(data_dict, mapping_dict):
    # -999 K is out of the coding range for airTemperature, so ecCodes
    # fails to pack the message
    data_dict["air_temperature"] = -999
    results = list(transform(to_csv([data_dict]), mapping_dict))
    assert results[0]["bufr4"] is None
    assert results[0]["_meta"]["result"]["code"] == csv2bufr.FAILED
    assert "'pack'" in results[0]["_meta"]["result"]["errors"][0]


def test_bufr_message_failed_encode_clears_cache():
    message = csv2bufr.BUFRMessage([12101])
    message.set_element("edition", 4)
    message.set_element("masterTablesVersionNumber", 36)
    message.set_element("unexpandedDescriptors", 12101)
    message.set_element("#1#airTemperature", 290.0)
    assert message.as_bufr() is not None
    assert message.md5() is not None
    # a failed encode must not leave the previous message's bytes or hash
    message.set_element("#1#airTemperature", -999)
    with pytest.raises(RuntimeError, match="'pack'"):
        message.as_bufr()
    assert message.bufr is None
    assert message.md5() is None
    # nor must reset
    message.set_element("#1#airTemperature", 290.0)
    message.as_bufr()
    message.reset()
    assert message.bufr is None
    assert message.md5() is None


@pytest.fixture
def warning_rows(data_dict, mapping_dict):
    # the first row has an out of range value and so a warning, the second
    # has none
    for element in mapping_dict["data"]:
        if element["eccodes_key"] == "#1#airTemperature":
            element["valid_min"] = "const:200.0"
            element["valid_max"] = "const:350.0"
    return [{**data_dict, "air_temperature": 400.0}, data_dict]


def _check_row_warnings(results):
    assert len(results) == 2
    assert any("out of valid range" in w
               for w in results[0]["_meta"]["result"]["warnings"])
    assert results[1]["_meta"]["result"]["warnings"] == []


def test_transform_advanced_from_copied_contexts(warning_rows, mapping_dict):
    # each step runs in a fresh copy of the context, so no context variable
    # token may be held across a yield
    results = transform(to_csv(warning_rows), mapping_dict)
    _check_row_warnings([contextvars.copy_context().run(next, results)
                         for _ in warning_rows])


def test_transform_advanced_with_asyncio_to_thread(warning_rows,
                                                   mapping_dict):
    async def consume():
        results = transform(to_csv(warning_rows), mapping_dict)
        return [await asyncio.to_thread(next, results) for _ in warning_rows]

    _check_row_warnings(asyncio.run(consume()))


def test_transform_interleaved(warning_rows, mapping_dict):
    # two transforms advanced in turn keep their warnings apart
    a = transform(to_csv(warning_rows), mapping_dict)
    b = transform(to_csv(warning_rows[::-1]), mapping_dict)
    a1, b1, a2, b2 = next(a), next(b), next(a), next(b)
    _check_row_warnings([a1, a2])
    _check_row_warnings([b2, b1])


def test_transform_warnings_not_set_for_caller(warning_rows, mapping_dict):
    results = transform(to_csv(warning_rows), mapping_dict)
    next(results)
    assert csv2bufr._warnings_var.get() is None
    list(results)
    assert csv2bufr._warnings_var.get() is None
    # nor after an error
    mapping_dict["wigos_station_identifier"] = "data:no_such_column"
    with pytest.raises(KeyError):
        list(transform(to_csv(warning_rows), mapping_dict))
    assert csv2bufr._warnings_var.get() is None


def test_transform_non_ascii_unmapped_value(data_dict, mapping_dict):
    # non-ASCII data in a column the template does not use only gives a
    # warning, the row is still encoded
    data_dict["note"] = "ok"
    rows = [data_dict, {**data_dict, "note": "ceäkes", "hour": 19}]

    results = list(transform(to_csv(rows), mapping_dict))

    assert len(results) == 2
    result = results[1]["_meta"]
    assert result["result"]["code"] == csv2bufr.PASSED
    assert result["properties"]["datetime"].hour == 19
    assert any("non ASCII data detected (ceäkes), value set to missing" in w
               for w in result["result"]["warnings"])
    assert results[0]["_meta"]["result"]["warnings"] == []


def test_transform_non_ascii_mapped_value(data_dict, mapping_dict):
    # a non-ASCII value that is mapped is encoded as missing, the rest of the
    # row is still encoded
    rows = [{**data_dict, "air_temperature": "29°"}]

    results = list(transform(to_csv(rows), mapping_dict))

    assert len(results) == 1
    assert results[0]["_meta"]["result"]["code"] == csv2bufr.PASSED
    assert any("non ASCII data detected (29°), value set to missing" in w
               for w in results[0]["_meta"]["result"]["warnings"])
    _, _, temps = decode_values(results[0]["bufr4"], "#1#airTemperature")
    assert temps == [CODES_MISSING_DOUBLE]
    _, _, pressures = decode_values(results[0]["bufr4"],
                                    "#1#pressureReducedToMeanSeaLevel")
    assert pressures == pytest.approx([data_dict["pressure"]])


def test_transform_non_ascii_not_nullified(data_dict, mapping_dict):
    rows = [{**data_dict, "note": "ceäkes"}]
    with mock.patch.object(csv2bufr, "NULLIFY_INVALID", False):
        with pytest.raises(ValueError, match="non ASCII data detected"):
            list(transform(to_csv(rows), mapping_dict))


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
