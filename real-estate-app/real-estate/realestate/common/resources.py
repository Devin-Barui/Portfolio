from dagster import resource, Field

from boto3 import session

class Boto3Connector(object):
    def __init__(self, aws_access_key_id, aws_secret_access_key, endpoint_url):
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.endpoint_url = endpoint_url

    # def get_session(self):

    #     session = session.Session()
    #     return session

    def get_client(self):
        session = session.Session()

        s3_client = session.client(
            service_name="s3",
            aws_access_key_id=self.aws_access_key_id,
            aws_secret_access_key=self.aws_secret_access_key,
            endpoint_url=self.endpoint_url,
        )
        return s3_client


@resource(
    config_schema={
        "aws_access_key_id": Field(str),
        "aws_secret_access_key": Field(str),
        "endpoint_url": Field(str),
    }
)
def boto3_connection(context):
    return Boto3Connector(
        context.resource_config["aws_access_key_id"],
        context.resource_config["aws_secret_access_key"],
        context.resource_config["endpoint_url"],
    )
