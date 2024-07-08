from dagster import (
    Definitions,
    ScheduleDefinition,
    define_asset_job,
    load_assets_from_package_module,
)

from .pipelines import scrape_realestate, resource_def


# from dagster import Definitions, load_assets_from_modules

# from . import assets

# all_assets = load_assets_from_modules([assets])

# defs = Definitions(
#     assets=all_assets,
# )
