import os

import multiprocessing

from datashader.utils import lnglat_to_meters
from static_render import StaticRenderer
from dynamic_render import DynamicRenderer
import pandas as pd


def _render(params):
    data = _load_data(params['file_format'], params['file_path'], params['coordinate_system'], params['longitude'],
                      params['latitude'])

    if params['mode'] == 'Static':
        static_renderer = StaticRenderer(data, params['color_map'], params['min_zoom'], params['max_zoom'],
                                         params['output_dir'])
        static_renderer.render_to_disk()
        exit(0)
    elif params['mode'] == 'Dynamic':
        dynamic_renderer = DynamicRenderer(data, params['color_map'])
        dynamic_renderer.render_to_browser()


def _load_data(file_format, file, coordinate_system, longitude, latitude):
    df = None

    if file_format == 'CSV':
        df = pd.read_csv(file, usecols=[longitude, latitude])
    elif file_format == 'Parquet':
        df = pd.read_parquet(file, columns=[longitude, latitude])

    if coordinate_system == 'WGS84':
        # EPSG3857 Coordinate System only supports Latitude bounds of -85.06 to 85.06
        df = df.loc[df[latitude].between(-85.06, 85.06)]
        # Convert to XY Coordinate System
        df['x'], df['y'] = lnglat_to_meters(df[longitude], df[latitude])
        df = df.drop(columns=[longitude, latitude], axis=1)
    elif coordinate_system == 'Web Mercator':
        df = df.rename(columns={longitude: 'x', latitude: 'y'})

    return df


if __name__ == '__main__':
    from kivy.config import Config

    Config.set('input', 'mouse', 'mouse,multitouch_on_demand')
    Config.set('graphics', 'resizable', False)

    from kivy.app import App
    from kivy.uix.button import Button
    from kivy.uix.label import Label
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.image import Image
    from kivy.uix.textinput import TextInput
    from kivy.uix.togglebutton import ToggleButton
    from kivy.uix.spinner import Spinner
    from kivy.uix.filechooser import FileChooserIconView
    from kivy.uix.popup import Popup
    from kivy.properties import StringProperty, NumericProperty
    from kivy.core.window import Window
    from kivy.clock import Clock
    from kivy.uix.progressbar import ProgressBar


    class DatashaderMapTiler(App):
        mode = 'Dynamic'
        coordinate_system = 'WGS84'
        file_format = 'CSV'
        file_path = None
        longitude = 'longitude'
        latitude = 'latitude'
        color_map = StringProperty(defaultvalue='fire')
        min_zoom = NumericProperty()
        max_zoom = NumericProperty()
        output_dir = StringProperty()
        app = FloatLayout(size=(500, 500))
        spn_min_zoom = None
        spn_max_zoom = None
        text_output_directory = None
        btn_browse_directory = None
        btn_render_button = None
        progress_bar = None
        render_thread = None

        def build(self):
            Window.bind(on_request_close=self.on_request_close)
            img_datashader = Image(source='datashader-logo.png', size_hint=(.75, .18), pos_hint={'x': .1, 'y': .82})
            img_0 = Image(source='osm_level_0.png',size_hint=(.35, .35), pos_hint={'x': .675, 'y': -0.1})
            self.app.add_widget(img_datashader)
            self.app.add_widget(img_0)
            self.build_mode_options()
            self.build_coordinate_system_options()
            self.build_file_format_options()
            self.build_file_selection_options()
            self.build_coordinate_column_options()
            self.build_colormap_options()
            self.build_optional_arguments()
            self.build_output_path_options()
            self.btn_render_button = Button(text='Render Tiles', size_hint=(.15, .05), pos_hint={'x': .4, 'y': .1})
            self.btn_render_button.bind(on_release=self.run_render)
            self.app.add_widget(self.btn_render_button)
            return self.app

        def build_mode_options(self):
            lbl_mode = Label(text='Mode:', size_hint=(.1, .05), pos_hint={'x': .08, 'y': .75})
            btn_mode_dynamic = ToggleButton(text='Dynamic', group='mode', state='down', size_hint=(.1, .05),
                                            pos_hint={'x': .16, 'y': .75})
            btn_mode_static = ToggleButton(text='Static', group='mode', size_hint=(.1, .05),
                                           pos_hint={'x': .26, 'y': .75})
            btn_mode_dynamic.bind(on_release=self.toggle_mode)
            btn_mode_static.bind(on_release=self.toggle_mode)
            self.app.add_widget(lbl_mode)
            self.app.add_widget(btn_mode_dynamic)
            self.app.add_widget(btn_mode_static)

        def build_coordinate_system_options(self):
            lbl_coordinate_system = Label(text='Coordinate System:', size_hint=(.1, .05), pos_hint={'x': .45, 'y': .75})
            btn_coordinate_system_wgs84 = ToggleButton(text='WGS84', group='coordinate_system', state='down',
                                                       size_hint=(.14, .05), pos_hint={'x': .59, 'y': .75})
            btn_coordinate_system_webmercator = ToggleButton(text='Web Mercator', group='coordinate_system',
                                                             size_hint=(.14, .05), pos_hint={'x': .73, 'y': .75})
            btn_coordinate_system_wgs84.bind(on_release=self.toggle_coordinate_system)
            btn_coordinate_system_webmercator.bind(on_release=self.toggle_coordinate_system)
            self.app.add_widget(lbl_coordinate_system)
            self.app.add_widget(btn_coordinate_system_wgs84)
            self.app.add_widget(btn_coordinate_system_webmercator)

        def build_file_format_options(self):
            spn_file_format = Spinner(text='File Format', values=('CSV', 'Parquet'), size_hint=(.15, .05),
                                      pos_hint={'x': .12, 'y': .65}, sync_height=True)
            spn_file_format.bind(text=self.select_file_format)
            self.app.add_widget(spn_file_format)

        def build_file_selection_options(self):
            lbl_file_path = Label(text='Input Data', size_hint=(.1, .05), pos_hint={'x': 0.5, 'y': .65})
            text_file_path = TextInput(text="", multiline=False, size_hint=(.5, .05), pos_hint={'x': .3, 'y': .6})
            text_file_path.bind(text=self.select_file_path)
            btn_file_dialog = Button(text='Browse', size_hint=(.09, .05), pos_hint={'x': .8, 'y': .6})
            btn_file_dialog.bind(on_release=lambda show_file_selection_dialog: file_chooser_dialog.open())
            self.app.add_widget(lbl_file_path)
            self.app.add_widget(text_file_path)
            self.app.add_widget(btn_file_dialog)
            file_chooser_dialog = Popup(title="Select File or Folder", size=(500, 500))
            file_chooser = FileChooserIconView()
            file_chooser.path = os.getcwd()
            file_chooser_layout = FloatLayout(size=(500, 500))
            file_chooser_layout.add_widget(file_chooser)
            file_chooser_dialog.add_widget(file_chooser_layout)
            btn_open_file = Button(text='Open', size_hint=(.1, .05), pos_hint={'x': .8, 'y': .01})
            btn_open_file.bind(
                on_release=lambda load_file: self.load_file(text_file_path, file_chooser_dialog, file_chooser.path,
                                                            file_chooser.selection))
            btn_cancel_file = Button(text='Cancel', size_hint=(.1, .05), pos_hint={'x': .9, 'y': .01})
            btn_cancel_file.bind(on_release=lambda cancel_file_selection_dialog: file_chooser_dialog.dismiss())
            file_chooser_layout.add_widget(btn_open_file)
            file_chooser_layout.add_widget(btn_cancel_file)

        def build_coordinate_column_options(self):
            lbl_longitude = Label(text='Longitudinal Column:', size_hint=(.2, .05), pos_hint={'x': 0.15, 'y': .45})
            text_longitude = TextInput(text="longitude", multiline=False, size_hint=(.15, .05),
                                       pos_hint={'x': .35, 'y': .45})
            text_longitude.bind(text=self.select_longitude_column)
            lbl_latitude = Label(text='Latitudinal Column:', size_hint=(.2, .05), pos_hint={'x': 0.5, 'y': .45})
            text_latitude = TextInput(text="latitude", multiline=False, size_hint=(.15, .05),
                                      pos_hint={'x': .69, 'y': .45})
            text_latitude.bind(text=self.select_latitude_column)
            self.app.add_widget(lbl_longitude)
            self.app.add_widget(lbl_latitude)
            self.app.add_widget(text_longitude)
            self.app.add_widget(text_latitude)

        def build_colormap_options(self):
            spn_color_map = Spinner(text='Color Map', values=('fire', 'bgy', 'bgyw', 'kbc', 'blues', 'bmw', 'bmy',
                                                              'kgy', 'gray', 'dimgray', 'kb', 'kg', 'kr'),
                                    size_hint=(.15, .05), pos_hint={'x': .12, 'y': .55}, sync_height=True)
            spn_color_map.bind(text=self.select_color_map)
            self.app.add_widget(spn_color_map)

        def build_optional_arguments(self):
            lbl_optional_arguments = Label(text='Static Render Arguments', size_hint=(.1, .05),
                                           pos_hint={'x': 0.4, 'y': .4})
            lbl_min_zoom = Label(text='Min Zoom:', size_hint=(.1, .05), pos_hint={'x': 0.11, 'y': .3})
            self.spn_min_zoom = Spinner(text='0', values=('0', '1', '2', '3', '4', '5', '6',
                                                          '7', '8', '9', '10', '11', '12'),
                                        size_hint=(.05, .05), pos_hint={'x': .21, 'y': .3}, sync_height=True)
            lbl_max_zoom = Label(text='Max Zoom:', size_hint=(.1, .05), pos_hint={'x': 0.11, 'y': .2})
            self.spn_max_zoom = Spinner(text='0', values=('0', '1', '2', '3', '4', '5', '6',
                                                          '7', '8', '9', '10', '11', '12'),
                                        size_hint=(.05, .05), pos_hint={'x': .21, 'y': .2}, sync_height=True)
            self.spn_min_zoom.disabled = True
            self.spn_max_zoom.disabled = True
            self.spn_min_zoom.bind(text=self.select_min_zoom)
            self.spn_max_zoom.bind(text=self.select_max_zoom)
            self.app.add_widget(lbl_optional_arguments)
            self.app.add_widget(lbl_min_zoom)
            self.app.add_widget(self.spn_min_zoom)
            self.app.add_widget(lbl_max_zoom)
            self.app.add_widget(self.spn_max_zoom)

        def build_output_path_options(self):
            lbl_file_path = Label(text='Output Directory', size_hint=(.1, .05), pos_hint={'x': 0.5, 'y': .3})
            self.text_output_directory = TextInput(text="", multiline=False, size_hint=(.5, .05),
                                                   pos_hint={'x': .3, 'y': .25})
            self.text_output_directory.bind(text=self.select_output_dir)
            self.text_output_directory.disabled = True
            self.btn_browse_directory = Button(text='Browse', size_hint=(.09, .05), pos_hint={'x': .8, 'y': .25})
            self.btn_browse_directory.disabled = True
            self.btn_browse_directory.bind(on_release=lambda show_file_selection_dialog: file_chooser_dialog.open())
            self.app.add_widget(lbl_file_path)
            self.app.add_widget(self.text_output_directory)
            self.app.add_widget(self.btn_browse_directory)
            file_chooser_dialog = Popup(title="Select Output Directory", size=(500, 500))
            file_chooser = FileChooserIconView()
            file_chooser.path = os.getcwd()
            file_chooser_layout = FloatLayout(size=(500, 500))
            file_chooser_layout.add_widget(file_chooser)
            file_chooser_dialog.add_widget(file_chooser_layout)
            btn_open_file = Button(text='Select Folder', size_hint=(.15, .05), pos_hint={'x': .75, 'y': .01})
            btn_open_file.bind(
                on_release=lambda load_file: self.select_directory(self.text_output_directory, file_chooser_dialog,
                                                                   file_chooser.path))
            btn_cancel_file = Button(text='Cancel', size_hint=(.1, .05), pos_hint={'x': .9, 'y': .01})
            btn_cancel_file.bind(on_release=lambda cancel_file_selection_dialog: file_chooser_dialog.dismiss())
            file_chooser_layout.add_widget(btn_open_file)
            file_chooser_layout.add_widget(btn_cancel_file)

        def load_file(self, text_file_path, file_chooser_dialog, file_path, file_name):
            if len(file_name) == 0:
                text_file_path.text = file_path
            else:
                text_file_path.text = os.path.join(file_path, file_name[0])
            file_chooser_dialog.dismiss()

        def select_directory(self, text_file_path, file_chooser_dialog, file_path):
            text_file_path.text = file_path
            file_chooser_dialog.dismiss()

        def toggle_mode(self, instance):
            print(instance.text)
            self.mode = instance.text

            if self.mode == 'Dynamic':
                self.spn_min_zoom.disabled = True
                self.spn_max_zoom.disabled = True
                self.btn_browse_directory.disabled = True
                self.text_output_directory.disabled = True
            else:
                self.spn_min_zoom.disabled = False
                self.spn_max_zoom.disabled = False
                self.btn_browse_directory.disabled = False
                self.text_output_directory.disabled = False

        def toggle_coordinate_system(self, instance):
            print(instance.text)
            self.coordinate_system = instance.text

        def select_file_format(self, spinner, text):
            print(text)
            self.file_format = text

        def select_file_path(self, instance, text):
            print(text)
            self.file_path = text

        def select_longitude_column(self, instance, text):
            print(text)
            self.longitude = text

        def select_latitude_column(self, instance, text):
            print(text)
            self.latitude = text

        def select_color_map(self, spinner, text):
            print(text)
            self.color_map = text

        def select_min_zoom(self, spinner, text):
            print(text)
            self.min_zoom = int(text)

        def select_max_zoom(self, spinner, text):
            print(text)
            self.max_zoom = int(text)

        def select_output_dir(self, instance, text):
            print(text)
            self.output_dir = text

        def on_request_close(self, *args):
            if self.render_thread is not None:
                self.render_thread.terminate()

        def loop_progress_bar(self, dt):
            if self.progress_bar.value == 100:
                self.progress_bar.value = 0
            else:
                self.progress_bar.value = self.progress_bar.value + 5

            if self.render_thread is not None and self.render_thread.exitcode is not None:
                exit(0)

        def run_render(self, instance):
            if not os.path.isfile(self.file_path) and self.file_format == 'CSV':
                popup = Popup(title='Error', content=Label(text='Must select a file.'), size_hint=(.7, .7),
                              auto_dismiss=True)
                popup.open()
            elif self.mode == 'Static' and self.min_zoom > self.max_zoom:
                popup = Popup(title='Error', content=Label(
                    text='Minimum zoom level must be less than or equal to maximum zoom level.'),
                              size_hint=(.7, .7), auto_dismiss=True)
                popup.open()
            else:
                self.btn_render_button.disabled = True

                params = {
                    'mode': self.mode,
                    'file_format': self.file_format,
                    'file_path': self.file_path,
                    'coordinate_system': self.coordinate_system,
                    'color_map': self.color_map,
                    'longitude': self.longitude,
                    'latitude': self.latitude,
                    'min_zoom': self.min_zoom,
                    'max_zoom': self.max_zoom,
                    'output_dir': self.output_dir
                }

                self.progress_bar = ProgressBar(max=100, value=0, size_hint=(.6, .9), pos_hint={'x': 0.5, 'y': 0.2})

                popup = Popup(title='Rendering...', content=self.progress_bar, size_hint=(.5, .2),
                              auto_dismiss=False)
                popup.open()

                Clock.schedule_interval(self.loop_progress_bar, 0.1)

                self.render_thread = multiprocessing.Process(target=_render, args=(params,))

                self.render_thread.start()






    DatashaderMapTiler().run()
