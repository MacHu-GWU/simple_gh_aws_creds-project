# -*- coding: utf-8 -*-

from simple_gh_aws_creds import api


def test():
    _ = api
    _ = api.SetupGitHubRepo


if __name__ == "__main__":
    from simple_gh_aws_creds.tests import run_cov_test

    run_cov_test(
        __file__,
        "simple_gh_aws_creds.api",
        preview=False,
    )
