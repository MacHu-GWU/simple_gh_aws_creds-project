# -*- coding: utf-8 -*-

if __name__ == "__main__":
    from simple_gh_aws_creds.tests import run_cov_test

    run_cov_test(
        __file__,
        "simple_gh_aws_creds",
        is_folder=True,
        preview=False,
    )
