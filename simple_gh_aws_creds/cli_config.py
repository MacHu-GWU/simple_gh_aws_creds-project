# -*- coding: utf-8 -*-

"""
Build a :class:`~simple_gh_aws_creds.impl.SetupGitHubRepo` for the command line
interface from a JSON config file, environment variables, and command line
overrides. ``cli.py`` only calls these functions, so the logic stays testable.

Secrets never come from the command line: the AWS credentials come from the
boto3 credential chain (optionally a named profile), and the GitHub token comes
from an environment variable whose *name* is passed in.
"""

import os
import json
from pathlib import Path

import boto3

from .impl import SetupGitHubRepo

#: Config keys that a command line argument may override. All are plain strings.
OVERRIDABLE_FIELDS = (
    "aws_region",
    "iam_user_name",
    "path_access_key_json",
    "github_user_name",
    "github_repo_name",
    "github_secret_name_aws_default_region",
    "github_secret_name_aws_access_key_id",
    "github_secret_name_aws_secret_access_key",
)

#: Every key the JSON config file may have.
CONFIG_FIELDS = OVERRIDABLE_FIELDS + (
    "tags",
    "policy_document",
    "attached_policy_arn_list",
)

#: Config keys that must be set, in the file or on the command line.
REQUIRED_FIELDS = (
    "aws_region",
    "iam_user_name",
    "policy_document",
    "path_access_key_json",
    "github_user_name",
    "github_repo_name",
)


def read_env_var(env_name: str) -> str:
    """
    Return the value of the environment variable ``env_name``.

    The error message names the variable and never shows a value.
    """
    value = os.environ.get(env_name, "")
    if not value:
        raise ValueError(f"Environment variable {env_name!r} is not set or empty.")
    return value


def load_config(path: str | Path) -> dict:
    """
    Load the JSON config file at ``path``.

    A relative ``path_access_key_json`` is resolved against the folder of the
    config file, not the current directory.
    """
    path = Path(path).expanduser().absolute()
    config = json.loads(path.read_text())
    if not isinstance(config, dict):
        raise ValueError(f"Config file {str(path)!r} must hold a JSON object.")
    unknown = sorted(set(config) - set(CONFIG_FIELDS))
    if unknown:
        raise ValueError(
            f"Unknown keys {unknown} in config file {str(path)!r}, "
            f"allowed keys: {list(CONFIG_FIELDS)}."
        )
    if "path_access_key_json" in config:
        p = Path(config["path_access_key_json"]).expanduser()
        if not p.is_absolute():
            p = path.parent / p
        config["path_access_key_json"] = p
    return config


def build_setup(
    config_path: str | Path,
    aws_profile: str | None = None,
    github_token_env_name: str = "GITHUB_TOKEN",
    need_github: bool = True,
    **overrides,
) -> SetupGitHubRepo:
    """
    Build a :class:`~simple_gh_aws_creds.impl.SetupGitHubRepo` from the config
    file at ``config_path``.

    :param aws_profile: AWS profile name; ``None`` uses the default boto3
        credential chain (environment variables, SSO, instance role, ...).
    :param github_token_env_name: name of the environment variable that holds
        the GitHub token.
    :param need_github: ``False`` for commands that never call GitHub; the
        token is then not read, so it does not need to be set.
    :param overrides: values that replace the config file's, only for the keys
        in :data:`OVERRIDABLE_FIELDS`. A relative ``path_access_key_json`` here
        is resolved against the current directory.
    """
    config = load_config(config_path)
    unknown = sorted(set(overrides) - set(OVERRIDABLE_FIELDS))
    if unknown:
        raise ValueError(
            f"Cannot override {unknown} on the command line, "
            f"overridable keys: {list(OVERRIDABLE_FIELDS)}."
        )
    for key, value in overrides.items():
        # python-fire parses "123" as an int, these are all strings
        config[key] = str(value)
    if "path_access_key_json" in overrides:
        config["path_access_key_json"] = (
            Path(config["path_access_key_json"]).expanduser().absolute()
        )
    missing = [key for key in REQUIRED_FIELDS if key not in config]
    if missing:
        raise ValueError(f"Missing required config keys: {missing}.")
    config.setdefault("tags", {})
    config.setdefault("attached_policy_arn_list", [])

    boto_ses = boto3.Session(
        profile_name=aws_profile or None,
        region_name=config["aws_region"],
    )
    github_token = read_env_var(github_token_env_name) if need_github else ""
    return SetupGitHubRepo(
        boto_ses=boto_ses,
        github_token=github_token,
        **config,
    )


def describe_teardown(setup: SetupGitHubRepo) -> str:
    """
    Describe what the teardown command deletes, shown when ``--yes`` is missing.
    """
    secret_names = ", ".join(
        [
            setup.github_secret_name_aws_default_region,
            setup.github_secret_name_aws_access_key_id,
            setup.github_secret_name_aws_secret_access_key,
        ]
    )
    return (
        f"teardown permanently deletes:\n"
        f"  - GitHub secrets {secret_names} of "
        f"{setup.github_user_name}/{setup.github_repo_name}\n"
        f"  - every access key and policy of IAM User {setup.iam_user_name!r}\n"
        f"  - IAM User {setup.iam_user_name!r}\n"
        f"Run it again with --yes to proceed."
    )


def describe_rotate_key(setup: SetupGitHubRepo) -> str:
    """
    Describe what the rotate_key command does, shown when ``--yes`` is missing.
    """
    return (
        f"rotate_key deletes every access key of IAM User {setup.iam_user_name!r}, "
        f"creates a new one, saves it to {str(setup.path_access_key_json)!r}, and "
        f"writes it to the GitHub secrets of "
        f"{setup.github_user_name}/{setup.github_repo_name}.\n"
        f"The old key stops working at once.\n"
        f"Run it again with --yes to proceed."
    )
