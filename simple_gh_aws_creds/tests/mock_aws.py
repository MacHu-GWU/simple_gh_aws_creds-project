# -*- coding: utf-8 -*-

import typing as T
import dataclasses

import moto
import boto3
import botocore.exceptions
from boto_session_manager import BotoSesManager

if T.TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_s3.client import S3Client


@dataclasses.dataclass(frozen=True)
class MockAwsTestConfig:
    use_mock: bool = dataclasses.field()
    aws_region: str = dataclasses.field()
    prefix: str = dataclasses.field()
    aws_profile: T.Optional[str] = dataclasses.field(default=None)


class BaseMockAwsTest:
    use_mock: bool = True

    @classmethod
    def setup_mock(cls, mock_aws_test_config: MockAwsTestConfig):
        cls.mock_aws_test_config = mock_aws_test_config
        if mock_aws_test_config.use_mock:
            cls.mock_aws = moto.mock_aws()
            cls.mock_aws.start()

        if mock_aws_test_config.use_mock:
            cls.bsm: "BotoSesManager" = BotoSesManager(
                region_name=mock_aws_test_config.aws_region
            )
        else:
            cls.bsm: "BotoSesManager" = BotoSesManager(
                profile_name=mock_aws_test_config.aws_profile,
                region_name=mock_aws_test_config.aws_region,
            )
        cls.boto_ses: "boto3.Session" = cls.bsm.boto_ses

    @classmethod
    def setup_class(cls):
        mock_aws_test_config = MockAwsTestConfig(
            use_mock=cls.use_mock,
            aws_region="us-east-1",
            prefix="test",
            aws_profile="bmt_app_dev_us_east_1",  # Use default profile
        )
        cls.setup_mock(mock_aws_test_config)
        cls.setup_mock_post_process()

    @classmethod
    def setup_mock_post_process(cls):
        pass

    @classmethod
    def teardown_class(cls):
        if cls.mock_aws_test_config.use_mock:
            cls.mock_aws.stop()


class MyBaseMockAwsTest(BaseMockAwsTest):
    use_mock: bool = True

    @classmethod
    def setup_class(cls):
        mock_aws_test_config = MockAwsTestConfig(
            use_mock=cls.use_mock,
            aws_region="us-east-1",
            prefix="test",
            aws_profile="bmt_app_dev_us_east_1",  # Use default profile
        )
        cls.setup_mock(mock_aws_test_config)
