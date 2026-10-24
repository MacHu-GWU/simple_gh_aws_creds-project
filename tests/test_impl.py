# -*- coding: utf-8 -*-

from simple_gh_aws_creds.impl import mask_value
from simple_gh_aws_creds.impl import SetupGitHubRepo

import os
import json

import pytest
import botocore.exceptions

from simple_gh_aws_creds.tests.mock_aws import BaseMockAwsTest


class FakeRepo:
    """
    Stands in for the PyGithub repository, so no test calls GitHub.
    """

    def __init__(self):
        self.secrets = dict()

    def create_secret(self, secret_name, unencrypted_value, secret_type):
        self.secrets[secret_name] = unencrypted_value

    def delete_secret(self, secret_name):
        return self.secrets.pop(secret_name, None) is not None


class FailingRepo:
    """
    A repository whose every API call fails, like one reached with a bad token.
    """

    def create_secret(self, secret_name, unencrypted_value, secret_type):
        raise PermissionError("Bad credentials")

    def delete_secret(self, secret_name):
        raise PermissionError("Bad credentials")


def test_mask_value():
    assert mask_value("AKIAABCDEFGHIJKL") == "AKIA...IJKL"
    with pytest.raises(ValueError):
        mask_value("short")


class TestSetupGitHubRepo(BaseMockAwsTest):
    @classmethod
    def setup_mock_post_process(cls):
        # moto has no AWS managed policies, so create a customer managed one
        res = cls.bsm.iam_client.create_policy(
            PolicyName="TestIAMReadOnlyAccess",
            PolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": ["iam:Get*", "iam:List*"],
                            "Resource": "*",
                        }
                    ],
                }
            ),
        )
        cls.test_managed_policy_arn = res["Policy"]["Arn"]

    def make_setup(self, tmp_path, iam_user_name: str) -> SetupGitHubRepo:
        return SetupGitHubRepo(
            boto_ses=self.bsm.boto_ses,
            aws_region="us-east-1",
            iam_user_name=iam_user_name,
            tags={},
            policy_document={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["iam:ListAccountAliases"],
                        "Resource": "*",
                    },
                ],
            },
            attached_policy_arn_list=[],
            # a folder that does not exist yet: s13 must create it
            path_access_key_json=tmp_path / "secrets" / "access_key.json",
            github_user_name="MacHu-GWU",
            github_repo_name="simple_gh_aws_creds-project",
            github_token="github_token_here",
        )

    def test_edge_cases(self, tmp_path):
        setup = self.make_setup(tmp_path, "gh-ci-edge-cases")
        path_access_key_json = setup.path_access_key_json
        assert "gh-ci-edge-cases" in setup.iam_user_console_url
        assert "MacHu-GWU" in setup.github_secrets_url
        setup.print_github_workflow_example()

        setup.s11_create_iam_user()
        setup.s11_create_iam_user()  # user exists, no tags to sync
        setup.tags = {"github_repo_name": "simple_gh_aws_creds-project"}
        setup.s11_create_iam_user()  # user exists, tags synced
        tags = setup.iam_client.list_user_tags(UserName=setup.iam_user_name)["Tags"]
        assert tags == [
            {"Key": "github_repo_name", "Value": "simple_gh_aws_creds-project"}
        ]
        setup.s12_put_iam_policy()
        access_key, _ = setup.s13_create_or_get_access_key()
        if os.name == "posix":
            assert path_access_key_json.stat().st_mode & 0o777 == 0o600

        # hot update: remote policies are overwritten to match the config,
        # the user and its access key stay as they are
        iam = setup.iam_client
        iam.put_user_policy(
            UserName=setup.iam_user_name,
            PolicyName="manually-added-inline-policy",
            PolicyDocument=json.dumps(setup.policy_document),
        )
        iam.attach_user_policy(
            UserName=setup.iam_user_name,
            PolicyArn=self.test_managed_policy_arn,
        )
        setup.policy_document["Statement"][0]["Action"] = ["iam:ListUsers"]
        setup.s12_put_iam_policy()
        inline_names = iam.list_user_policies(UserName=setup.iam_user_name)[
            "PolicyNames"
        ]
        assert inline_names == [setup.policy_document_name]
        doc = iam.get_user_policy(
            UserName=setup.iam_user_name,
            PolicyName=setup.policy_document_name,
        )["PolicyDocument"]
        if isinstance(doc, str):
            doc = json.loads(doc)
        assert doc["Statement"][0]["Action"] == ["iam:ListUsers"]
        attached = iam.list_attached_user_policies(UserName=setup.iam_user_name)
        assert attached["AttachedPolicies"] == []

        setup.attached_policy_arn_list = [self.test_managed_policy_arn]
        setup.s12_put_iam_policy()
        setup.s12_put_iam_policy()  # already attached
        attached = iam.list_attached_user_policies(UserName=setup.iam_user_name)
        assert [dct["PolicyArn"] for dct in attached["AttachedPolicies"]] == [
            self.test_managed_policy_arn
        ]
        assert setup.s13_create_or_get_access_key()[0] == access_key

        # the local file is gone: the existing key cannot be reused
        path_access_key_json.unlink()
        with pytest.raises(RuntimeError):
            setup.s13_create_or_get_access_key()

        # the local file holds a key that no longer exists in AWS
        path_access_key_json.write_text(
            json.dumps({"access_key": "AKIA_STALE_KEY_0000", "secret_key": "x"})
        )
        with pytest.raises(RuntimeError):
            setup.s13_create_or_get_access_key()

        # a user still holding access keys cannot be deleted
        iam.create_access_key(UserName=setup.iam_user_name)
        with pytest.raises(botocore.exceptions.ClientError):
            setup.s24_delete_iam_user()

        # every access key is deleted, not only the first one
        setup.s22_delete_access_key()
        res = iam.list_access_keys(UserName=setup.iam_user_name)
        assert res["AccessKeyMetadata"] == []
        setup.s22_delete_access_key()  # no key left

        # an inline policy left over from an earlier aws_region must not block
        # the user deletion; the managed policy is detached too
        iam.put_user_policy(
            UserName=setup.iam_user_name,
            PolicyName=f"iam-user-us-west-2-{setup.iam_user_name}-inline-policy",
            PolicyDocument=json.dumps(setup.policy_document),
        )
        setup.s23_delete_iam_policy()
        assert iam.list_user_policies(UserName=setup.iam_user_name)["PolicyNames"] == []
        attached = iam.list_attached_user_policies(UserName=setup.iam_user_name)
        assert attached["AttachedPolicies"] == []
        setup.s23_delete_iam_policy()  # no policies left
        setup.s24_delete_iam_user()
        setup.s24_delete_iam_user()  # user gone

    def test_workflows(self, tmp_path):
        setup = self.make_setup(tmp_path, "gh-ci-workflows")
        path_access_key_json = setup.path_access_key_json
        repo = FakeRepo()
        setup.__dict__["repo"] = repo  # replace the cached_property
        iam = setup.iam_client

        # rotate needs an existing IAM user
        with pytest.raises(RuntimeError):
            setup.s31_rotate_access_key()

        setup.setup_all()
        setup.setup_all()  # idempotent
        old_key, old_secret = setup.s13_create_or_get_access_key(verbose=False)
        assert repo.secrets == {
            "AWS_DEFAULT_REGION": "us-east-1",
            "AWS_ACCESS_KEY_ID": old_key,
            "AWS_SECRET_ACCESS_KEY": old_secret,
        }

        # rotate: one new key, saved locally and written to GitHub
        setup.s31_rotate_access_key()
        keys = iam.list_access_keys(UserName=setup.iam_user_name)["AccessKeyMetadata"]
        assert len(keys) == 1
        new_key = keys[0]["AccessKeyId"]
        assert new_key != old_key
        data = json.loads(path_access_key_json.read_text())
        assert data["access_key"] == new_key
        assert repo.secrets["AWS_ACCESS_KEY_ID"] == new_key
        assert repo.secrets["AWS_SECRET_ACCESS_KEY"] == data["secret_key"]

        # rotate also recovers from a lost local file
        path_access_key_json.unlink()
        with pytest.raises(RuntimeError):
            setup.s13_create_or_get_access_key()
        setup.s31_rotate_access_key()
        assert setup.s13_create_or_get_access_key(verbose=False)[0] != new_key

        # a GitHub failure is raised, not swallowed
        setup.__dict__["repo"] = FailingRepo()
        with pytest.raises(PermissionError):
            setup.s14_setup_github_secrets()
        with pytest.raises(PermissionError):
            setup.s21_delete_github_secrets()
        setup.__dict__["repo"] = repo

        setup.teardown_all()
        setup.teardown_all()  # idempotent
        assert repo.secrets == {}
        with pytest.raises(botocore.exceptions.ClientError):
            iam.get_user(UserName=setup.iam_user_name)


if __name__ == "__main__":
    from simple_gh_aws_creds.tests import run_cov_test

    run_cov_test(
        __file__,
        "simple_gh_aws_creds.impl",
        preview=False,
    )
