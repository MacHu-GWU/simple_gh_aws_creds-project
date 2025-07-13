# -*- coding: utf-8 -*-

from pathlib import Path
from boto_session_manager import BotoSesManager
from home_secret.api import hs
from simple_gh_aws_creds.api import SetupGitHubRepo

aws_region = "us-east-1"
github_user_name = "MacHu-GWU"
github_repo_name = "simple_gh_aws_creds-project"

setup = SetupGitHubRepo(
    boto_ses=BotoSesManager(
        profile_name="bmt_app_dev_us_east_1",
        region_name=aws_region,
    ).boto_ses,
    aws_region=aws_region,
    iam_user_name="gh-ci-simple_gh_aws_creds",
    tags={
        "tech:use_case": "for GitHub Action to list Account aliases",
        "github_user_name": github_user_name,
        "github_repo_name": github_repo_name,
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
        "arn:aws:iam::aws:policy/IAMReadOnlyAccess",
    ],
    path_access_key_json=(
        Path(__file__).absolute().parent.joinpath("dev_access_key.json")
    ),
    github_user_name=github_user_name,
    github_repo_name=github_repo_name,
    github_token=hs.v("providers.github.accounts.sh.users.sh.secrets.dev.value"),
    github_secret_name_aws_default_region="DEV_ACC_AWS_REGION",
    github_secret_name_aws_access_key_id="DEV_ACC_AWS_ACCESS_KEY_ID",
    github_secret_name_aws_secret_access_key="DEV_ACC_AWS_SECRET_ACCESS_KEY",
)

if __name__ == "__main__":

    def setup_all():
        setup.s11_create_iam_user()
        setup.s12_put_iam_policy()
        setup.s13_create_or_get_access_key()
        setup.s14_setup_github_secrets()

    def teardown_all():
        setup.s21_delete_github_secrets()
        setup.s22_delete_access_key()
        setup.s23_delete_iam_policy()
        setup.s24_delete_iam_user()

    setup_all()
    # teardown_all()
