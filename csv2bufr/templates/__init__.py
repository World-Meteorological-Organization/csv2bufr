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

from jsonschema import FormatChecker, validate

THISDIR = os.path.dirname(os.path.realpath(__file__))
LOGGER = logging.getLogger(__name__)
SCHEMA = f"{THISDIR}{os.sep}resources{os.sep}schema"
# supported schema versions, oldest first
SCHEMA_VERSIONS = ['csv2bufr-template-v2.json', 'csv2bufr-template-v3.json',
                   'csv2bufr-template-v4.json']
# schema used when the template does not name a supported version
DEFAULT_SCHEMA = 'csv2bufr-template-v3.json'
# schema versions where formats and history are enforced rather than warned
STRICT_SCHEMA_VERSIONS = ['csv2bufr-template-v4.json']
# header keys set by csv2bufr, not allowed in STRICT_SCHEMA_VERSIONS templates
AUTOMATIC_HEADER_KEYS = ['numberOfSubsets', 'compressedData']
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
        Path("/opt/csv2bufr/templates") not in TEMPLATE_DIRS:
    TEMPLATE_DIRS.append(Path("/opt/csv2bufr/templates"))

if _template_flag:
    LOGGER.warning(f"""CSV2BUFR_TEMPLATES is not set, default search path(s)
        will be used ({TEMPLATE_DIRS}).""")

# Dictionary to store template filename and label (if assigned)
TEMPLATES = {}


# Helper function to return info on mapping template
def template_info(mapping: dict) -> dict:
    """
    Returns the label, version and id identifying a template, used to trace
    output and errors back to the template that produced them.

    :param mapping: dictionary containing the template

    :returns: `dict` with keys label, version and id (None if not set)
    """
    metadata = {}
    if isinstance(mapping, dict) and isinstance(mapping.get("metadata"), dict):
        metadata = mapping["metadata"]
    return {
        "label": metadata.get("label"),
        "version": metadata.get("version"),
        "id": metadata.get("id")
    }


# Now function to return that info as a string
def describe_template(mapping: dict) -> str:
    """
    :param mapping: dictionary containing the template

    :returns: `str` describing the template, e.g. for log messages
    """
    info = template_info(mapping)
    return f"'{info['label']}' version {info['version']} (id {info['id']})"


# function to load template by name
def load_template(template_name: str, isFile=False) -> Union[dict, None]:
    """
    Checks whether specified template exists and loads file.
    Raises an error if no template found.

    :param template_name: The id of the template (exactly that version), or
                          the name of the template file (without file
                          extension). If several files have the name, the
                          first in TEMPLATE_DIRS is used and a warning
                          logged.

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
        # look up by file name (stem), the same name can be in several
        # directories, the index is in search path order so use the first
        matches = [_template.get('path') for _template in TEMPLATES.values()
                   if template_name == _template.get('name')]
        if matches:
            fname = matches[0]
            if len(matches) > 1:
                LOGGER.warning(f"Several templates named '{template_name}' found ({', '.join(matches)}), using {fname}")  # noqa
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

        LOGGER.info(f"Using template {describe_template(template)} from {fname}")  # noqa

        return template


def schema_version(mapping: dict) -> str:
    """
    Returns the schema to validate a template against: the highest supported
    version listed in the template's conformsTo, or DEFAULT_SCHEMA if none
    is listed.

    :param mapping: dictionary containing the template

    :returns: `str` schema file name
    """
    conforms_to = mapping.get("conformsTo", [])
    if isinstance(conforms_to, str):
        conforms_to = [conforms_to]
    supported = [sc for sc in SCHEMA_VERSIONS if sc in conforms_to]
    if supported:
        return supported[-1]
    return DEFAULT_SCHEMA


def check_history(mapping: dict) -> list:
    """
    Checks the template history that JSON schema cannot express: the last
    entry must match the current version and id, and ids must be unique.

    :param mapping: dictionary containing the template

    :returns: `list` of problems found, empty if none
    """
    metadata = mapping.get("metadata", {})
    history = metadata.get("history")
    if not history:
        return []
    # v2/v3 schemas do not define history, so check its shape here
    if not isinstance(history, list) or \
            not all(isinstance(entry, dict) for entry in history):
        return ["history must be an array of objects"]

    problems = []
    last = history[-1]
    if (last.get("version"), last.get("id")) != \
            (metadata.get("version"), metadata.get("id")):
        problems.append(
            f"last history entry (version {last.get('version')}, id {last.get('id')}) "  # noqa
            f"does not match metadata (version {metadata.get('version')}, id {metadata.get('id')})")  # noqa

    ids = [str(entry.get("id")) for entry in history]
    duplicates = sorted({id_ for id_ in ids if ids.count(id_) > 1})
    if duplicates:
        problems.append(f"duplicate ids in history: {', '.join(duplicates)}")

    return problems


def validate_template(mapping: dict) -> bool:
    """
    Validates dictionary containing mapping to BUFR against internal schema.
    The schema is chosen from the template's conformsTo (see
    `schema_version`). Returns True if the dictionary passes and raises an
    error otherwise.

    For schema versions in STRICT_SCHEMA_VERSIONS, formats (e.g. uuid, date)
    are checked and history problems are errors. For older versions history
    problems are logged as warnings.

    :param mapping: dictionary containing mappings to specified BUFR
                        sequence using ecCodes key.

    :returns: `bool` of validation result
    """
    # load internal file schema for mappings
    schema_name = schema_version(mapping)
    strict = schema_name in STRICT_SCHEMA_VERSIONS
    file_schema = f"{SCHEMA}{os.sep}{schema_name}"
    try:
        with open(file_schema) as fh:
            schema = json.load(fh)
    except Exception as e:
        LOGGER.error("Error: Exception loading mapping schema file")
        raise e

    # the schema also rejects these, but with an unclear message
    if strict:
        keys = [element.get("eccodes_key")
                for element in mapping.get("header", [])
                if isinstance(element, dict) and element.get("eccodes_key") in AUTOMATIC_HEADER_KEYS]  # noqa
        if keys:
            raise RuntimeError(f"{', '.join(keys)} set by csv2bufr and must not be set in {schema_name} templates. Invalid BUFR template mapping file: {mapping}")  # noqa

    # now validate
    try:
        if strict:
            validate(mapping, schema, format_checker=FormatChecker())
        else:
            validate(mapping, schema)
    except Exception as e:
        msg = f"Exception ({e}). Invalid BUFR template mapping file: {mapping}"
        raise RuntimeError(msg)

    problems = check_history(mapping)
    if problems:
        msg = f"Invalid template history ({'; '.join(problems)})"
        if strict:
            raise RuntimeError(f"{msg}. Invalid BUFR template mapping file: {mapping}")  # noqa
        LOGGER.warning(msg)

    return _SUCCESS_


def index_templates() -> bool:
    """
    Indexes the templates in the search path (TEMPLATE_DIRS) by id, into
    TEMPLATES. Directories are searched in order, and files in name order;
    when two files have the same id the first found is kept and a warning
    names both.

    :returns: `bool` of indexing result
    """
    for dir_ in TEMPLATE_DIRS:
        if not dir_.is_dir():
            LOGGER.warning(f"Template directory {dir_} not found, skipping")
            continue
        # sort the templates so order is repeatable (it can differ between FS)
        for template in sorted(dir_.iterdir()):
            try:
                if template.suffix == ".json":
                    # check if valid mapping file
                    with template.open() as fh:
                        tmpl = json.load(fh)
                    valid_schema = False
                    for sc in SCHEMA_VERSIONS:
                        if sc in tmpl.get("conformsTo", []):
                            valid_schema = True
                            break
                    if not valid_schema:
                        LOGGER.warning(
                            "No supported schema found in " +  # noqa
                            f"conformsTo for file {template}, skipping")  # noqa
                        continue

                    if validate_template(tmpl) == _SUCCESS_:
                        # get label if exists else set to empty string
                        fname = str(template)
                        id = tmpl['metadata'].get("id", "")
                        if not id:
                            LOGGER.warning(f"Template {fname} has no id, not indexed")  # noqa
                        elif id in TEMPLATES:
                            LOGGER.warning(f"Duplicate template id {id}: {fname} ignored, using {TEMPLATES[id]['path']}")  # noqa
                        else:
                            TEMPLATES[id] = {
                                "label": tmpl['metadata'].get("label", ""),
                                "description": tmpl['metadata'].get("description", ""),  # noqa
                                "version": tmpl['metadata'].get("version", ""),
                                "author": tmpl['metadata'].get("author", ""),
                                "dateCreated": tmpl['metadata'].get("dateCreated", ""),  # noqa
                                "id": tmpl['metadata'].get("id", ""),
                                "references": tmpl['metadata'].get("references", []),  # noqa
                                "history": tmpl['metadata'].get("history", []),  # noqa
                                "path": fname,
                                "name": Path(fname).stem
                            }

            except Exception as e:
                LOGGER.warning(f"Warning raised indexing csv2bufr templates: {e}, skipping file {template}.")  # noqa

    return _SUCCESS_


def list_templates() -> dict:
    """
    :returns: Dictionary of known templates in search path
              (CSV2BUFR_TEMPLATES), keyed by id. Each entry has the
              template's label, description, version, author, dateCreated,
              id, references and history (empty lists if not set), path and
              name (file name without extension). An empty dictionary is
              returned if no templates are found.
    """
    return TEMPLATES


if index_templates() != _SUCCESS_:
    LOGGER.error("Error indexing csv2bufr templates, see logs")
