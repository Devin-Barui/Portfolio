import os
from dagster._core.storage.file_manager import LocalFileManager
from dagster_aws.s3 import S3Resource
from pandas.io.pytables import config

from .resources import boto3_connection
from dagster import LocalFileHandle, fs_io_manager, local_file_manager

from dagster_deltalake_pandas import (
    DeltaLakePandasIOManager,
    DeltaLakePandasTypeHandler,
)
from dagster_deltalake import S3Config

MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "minio")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "miniostorage")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://127.0.0.1:9000")

resource_def = {
    "local": {
        "s3": S3Resource(
            endpoint_url=MINIO_ENDPOINT,
        ),
        "boto3": boto3_connection,
        "fs_io_manager": fs_io_manager,
        "file_manager": LocalFileManager(base_dir="/tmp/dagster/file_cache"),
        "io_manager": DeltaLakePandasIOManager(
            root_uri="lake/bronze/",  # required
            storage_options=S3Config(
                bucket="real-estate",  # Usually this is defined in the table not as general
                access_key_id=MINIO_ACCESS_KEY,
                secret_access_key=MINIO_SECRET_KEY,
                endpoint=MINIO_ENDPOINT,
            ),
        ),
    },
}