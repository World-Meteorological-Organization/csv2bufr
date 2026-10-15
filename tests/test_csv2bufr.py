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
import copy
import csv
import json
import os

from datetime import datetime
from io import StringIO
from types import SimpleNamespace
from unittest import mock
import logging

from eccodes import (codes_bufr_new_from_samples, codes_release,
                     codes_new_from_message, codes_set, codes_get,
                     codes_get_array, CODES_MISSING_DOUBLE)
import jsonschema
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


@pytest.fixture
def mapping_dict_v4(mapping_dict):
    mapping = copy.deepcopy(mapping_dict)
    mapping["conformsTo"] = ["csv2bufr-template-v4.json"]
    # set by csv2bufr for v4 templates
    mapping["header"] = [h for h in mapping["header"]
                         if h["eccodes_key"] not in
                         ("numberOfSubsets", "compressedData")]
    mapping["metadata"]["references"] = [
        {"title": "Manual on Codes (WMO-No. 306), Volume I.2",
         "edition": "2023"}
    ]
    mapping["metadata"]["history"] = [
        {"version": "1", "id": "99cad042-a73d-40a9-a646-cf140612394d",
         "date": "2023-09-01", "editor": "pytest",
         "changes": "Initial version."},
        {"version": "2", "id": "eb37ac4f-13ce-4254-b372-5c1d097ea857",
         "date": "2024-01-12", "editor": "pytest",
         "changes": "Second version.", "references": ["B/C1"]}
    ]
    return mapping


def test_schema_version(mapping_dict, mapping_dict_v4):
    assert c2bt.schema_version(mapping_dict) == "csv2bufr-template-v3.json"
    assert c2bt.schema_version(mapping_dict_v4) == "csv2bufr-template-v4.json"  # noqa
    # highest supported version is used, unknown versions are ignored
    mapping_dict["conformsTo"] = ["csv2bufr-template-v4.json",
                                  "csv2bufr-template-v2.json",
                                  "csv2bufr-template-v9.json"]
    assert c2bt.schema_version(mapping_dict) == "csv2bufr-template-v4.json"
    # conformsTo may be a string
    mapping_dict["conformsTo"] = "csv2bufr-template-v2.json"
    assert c2bt.schema_version(mapping_dict) == "csv2bufr-template-v2.json"
    # nothing supported, fall back to the default
    mapping_dict["conformsTo"] = []
    assert c2bt.schema_version(mapping_dict) == c2bt.DEFAULT_SCHEMA


def test_validate_v2_v3_pass(mapping_dict):
    assert c2bt.validate_template(mapping_dict) == SUCCESS
    mapping_dict["conformsTo"] = ["csv2bufr-template-v2.json"]
    assert c2bt.validate_template(mapping_dict) == SUCCESS


def test_validate_v4_pass(mapping_dict_v4):
    assert c2bt.validate_template(mapping_dict_v4) == SUCCESS


def test_validate_v4_history_mismatch_fails(mapping_dict_v4):
    mapping_dict_v4["metadata"]["history"][-1]["version"] = "3"
    with pytest.raises(RuntimeError, match="does not match metadata"):
        c2bt.validate_template(mapping_dict_v4)


def test_validate_v4_duplicate_history_ids_fails(mapping_dict_v4):
    history = mapping_dict_v4["metadata"]["history"]
    history[0]["id"] = history[1]["id"]
    with pytest.raises(RuntimeError, match="duplicate ids"):
        c2bt.validate_template(mapping_dict_v4)


@pytest.mark.parametrize("field, value", [
    ("id", "not-a-uuid"),
    ("dateCreated", "2023-13-01")
])
def test_validate_v4_formats_checked(mapping_dict_v4, field, value):
    mapping_dict_v4["metadata"][field] = value
    with pytest.raises(RuntimeError):
        c2bt.validate_template(mapping_dict_v4)


def test_validate_v4_reference_requires_title(mapping_dict_v4):
    mapping_dict_v4["metadata"]["references"] = [{"edition": "2023"}]
    with pytest.raises(RuntimeError):
        c2bt.validate_template(mapping_dict_v4)


def test_validate_v3_problems_warn_only(mapping_dict_v4, caplog):
    # the same problems only warn when the template declares v3
    mapping_dict_v4["conformsTo"] = ["csv2bufr-template-v3.json"]
    mapping_dict_v4["metadata"]["id"] = "not-a-uuid"
    mapping_dict_v4["metadata"]["history"][-1]["version"] = "3"
    assert c2bt.validate_template(mapping_dict_v4) == SUCCESS
    assert "does not match metadata" in caplog.text


def test_validate_pack_subsets(mapping_dict_v4):
    mapping_dict_v4["pack_subsets"] = True
    mapping_dict_v4["on_row_error"] = "fail"
    assert c2bt.validate_template(mapping_dict_v4) == SUCCESS
    mapping_dict_v4["on_row_error"] = "ignore"
    with pytest.raises(RuntimeError):
        c2bt.validate_template(mapping_dict_v4)
    mapping_dict_v4["on_row_error"] = "skip"
    mapping_dict_v4["pack_subsets"] = "yes"
    with pytest.raises(RuntimeError):
        c2bt.validate_template(mapping_dict_v4)


def test_validate_pack_multiple_stations(mapping_dict_v4, caplog):
    mapping_dict_v4["pack_multiple_stations"] = True
    assert c2bt.validate_template(mapping_dict_v4) == SUCCESS
    # ignored without pack_subsets
    assert "pack_multiple_stations is ignored" in caplog.text
    mapping_dict_v4["pack_subsets"] = True
    mapping_dict_v4["pack_multiple_stations"] = "yes"
    with pytest.raises(RuntimeError):
        c2bt.validate_template(mapping_dict_v4)


@pytest.mark.parametrize("key", ["numberOfSubsets", "compressedData"])
def test_validate_v4_automatic_header_keys_not_allowed(mapping_dict,
                                                       mapping_dict_v4, key):
    mapping_dict_v4["header"].append({"eccodes_key": key, "value": "const:1"})
    with pytest.raises(RuntimeError, match=f"{key} set by csv2bufr"):
        c2bt.validate_template(mapping_dict_v4)
    # still allowed for v2/v3
    assert any(h["eccodes_key"] == key for h in mapping_dict["header"])
    assert c2bt.validate_template(mapping_dict) == SUCCESS


def test_schema_v4_automatic_header_keys_not_allowed(mapping_dict_v4):
    # also rejected by the schema itself, for other validators
    with open(f"{c2bt.SCHEMA}/csv2bufr-template-v4.json") as fh:
        schema = json.load(fh)
    jsonschema.validate(mapping_dict_v4, schema)
    for key in ("numberOfSubsets", "compressedData"):
        mapping = copy.deepcopy(mapping_dict_v4)
        mapping["header"].append({"eccodes_key": key, "value": "const:1"})
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(mapping, schema)


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


def test_transform_pack_subsets_pack_failure_reported(multi_mapping,
                                                      packed_rows):
    packed_rows[0]["air_temperature"] = -999
    results = list(transform(to_csv(packed_rows), multi_mapping))
    assert len(results) == 1
    assert results[0]["bufr4"] is None
    assert results[0]["_meta"]["result"]["code"] == csv2bufr.FAILED
    assert any("'pack'" in e for e in results[0]["_meta"]["result"]["errors"])  # noqa


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
                                     'end_datetime', 'md5',
                                     'number_of_subsets',
                                     'originating_centre', 'start_datetime',
                                     'wigos_station_identifier']

        assert sorted(item["_meta"].keys()) == item_meta_keys
        assert sorted(item["_meta"]["properties"].keys()) == item_meta_properties_keys  # noqa
        assert item["_meta"]["properties"]["md5"] == "981938dbd97be3e5adc8e7b1c6eb642c"  # noqa


@pytest.fixture
def template_info():
    return {"label": "pytest", "version": "2",
            "id": "eb37ac4f-13ce-4254-b372-5c1d097ea857"}


def to_csv(rows):
    output = StringIO()
    writer = csv.DictWriter(output, quoting=csv.QUOTE_NONNUMERIC,
                            fieldnames=rows[0].keys())
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return output.getvalue()


def test_transform_template_provenance(data_dict, mapping_dict,
                                       template_info, caplog):
    caplog.set_level(logging.INFO)
    results = list(transform(to_csv([data_dict]), mapping_dict,
                             include_provenance=True))
    assert results[0]["_meta"]["properties"]["template"] == template_info
    assert "Using template 'pytest' version 2 (id eb37ac4f-13ce-4254-b372-5c1d097ea857)" in caplog.text  # noqa


def test_transform_template_provenance_off_by_default(
        data_dict, mapping_dict):
    # assumes CSV2BUFR_INCLUDE_PROV is not set when the tests are run
    results = list(transform(to_csv([data_dict]), mapping_dict))
    assert "template" not in results[0]["_meta"]["properties"]
    results = list(transform(to_csv([data_dict]), mapping_dict,
                             include_provenance=False))
    assert "template" not in results[0]["_meta"]["properties"]


def test_transform_failed_row_has_template(data_dict, mapping_dict,
                                           template_info):
    # -999 K is out of the coding range for airTemperature, so encoding fails
    data_dict["air_temperature"] = -999
    results = list(transform(to_csv([data_dict]), mapping_dict,
                             include_provenance=True))
    assert results[0]["bufr4"] is None
    assert results[0]["_meta"]["properties"]["template"] == template_info


def test_transform_wsi_error_includes_template(data_dict, mapping_dict,
                                               template_info):
    mapping_dict["wigos_station_identifier"] = "data:no_such_column"
    with pytest.raises(KeyError, match=f"\\[template {template_info['id']}\\]"):  # noqa
        list(transform(to_csv([data_dict]), mapping_dict))


def test_transform_invalid_template_includes_template(data_dict, mapping_dict,
                                                      template_info):
    del mapping_dict["header"]
    with pytest.raises(RuntimeError, match=f"\\[template {template_info['id']}\\]"):  # noqa
        list(transform(to_csv([data_dict]), mapping_dict))


def test_transform_log_prefix(data_dict, mapping_dict, template_info, caplog):
    prefix = f"[template {template_info['id']}]"
    data_dict["note"] = "ok"
    rows = [{**data_dict, "note": "ceäkes"}, data_dict]
    results = transform(to_csv(rows), mapping_dict)
    next(results)
    # warnings logged while transforming carry the template id
    assert f"{prefix} csv read error, non ASCII data detected" in caplog.text
    # but the template is not set while the caller handles a result
    assert csv2bufr._template_var.get() is None
    LOGGER.warning("caller log")
    assert caplog.records[-1].getMessage() == "caller log"
    results.close()
    assert csv2bufr._template_var.get() is None


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


@pytest.fixture
def packed_mapping(mapping_dict_v4):
    mapping_dict_v4["pack_subsets"] = True
    mapping_dict_v4["wigos_station_identifier"] = "data:wsi"
    return mapping_dict_v4


@pytest.fixture
def multi_mapping(packed_mapping):
    packed_mapping["pack_multiple_stations"] = True
    return packed_mapping


@pytest.fixture
def packed_rows(data_dict):
    # two stations, interleaved, with different temperatures and times
    return [
        {**data_dict, "wsi": "0-1-2-A", "air_temperature": 280.1, "hour": 6},
        {**data_dict, "wsi": "0-1-2-B", "air_temperature": 290.2, "hour": 6},
        {**data_dict, "wsi": "0-1-2-A", "air_temperature": 281.3, "hour": 7}
    ]


def decode_values(bufr, key):
    msg = codes_new_from_message(bufr)
    try:
        codes_set(msg, "unpack", 1)
        return (codes_get(msg, "numberOfSubsets"),
                codes_get(msg, "compressedData"),
                list(codes_get_array(msg, key)))
    finally:
        codes_release(msg)


def test_transform_pack_subsets(packed_mapping, packed_rows, template_info):
    results = list(transform(to_csv(packed_rows), packed_mapping,
                             include_provenance=True))

    # one message per station, in the order first seen
    assert len(results) == 2
    a, b = results
    for r, wsi, n in ((a, "0-1-2-A", 2), (b, "0-1-2-B", 1)):
        props = r["_meta"]["properties"]
        assert props["wigos_station_identifier"] == wsi
        assert "geometry_index" not in props  # one station
        assert props["number_of_subsets"] == n
        assert props["template"] == template_info
        assert r["_meta"]["id"] == \
            f"WIGOS_{wsi}_{props['datetime']:%Y%m%dT%H%M%S}"
        assert r["_meta"]["geometry"] == {
            "type": "Point", "coordinates": [0.0, 55.154]}
    # typical date/time from the station's first row
    assert a["_meta"]["properties"]["datetime"].hour == 6

    subsets, compressed, temps = decode_values(a["bufr4"], "#1#airTemperature")  # noqa
    assert (subsets, compressed) == (2, 1)
    assert temps == pytest.approx([280.1, 281.3])
    subsets, compressed, temps = decode_values(b["bufr4"], "#1#airTemperature")  # noqa
    assert (subsets, compressed) == (1, 0)
    assert temps == pytest.approx([290.2])


@pytest.mark.parametrize("wsi", ["", "0-1-2-"])
def test_transform_pack_subsets_incomplete_wsi(packed_mapping, packed_rows,
                                               wsi):
    packed_rows[1]["wsi"] = wsi
    results = list(transform(to_csv(packed_rows), packed_mapping))
    # the row fails on its own, the other station is still encoded
    assert len(results) == 2
    bad, a = results
    assert bad["bufr4"] is None
    assert bad["_meta"]["result"]["code"] == csv2bufr.FAILED
    assert bad["_meta"]["result"]["errors"][0].startswith(
        "row 3: incomplete WIGOS station identifier")
    assert a["_meta"]["properties"]["number_of_subsets"] == 2


def test_transform_pack_multiple_stations(multi_mapping, packed_rows,
                                          template_info):
    results = list(transform(to_csv(packed_rows), multi_mapping,
                             include_provenance=True))

    # all rows of the file in one message
    assert len(results) == 1
    r = results[0]
    props = r["_meta"]["properties"]
    assert props["number_of_subsets"] == 3
    assert props["template"] == template_info
    # several stations
    assert props["wigos_station_identifier"] is None
    assert [s["wigos_station_identifier"] for s in
            props["geometry_index"][0]["wigos_station_identifiers"]] == \
        ["0-1-2-A", "0-1-2-B"]
    assert r["_meta"]["id"] == f"BUFR_{props['md5']}"
    # all rows have the same location
    assert r["_meta"]["geometry"] == {
        "type": "Point", "coordinates": [0.0, 55.154]}
    # typical date/time from the first row
    assert props["datetime"].hour == 6

    subsets, compressed, temps = decode_values(r["bufr4"], "#1#airTemperature")  # noqa
    assert (subsets, compressed) == (3, 1)
    assert temps == pytest.approx([280.1, 290.2, 281.3])


def test_transform_pack_subsets_one_station(packed_mapping, packed_rows):
    rows = [row for row in packed_rows if row["wsi"] == "0-1-2-A"]
    r = list(transform(to_csv(rows), packed_mapping))[0]
    props = r["_meta"]["properties"]
    assert props["wigos_station_identifier"] == "0-1-2-A"
    assert "geometry_index" not in props
    assert props["number_of_subsets"] == 2


def test_transform_pack_subsets_one_row_uncompressed(packed_mapping,
                                                     packed_rows):
    r = list(transform(to_csv(packed_rows[:1]), packed_mapping))[0]
    subsets, compressed, temps = decode_values(r["bufr4"], "#1#airTemperature")  # noqa
    assert (subsets, compressed) == (1, 0)
    assert temps == pytest.approx([280.1])


def test_transform_v4_not_packed_uncompressed(data_dict, mapping_dict_v4):
    r = list(transform(to_csv([data_dict]), mapping_dict_v4))[0]
    subsets, compressed, _ = decode_values(r["bufr4"], "#1#airTemperature")
    assert (subsets, compressed) == (1, 0)


def test_transform_pack_subsets_geometry(multi_mapping, packed_rows):
    locations = [(10.0, 50.0), (12.0, 50.0), (11.0, 52.0)]
    for row, (lon, lat) in zip(packed_rows, locations):
        row["longitude"], row["latitude"] = lon, lat
    r = list(transform(to_csv(packed_rows), multi_mapping))[0]
    # bounding box of the locations
    assert r["_meta"]["geometry"] == {
        "type": "Polygon",
        "coordinates": [[[10.0, 50.0], [12.0, 50.0], [12.0, 52.0],
                         [10.0, 52.0], [10.0, 50.0]]]}


def test_geometry_point():
    assert csv2bufr._geometry([(1.0, 2.0), (1.0, 2.0)]) == {
        "type": "Point", "coordinates": [1.0, 2.0]}


@pytest.mark.parametrize("points", [
    [(0.0, 0.0), (2.0, 1.0)],  # two locations
    [(0.0, 0.0), (1.0, 0.5), (2.0, 1.0)],  # on one line
    [(0.0, 1.0), (2.0, 0.0), (1.0, 0.5), (None, None)]  # unknown left out
])
def test_geometry_bbox(points):
    assert csv2bufr._geometry(points) == {
        "type": "Polygon",
        "coordinates": [[[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0],
                         [0.0, 0.0]]]}


def test_transform_pack_subsets_time_range(packed_mapping, packed_rows):
    a = list(transform(to_csv(packed_rows), packed_mapping))[0]
    props = a["_meta"]["properties"]
    # typical date/time from the header, range from the subsets
    assert props["datetime"] == datetime(2021, 11, 18, 6)
    assert props["start_datetime"] == datetime(2021, 11, 18, 6)
    assert props["end_datetime"] == datetime(2021, 11, 18, 7)


def test_result_format_same_for_all_paths(data_dict, mapping_dict,
                                          packed_mapping, packed_rows):
    # a row on its own, a packed message of one station and of several
    # stations have the same keys, apart from geometry_index (only with
    # several stations)
    multi_mapping = {**packed_mapping, "pack_multiple_stations": True}
    single = list(transform(to_csv([data_dict]), mapping_dict))[0]
    packed = list(transform(to_csv(packed_rows), packed_mapping))[0]
    multi = list(transform(to_csv(packed_rows), multi_mapping))[0]
    for r in (single, packed, multi):
        assert r["_meta"]["result"]["code"] == csv2bufr.PASSED
        assert sorted(r["_meta"]) == ["geometry", "id", "properties",
                                      "result"]
    keys = sorted(single["_meta"]["properties"])
    assert sorted(packed["_meta"]["properties"]) == keys
    assert sorted(multi["_meta"]["properties"]) == \
        sorted(keys + ["geometry_index"])
    assert single["_meta"]["properties"]["number_of_subsets"] == 1
    assert single["_meta"]["id"].startswith("WIGOS_")


def test_failed_result_format_same_for_all_paths(data_dict, mapping_dict,
                                                 multi_mapping, packed_rows):
    data_dict["air_temperature"] = -999  # fails to pack
    single = list(transform(to_csv([data_dict]), mapping_dict))[0]
    packed_rows[0]["air_temperature"] = -999
    multi = list(transform(to_csv(packed_rows), multi_mapping))[0]
    for r in (single, multi):
        assert r["bufr4"] is None
        assert r["_meta"]["result"]["code"] == csv2bufr.FAILED
        assert r["_meta"]["properties"]["start_datetime"] is None
        assert r["_meta"]["properties"]["number_of_subsets"] == 0
    assert sorted(single["_meta"]["properties"]) == \
        sorted(multi["_meta"]["properties"])
    # the station is kept if there is one
    assert single["_meta"]["properties"]["wigos_station_identifier"] == \
        "0-1-2-ABCD"
    assert multi["_meta"]["properties"]["wigos_station_identifier"] is None


@pytest.mark.parametrize("subset, expected", [
    ({"#1#year": 2021, "#1#month": 11, "#1#day": 18},
     datetime(2021, 11, 18)),
    ({"#1#year": 2021.0, "#1#month": 11.0, "#1#day": 18.0, "#1#hour": 6.0,
      "#1#minute": None, "#1#second": 30.0},
     datetime(2021, 11, 18, 6, 0, 30)),
    ({"#1#year": 2021, "#1#month": 11, "#1#hour": 6}, None),  # no day
    ({"#1#year": 2021, "#1#month": 2, "#1#day": 30}, None),  # not valid
])
def test_subset_datetime(subset, expected):
    assert csv2bufr._subset_datetime(subset) == expected


def test_time_range():
    t1, t2 = datetime(2021, 1, 1), datetime(2021, 1, 2)
    assert csv2bufr._time_range([t2, None, t1]) == (t1, t2)
    assert csv2bufr._time_range([None], t1) == (t1, t1)


@pytest.mark.parametrize("points, expected", [
    ([(1.0, 2.0)], [1.0, 2.0, 1.0, 2.0]),
    ([(10.0, 50.0), (12.0, 52.0), (None, None)], [10.0, 50.0, 12.0, 52.0]),
    # crossing the antimeridian, west > east
    ([(170.0, 10.0), (-170.0, 12.0), (175.0, 11.0)],
     [170.0, 10.0, -170.0, 12.0]),
    ([(None, None)], None)
])
def test_bbox(points, expected):
    assert csv2bufr._bbox(points) == expected


def test_transform_pack_multiple_stations_index(multi_mapping,
                                                packed_rows):
    locations = [(10.0, 50.0), (12.0, 50.0), (10.0, 50.0)]
    for row, (lon, lat) in zip(packed_rows, locations):
        row["longitude"], row["latitude"] = lon, lat
    r = list(transform(to_csv(packed_rows), multi_mapping))[0]
    props = r["_meta"]["properties"]
    assert len(props["geometry_index"]) == 1
    entry = props["geometry_index"][0]
    assert [(s["wigos_station_identifier"], s["geometry"], s["bbox"],
             s["subsets"]) for s in entry["wigos_station_identifiers"]] == [
        ("0-1-2-A", {"type": "Point", "coordinates": [10.0, 50.0]},
         [10.0, 50.0, 10.0, 50.0], [1, 3]),
        ("0-1-2-B", {"type": "Point", "coordinates": [12.0, 50.0]},
         [12.0, 50.0, 12.0, 50.0], [2])]
    assert entry["subsets"] == [1, 2, 3]
    assert entry["polygon"] == r["_meta"]["geometry"]
    assert entry["bbox"] == [10.0, 50.0, 12.0, 50.0]


def test_transform_pack_multiple_stations_antimeridian(multi_mapping,
                                                       packed_rows):
    packed_rows.append({**packed_rows[1], "wsi": "0-1-2-C"})
    locations = [(170.0, 10.0), (-170.0, 10.0), (175.0, 12.0),
                 (-175.0, 12.0)]
    for row, (lon, lat) in zip(packed_rows, locations):
        row["longitude"], row["latitude"] = lon, lat
    r = list(transform(to_csv(packed_rows), multi_mapping))[0]
    east, west = r["_meta"]["properties"]["geometry_index"]
    assert east["subsets"] == [1, 3]

    def stations(side):
        return [(s["wigos_station_identifier"], s["subsets"])
                for s in side["wigos_station_identifiers"]]

    assert stations(east) == [("0-1-2-A", [1, 3])]
    assert west["subsets"] == [2, 4]
    assert stations(west) == [("0-1-2-B", [2]), ("0-1-2-C", [4])]
    assert east["bbox"] == [170.0, 10.0, 175.0, 12.0]
    assert west["bbox"] == [-175.0, 10.0, -170.0, 12.0]
    # two locations each side, so bounding boxes
    assert east["polygon"]["type"] == west["polygon"]["type"] == "Polygon"
    assert r["_meta"]["geometry"] == {
        "type": "MultiPolygon",
        "coordinates": [east["polygon"]["coordinates"],
                        west["polygon"]["coordinates"]]}


@pytest.mark.parametrize("lons, groups", [
    ([10.0, -10.0], [[0, 1]]),  # across 0, not split
    ([100.0, -100.0, 0.0], [[0, 1, 2]]),  # shorter through 0
    ([170.0, -170.0], [[0], [1]]),
    ([None, -170.0, 170.0], [[0, 2], [1]])  # unknown goes east
])
def test_antimeridian_groups(lons, groups):
    points = [(x, None if x is None else 0.0) for x in lons]
    assert csv2bufr._antimeridian_groups(points) == groups


def test_geometry_unknown_location():
    assert csv2bufr._geometry([(None, None), (1.0, None)]) == {
        "type": None, "coordinates": None}


def test_transform_pack_subsets_missing_values(multi_mapping, packed_rows):
    packed_rows[2]["air_temperature"] = ""
    results = list(transform(to_csv(packed_rows), multi_mapping))
    _, _, temps = decode_values(results[0]["bufr4"], "#1#airTemperature")
    assert temps[:2] == pytest.approx([280.1, 290.2])
    assert temps[2] == CODES_MISSING_DOUBLE


def test_transform_pack_subsets_row_error_skip(multi_mapping, packed_rows):
    packed_rows[0]["air_temperature"] = "abc"
    results = list(transform(to_csv(packed_rows), multi_mapping))
    a = results[0]
    assert a["_meta"]["result"]["code"] == csv2bufr.PASSED
    assert a["_meta"]["properties"]["number_of_subsets"] == 2
    # stations of the rows in the message, in the order first seen
    assert [s["wigos_station_identifier"] for s in
            a["_meta"]["properties"]["geometry_index"][0]
            ["wigos_station_identifiers"]] == ["0-1-2-B", "0-1-2-A"]
    # skipped row is reported by its line number in the file (header = 1)
    assert any(w.startswith("row 2: ") and w.endswith("row skipped")
               for w in a["_meta"]["result"]["warnings"])
    _, _, temps = decode_values(a["bufr4"], "#1#airTemperature")
    assert temps == pytest.approx([290.2, 281.3])


def test_transform_pack_subsets_row_error_fail(multi_mapping, packed_rows,
                                               template_info):
    multi_mapping["on_row_error"] = "fail"
    packed_rows[0]["air_temperature"] = "abc"
    results = list(transform(to_csv(packed_rows), multi_mapping,
                             include_provenance=True))
    assert len(results) == 1
    a = results[0]
    assert a["bufr4"] is None
    assert a["_meta"]["result"]["code"] == csv2bufr.FAILED
    assert a["_meta"]["result"]["errors"][0].startswith("row 2: ")
    assert a["_meta"]["properties"]["template"] == template_info
    # several stations, so none kept
    assert a["_meta"]["properties"]["wigos_station_identifier"] is None


def test_transform_pack_subsets_needs_v4(packed_mapping, packed_rows, caplog):
    packed_mapping["conformsTo"] = ["csv2bufr-template-v3.json"]
    results = list(transform(to_csv(packed_rows), packed_mapping))
    assert len(results) == 3
    assert "pack_subsets is not supported" in caplog.text


def test_transform_pack_subsets_row_error_fail_per_station(packed_mapping,
                                                           packed_rows):
    packed_mapping["on_row_error"] = "fail"
    packed_rows[0]["air_temperature"] = "abc"
    a, b = list(transform(to_csv(packed_rows), packed_mapping))
    # only the message of the station with the bad row fails
    assert a["_meta"]["result"]["code"] == csv2bufr.FAILED
    assert a["_meta"]["properties"]["wigos_station_identifier"] == "0-1-2-A"
    assert b["_meta"]["result"]["code"] == csv2bufr.PASSED


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


@pytest.fixture
def template_dirs(tmp_path, mapping_dict_v4):
    """
    Two empty template directories, searched in order (dirs), and a function
    to write a template to one of the directories (write). While the test
    runs, TEMPLATE_DIRS is dirs and TEMPLATES is empty; both are restored
    afterwards.
    """
    dirs = [tmp_path / "first", tmp_path / "second"]
    for dir_ in dirs:
        dir_.mkdir()

    def write(dir_index, name, id_, version="2",
              conforms_to="csv2bufr-template-v4.json"):
        tmpl = copy.deepcopy(mapping_dict_v4)
        tmpl["conformsTo"] = [conforms_to]
        tmpl["metadata"]["id"] = id_
        tmpl["metadata"]["version"] = version
        tmpl["metadata"]["history"][-1].update(id=id_, version=version)
        path = dirs[dir_index] / f"{name}.json"
        path.write_text(json.dumps(tmpl))
        return str(path)

    with mock.patch.object(c2bt, "TEMPLATE_DIRS", dirs), \
            mock.patch.dict(c2bt.TEMPLATES, clear=True):
        yield SimpleNamespace(dirs=dirs, write=write)


ID_A = "11111111-1111-4111-8111-111111111111"
ID_B = "22222222-2222-4222-8222-222222222222"


def test_template_search_path_has_no_duplicates():
    assert len(set(c2bt.TEMPLATE_DIRS)) == len(c2bt.TEMPLATE_DIRS)


def test_index_duplicate_id_warns(template_dirs, caplog):
    t = template_dirs
    first = t.write(0, "a", ID_A)
    second = t.write(1, "b", ID_A)
    c2bt.index_templates()
    assert c2bt.TEMPLATES[ID_A]["path"] == first
    assert f"Duplicate template id {ID_A}: {second} ignored, using {first}" in caplog.text  # noqa


def test_index_empty_id_not_indexed(template_dirs, caplog):
    # v4 rejects an empty id as not a uuid, v2/v3 do not check the format
    t = template_dirs
    path = t.write(0, "a", "", conforms_to="csv2bufr-template-v3.json")
    c2bt.index_templates()
    assert c2bt.TEMPLATES == {}
    assert f"Template {path} has no id, not indexed" in caplog.text
    assert "Duplicate" not in caplog.text


def test_index_missing_directory_skipped(template_dirs, tmp_path, caplog):
    t = template_dirs
    t.write(0, "a", ID_A)
    t.dirs.insert(0, tmp_path / "missing")
    c2bt.index_templates()
    assert ID_A in c2bt.TEMPLATES
    assert "not found, skipping" in caplog.text


def test_load_template_by_id_gets_exact_version(template_dirs):
    # two versions of a template side by side
    t = template_dirs
    t.write(0, "pytest-v1", ID_A, version="1")
    t.write(0, "pytest-v2", ID_B, version="2")
    c2bt.index_templates()
    assert c2bt.load_template(ID_A)["metadata"]["version"] == "1"
    assert c2bt.load_template(ID_B)["metadata"]["version"] == "2"


def test_load_template_by_name_duplicates_warn(template_dirs, caplog):
    t = template_dirs
    first = t.write(0, "pytest", ID_A, version="1")
    second = t.write(1, "pytest", ID_B, version="2")
    c2bt.index_templates()
    assert c2bt.load_template("pytest")["metadata"]["version"] == "1"
    assert f"Several templates named 'pytest' found ({first}, {second}), using {first}" in caplog.text  # noqa


def test_index_includes_provenance(template_dirs, mapping_dict_v4):
    t = template_dirs
    t.write(0, "a", ID_A)
    c2bt.index_templates()
    entry = c2bt.TEMPLATES[ID_A]
    assert entry["references"] == mapping_dict_v4["metadata"]["references"]
    assert [h["version"] for h in entry["history"]] == ["1", "2"]


def test_load_template_logs_template(caplog):
    caplog.set_level(logging.INFO)
    tmpl = c2bt.load_template('aws-template')
    path = c2bt.TEMPLATES[tmpl["metadata"]["id"]]["path"]
    assert f"Using template {c2bt.describe_template(tmpl)} from {path}" in caplog.text  # noqa
