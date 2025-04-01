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
import os.path

import click

from csv2bufr import __version__, BUFRMessage, transform as transform_csv
import csv2bufr.templates as c2bt

THISDIR = os.path.dirname(os.path.realpath(__file__))
MAPPINGS = f"{THISDIR}{os.sep}resources{os.sep}mappings"

# configure logging
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.DEBUG)


def cli_option_verbosity(f):
    logging_options = ["ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"]

    def callback(ctx, param, value):
        if value is not None:
            LOGGER.setLevel(getattr(logging, value))
        return True

    return click.option("--verbosity", "-v",
                        type=click.Choice(logging_options),
                        help="Verbosity",
                        callback=callback)(f)


def cli_callbacks(f):
    f = cli_option_verbosity(f)
    return f


@click.group()
@click.version_option(version=__version__)
def cli():
    """csv2bufr"""
    pass


@click.group()
def data():
    """data workflows"""
    pass


@click.group()
def mappings():
    """stored mappings"""
    pass


@click.command('list')
@click.pass_context
def list_mappings(ctx):
    templates = c2bt.list_templates()
    for tmpl in templates.items():
        click.echo(json.dumps(tmpl, indent=4))


@click.command('create')
@click.pass_context
@click.argument("sequence", nargs=-1, type=int)
@click.option("--output", "output", help="File to save the template to")
@cli_option_verbosity
def create_mappings(ctx, sequence, output, verbosity):
    msg = BUFRMessage(sequence)
    template = msg.create_template()
    if output:
        with open(output, "w") as fh:
            fh.write(json.dumps(template, indent=4))
    else:
        print(json.dumps(template, indent=4))


@click.command()
@click.pass_context
@click.argument("csv_file", type=click.File(errors="ignore"))
@click.option("--bufr-template", "mapping", required=True,
              help="Name of file or mapping template to use to map from CSV to BUFR")  # noqa
@click.option("--output-dir", "output_dir", required=False,
              help="Name of output file", default='.')
@cli_option_verbosity
def transform(ctx, csv_file, mapping, output_dir, verbosity):  # noqa
    result = None
    click.echo(f"\nCLI:\t... Transforming {csv_file.name} to BUFR ...")

    # load / identify mapping to use
    if not os.path.isfile(mapping):
        try:
            mappings = c2bt.load_template(mapping)
            if mappings is None:
                raise click.ClickException(
                    f"Error loading mappings {mapping}")
        except Exception as err:
            raise click.ClickException(err)
    else:
        try:
            mappings = c2bt.load_template(mapping, isFile=True)
        except Exception as err:
            raise click.ClickException(err)

    try:
        result = transform_csv(csv_file.read(), mappings)
    except Exception as err:
        raise click.ClickException(err)

    click.echo("CLI:\t... Processing subsets:")
    try:
        for item in result:
            key = item['_meta']["id"]
            bufr_filename = f"{output_dir}{os.sep}{key}.bufr4"
            if item['bufr4'] is not None:
                with open(bufr_filename, "wb") as fh:
                    fh.write(item["bufr4"])
                    nbytes = fh.tell()
                click.echo(f"CLI:\t..... {nbytes} bytes written to {bufr_filename}")  # noqa
            else:
                click.echo("CLI:\t..... 'None' found in BUFR output, no data written")  # noqa
    except Exception as err:
        raise click.ClickException(err)
    click.echo("CLI:\tEnd of processing, exiting.\n")


data.add_command(transform)
mappings.add_command(list_mappings)
mappings.add_command(create_mappings)

cli.add_command(data)
cli.add_command(mappings)
