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

__version__ = '0.8.6'

import csv
import uuid
from datetime import timezone, datetime
import hashlib
from io import StringIO, BytesIO
import json
import logging
import os.path
import threading
from typing import Any, Iterator, Union

from eccodes import (codes_bufr_new_from_samples,
                     codes_set_array, codes_set, codes_get_native_type,
                     codes_write, codes_release, codes_get,
                     codes_bufr_keys_iterator_new,
                     codes_bufr_keys_iterator_next,
                     codes_bufr_keys_iterator_delete,
                     codes_bufr_keys_iterator_get_name, CodesInternalError)

import csv2bufr.templates as c2bt

# some 'constants'
SUCCESS = True
NUMBERS = (float, int, complex)
MISSING = ["NA", "NaN", "NAN", "None", "", None]

if os.environ.get("CSV2BUFR_MISSING_VALUE") is not None:
    MISSING.append(os.environ.get("CSV2BUFR_MISSING_VALUE"))

if 'CSV2BUFR_NULLIFY_INVALID' in os.environ:
    NULLIFY_INVALID = os.environ['CSV2BUFR_NULLIFY_INVALID']
    if NULLIFY_INVALID == "True":
        NULLIFY_INVALID = True
    else:
        NULLIFY_INVALID = False
else:
    NULLIFY_INVALID = True

LOGGER = logging.getLogger(__name__)

BUFR_TABLE_VERSION = os.environ.get("BUFR_TABLE_VERSION", 41)  # noqa default BUFR table version
# list of BUFR attributes
ATTRIBUTES = ['code', 'units', 'scale', 'reference', 'width']
# list of ecCodes keys for BUFR headers
HEADERS = ["edition", "masterTableNumber", "bufrHeaderCentre",
           "bufrHeaderSubCentre", "updateSequenceNumber", "dataCategory",
           "internationalDataSubCategory", "dataSubCategory",
           "masterTablesVersionNumber", "localTablesVersionNumber",
           "typicalYear", "typicalMonth", "typicalDay", "typicalHour",
           "typicalMinute", "typicalSecond", "typicalDate", "typicalTime",
           "numberOfSubsets", "observedData", "compressedData",
           "unexpandedDescriptors", "subsetNumber"]

HEADERS_EXCLUDE = ['typicalTime', 'typicalDate', 'localTablesVersionNumber',
                   'bufrHeaderSubCentre', 'updateSequenceNumber',
                   'dataSubCategory', 'localTablesVersionNumber',
                   'subsetNumber']

DEFAULTS = {
    'edition': 'const:4',
    'masterTableNumber': 'const:0',
    'dataCategory': 'const:0',
    'internationalDataSubCategory': 'const:6',
    'masterTablesVersionNumber': f'const:{BUFR_TABLE_VERSION}',
    'numberOfSubsets': 'const:1',
    'observedData': 'const:1',
    'compressedData': 'const:0',
    'typicalYear': 'data:year',
    'typicalMonth': 'data:month',
    'typicalDay': 'data:day',
    'typicalHour': 'data:hour',
    'typicalMinute': 'data:minute',
    'typicalSecond': 'const:0'
}

_warnings_global = {}

# status codes
FAILED = 0
PASSED = 1

DELIMITER = ","
QUOTING = "QUOTE_NONNUMERIC"
QUOTECHAR = '"'


# Errors
# index_, key not found
# column not found in input data
# invalid mapping, data type not recognised
# invalid mapping file
# error applying scaling to data
# validation error, value out of range
# error getting key for variable
# conversion error, non-int to int
# conversion error, non-float to float
# eccodes, codes_set_array
# eccodes, codes_set
# error creating internal BytesIO for BUFR
# error scaling data
# error validating data


# function to find position in array of requested element
def index_(key, mapping):
    global _warnings_global
    tidx = f"t-{threading.get_ident()}"
    idx = 0
    for item in mapping:
        if item['eccodes_key'] == key:
            return idx
        idx += 1
    if NULLIFY_INVALID:
        msg = f"Warning: key {key} not found in {mapping}"
        LOGGER.warning(msg)
        _warnings_global[tidx].append(msg)
        return None
    else:
        msg = f"Error: key {key} not found in {mapping}"
        # LOGGER.error(msg)
        raise ValueError(msg)


def parse_value(element: str, data: dict):
    global _warnings_global
    tidx = f"t-{threading.get_ident()}"

    data_type = element.split(":")
    if data_type[0] == "const":
        value = data_type[1]
        if "." in value:
            value = float(value)
        else:
            value = int(value)
    elif data_type[0] == "data":
        column = data_type[1]
        if column not in data:
            msg = f"Column {column} not found in input data: {data}"
            if NULLIFY_INVALID:
                LOGGER.warning(msg)  # noqa
                _warnings_global[tidx].append(msg)
            else:
                # LOGGER.error(msg)  # noqa
                raise ValueError(msg)
        value = data[column]
    elif data_type[0] == "array":
        value = data_type[1]
        # determine if float or int
        if "." in value:
            func = float
        else:
            func = int
        # split into words, strip white space and convert
        words = value.split(",")
        value = list(map(lambda x: func(x.strip()), words))
    elif data_type[0] in ["", None]:
        return None
    else:
        msg = f"Data type ({data_type[0]}) not recognised in mapping: {element}"  # noqa
        # LOGGER.error(msg)  # noqa
        raise ValueError(msg)
    return value


# function to retrieve data
def get_(key: str, mapping: dict, data: dict):
    global _warnings_global
    tidx = f"t-{threading.get_ident()}"
    # get position in mapping
    try:
        idx = index_(key, mapping)
        element = mapping[idx]
        value = parse_value(element['value'], data)
    except Exception as e:
        msg = f"Warning ({e}) raised getting value for {key}, None returned for {key}"  # noqa
        if NULLIFY_INVALID:
            LOGGER.warning(msg)  # noqa
            _warnings_global[tidx].append(msg)
            value = None
        else:
            raise KeyError(msg)
    return value


def apply_scaling(value: Union[NUMBERS], scale: Union[NUMBERS],
                  offset: Union[NUMBERS]) -> Union[NUMBERS]:
    """
    Applies a simple scaling and offset to the input data value.
    Scaling follows the BUFR conventions, e.g.

    .. math::
        \\mbox{scaled\\_value} =
            \\mbox{value} \\times 10^{\\mbox{scale}} + \\mbox{offset}

    :param value: The input value to have scaling and offset applied to
    :param scale: The scale factor to use
    :param offset: The offset factor to use

    :returns: scaled value
    """
    global _warnings
    if isinstance(value, NUMBERS):
        if None not in [scale, offset]:
            try:
                value = value * pow(10, scale) + offset
            except Exception as e:
                msg = f"Error ({e}) applying scaling and offset"
                # LOGGER.error(f"{msg}")
                raise RuntimeError(msg)
    return value


def validate_value(key: str, value: Union[NUMBERS],
                   valid_min: Union[NUMBERS] = float('-inf'),
                   valid_max: Union[NUMBERS] = float('+inf'),
                   nullify_on_fail: bool = False) -> Union[NUMBERS]:
    """
    Check numeric values lie within specified range (if specified)

    :param key: ECCODES key used when giving feedback / logging
    :param value: The value to validate
    :param valid_min: Valid minimum value
    :param valid_max: Valid maximum value
    :param nullify_on_fail: Action to take on fail, either set to None
                           (nullify_on_fail=True) or through an error (default)

    :returns: validated value
    """
    global _warnings_global
    tidx = f"t-{threading.get_ident()}"
    # TODO move this function to the class as part of set value

    if value is None:
        return value
    if not isinstance(value, NUMBERS):
        # TODO: add checking against code / flag table here?
        return value

    if None not in [valid_min, valid_max]:
        if (value > valid_max) or (value < valid_min):
            msg = f"{key}: Value ({value}) out of valid range ({valid_min} - {valid_max})."  # noqa
            if nullify_on_fail:
                LOGGER.warning(f"{msg}; Element set to missing")
                _warnings_global[tidx].append(f"{msg}; Element set to missing")
                return None
            else:
                raise ValueError(msg)

    return value


class BUFRMessage:
    def __init__(self, descriptors: list,
                 short_delayed_replications: list = list(),
                 delayed_replications: list = list(),
                 extended_delayed_replications: list = list(),
                 table_version: int = BUFR_TABLE_VERSION) -> None:
        """
        Constructor

        :param descriptors: list of BUFR descriptors to use in this instance
                            e.g. descriptors=[301150, 307014]
        :param delayed_replications: delayed replicators to use in the sequence
                                     if not set ECCODES sets the delayed
                                     replicators to 1. Omit if unsure of value
        :param table_version: version of Master Table 0 to use, default 36

        """
        self.warnings = []
        # ================================
        # first create empty bufr messages
        # ================================
        bufr_msg = codes_bufr_new_from_samples("BUFR4")
        # ===============================
        # set delayed replication factors
        # ===============================
        if len(short_delayed_replications) > 0:
            codes_set_array(bufr_msg,
                            "inputShortDelayedDescriptorReplicationFactor",
                            short_delayed_replications)

        if len(delayed_replications) > 0:
            codes_set_array(bufr_msg,
                            "inputDelayedDescriptorReplicationFactor",
                            delayed_replications)
        if len(extended_delayed_replications) > 0:
            codes_set_array(bufr_msg,
                            "inputExtendedDelayedDescriptorReplicationFactor",
                            extended_delayed_replications)

        # ===============================
        # set master table version number
        # ===============================
        codes_set(bufr_msg, "masterTablesVersionNumber", table_version)
        # now set unexpanded descriptors
        codes_set_array(bufr_msg, "unexpandedDescriptors", descriptors)
        # ================================================
        # now iterator over and add to internal dictionary
        # ================================================
        self.dict = dict()  # need a more descriptive name
        iterator = codes_bufr_keys_iterator_new(bufr_msg)
        while codes_bufr_keys_iterator_next(iterator):
            key = codes_bufr_keys_iterator_get_name(iterator)
            # place holder for data
            self.dict[key] = dict()
            self.dict[key]["value"] = None
            # add native type, used when encoding later
            native_type = codes_get_native_type(bufr_msg, key)
            self.dict[key]["type"] = native_type.__name__
            # now add attributes (excl. BUFR header elements)
            if key not in HEADERS:
                for attr in ATTRIBUTES:
                    try:
                        self.dict[key][attr] = \
                            codes_get(bufr_msg, f"{key}->{attr}")
                    except Exception as e:
                        msg = f"Error ({e}) getting attribute {attr} for {key}."  # noqa
                        # LOGGER.error(f"{msg}")
                        raise RuntimeError(msg)

        codes_bufr_keys_iterator_delete(iterator)
        # ============================================
        # now release the BUFR message back to eccodes
        # ============================================
        codes_release(bufr_msg)
        # ============================================
        # finally add last few items to class
        # ============================================
        self.descriptors = descriptors
        self.delayed_replications = delayed_replications  # used when encoding
        self.short_delayed_replications = \
            short_delayed_replications  # used when encoding
        self.extended_delayed_replications = \
            extended_delayed_replications  # used when encoding
        self.bufr = None  # placeholder for BUFR bytes
        self._hash = None  # placeholder for hash of data
        # ============================================

    def create_template(self) -> None:
        template = {}
        template["conformsTo"] = ["csv2bufr-template-v3.json"]
        template["metadata"] = {
            "label": "",
            "description": "",
            "version": "0",
            "author": "",
            "editor": "",
            "dateCreated": datetime.now().strftime("%Y-%m-%d"),
            "dateModified": datetime.now().strftime("%Y-%m-%d"),
            "id": str(uuid.uuid4())
        }
        template["inputDelayedDescriptorReplicationFactor"] = \
            self.delayed_replications

        template["inputShortDelayedDescriptorReplicationFactor"] = \
            self.short_delayed_replications
        template["inputExtendedDelayedDescriptorReplicationFactor"] = \
            self.extended_delayed_replications
        template["number_header_rows"] = 1
        template["column_names_row"] = 1
        template["delimiter"] = ","
        template["quoting"] = "QUOTE_NONE"
        template["quotechar"] = ""
        template["header"] = []
        # create header section
        for element in HEADERS:
            if element in HEADERS_EXCLUDE:
                continue
            value = ""
            if element == "unexpandedDescriptors":
                value = ",".join(str(x) for x in self.descriptors)
                value = f"array:{value}"
            elif element in DEFAULTS:
                value = DEFAULTS.get(element)
                if value is None:
                    value = ""
            entry = {
                "eccodes_key": element,
                "value": value
            }
            template["header"].append(entry)
        # now create data section
        template["data"] = []
        for element in self.dict:
            if element not in HEADERS:
                element_stub = element.split("#")[2]
                if self.dict[element]['type'] in ('int', 'float'):
                    # calculate valid min and max
                    scale = self.dict[element]['scale']
                    offset = self.dict[element]['reference']
                    width = self.dict[element]['width']
                    valid_min = round((0 + offset) * pow(10, -1 * scale), scale)  # noqa
                    valid_max = round((pow(2, width) - 1 + offset) * pow(10, -1 * scale), scale)  # noqa
                    entry = {
                        "eccodes_key": element,
                        "value": f"data:{element_stub}",
                        "valid_min": f"const:{valid_min}",
                        "valid_max": f"const:{valid_max}",
                        "scale": "const:0",
                        "offset": "const:0"
                    }
                else:
                    entry = {
                        "eccodes_key": element,
                        "value": f"data:{element_stub}"
                    }
                template["data"].append(entry)

        return template

    def reset(self) -> None:
        """
        Function resets BUFRMessage

        :returns: `None`
        """
        for key in self.dict:
            self.dict[key]["value"] = None
        self.bufr = None
        self.warnings = []

    def set_element(self, key: str, value: object) -> None:
        """
        Function to set element in BUFR message

        :param key: the key of the element to set (using ECCODES keys)
        :param value: the value of the element

        :returns: `None`
        """
        # TODO move value validation here

        if value is not None and not isinstance(value, list):
            expected_type = self.dict[key]["type"]
            if expected_type == "int" and not isinstance(value, int):
                if isinstance(value, float):
                    value = int(round(value))
                else:
                    try:
                        value = int(float(value))
                    except Exception as e:
                        if NULLIFY_INVALID:
                            value = None
                            LOGGER.warning(f"{e}: Unable to convert value {value} to int for {key}, set to None")  # noqa
                            self.warnings.append(f"{e}: Unable to convert value {value} to int for {key}, set to None")  # noqa
                        else:
                            raise RuntimeError(f"{e}: Unable to convert value {value} to int for {key}")  # noqa
            elif expected_type == "float" and not isinstance(value, float):
                try:
                    value = float(value)
                except Exception as e:
                    if NULLIFY_INVALID:
                        value = None
                        LOGGER.warning(f"{e}: Unable to convert value {value} to float for {key}, set to None")  # noqa
                        self.warnings.append(f"{e}: Unable to convert value {value} to float for {key}, set to None")  # noqa
                    else:
                        raise RuntimeError(f"{e}: Unable to convert value {value} to float for {key}")  # noqa
            else:
                value = value
        self.dict[key]["value"] = value

    def get_element(self, key: str) -> Any:
        """
        Function to retrieve value from BUFR message

        :param key: the key of the element to set (using ECCODES keys)

        :returns: value of the element
        """
        result = None
        try:
            # check if we want value or an attribute (indicated by ->)
            if "->" in key:
                tokens = key.split("->")
                result = self.dict[tokens[0]][tokens[1]]
            else:
                result = self.dict[key]["value"]

        except Exception as e:
            if NULLIFY_INVALID:
                result = None
                LOGGER.warning(f"Error {e} whilst fetching {key} from data, None returned")  # noqa
                self.warnings.append(f"Error {e} whilst fetching {key} from data, None returned")  # noqa
            else:
                msg = f"Error {e} whilst fetching {key} from data."
                raise RuntimeError(msg)

        return result

    def as_bufr(self, use_cached: bool = False) -> bytes:
        """
        Function to get BUFR message encoded into bytes. Once called the bytes
        are cached and the cached value returned unless specified otherwise.

        :param use_cached: Boolean indicating whether to use cached value

        :returns: bytes containing BUFR data
        """
        if use_cached and (self.bufr is not None):
            return self.bufr
        # ===========================
        # initialise new BUFR message
        # ===========================
        bufr_msg = codes_bufr_new_from_samples("BUFR4")
        # set delayed replications, this is needed again as we only used it the
        # first time to set the keys
        if len(self.short_delayed_replications) > 0:
            try:
                codes_set_array(bufr_msg,
                                "inputShortDelayedDescriptorReplicationFactor",
                                self.short_delayed_replications)
            except Exception as e:
                msg = f"Error ({e}) setting inputShortDelayedDescriptorReplicationFactor"  # noqa
                raise RuntimeError(msg)

        if len(self.delayed_replications) > 0:
            try:
                codes_set_array(bufr_msg,
                                "inputDelayedDescriptorReplicationFactor",
                                self.delayed_replications)
            except Exception as e:
                msg = f"Error ({e}) setting inputDelayedDescriptorReplicationFactor"  # noqa
                raise RuntimeError(msg)

        if len(self.extended_delayed_replications) > 0:
            try:
                codes_set_array(bufr_msg,
                                "inputExtendedDelayedDescriptorReplicationFactor",  # noqa
                                self.extended_delayed_replications)
            except Exception as e:
                msg = f"Error ({e}) setting inputExtendedDelayedDescriptorReplicationFactor"  # noqa
                raise RuntimeError(msg)

        # ============================
        # iterate over keys and encode
        # ============================
        for eccodes_key in self.dict:
            value = self.dict[eccodes_key]["value"]
            if value is not None:
                if isinstance(value, list):
                    try:
                        codes_set_array(bufr_msg, eccodes_key, value)
                    except Exception as e:
                        msg = f"Error ({e}) calling codes_set_array({bufr_msg}, {eccodes_key}, {value})"  # noqa
                        raise RuntimeError(msg)
                else:
                    try:
                        codes_set(bufr_msg, eccodes_key, value)
                    except Exception as e:
                        msg = f"Error ({e}) calling codes_set({bufr_msg}, {eccodes_key}, {value})"  # noqa
                        # LOGGER.error(f"{msg}")  # noqa
                        raise RuntimeError(msg)
        # ==============================
        # Message now ready to be packed
        # ==============================
        try:
            codes_set(bufr_msg, "pack", True)
        except CodesInternalError as e:
            msg = f"Error ({e}) calling codes_set({bufr_msg}, 'pack', True). Null message returned"  # noqa
            LOGGER.warning(f"{msg}")  # noqa
            self.warnings.append(f"{msg}")  # noqa
            codes_release(bufr_msg)
            return self.bufr
        except Exception as e:
            msg = f"Error ({e}) calling codes_set({bufr_msg}, 'pack', True)"
            # LOGGER.error(f"{msg}") # noqa
            LOGGER.debug(json.dumps(self.dict, indent=4))
            raise RuntimeError(msg)
        # =======================================================
        # now write to in memory file and return bytes to caller
        # =======================================================
        try:
            fh = BytesIO()
            codes_write(bufr_msg, fh)
            codes_release(bufr_msg)
            fh.seek(0)
        except Exception as e:
            msg = f"Error ({e}) writing to internal BytesIO object"
            # LOGGER.error(f"{msg}")
            raise RuntimeError(msg)
        # =============================================
        # Return BUFR message bytes
        # =============================================
        self.bufr = fh.read()
        try:
            # set hash
            self._hash = hashlib.md5(self.bufr).hexdigest()
        except Exception as e:
            msg = f"Error ({e}) calculating hash (md5) of BUFR string: {self.bufr}"  # noqa
            raise RuntimeError(msg)

        return self.bufr

    def md5(self) -> str:
        """
        Calculates and returns md5 of BUFR message

        :returns: md5 of BUFR message
        """
        return self._hash

    def parse(self, data: dict, mappings: dict) -> None:
        """
        Function to parse observation data and station metadata, mapping to the
        specified BUFR sequence.

        :param data: dictionary of key value pairs containing the
                    data to be encoded.
        :param mappings: dictionary containing list of BUFR elements to
                        encode (specified using ECCODES key) and whether
                        to get the value from (fixed, csv or metadata)
        :returns: `None`
        """

        # ==================================================
        # Parse the data.
        # ==================================================
        for section in ("header", "data"):
            for element in mappings[section]:
                # get eccodes key
                eccodes_key = element["eccodes_key"]
                # get value
                value = get_(eccodes_key, mappings[section], data)
                if value in MISSING:
                    value = None
                else:
                    # convert to expected data type
                    expected_type = self.dict[eccodes_key]["type"]
                    if (expected_type in ("float", "int")) and \
                            (eccodes_key not in HEADERS):
                        try:
                            value = float(value)
                        except Exception as e:
                            msg = f"Error ({e}) converting value ({value}) to expected type"  # noqa
                            # LOGGER.error(f"{e}")
                            raise RuntimeError(msg)
                # ==============
                # validate value
                # ==============
                valid_min = None
                valid_max = None
                if "valid_min" in element:
                    valid_min = parse_value(element["valid_min"], data)  # noqa
                if "valid_max" in element:
                    valid_max = parse_value(element["valid_max"], data)  # noqa
                try:
                    value = validate_value(element["eccodes_key"], value,
                                           valid_min, valid_max,
                                           NULLIFY_INVALID)
                except Exception as e:
                    if NULLIFY_INVALID:
                        LOGGER.warning(f"Error raised whilst validating {element['eccodes_key']}, value set to None\ndata: {data}")  # noqa
                        self.warnings.append(f"Error raised whilst validating {element['eccodes_key']}, value set to None\ndata: {data}")  # noqa
                        value = None
                    else:
                        # LOGGER.error(f"Error raised whilst validating {element['eccodes_key']}, raising error")  # noqa
                        # LOGGER.error(f"data: {data}")
                        raise e

                # ===================================
                # now apply specified scaling to data
                # ===================================
                if value in MISSING:
                    value = None
                else:
                    scale = None
                    offset = None
                    try:
                        if "scale" in element:
                            scale = parse_value(element["scale"], data)
                        if "offset" in element:
                            offset = parse_value(element["offset"], data)
                        value = apply_scaling(value, scale, offset)
                    except Exception as e:
                        msg = f"Error ({e}) scaling data: scale={scale}, offet={offset}, value={value}"  # noqa
                        # LOGGER.error(f"{msg}")  # noqa
                        LOGGER.debug(f"data: {data}")
                        raise RuntimeError(msg)

                # ==================================================
                # at this point we should have the eccodes key and a
                # validated value to use, add to dict
                # ==================================================
                self.set_element(eccodes_key, value)

    def get_datetime(self) -> datetime:
        """
        Function to extract characteristic date and time from the BUFR message

        :returns: `datetime.datetime` of ISO8601 representation of the
                  characteristic date/time
        """
        if None in [
            self.get_element("typicalYear"),
            self.get_element("typicalMonth"),
            self.get_element("typicalDay"),
            self.get_element("typicalHour"),
            self.get_element("typicalMinute")
        ]:
            msg = 'Error: invalid datetime'
            # LOGGER.error(msg)
            raise RuntimeError(msg)

        return datetime(
            self.get_element("typicalYear"),
            self.get_element("typicalMonth"),
            self.get_element("typicalDay"),
            self.get_element("typicalHour"),
            self.get_element("typicalMinute")
        )


def transform(data: str, mappings: dict) -> Iterator[dict]:
    """
    This function returns an iterator to process each line in the input CSV
    string. On each iteration a dictionary is returned containing the BUFR
    encoded data. The mapping to BUFR is specified by the "mappings"
    dictionary using the ecCodes keys. For more information and a list of the
    keys see the tables at:

        https://confluence.ecmwf.int/display/ECC/WMO%3D37+element+table

    The dictionary returned by the iterator contains the following keys:

        - ["bufr4"] = data encoded into BUFR;
        - ["_meta"] = GeoJSON metadata on the data.

    The ["_meta"] element includes the following:

        - ["id"] = identifier for report (WIGOS_<WSI>_<ISO8601>);
        - ["geometry"] = GeoJSON geometry object;
        - ["properties"] = key/value pairs of properties/attributes

    The ["_meta"]["properties"] element includes the following:

        - ["md5"] = md5 checksum of BUFR encoded data;
        - ["wigos_station_identifier"] = WIGOS identifier;
        - ["datetime"] = characteristic date of data;
        - ["originating_centre"] = Originating centre (see Common code table C11);  # noqa
        - ["data_category"] = Category of data, see BUFR Table A.

    :param data: string containing csv separated data. First line should
                contain the column headers, second line the data
    :param metadata: string containing static CSV metadata to include in the BUFR  # noqa
    :param mappings: dictionary containing list of BUFR elements to
                    encode (specified using ecCodes key) and whether
                    to get the value from (fixed, csv or metadata)

    :returns: iterator
    """
    global _warnings_global
    job_id = f"t-{threading.get_ident()}"  # job ID based on thread
    _warnings_global[job_id] = []
    # ======================
    # validate mapping files
    # ======================
    e = c2bt.validate_template(mappings)

    if e is not SUCCESS:
        raise ValueError("Invalid mappings")

    # identify how we are getting the WSi
    wsi = mappings.get("wigos_station_identifier")
    if wsi is not None:
        wsi = wsi.split(":")
        if len(wsi) != 2:
            raise ValueError(
                "Invalid wigos_station_identifier mapping specified")
        if wsi[0] == "const":
            wsi_kind = 1
            wsi_value = wsi[1]
            wsi_field = None
        else:
            wsi_kind = 2
            wsi_field = wsi[1]
            wsi_value = None
    else:
        wigosIdentifierSeries = None
        wigosIssuerOfIdentifier = None
        wigosIssueNumber = None
        wigosLocalIdentifierCharacter = None
        for item in mappings["data"]:
            if item["eccodes_key"] == "#1#wigosIdentifierSeries":
                wigosIdentifierSeries = item["value"]
            if item["eccodes_key"] == "#1#wigosIssuerOfIdentifier":
                wigosIssuerOfIdentifier = item["value"]
            if item["eccodes_key"] == "#1#wigosIssueNumber":
                wigosIssueNumber = item["value"]
            if item["eccodes_key"] == "#1#wigosLocalIdentifierCharacter":
                wigosLocalIdentifierCharacter = item["value"]
        if None in (wigosIdentifierSeries, wigosIssuerOfIdentifier,
                    wigosIssueNumber, wigosLocalIdentifierCharacter):
            raise ValueError(
                "Invalid wigos_station_identifier mapping specified")
        wsi_kind = 3

    # ==========================================================
    # Now extract descriptors and replications from mapping file
    # ==========================================================
    short_delayed_replications = mappings["inputShortDelayedDescriptorReplicationFactor"]  # noqa
    delayed_replications = mappings["inputDelayedDescriptorReplicationFactor"]
    extended_delayed_replications = mappings["inputExtendedDelayedDescriptorReplicationFactor"]   # noqa

    # get number of rows to skip
    skip = mappings["number_header_rows"]
    col_names_row = mappings["column_names_row"] - 1

    unexpanded_descriptors = get_("unexpandedDescriptors", mappings["header"], data = None)  # noqa
    table_version = get_("masterTablesVersionNumber", mappings["header"], data = None)  # noqa

    # check if we have delimiter
    if "delimiter" in mappings:
        _delimiter = mappings["delimiter"]
        if _delimiter not in [",", ";", "|", "\t"]:
            msg = "Invalid delimiter specified in mapping template, reverting to comma ','"  # noqa
            LOGGER.warning(msg)
            _warnings_global[job_id].append(msg)
            _delimiter = ","
    else:
        _delimiter = DELIMITER

    # quoting
    if 'QUOTING' in mappings:
        _quoting = mappings['QUOTING']
    elif 'quoting' in mappings:
        _quoting = mappings['quoting']
    else:
        _quoting = QUOTING

    _quoting = getattr(csv, _quoting)

    if 'QUOTECHAR' in mappings:
        _quotechar = mappings['QUOTECHAR']
    if 'quotechar' in mappings:
        _quotechar = mappings['quotechar']
    else:
        _quotechar = QUOTECHAR

    # =========================================
    # Now we need to convert string back to CSV
    # and iterate over rows
    # =========================================
    fh = StringIO(data)
    try:
        if _quoting == csv.QUOTE_NONE:
            reader = csv.reader(fh, delimiter=_delimiter, quoting=_quoting)
        else:
            reader = csv.reader(fh, delimiter=_delimiter, quoting=_quoting,
                            quotechar=_quotechar)
    except Exception as e:
        msg = f"Error ({e}) reading csv data\n{data}"
        LOGGER.critical(f"{msg}")
        raise RuntimeError(msg)

    # read in header rows
    if skip > 0:
        rows_read = 0
        while rows_read < skip:
            row = next(reader)
            if rows_read == col_names_row:
                col_names = row

            rows_read += 1

    # initialise new BUFRMessage (and reuse later)
    try:
        message = BUFRMessage(unexpanded_descriptors,
                              short_delayed_replications,
                              delayed_replications,
                              extended_delayed_replications,
                              table_version)
    except Exception as e:
        msg = f"Error ({e}) initialising BUFR message"
        LOGGER.critical(f"{msg}")
        raise RuntimeError(msg)

    # now iterate over remaining rows
    for row in reader:
        wsi = None
        result = dict()
        # check and make sure we have ascii data
        for val in row:
            if isinstance(val, str):
                if not val.isascii():
                    if NULLIFY_INVALID:
                        msg = f"csv read error, non ASCII data detected ({val}), skipping row"  # noqa
                        LOGGER.warning(msg)  # noqa
                        _warnings_global[job_id].append(msg)
                        LOGGER.debug(row)
                        continue
                    else:
                        msg = f"csv read error, non ASCII data detected ({val})"  # noqa
                        raise ValueError(msg)
        # valid data row, make dictionary
        data_dict = dict(zip(col_names, row))
        # parse and split WSI
        try:
            # extract WSI and split into required components
            if wsi_kind == 2:
                wsi = data_dict[wsi_field]
            elif wsi_kind == 1:
                wsi = wsi_value
            elif wsi_kind == 3:
                wsi = f"{parse_value(wigosIdentifierSeries, data_dict)}"
                wsi += f"-{parse_value(wigosIssuerOfIdentifier, data_dict)}"
                wsi += f"-{parse_value(wigosIssueNumber, data_dict)}"
                wsi += f"-{parse_value(wigosLocalIdentifierCharacter, data_dict)}"  # noqa

            wsi_series, wsi_issuer, wsi_issue_number, wsi_local = wsi.split("-")   # noqa
            data_dict["_wsi_series"] = wsi_series
            data_dict["_wsi_issuer"] = wsi_issuer
            data_dict["_wsi_issue_number"] = wsi_issue_number
            data_dict["_wsi_local"] = wsi_local
        except KeyError as e:
            msg = f"Error, key {e} not found in input data when building WIGOS station identifier"  # noqa
            # LOGGER.error(f"{msg}")
            LOGGER.debug(f"data:{data_dict}")
            raise KeyError(msg)
        except Exception as e:
            msg = f"Error ({e}) parsing WIGOS station identifier"
            # LOGGER.error(f"{msg}")
            LOGGER.debug(f"data:{data_dict}")
            raise ValueError(msg)
        # reset BUFR message to clear data
        message.reset()
        cksum = None
        try:
            # parse to BUFR sequence
            message.parse(data_dict, mappings)
            # encode to BUFR
            result["bufr4"] = message.as_bufr()
            status = {
                "code": PASSED,
                "message": "",
                "errors": [],
                "warnings": message.warnings + _warnings_global[job_id]
            }
            cksum = message.md5()
            # now identifier based on WSI and observation date as identifier
            isodate = message.get_datetime().strftime('%Y%m%dT%H%M%S')
            rmk = f"WIGOS_{wsi}_{isodate}"
            # now additional metadata elements
            result["_meta"] = {
                "id": rmk,
                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        message.get_element('#1#longitude'),
                        message.get_element('#1#latitude')
                    ]
                },
                "properties": {
                    "md5": cksum,
                    "wigos_station_identifier": wsi,
                    "datetime": message.get_datetime(),
                    "originating_centre": message.get_element("bufrHeaderCentre"),  # noqa
                    "data_category": message.get_element("dataCategory")
                },
                "result": status
            }

        except Exception as e:
            msg = f"Error ({e}) encoding BUFR, BUFR set to None"
            LOGGER.error(f"{msg}")
            LOGGER.debug(f"data:{data_dict}")
            result["bufr4"] = None
            status = {
                "code": FAILED,
                "message": "Error encoding row, BUFR set to None",
                "errors": [f"{msg}\n\t\tData: {data_dict}"],
                "warnings": message.warnings + _warnings_global[job_id]
            }
            result["_meta"] = {
                "id": None,
                "geometry": {
                    "type": None,
                    "coordinates": None
                },
                "properties": {
                    "md5": None,
                    "wigos_station_identifier": None,
                    "datetime": None,
                    "originating_centre": None,
                    "data_category": None
                },
                "result": status
            }

        time_ = datetime.now(timezone.utc).isoformat()
        LOGGER.info(f"{time_}|{result['_meta']}")
        # now yield result back to caller
        yield result
        # clear warnings
        _warnings_global[job_id] = []

    fh.close()
