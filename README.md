[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/davidbrochart/xtrude/master?filepath=examples%2Fintroduction.ipynb)

# xtrude: an xarray extension for 3D terrain visualization

xtrude aims to be a 3D equivalent to [xarray-leaflet](https://github.com/davidbrochart/xarray_leaflet). It uses [xarray](http://xarray.pydata.org) to generate PNG-encoded elevation tiles from a DEM `DataArray`, on the fly as they are requested by [deck.gl](https://deck.gl), which renders them in 3D using WebGL in the browser.

## Installation

Using conda:

```bash
conda install -c conda-forge xtrude
```

Using pip:

```bash
pip install xtrude
