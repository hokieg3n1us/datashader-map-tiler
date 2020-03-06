import pandas as pd
import datashader as ds
from datashader import transfer_functions as tf
from datashader_tms.tiles_serial import render_tiles
from colorcet import cm

import warnings

warnings.simplefilter("ignore")


def _get_extents():
    return df.x.min(), df.y.min(), df.x.max(), df.y.max()


def _load_data_func(x_range, y_range):
    return df.loc[df.x.between(*x_range) & df.y.between(*y_range)]


def _rasterize_func(df, x_range, y_range, height, width):
    cvs = ds.Canvas(x_range=x_range, y_range=y_range,
                    plot_height=height, plot_width=width)
    agg = cvs.points(df, 'x', 'y')
    return agg


def _shader_func(agg, span=None):
    img = tf.shade(agg, cmap=cm['fire'])
    return img


def _post_render_func(img, **kwargs):
    return img


if __name__ == '__main__':
    output_path = 'C:/Users/hokie/Documents/Datashader/output_tiles/benchmark_'

    benchmark_results = open('tms_tiles_performance_fix.csv', 'w')

    df = pd.read_parquet('data/osm-50million.parq')

    #Write CSV Header
    print('{},{},{},{},{}'.format('level', 'super_tile_count', 'calc_stats_time', 'render_time', 'total_time'), file=benchmark_results)

    for n in range(10):
        for result in render_tiles(_get_extents(),
                                   range(0, 8),
                                   load_data_func=_load_data_func,
                                   rasterize_func=_rasterize_func,
                                   shader_func=_shader_func,
                                   post_render_func=_post_render_func,
                                   output_path=output_path + str(n)):
            print('{},{},{:.2f},{:.2f},{:.2f}'.format(result['level'], result['supertile_count'], result['calc_stats_time'], result['render_time'], result['calc_stats_time'] + result['render_time']),
                  file=benchmark_results, flush=True)

    benchmark_results.close()