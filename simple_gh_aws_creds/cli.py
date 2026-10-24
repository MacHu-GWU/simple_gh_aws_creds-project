# -*- coding: utf-8 -*-

"""
Command line interface: ``simple-gh-aws-creds <command> --config <path> ...``.

Every command returns ``None``, so python-fire never prints a return value
(which could hold a secret). The logic lives in :mod:`.cli_config` and
:mod:`.impl`.
"""

from __future__ import annotations

import sys

import fire

from .cli_config import build_setup
from .cli_config import describe_teardown
from .cli_config import describe_rotate_key


class Command:
    """
    Set up AWS credentials for GitHub Actions.

    Every command takes ``--config`` (path to the JSON config file), an optional
    ``--aws_profile``, and overrides of plain config values such as
    ``--aws_region us-west-2``. The GitHub token is read from the environment
    variable named by ``--github_token_env_name`` (default ``GITHUB_TOKEN``).
    """

    def setup(
        self,
        config: str,
        aws_profile: str | None = None,
        github_token_env_name: str = "GITHUB_TOKEN",
        **overrides,
    ) -> None:
        """
        Create the IAM user, its policies and access key, and the GitHub secrets.
        Safe to run again: it also repairs a partial setup.
        """
        build_setup(
            config,
            aws_profile=aws_profile,
            github_token_env_name=github_token_env_name,
            **overrides,
        ).setup_all()

    def teardown(
        self,
        config: str,
        yes: bool = False,
        aws_profile: str | None = None,
        github_token_env_name: str = "GITHUB_TOKEN",
        **overrides,
    ) -> None:
        """
        Delete the GitHub secrets, the access keys, the policies, and the IAM
        user. Requires --yes.
        """
        if not yes:
            setup = build_setup(
                config,
                aws_profile=aws_profile,
                need_github=False,
                **overrides,
            )
            print(describe_teardown(setup))
            sys.exit(1)
        build_setup(
            config,
            aws_profile=aws_profile,
            github_token_env_name=github_token_env_name,
            **overrides,
        ).teardown_all()

    def update_policy(
        self,
        config: str,
        aws_profile: str | None = None,
        **overrides,
    ) -> None:
        """
        Make the IAM user's policies match the config file. The IAM user, the
        access key, and the GitHub secrets stay as they are. No GitHub token needed.
        """
        build_setup(
            config,
            aws_profile=aws_profile,
            need_github=False,
            **overrides,
        ).s12_put_iam_policy()

    def rotate_key(
        self,
        config: str,
        yes: bool = False,
        aws_profile: str | None = None,
        github_token_env_name: str = "GITHUB_TOKEN",
        **overrides,
    ) -> None:
        """
        Replace the IAM user's access key with a new one and update the GitHub
        secrets. Requires --yes.
        """
        if not yes:
            setup = build_setup(
                config,
                aws_profile=aws_profile,
                need_github=False,
                **overrides,
            )
            print(describe_rotate_key(setup))
            sys.exit(1)
        build_setup(
            config,
            aws_profile=aws_profile,
            github_token_env_name=github_token_env_name,
            **overrides,
        ).s31_rotate_access_key()


def main() -> None:
    """
    Entry point of the ``simple-gh-aws-creds`` command.
    """
    # an instance, so that --help lists the commands
    fire.Fire(Command())
