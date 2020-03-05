from gooey import Gooey, GooeyParser
from datashader.utils import lnglat_to_meters
from static_render import StaticRenderer
from dynamic_render import DynamicRenderer
import pandas as pd

import warnings

warnings.simplefilter("ignore")


@Gooey(program_name='Datashader MapTiler',
       default_size=(700, 750), disable_progress_bar_animation=True)
def main():
    parser = GooeyParser()
    parser.add_argument('mode',
                        choices=['Dynamic', 'Static'], help='Render Mode:')
    parser.add_argument('file_format', choices=['CSV', 'Parquet'], help='File Format:')
    parser.add_argument("file", help="File:", widget="FileChooser")
    parser.add_argument('longitude', default='longitude', type=str,
                        help='Column name containing longitude (in WGS84 format).')
    parser.add_argument('latitude', default='latitude', type=str,
                        help='Column name containing latitude (in WGS84 format).')
    parser.add_argument('color_map',
                        choices=['fire', 'bgy', 'bgyw', 'kbc', 'blues', 'bmw', 'bmy', 'kgy', 'gray', 'dimgray', 'kb',
                                 'kg', 'kr'], help='Colormap:')
    parser.add_argument('--min_zoom', type=int, default=0, help='Minimum zoom level for static tile set.',
                        choices=range(0, 15))
    parser.add_argument('--max_zoom', type=int, default=0, help='Maximum zoom level for static tile set.',
                        choices=range(0, 15))
    parser.add_argument("--output_path", help="Output directory for static tile set.", widget="DirChooser")

    args = parser.parse_args()

    if args.min_zoom > args.max_zoom:
        print("Minimum zoom level must be less than or equal to maximum zoom level.")
        exit(-1)

    data = _load_data(args.file_format, args.file, args.longitude, args.latitude)

    if args.mode == 'Static':
        static_renderer = StaticRenderer(data, args.color_map, args.min_zoom, args.max_zoom, args.output_path)
        static_renderer.render_to_disk()
        exit(0)
    elif args.mode == 'Dynamic':
        dynamic_renderer = DynamicRenderer(data, args.color_map)
        dynamic_renderer.render_to_browser()


def _load_data(file_format, file, longitude, latitude):
    df = None

    if file_format == 'CSV':
        df = pd.read_csv(file, usecols=[longitude, latitude])
    elif file_format == 'Parquet':
        df = pd.read_parquet(file, columns=[longitude, latitude])

    # EPSG3857 Coordinate System only supports Latitude bounds of -85.06 to 85.06
    df = df.loc[df[latitude].between(-85.06, 85.06)]

    # Convert to XY Coordinate System
    df['x'], df['y'] = lnglat_to_meters(df[longitude], df[latitude])

    df = df.drop(columns=[longitude, latitude], axis=1)

    return df


if __name__ == '__main__':
    main()
