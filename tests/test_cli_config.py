# -*- coding: utf-8 -*-

from simple_gh_aws_creds.cli_config import read_env_var
from simple_gh_aws_creds.cli_config import load_config
from simple_gh_aws_creds.cli_config import build_setup
from simple_gh_aws_creds.cli_config import describe_teardown
from simple_gh_aws_creds.cli_config import describe_rotate_key

import json

import pytest

ENV_NAME = "SIMPLE_GH_AWS_CREDS_TEST_TOKEN"
TOKEN_VALUE = "ghp_test_value_never_shown"

CONFIG = {
    "aws_region": "us-east-1",
    "iam_user_name": "gh-ci-test",
    "policy_document": {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["iam:ListAccountAliases"],
                "Resource": "*",
            },
        ],
    },
    "path_access_key_json": "dev_access_key.json",
    "github_user_name": "MacHu-GWU",
    "github_repo_name": "simple_gh_aws_creds-project",
}


def write_config(tmp_path, config, name="config.json"):
    path = tmp_path / name
    path.write_text(json.dumps(config))
    return path


def test_read_env_var(monkeypatch):
    monkeypatch.setenv(ENV_NAME, TOKEN_VALUE)
    assert read_env_var(ENV_NAME) == TOKEN_VALUE

    monkeypatch.setenv(ENV_NAME, "")
    with pytest.raises(ValueError) as e:
        read_env_var(ENV_NAME)
    assert ENV_NAME in str(e.value)

    monkeypatch.delenv(ENV_NAME)
    with pytest.raises(ValueError):
        read_env_var(ENV_NAME)


def test_load_config(tmp_path):
    # a relative path_access_key_json is resolved against the config folder
    config = load_config(write_config(tmp_path, CONFIG))
    assert config["path_access_key_json"] == tmp_path / "dev_access_key.json"

    # an absolute one is kept
    absolute = tmp_path / "elsewhere" / "key.json"
    config = load_config(
        write_config(tmp_path, {**CONFIG, "path_access_key_json": str(absolute)})
    )
    assert config["path_access_key_json"] == absolute

    with pytest.raises(ValueError):
        load_config(write_config(tmp_path, {**CONFIG, "unknown_key": 1}))
    with pytest.raises(ValueError):
        load_config(write_config(tmp_path, [CONFIG]))


def test_build_setup(tmp_path, monkeypatch):
    path = write_config(tmp_path, CONFIG)
    monkeypatch.setenv(ENV_NAME, TOKEN_VALUE)

    setup = build_setup(path, github_token_env_name=ENV_NAME)
    assert setup.github_token == TOKEN_VALUE
    assert setup.tags == {}
    assert setup.attached_policy_arn_list == []
    assert setup.boto_ses.region_name == "us-east-1"
    assert setup.github_secret_name_aws_access_key_id == "AWS_ACCESS_KEY_ID"

    # overrides win, and python-fire's ints become strings
    monkeypatch.chdir(tmp_path)
    setup = build_setup(
        path,
        github_token_env_name=ENV_NAME,
        aws_region="us-west-2",
        github_repo_name=123,
        path_access_key_json="override.json",
    )
    assert setup.aws_region == "us-west-2"
    assert setup.boto_ses.region_name == "us-west-2"
    assert setup.github_repo_name == "123"
    assert setup.path_access_key_json == tmp_path / "override.json"

    # complex values and unknown keys cannot be overridden
    with pytest.raises(ValueError):
        build_setup(path, github_token_env_name=ENV_NAME, tags="{}")
    with pytest.raises(ValueError):
        build_setup(path, github_token_env_name=ENV_NAME, not_a_field="x")

    # missing required keys
    config = dict(CONFIG)
    del config["iam_user_name"]
    with pytest.raises(ValueError):
        build_setup(
            write_config(tmp_path, config, "missing.json"),
            github_token_env_name=ENV_NAME,
        )

    # the token is required unless the command never calls GitHub
    monkeypatch.delenv(ENV_NAME)
    with pytest.raises(ValueError) as e:
        build_setup(path, github_token_env_name=ENV_NAME)
    assert TOKEN_VALUE not in str(e.value)
    setup = build_setup(path, github_token_env_name=ENV_NAME, need_github=False)
    assert setup.github_token == ""


def test_describe(tmp_path):
    setup = build_setup(write_config(tmp_path, CONFIG), need_github=False)
    text = describe_teardown(setup)
    assert "gh-ci-test" in text
    assert "AWS_SECRET_ACCESS_KEY" in text
    assert "--yes" in text
    text = describe_rotate_key(setup)
    assert "gh-ci-test" in text
    assert "--yes" in text


if __name__ == "__main__":
    from simple_gh_aws_creds.tests import run_cov_test

    run_cov_test(
        __file__,
        "simple_gh_aws_creds.cli_config",
        preview=False,
    )
