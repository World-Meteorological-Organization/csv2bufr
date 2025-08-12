# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))

import os
import re
import wmo_sphinx_theme

# -- Project information -----------------------------------------------------
project = 'csv2bufr'
author = 'World Meteorological Organization (WMO)'
license = 'This work is licensed under a Creative Commons Attribution 4.0 International License'  # noqa
copyright = '2021-2023, ' + author + ' ' + license

# The full version, including alpha/beta/rc tags

file_ = '../csv2bufr/__init__.py'
filepath = os.path.join(os.path.abspath('..'), file_)

with open(filepath) as fh:
    contents = fh.read().strip()

    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                              contents, re.M)
    if version_match:
        version = version_match.group(1)
    else:
        version = 'UNKNOWN'

release = version
# -- General configuration ---------------------------------------------------
master_doc = 'index'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.graphviz',
              'sphinx.ext.imgmath']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_theme = "wmo_sphinx_theme"
html_theme_path = wmo_sphinx_theme.get_html_theme_path()


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

html_css_files = [
    'wmo.css',  # overrides for wide tables in RTD theme
]

# options for maths
imgmath_image_format = 'svg'


# added configuration directives

today_fmt = '%Y-%m-%d'

html_sidebars = {
    '**': [
        'relations.html',  # needs 'show_related': True theme option to display
        'searchbox.html',
        'indexsidebar.html']
}

html_favicon = 'https://public.wmo.int/sites/all/themes/wmo/favicon.ico'
