"""Type-definitions for real-estate project"""

import json
from dagster import (
    Field,
    String,
    StringSource,
    Int,
    IntSource,
    DagsterType,
    usable_as_dagster_type
)

from dagster_aws.s3.ops import dict_with_fields

SearchCoordinate = dict_with_fields(
    "SearchCoordinate",
    fields={
        "propertyType": Field(
            StringSource,
            description="Type of the Property [house, flat, real-estate (flat and house), plot, parking-space, multi-family-residential, office-commerce-industry, agriculture, other-objects]",
        ),
        "rentOrBuy": Field(
            StringSource,
            description="Searching for rent or to buy",
        ),
        "radius": Field(
            IntSource,
            description="Searched radius",
        ),
        "city": Field(StringSource, "The city in you want to search for properties"),
    },
)

PropertyDataFrame = DagsterType(
    name="PropertyDataFrame",
    type_check_fn=lambda _, value: isinstance(value, list),
    description="A List with scraped Properties with id, last_normalized_price and search criterias which it was found.",
)

#################################################################################
# Delta Coordinate
#################################################################################

# Define the type check function
def delta_coordinate_type_check(_context, value):
    # Check if value is a dictionary
    if not isinstance(value, dict):
        return False

    # Check for required keys and types
    expected_fields = {
        "database": str,
        "table_name": str,
        "s3_coordinate_bucket": str,
        "s3_coordinate_key": str,
    }

    # Ensure all fields are present and of the correct type
    for field, field_type in expected_fields.items():
        if field not in value or not isinstance(value[field], field_type):
            return False

    return True


# Define the custom DagsterType
DeltaCoordinate = DagsterType(
    name="DeltaCoordinate",
    description="""A dictionary containing details about a delta coordinate, 
                   including 'database', 'table_name', 's3_coordinate_bucket', 
                   and 's3_coordinate_key'.""",
    type_check_fn=delta_coordinate_type_check,
)