# Datashader Map Tiler
![alt text](images/ui_screenshot.png "Datashader Map Tiler")

Datashader Map Tiler is a Kivy-based Python application for rendering of large scale geospatial data using [Datashader](https://datashader.org/).

* Mode
    - Dynamic - Opens a browser tab and renders data live, allowing panning and zooming.
    - Static - Renders a TMS tileset to disk that can be hosted and used by web map frameworks such as Leaflet.
* Coordinate System
    - WGS84
    - Web Mercator
* File Format
    - CSV
    - Parquet - Either a single parquet file, or a directory of partitioned parquet data.
* Input Data
* Color Map - Linear Colormaps from [Colorcet](https://colorcet.holoviz.org/)
* Longitudinal Column - The column name for the longitude in the input data
* Latitudinal Column - The column name for the latitude in the input data
* Min Zoom - The minimum zoom level for the TMS tileset
* Max Zoom - The maximum zoom level for the TMS tileset
* Output Directory - The directory that Datashader Map Tiler will use for storing Static TMS tileset