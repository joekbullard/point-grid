#! /usr/bin/python
from osgeo import ogr, osr
import argparse
import sys
import os.path


def get_driver(input):
    """Returns correct driver for spatial data file

    Args:
        input (filepath): filepath of spatial data file with extension

    Return:
        driver (ogr.Driver()): File driver
    """
    extension = os.path.splitext(input)[1][1:]

    # Assign correct driver based on extension
    # TODO extend number of drivers
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


def roundup(value, rounded) -> int:
    """Rounds value up to nearest whole number.
    Used to ensure x/y start points fall inside boundary polygon

    Args:
        value (integer): input value to be rounded up
        rounded (integer): number to round value up to

    Returns:
        integer: rounded up value
    """
    return value if value % rounded == 0 else value + rounded - value % rounded


def main():

    # Argparse to define command line args
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

    # Assign args
    boundary_path = args.boundary_path
    out_path = args.output_path
    x_spacing = args.x_spacing
    y_spacing = args.y_spacing

    # Load boundary features
    boundary_driver = get_driver(boundary_path)
    boundary_source = boundary_driver.Open(boundary_path)
    boundary_layer = boundary_source.GetLayer()

    # Get initial feature
    feature = boundary_layer.GetNextFeature()

    # Get EPSG of boundary layer and check it's EPSG:27700
    input_srs = boundary_layer.GetSpatialRef()
    input_epsg = input_srs.GetAttrValue("AUTHORITY", 1)
    if not input_epsg == "27700":
        print("Invalid EPSG, this function is for EPSG:27700 only")

    # Load output file
    out_driver = get_driver(out_path)

    # If output file already exists then delete
    if os.path.exists(out_path):
        out_driver.DeleteDataSource(out_path)

    # Assign output EPSG:27700
    output_srs = osr.SpatialReference()
    output_srs.ImportFromEPSG(27700)

    # Create output layer
    out_source = out_driver.CreateDataSource(out_path)
    out_layer = out_source.CreateLayer(
        "regular_grid", output_srs, geom_type=ogr.wkbPoint
    )

    # Create fields
    field_name = ogr.FieldDefn("sample_id", ogr.OFTString)
    field_name.SetWidth(20)
    field_easting = ogr.FieldDefn("easting", ogr.OFTInteger)
    field_northing = ogr.FieldDefn("northing", ogr.OFTInteger)
    out_layer.CreateField(field_name)
    out_layer.CreateField(field_easting)
    out_layer.CreateField(field_northing)

    count = 1

    print(f"Creating {x_spacing}*{y_spacing} point grid")

    # Iterate over features
    while feature:
        # Start transaction - this results in better performance for gpkg
        out_layer.StartTransaction()
        # Get bounding box of polygon
        geom = feature.GetGeometryRef()
        (min_x, max_x, min_y, max_y) = geom.GetEnvelope()
        boundary_geom = feature.geometry()

        # Get start x/y points from boundary geom
        start_x = roundup(min_x, x_spacing)
        start_y = roundup(min_y, y_spacing)
        end_x = max_x
        end_y = max_y

        # Set starting y point
        y = start_y

        while y < end_y:
            # Nested loop to create features row by row
            x = start_x
            while x < end_x:
                # Create points
                out_feature = ogr.Feature(out_layer.GetLayerDefn())
                point_wkt = f"POINT({x} {y})"
                point = ogr.CreateGeometryFromWkt(point_wkt)
                if point.Intersects(boundary_geom):
                    # Test if point falls within polygon boundary
                    # If yes, create point, else skip to next point
                    out_feature.SetField("sample_id", f"PDS_{count}")
                    out_feature.SetField("easting", x)
                    out_feature.SetField("northing", y)
                    out_feature.SetGeometry(point)
                    out_layer.CreateFeature(out_feature)
                    count += 1

                # Add x spacing on to x distance ahead of next iteration
                x += x_spacing

            # Add y spacing on to y distance ahead of next iteration
            y += y_spacing

        # Commit transaction and iterate onto next feature
        # TODO check if this is faster than commiting at end of loop?
        out_layer.CommitTransaction()
        feature = boundary_layer.GetNextFeature()

    # Close source
    out_source = None


if __name__ == "__main__":
    main()
