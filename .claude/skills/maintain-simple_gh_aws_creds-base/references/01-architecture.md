---
description: "The modules of simple_gh_aws_creds and what each one owns: SetupGitHubRepo and its numbered steps in impl.py, the thin python-fire CLI in cli.py, and the config loading in cli_config.py. Read before changing any module, to know where a change belongs."
---

# Architecture

---

## 1. Modules

| File | Owns |
| :--- | :--- |
| `simple_gh_aws_creds/impl.py` | `SetupGitHubRepo`, a dataclass that does all AWS (boto3 IAM) and GitHub (PyGithub) work, and the helper `mask_value()` |
| `simple_gh_aws_creds/cli_config.py` | Everything the CLI needs besides argument parsing: `load_config()`, `build_setup()`, `read_env_var()`, `describe_teardown()`, `describe_rotate_key()`, and the key lists `OVERRIDABLE_FIELDS`, `CONFIG_FIELDS`, `REQUIRED_FIELDS` |
| `simple_gh_aws_creds/cli.py` | `class Command` with four methods (`setup`, `teardown`, `update_policy`, `rotate_key`) and `main()`, which runs `fire.Fire(Command())`. Registered as `simple-gh-aws-creds` in `[project.scripts]` |
| `simple_gh_aws_creds/api.py` | The public API: only `SetupGitHubRepo` |

`cli.py` is excluded from coverage (`.coveragerc`), so it holds no logic: each `Command` method builds a `SetupGitHubRepo` with `build_setup()` and calls one method on it. Logic that the CLI needs goes into `cli_config.py`, which is tested to 100% by `tests/test_cli_config.py`.

---

## 2. The steps of `SetupGitHubRepo`

Methods are numbered by workflow: `s1x` set up, `s2x` tear down, `s3x` maintain.

| Method | AWS / GitHub calls |
| :--- | :--- |
| `s11_create_iam_user` | `create_user`, or `tag_user` when it already exists |
| `s12_put_iam_policy` | `put_user_policy`, then delete other inline policies, detach unlisted managed policies, attach missing ones |
| `s13_create_or_get_access_key` | `list_access_keys`; `create_access_key` only when the user has none |
| `s14_setup_github_secrets` | `repo.create_secret` for the three secrets, then `print_github_workflow_example()` |
| `s21_delete_github_secrets` | `repo.delete_secret` for the three secrets |
| `s22_delete_access_key` | `delete_access_key` for every key |
| `s23_delete_iam_policy` | detach every managed policy, delete every inline policy |
| `s24_delete_iam_user` | `delete_user` |
| `s31_rotate_access_key` | `get_user`, then `s22`, `s13`, `s14` |

`setup_all()` runs s11 to s14 and `teardown_all()` runs s21 to s24. The CLI maps `setup` to `setup_all`, `update_policy` to `s12`, `rotate_key` to `s31`, and `teardown` to `teardown_all`.

GitHub access goes through two `cached_property` values, `gh` and `repo` (`# pragma: no cover`). Nothing else in the class talks to GitHub, which is what lets unit tests replace `repo`.

---

## 3. From config file to object

`cli_config.build_setup()`:

1. `load_config()` reads the JSON file, rejects keys outside `CONFIG_FIELDS`, and resolves a relative `path_access_key_json` against the config file's folder.
2. Command line overrides may set only keys in `OVERRIDABLE_FIELDS`, and are converted to `str`. A relative `path_access_key_json` override is resolved against the current folder.
3. Missing `REQUIRED_FIELDS` raise `ValueError`. `tags` defaults to `{}`, `attached_policy_arn_list` to `[]`.
4. `boto3.Session(profile_name=aws_profile or None, region_name=aws_region)`.
5. The GitHub token is read with `read_env_var(github_token_env_name)`, or is `""` when `need_github=False`.

The config keys are exactly the `SetupGitHubRepo` fields minus `boto_ses` and `github_token`. A new field needs an entry in `CONFIG_FIELDS` (and in `OVERRIDABLE_FIELDS` if it is a plain string), or the CLI cannot set it.
