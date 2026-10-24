# -*- coding: utf-8 -*-

"""
Base class for tests that run against moto, an in-memory mock of AWS.
"""

from __future__ import annotations

import dataclasses

import moto
import boto3
from boto_session_manager.api import BotoSesManager


@dataclasses.dataclass(frozen=True)
class MockAwsTestConfig:
    """
    How a test class talks to AWS.
    """

    # fmt: off
    use_mock: bool = dataclasses.field()  #: ``True`` runs against moto; ``False`` against a real account.
    aws_region: str = dataclasses.field()  #: Region of the boto3 session.
    aws_profile: str | None = dataclasses.field(default=None)  #: AWS profile, used only when ``use_mock`` is ``False``.
    # fmt: on


class BaseMockAwsTest:
    """
    Start moto before the tests of a class and stop it after. Subclasses add
    their fixtures in :meth:`setup_mock_post_process`.
    """

    use_mock: bool = True

    @classmethod
    def setup_mock(cls, mock_aws_test_config: MockAwsTestConfig) -> None:
        cls.mock_aws_test_config = mock_aws_test_config
        if mock_aws_test_config.use_mock:
            cls.mock_aws = moto.mock_aws()
            cls.mock_aws.start()
            cls.bsm = BotoSesManager(region_name=mock_aws_test_config.aws_region)
        else:
            cls.bsm = BotoSesManager(
                profile_name=mock_aws_test_config.aws_profile,
                region_name=mock_aws_test_config.aws_region,
            )
        cls.boto_ses: boto3.Session = cls.bsm.boto_ses

    @classmethod
    def setup_class(cls) -> None:
        mock_aws_test_config = MockAwsTestConfig(
            use_mock=cls.use_mock,
            aws_region="us-east-1",
        )
        cls.setup_mock(mock_aws_test_config)
        cls.setup_mock_post_process()

    @classmethod
    def setup_mock_post_process(cls) -> None:
        pass

    @classmethod
    def teardown_class(cls) -> None:
        if cls.mock_aws_test_config.use_mock:
            cls.mock_aws.stop()
