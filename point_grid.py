#! /usr/bin/python
from osgeo import ogr, osr
import argparse
import sys
import os.path


def get_driver(input):
    """Returns correct driver for spatial data file

    Args:
        input (filepath): filepath of spatial data file with extension
    """
    extension = os.path.splitext(input)[1][1:]

    if extension == "shp":
        print("ESRI Shapefile detected")
        driver_name = "ESRI Shapefile"
    elif extension == "gpkg":
        print("GPKG detected")
        driver_name = "GPKG"
    elif extension == "GeoJSON":
        print("GeoJSON detected")
        driver_name = "GeoJSON"
    else:
        sys.exit("Unknown file type - please check input paramters")

    driver = ogr.GetDriverByName(driver_name)

    return driver


def roundup(value, rounded):
    return value if value % rounded == 0 else value + rounded - value % rounded


def main():

    parser = argparse.ArgumentParser(
        description="Fill polygon with regular point grid. Takes up to 4 arguments."
    )
    parser.add_argument("boundary_path", help="File path of boundary polygon")
    parser.add_argument("output_path", help="File path of output point grid")
    parser.add_argument(
        "-x",
        "--x_spacing",
        type=int,
        default=100,
        help="Set x grid spacing (m), default is 100",
    )
    parser.add_argument(
        "-y",
        "--y_spacing",
        type=int,
        default=100,
        help="Set y grid spacing (m), default is 100",
    )

    args = parser.parse_args()

    boundary_path = args.boundary_path
    out_path = args.output_path
    x_spacing = args.x_spacing
    y_spacing = args.y_spacing

    out_driver = get_driver(boundary_path)
    boundary_source = out_driver.Open(boundary_path)
    boundary_layer = boundary_source.GetLayer()
    feature = boundary_layer.GetNextFeature()

    input_srs = boundary_layer.GetSpatialRef()
    input_epsg = input_srs.GetAttrValue("AUTHORITY", 1)

    if not input_epsg == "27700":
        print("Invalid EPSG, this function is for EPSG:27700 only")

    out_driver = get_driver(out_path)

    if os.path.exists(out_path):
        out_driver.DeleteDataSource(out_path)

    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(27700)

    out_source = out_driver.CreateDataSource(out_path)
    out_layer = out_source.CreateLayer(
        "peat_depth_points", output_srs, geom_type=ogr.wkbPoint
    )

    field_name = ogr.FieldDefn("sample_id", ogr.OFTString)
    field_name.SetWidth(20)
    field_easting = ogr.FieldDefn("easting", ogr.OFTInteger)
    field_northing = ogr.FieldDefn("northing", ogr.OFTInteger)
    out_layer.CreateField(field_name)
    out_layer.CreateField(field_easting)
    out_layer.CreateField(field_northing)

    count = 1

    out_layer.StartTransaction()

    print(f"Creating {x_spacing}*{y_spacing} point grid")

    while feature:

        geom = feature.GetGeometryRef()
        (min_x, max_x, min_y, max_y) = geom.GetEnvelope()
        boundary_geom = feature.geometry()

        start_x = roundup(min_x, x_spacing)
        start_y = roundup(min_y, y_spacing)
        end_x = max_x
        end_y = max_y

        y = start_y

        while y < end_y:
            x = start_x
            while x < end_x:
                out_feature = ogr.Feature(out_layer.GetLayerDefn())
                point_wkt = f"POINT({x} {y})"
                point = ogr.CreateGeometryFromWkt(point_wkt)
                if point.Intersects(boundary_geom):
                    """put makepoint function here"""
                    out_feature.SetField("sample_id", f"PDS_{count}")
                    out_feature.SetField("easting", x)
                    out_feature.SetField("northing", y)
                    out_feature.SetGeometry(point)
                    out_layer.CreateFeature(out_feature)
                    count += 1
                x += x_spacing

            y += y_spacing

        feature = boundary_layer.GetNextFeature()

    out_layer.CommitTransaction()
    out_source = None


if __name__ == "__main__":
    main()
