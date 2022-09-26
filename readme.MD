# Point grid

Command line function to create regular point grids within boundary of input polygon

Uses osgeo.ogr library

Example syntax: ```python point_grid.py test_poly.shp output.gpkg```

Default x and y spacing values are 100, to set different values use `-x` and `-y` flags

Example syntax ```python point_grid.py test_poly.shp output.gpkg -x 50 -y 50```

