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
import json
import logging
import os
from pathlib import Path
from typing import Union

from jsonschema import validate

THISDIR = os.path.dirname(os.path.realpath(__file__))
LOGGER = logging.getLogger(__name__)
SCHEMA = f"{THISDIR}{os.sep}resources{os.sep}schema"
TEMPLATE_DIRS = []  # [Path("./")]

_SUCCESS_ = True

# check if originating centre and subcentre are set as env , default to 255
ORIGINATING_CENTRE = os.environ.get('BUFR_ORIGINATING_CENTRE', 65535)
ORIGINATING_SUBCENTRE = os.environ.get('BUFR_ORIGINATING_SUBCENTRE', 65535)

if ORIGINATING_CENTRE is None:
    msg = "Invalid BUFR originating centre, please ensure the BUFR_ORIGINATING_CENTRE is set to a valid value"  # noqa
    LOGGER.error(msg)
    raise RuntimeError(msg)

if ORIGINATING_SUBCENTRE is None:
    msg = "Invalid BUFR originating subcentre, please ensure the BUFR_ORIGINATING_SUBCENTRE is set to a valid value"  # noqa
    LOGGER.error(msg)
    raise RuntimeError(msg)

_template_flag = False
# Set user defined location first
if 'CSV2BUFR_TEMPLATES' in os.environ:
    TEMPLATE_DIRS.append(Path(os.environ['CSV2BUFR_TEMPLATES']))
else:
    TEMPLATE_DIRS.append(Path("./"))
    _template_flag = True

# Check if /opt/csv2bur/templates exists and add to search path
if Path("/opt/csv2bufr/templates").exists() and \
        "/opt/csv2bufr/templates" not in TEMPLATE_DIRS:
    TEMPLATE_DIRS.append(Path("/opt/csv2bufr/templates"))

if _template_flag:
    LOGGER.warning(f"""CSV2BUFR_TEMPLATES is not set, default search path(s)
        will be used ({TEMPLATE_DIRS}).""")

if Path("/opt/csv2bufr/templates").exists():
    TEMPLATE_DIRS.append(Path("/opt/csv2bufr/templates"))

# Dictionary to store template filename and label (if assigned)
TEMPLATES = {}


# function to load template by name
def load_template(template_name: str, isFile=False) -> Union[dict, None]:
    """
    Checks whether specified template exists and loads file.
    Returns none and prints a warning if no template found.

    :param template_name: The name of the template (without file extension)
                          to load.

    :returns: BUFR template as a dictionary or none in the case of template
              not found.
    """
    template = None
    msg = False
    fname = None
    error_flag = False
    if isFile:
        fname = template_name
    elif (template_name not in TEMPLATES) and (not isFile):
        for _template in TEMPLATES.values():
            if template_name == _template.get('name'):
                fname = _template.get('path')
                break
        if fname is None:
            msg = f"Requested template '{template_name}' not found. " +\
                  f"Search path = {TEMPLATE_DIRS}. Please update " +\
                  "search path (e.g. 'export CSV2BUFR_TEMPLATE=...')"
            error_flag = True
    else:
        fname = TEMPLATES[template_name].get('path')

    if fname is None:
        msg = f"Error loading template {template_name}, no path found"
        error_flag = True
    else:
        try:
            with open(fname) as fh:
                template = json.load(fh)
        except Exception as e:
            LOGGER.error(f"Error: Exception raised whilst loading json mapping file {fname}, see additional error messages")  # noqa
            raise e

    if error_flag:
        raise RuntimeError(msg)
    else:
        # update template originating centre and subcentre
        ocset = False
        oscset = False
        for hidx in range(len(template['header'])):
            if template['header'][hidx]["eccodes_key"] == "bufrHeaderCentre":
                ocset = True
            if template['header'][hidx]["eccodes_key"] == "bufrHeaderSubCentre":  # noqa
                oscset = True

        if not ocset:
            template['header'].append(
                {"eccodes_key": "bufrHeaderCentre",
                 "value": f"const:{ORIGINATING_CENTRE}"})

        if not oscset:
            template['header'].append(
                {"eccodes_key": "bufrHeaderSubCentre",
                 "value": f"const:{ORIGINATING_SUBCENTRE}"})

        if msg:
            LOGGER.warning(msg)

        return template


def validate_template(mapping: dict) -> bool:
    """
    Validates dictionary containing mapping to BUFR against internal schema.
    Returns True if the dictionary passes and raises an error otherwise.

    :param mapping: dictionary containing mappings to specified BUFR
                        sequence using ecCodes key.

    :returns: `bool` of validation result
    """
    # load internal file schema for mappings
    file_schema = f"{SCHEMA}{os.sep}csv2bufr-template-v3.json"
    try:
        with open(file_schema) as fh:
            schema = json.load(fh)
    except Exception as e:
        LOGGER.error("Error: Exception loading mapping schema file")
        raise e

    # now validate
    try:
        validate(mapping, schema)
    except Exception as e:
        msg = f"Exception ({e}). Invalid BUFR template mapping file: {mapping}"
        raise RuntimeError(msg)

    return _SUCCESS_


def index_templates() -> bool:
    for dir_ in TEMPLATE_DIRS:
        for template in dir_.iterdir():
            try:
                if template.suffix == ".json":
                    # check if valid mapping file
                    with template.open() as fh:
                        tmpl = json.load(fh)
                    if 'csv2bufr-template-v3.json' not in tmpl.get("conformsTo",[]):  # noqa
                        if 'csv2bufr-template-v2.json' in tmpl.get("conformsTo",[]):  # noqa
                            LOGGER.warning("Deprecated 'csv2bufr-template-v2.json' found in " +  # noqa
                                       f"conformsTo for file {template}")  # noqa
                            LOGGER.warning("Support for 'csv2bufr-template-v2.json' will be removed in a future release")  # noqa
                        else:
                            LOGGER.warning("'csv2bufr-template-v3.json' not found in " +  # noqa
                                       f"conformsTo for file {template}, skipping")  # noqa
                            continue
                    if validate_template(tmpl) == _SUCCESS_:
                        # get label if exists else set to empty string
                        fname = str(template)
                        id = tmpl['metadata'].get("id", "")
                        if id in TEMPLATES:
                            pass
                        else:
                            TEMPLATES[id] = {
                                "label": tmpl['metadata'].get("label", ""),
                                "description": tmpl['metadata'].get("description", ""),  # noqa
                                "version": tmpl['metadata'].get("version", ""),
                                "author": tmpl['metadata'].get("author", ""),
                                "dateCreated": tmpl['metadata'].get("dateCreated", ""),  # noqa
                                "id": tmpl['metadata'].get("id", ""),
                                "path": fname,
                                "name": Path(fname).stem
                            }

            except Exception as e:
                LOGGER.warning(f"Warning raised indexing csv2bufr templates: {e}, skipping file {template}.")  # noqa

    return _SUCCESS_


def list_templates() -> dict:
    """
    :returns: Dictionary of known templates in search path
              (CSV2BUFR_TEMPLATES). An empty dictionary is return if no
              templates are found.
    """
    return TEMPLATES


if index_templates() != _SUCCESS_:
    LOGGER.error("Error indexing csv2bufr templates, see logs")
