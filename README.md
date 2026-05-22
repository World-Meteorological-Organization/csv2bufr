# csv2bufr

The csv2bufr Python module contains both a command line interface and an API to convert data stored in a CSV file to the WMO BUFR data format.
More information on the BUFR format can be found in the [WMO Manual on Codes, Volume I.2](https://library.wmo.int/doc_num.php?explnum_id=10722).

## Installation

### Requirements
- Python 3 and above
- [ecCodes](https://confluence.ecmwf.int/display/ECC)

### Dependencies

Dependencies are listed in [requirements.txt](https://github.com/World-Meteorological-Organization/csv2bufr/blob/main/requirements.txt). Dependencies are automatically installed during csv2bufr installation.

```bash
docker pull wmoim/csv2bufr
```

## Running

Transform data from file `<my-csv-file.csv>` to BUFR using the mapping template
specified in `<csv-to-bufr-mapping.json>`. Write output files to `<output-directory-path>`.

```bash
csv2bufr data transform <my-csv-file.csv> \
    --bufr-template <csv-to-bufr-mapping.json> \
    --output-dir <output-directory-path>
```

## Releasing

```bash
# create release (x.y.z is the release version)
vi csv2bufr/__init__.py  # update __version__
git commit -am 'update release version vx.y.z'
git push origin main
git tag -a vx.y.z -m 'tagging release version vx.y.z'
git push --tags

# upload to PyPI
rm -fr build dist *.egg-info
python setup.py sdist bdist_wheel --universal
twine upload dist/*

# publish release on GitHub (https://github.com/World-Meteorological-Organization/csv2bufr/releases/new)

# bump version back to dev
vi csv2bufr/__init__.py  # update __version__
git commit -am 'back to dev'
git push origin main
```
## Documentation

The full documentation for csv2bufr can be found at [https://csv2bufr.readthedocs.io](https://csv2bufr.readthedocs.io), including sample files.

### Code Conventions

* [PEP8](https://www.python.org/dev/peps/pep-0008)

### Bugs and Issues

All bugs, enhancements and issues are managed on [GitHub](https://github.com/World-Meteorological-Organization/csv2bufr/issues).

## Contact

* [David Berry](https://github.com/david-i-berry)
