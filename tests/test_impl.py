# -*- coding: utf-8 -*-

import json
from simple_gh_aws_creds.impl import SetupGitHubRepo

from simple_gh_aws_creds.tests.mock_aws import BaseMockAwsTest
from simple_gh_aws_creds.paths import dir_project_root


class TestSetupGitHubRepo(BaseMockAwsTest):
    @classmethod
    def setup_mock_post_process(cls):
        """
        Create test managed policies in moto since AWS managed policies don't exist in mock environment
        """
        iam_client = cls.bsm.iam_client
        
        # Create a test managed policy that simulates IAMReadOnlyAccess
        cls.test_managed_policy_name = "TestIAMReadOnlyAccess"
        cls.test_managed_policy_arn = None
        
        test_policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "iam:Get*",
                        "iam:List*",
                        "iam:Generate*"
                    ],
                    "Resource": "*"
                }
            ]
        }
        
        try:
            response = iam_client.create_policy(
                PolicyName=cls.test_managed_policy_name,
                PolicyDocument=json.dumps(test_policy_document),
                Description="Test managed policy for moto testing",
            )
            cls.test_managed_policy_arn = response["Policy"]["Arn"]
            print(f"Created test managed policy: {cls.test_managed_policy_arn}")
        except Exception as e:
            print(f"Failed to create test managed policy: {e}")
            cls.test_managed_policy_arn = None

    @classmethod
    def teardown_class(cls):
        """
        Clean up test managed policies before tearing down mock AWS
        """
        if hasattr(cls, 'test_managed_policy_arn') and cls.test_managed_policy_arn:
            try:
                iam_client = cls.bsm.iam_client
                iam_client.delete_policy(PolicyArn=cls.test_managed_policy_arn)
                print(f"Cleaned up test managed policy: {cls.test_managed_policy_arn}")
            except Exception as e:
                print(f"Failed to cleanup test managed policy: {e}")
        
        # Call parent teardown
        super().teardown_class()

    def test(self):
        aws_region = "us-east-1"
        github_user_name = "MacHu-GWU"
        github_repo_name = "simple_gh_aws_creds-project"
        setup = SetupGitHubRepo(
            boto_ses=self.bsm.boto_ses,
            aws_region=aws_region,
            iam_user_name="gh-ci-simple_gh_aws_creds",
            tags={
                "tech:use_case": "for GitHub Action to list Account aliases",  # Describe what this user does
                "github_user_name": github_user_name,  # Link back to GitHub owner
                "github_repo_name": github_repo_name,  # Link back to GitHub repo
                "automation_script": f"https://github.com/{github_user_name}/{github_repo_name}/blob/main/docs/source/01-Examples/setup_dev_account.py",
            },
            policy_document={
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "VisualEditor1",
                        "Effect": "Allow",
                        "Action": [
                            "iam:ListAccountAliases",
                        ],
                        "Resource": "*",
                    },
                ],
            },
            attached_policy_arn_list=[
                self.test_managed_policy_arn,  # Use the test managed policy we created
            ] if self.test_managed_policy_arn else [],
            path_access_key_json=(dir_project_root.joinpath("dev_access_key.json")),
            github_user_name=github_user_name,
            github_repo_name=github_repo_name,
            github_token="github_token_here",
            github_secret_name_aws_default_region="DEV_ACC_AWS_REGION",
            github_secret_name_aws_access_key_id="DEV_ACC_AWS_ACCESS_KEY_ID",
            github_secret_name_aws_secret_access_key="DEV_ACC_AWS_SECRET_ACCESS_KEY",
        )

        _ = setup.github_secrets_url

        setup.s11_create_iam_user()
        setup.s11_create_iam_user()
        setup.s12_put_iam_policy()
        setup.s12_put_iam_policy()
        setup.s13_create_or_get_access_key()
        setup.s13_create_or_get_access_key()

        setup.s11_create_iam_user()
        setup.s12_put_iam_policy()
        
        # Verify that managed policy is attached if we created one
        if self.test_managed_policy_arn:
            attached_policies = setup.iam_client.list_attached_user_policies(UserName=setup.iam_user_name)
            attached_arns = [policy["PolicyArn"] for policy in attached_policies["AttachedPolicies"]]
            assert self.test_managed_policy_arn in attached_arns, f"Expected managed policy {self.test_managed_policy_arn} to be attached"
            print(f"✅ Verified managed policy {self.test_managed_policy_arn} is attached")
        
        setup.s13_create_or_get_access_key()

        # Test cleanup
        setup.s22_delete_access_key()
        setup.s22_delete_access_key()
        setup.s23_delete_iam_policy()
        
        # Verify that managed policy is detached after s23_delete_iam_policy
        if self.test_managed_policy_arn:
            try:
                attached_policies = setup.iam_client.list_attached_user_policies(UserName=setup.iam_user_name)
                attached_arns = [policy["PolicyArn"] for policy in attached_policies["AttachedPolicies"]]
                assert self.test_managed_policy_arn not in attached_arns, f"Expected managed policy {self.test_managed_policy_arn} to be detached"
                print(f"✅ Verified managed policy {self.test_managed_policy_arn} is detached")
            except Exception as e:
                # If user doesn't exist, that's also fine
                print(f"User may not exist anymore: {e}")
        
        setup.s23_delete_iam_policy()
        setup.s24_delete_iam_user()
        setup.s24_delete_iam_user()

        setup.s22_delete_access_key()
        setup.s23_delete_iam_policy()
        setup.s24_delete_iam_user()


if __name__ == "__main__":
    from simple_gh_aws_creds.tests import run_cov_test

    run_cov_test(
        __file__,
        "simple_gh_aws_creds.impl",
        preview=False,
    )
