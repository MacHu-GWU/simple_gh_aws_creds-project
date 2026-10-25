# simple_gh_aws_creds Public API

```python
from simple_gh_aws_creds.api import SetupGitHubRepo
```

The only public symbol is `SetupGitHubRepo`. It talks to AWS through `boto_ses` (IAM) and to GitHub through PyGithub, and prints one progress line per action (keys masked, the secret key never printed).

---

## `SetupGitHubRepo` (dataclass)

```python
SetupGitHubRepo(
    boto_ses: boto3.Session,
    aws_region: str,
    iam_user_name: str,
    tags: dict[str, str],
    policy_document: dict[str, Any],
    attached_policy_arn_list: list[str],
    path_access_key_json: Path,
    github_user_name: str,
    github_repo_name: str,
    github_token: str,
    github_secret_name_aws_default_region: str = "AWS_DEFAULT_REGION",
    github_secret_name_aws_access_key_id: str = "AWS_ACCESS_KEY_ID",
    github_secret_name_aws_secret_access_key: str = "AWS_SECRET_ACCESS_KEY",
)
```

| Field | Meaning |
| :--- | :--- |
| `boto_ses` | Session allowed to create users, put/attach/detach user policies, and create/delete access keys |
| `aws_region` | IAM is global; the region is the value of the region secret, part of the inline policy name, and used in the console URL |
| `iam_user_name` | One user per repository. Suggested convention for open source projects: `pypi-<package_name>` |
| `tags` | Set on create, and synced on an existing user (tags not listed are left alone) |
| `policy_document` | Standard IAM policy JSON, as a dict: the user's only inline policy |
| `attached_policy_arn_list` | Existing managed policy ARNs (AWS or customer managed). Never created, only attached and detached |
| `path_access_key_json` | `{"access_key": ..., "secret_key": ...}`, written with mode 0600, folder created if needed. The only copy of the secret key |
| `github_user_name`, `github_repo_name` | The repository whose Actions secrets are managed |
| `github_token` | Fine-grained PAT with "Secrets: Read and write" on the repo, or classic PAT with `repo` scope. Pass `""` if you only call IAM steps |
| `github_secret_name_*` | Names of the three repository secrets |

### Properties

| Property | Value |
| :--- | :--- |
| `policy_document_name: str` | `iam-user-{aws_region}-{iam_user_name}-inline-policy` |
| `iam_user_console_url: str` | AWS console page of the user |
| `github_secrets_url: str` | `https://github.com/{owner}/{repo}/settings/secrets/actions` |
| `iam_client` | boto3 IAM client of `boto_ses` (cached) |

---

## Workflow methods

### `setup_all() -> None`

Runs `s11_create_iam_user`, `s12_put_iam_policy`, `s13_create_or_get_access_key`, `s14_setup_github_secrets`. Idempotent: re-running repairs a partial setup and changes nothing that is already right.

### `s12_put_iam_policy() -> None`

Makes the user's permissions exactly match the config: overwrites the inline policy `policy_document_name`, **deletes any other inline policy**, attaches the listed managed policies and **detaches any other**. Touches neither the user nor the key, so it hot-updates permissions: edit `policy_document` / `attached_policy_arn_list`, then call it. Policies added by hand in the console are removed.

```python
setup.policy_document["Statement"][0]["Action"] = ["s3:ListBucket", "s3:GetObject"]
setup.s12_put_iam_policy()
```

### `s31_rotate_access_key() -> None`

Deletes every key of the user, creates a new one, writes it to `path_access_key_json`, then writes it to the GitHub secrets. The old key stops working at once (a few seconds of downtime). If the GitHub step fails, the new key is already saved: fix the cause and call `setup_all()`.

- Raises `RuntimeError` if the user does not exist.

### `teardown_all() -> None`

Runs `s21_delete_github_secrets`, `s22_delete_access_key`, `s23_delete_iam_policy`, `s24_delete_iam_user`. Idempotent. Does not delete the local key file. Acts at once: no confirmation.

---

## Step methods

| Method | Does | Notes |
| :--- | :--- | :--- |
| `s11_create_iam_user() -> None` | Create the user with `tags` | Existing user: sync tags |
| `s13_create_or_get_access_key(verbose: bool = True) -> tuple[str, str]` | Return `(access_key_id, secret_access_key)` | Creates and saves a key only if the user has none. Raises `RuntimeError` if the user has a key whose ID is not in the local file: AWS cannot return an old secret, so rotate |
| `s14_setup_github_secrets() -> None` | Write the three secrets, overwriting | Gets the key from `s13`, then prints the workflow snippet. Raises on a GitHub failure |
| `s21_delete_github_secrets() -> None` | Delete the three secrets | Missing secrets are skipped. Deletes by name, whoever created them |
| `s22_delete_access_key() -> None` | Delete every key of the user | Local file untouched |
| `s23_delete_iam_policy() -> None` | Detach every managed policy, delete every inline policy | Whatever their names |
| `s24_delete_iam_user() -> None` | Delete the user | Raises `botocore.exceptions.ClientError` (`DeleteConflict`) if keys, policies, or other attachments remain |
| `print_github_workflow_example() -> None` | Print a workflow snippet | Uses the configured secret names |

---

## Errors

| Error | Cause | Fix |
| :--- | :--- | :--- |
| `RuntimeError` from `s13` | User has a key, local file missing or holds another key | `s31_rotate_access_key()` |
| `RuntimeError` from `s31` | User does not exist | `setup_all()` first |
| PyGithub exception from `s14` / `s21` | Bad token, missing permission, wrong repo | Fix the token, then `setup_all()` |
| `ClientError` `DeleteConflict` from `s24` | Login profile, MFA device, group, ... added by hand | Remove it in the IAM console, re-run |
| Other `botocore.exceptions.ClientError` | AWS refused a call | Check `boto_ses` permissions |
