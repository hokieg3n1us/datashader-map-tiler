import warnings

import holoviews as hv
import panel as pn
from colorcet import cm
from holoviews.element.tiles import CartoDark
from holoviews.operation.datashader import rasterize, shade

warnings.simplefilter("ignore")

hv.extension('bokeh', logo=False)


class DynamicRenderer():
    data = None
    color_map = None
    opts = dict(width=1200, height=800, xaxis=None, yaxis=None, bgcolor='black', show_grid=False)

    def __init__(self, data, color_map, **params):
        self.data = data
        self.color_map = color_map

    def render_to_browser(self, **kwargs):
        points = hv.DynamicMap(hv.Points(self.data, kdims=['x', 'y']))
        tiles = CartoDark().apply.opts(**self.opts)
        agg = rasterize(points, width=1200, height=800)
        pn.serve(pn.Row(tiles * shade(agg, cmap=cm[self.color_map])), title='Datashader MapTiler')
