# -*- coding: utf-8 -*-

from simple_gh_aws_creds.impl import SetupGitHubRepo

from simple_gh_aws_creds.tests.mock_aws import BaseMockAwsTest
from simple_gh_aws_creds.paths import dir_project_root


class TestSetupGitHubRepo(BaseMockAwsTest):
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
                # "arn:aws:iam::aws:policy/IAMReadOnlyAccess",
            ],
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
        setup.s13_create_or_get_access_key()

        setup.s22_delete_access_key()
        setup.s22_delete_access_key()
        setup.s23_delete_iam_policy()
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
