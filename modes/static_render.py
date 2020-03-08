import datashader as ds
from datashader import transfer_functions as tf
from datashader_tms.tiles_serial import render_tiles
from colorcet import cm

import warnings

warnings.simplefilter("ignore")


class StaticRenderer:
    data = None
    color_map = None
    min_zoom = 0
    max_zoom = 0
    output_path = None

    def __init__(self, data, color_map, min_zoom, max_zoom, output_path):
        self.data = data
        self.color_map = color_map
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom
        self.output_path = output_path

    def render_to_disk(self):
        for result in render_tiles(self._get_extents(),
                                   range(self.min_zoom, self.max_zoom + 1),
                                   load_data_func=self._load_data_func,
                                   rasterize_func=self._rasterize_func,
                                   shader_func=self._shader_func,
                                   post_render_func=self._post_render_func,
                                   output_path=self.output_path):
            print('Rendered {} supertiles for zoom level {} with span={} in {:.2f}s.'.format(result['supertile_count'],
                                                                                              result['level'],
                                                                                              result['stats'],
                                                                                              result['calc_stats_time'] +
                                                                                              result['render_time']))

    def _get_extents(self):
        return self.data.x.min(), self.data.y.min(), self.data.x.max(), self.data.y.max()

    def _load_data_func(self, x_range, y_range):
        return self.data.loc[self.data.x.between(*x_range) & self.data.y.between(*y_range)]

    def _rasterize_func(self, df, x_range, y_range, height, width):
        cvs = ds.Canvas(x_range=x_range, y_range=y_range,
                        plot_height=height, plot_width=width)
        agg = cvs.points(df, 'x', 'y')
        return agg

    def _shader_func(self, agg, span=None):
        img = tf.shade(agg, cmap=cm[self.color_map])
        return img

    def _post_render_func(self, img, **kwargs):
        return img
