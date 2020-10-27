import asyncio
from io import BytesIO
import warnings

from aiohttp import web
import aiohttp_cors
import xarray as xr
import pydeck as pdk
from ipywidgets import Output
from traitlets import HasTraits, Bool, observe
import ipyspin
import mercantile
from PIL import Image
import numpy as np
from rasterio.warp import Resampling
from affine import Affine


@xr.register_dataarray_accessor('xtrude')
class TerrainMap(HasTraits):
    """A xarray.DataArray extension for 3D terrain visualization, based on pydeck.
    """

    map_ready = Bool(False)

    @observe('map_ready')
    def _map_ready_changed(self, change):
        self._start()


    def __init__(self, da):
        self.da = da

    def plot(self,
             x_dim='x',
             y_dim='y',
             colormap=None,
             vmin=None,
             vmax=None,
             surface_url=None,
             debug_output=None):
        """Display a DEM array as a 3D interactive map.

        Returns
        -------
        l : terrain layer
            A handler to the terrain layer.
        """

        if debug_output is None:
            self.debug_output = Output()
        else:
            self.debug_output = debug_output

        with self.debug_output:
            self.s = ipyspin.Spinner()
            self.window_url = ''
            asyncio.ensure_future(self.async_wait_for_window_url())

            self.tile_width = 256
            self.factor = 10
            self.offset = 10000

            if (colormap is not None) and (surface_url is not None):
                raise ValueError(
                    "Cannot have a colormap and a "
                    "surface_url at the same time."
                )
            self.vmin = vmin
            self.vmax = vmax
            self.surface_url = surface_url
            self.colormap = colormap
            self.tiles = {}
            self.da = self.da.rename({y_dim: 'y', x_dim: 'x'})

            # ensure latitudes are descending
            if np.any(np.diff(self.da.y.values) >= 0):
                self.da = self.da.sel(y=slice(None, None, -1))

            # infer grid specifications (assume a rectangular grid)
            y = self.da.y.values
            x = self.da.x.values

            self.x_left = float(x.min())
            self.x_right = float(x.max())
            self.y_lower = float(y.min())
            self.y_upper = float(y.max())

            self.dx = float((self.x_right - self.x_left) / (x.size - 1))
            self.dy = float((self.y_upper - self.y_lower) / (y.size - 1))

            self.l = pdk.Layer("TerrainLayer", data=None, elevation_decoder=None, elevation_data=None, texture=None)

            return self.l


    def _start(self):
        with self.debug_output:
            if self.window_url.endswith('/lab'):
                # we are in JupyterLab
                self.base_url = self.window_url[:-4]
            else:
                if '/notebooks/' in self.window_url:
                    # we are in classical Notebook
                    i = self.window_url.rfind('/notebooks/')
                    self.base_url = self.window_url[:i]
                elif '/voila/' in self.window_url:
                    # we are in Voila
                    i = self.window_url.rfind('/voila/')
                    self.base_url = self.window_url[:i]
            if ':' in self.base_url:
                self.base_url = self.base_url[:self.base_url.rfind(':')]
            self.host = self.base_url[7:]  # remove http://
            self.start_server(8080, self.terrain_handler)
            if self.colormap is None:
                surface_url = self.surface_url
            else:
                self.start_server(8081, self.surface_handler)
                surface_url = self.base_url + ':8081/{z}/{x}/{y}.png'

            terrain_url = self.base_url + ':8080/{z}/{x}/{y}.png'
            elevation_decoder= {"rScaler": 65536 / self.factor, "gScaler": 256 / self.factor, "bScaler": 1 / self.factor, "offset": -self.offset}

            self.l.elevation_decoder = elevation_decoder
            self.l.elevation_data = terrain_url
            self.l.texture = surface_url


    async def surface_handler(self, request):
        with self.debug_output:
            z, x, y = str(request.url).split('/')[-3:]
            z = int(z)
            x = int(x)
            y = int(y[:-4])  # remove ".png"

            if self.vmin is None:
                self.vmin = self.da.min().values
            if self.vmax is None:
                self.vmax = self.da.max().values
            data = (self.get_tile(x, y, z) - self.vmin) / (self.vmax - self.vmin)
            rgb = self.colormap(data)[:, :, :3] * 255
            image = Image.fromarray(rgb.astype(np.uint8))
            with BytesIO() as f:
                image.save(f, format='PNG')
                return web.Response(body=f.getvalue(), status=200, content_type="image/png")

    async def terrain_handler(self, request):
        with self.debug_output:
            z, x, y = str(request.url).split('/')[-3:]
            z = int(z)
            x = int(x)
            y = int(y[:-4])  # remove ".png"

            data = self.get_tile(x, y, z)
            data = (data + self.offset) * self.factor
            rgb = np.empty((self.tile_width, self.tile_width, 3), dtype=np.uint8)
            rgb[:, :, 2] = data % 256
            rgb[:, :, 1] = (data // 256) % 256
            rgb[:, :, 0] = (data // (256 * 256)) % 256
            image = Image.fromarray(rgb)
            with BytesIO() as f:
                image.save(f, format='PNG')
                return web.Response(body=f.getvalue(), status=200, content_type="image/png")


    def start_server(self, port, handler):
        app = web.Application()

        cors = aiohttp_cors.setup(app)
        resource = cors.add(app.router.add_resource("/{z}/{x}/{y}.png"))
        cors.add(resource.add_route("GET", handler), {"*": aiohttp_cors.ResourceOptions(expose_headers="*", allow_headers="*")})

        asyncio.ensure_future(web._run_app(app, host=self.host, port=port))


    def get_tile(self, x, y, z):
        with self.debug_output:
            key = (x, y, z)
            if key not in self.tiles:
                tile = mercantile.Tile(x, y, z)
                bounds = mercantile.bounds(tile)
                xy_bounds = mercantile.xy_bounds(tile)
                x_pix = (xy_bounds.right - xy_bounds.left) / self.tile_width
                y_pix = (xy_bounds.top - xy_bounds.bottom) / self.tile_width
                da_tile = self.da.sel(y=slice(bounds.north + self.dy, bounds.south - self.dy), x=slice(bounds.west - self.dx, bounds.east + self.dx))
                da_tile = coarsen(da_tile, self.tile_width)
                data = reproject(da_tile, xy_bounds.left, xy_bounds.top, x_pix, y_pix, self.tile_width)
                self.tiles[key] = data
            return self.tiles[key]


    async def async_wait_for_window_url(self):
        with self.debug_output:
            if not self.s.window_url:
                await wait_for_change(self.s, 'window_url')
            self.window_url = str(self.s.window_url)
            #del self.s
            self.map_ready = True


def coarsen(array, tile_width):
    ny, nx = array.shape
    wx = nx // (tile_width * 2)
    wy = ny // (tile_width * 2)
    dim = {}
    if wx > 1:
        dim['x'] = wx
    if wy > 1:
        dim['y'] = wy
    try:
        c = array.coarsen(**dim, boundary='pad')
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            array = xr.core.rolling.DataArrayCoarsen.mean(c)
    except:
        pass
    return array


def reproject(source, x0, y0, x_res, y_res, tile_width):
    a = x_res
    b = 0
    c = x0
    d = 0
    e = -y_res
    f = y0
    dst_affine = Affine(a, b, c, d, e, f)
    destination = source.rio.reproject('EPSG:3857', transform=dst_affine, shape=(tile_width, tile_width), resampling=Resampling.bilinear)
    return destination.values


def wait_for_change(widget, value):
    future = asyncio.Future()
    def get_value(change):
        future.set_result(change.new)
        widget.unobserve(get_value, value)
    widget.observe(get_value, value)
    return future
