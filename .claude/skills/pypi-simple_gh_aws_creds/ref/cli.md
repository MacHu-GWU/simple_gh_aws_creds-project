# simple-gh-aws-creds CLI

```bash
simple-gh-aws-creds COMMAND --config PATH [OPTIONS]
```

Run with `uvx simple-gh-aws-creds`, `simple-gh-aws-creds` after `pip install simple-gh-aws-creds`, or `.venv/bin/simple-gh-aws-creds` in a project venv. Python-fire: options take `--name value` or `--name=value`, and hyphens work for underscores. Commands print progress and return nothing, so no secret is printed.

---

## Config file (JSON)

| Key | Required | Meaning |
| :--- | :--- | :--- |
| `aws_region` | yes | Region secret value; part of the inline policy name |
| `iam_user_name` | yes | IAM user, one per repo (convention: `pypi-<package_name>`) |
| `policy_document` | yes | The user's inline IAM policy |
| `path_access_key_json` | yes | Local key file, **relative to the config file's folder**. Keep it out of git (`*access_key.json` in `.gitignore`) |
| `github_user_name` | yes | Repo owner |
| `github_repo_name` | yes | Repo name |
| `tags` | no, `{}` | User tags |
| `attached_policy_arn_list` | no, `[]` | Existing managed policy ARNs |
| `github_secret_name_aws_default_region` | no, `AWS_DEFAULT_REGION` | Secret name |
| `github_secret_name_aws_access_key_id` | no, `AWS_ACCESS_KEY_ID` | Secret name |
| `github_secret_name_aws_secret_access_key` | no, `AWS_SECRET_ACCESS_KEY` | Secret name |

Unknown keys are an error. The file holds no secret, so it can be committed (for example as `.github/simple_gh_aws_creds.json`).

```json
{
    "aws_region": "us-east-1",
    "iam_user_name": "pypi-my_package",
    "policy_document": {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": ["iam:GetUser"], "Resource": "arn:aws:iam::*:user/${aws:username}"}]},
    "path_access_key_json": "../my_access_key.json",
    "github_user_name": "my-user",
    "github_repo_name": "my-repo"
}
```

---

## Options

| Option | Type, default | On | Meaning |
| :--- | :--- | :--- | :--- |
| `--config` | path, required | all | The config file |
| `--aws_profile` | str, none | all | AWS profile; none = boto3 chain (env vars, default profile, SSO, role) |
| `--github_token_env_name` | str, `GITHUB_TOKEN` | setup, rotate_key, teardown | **Name** of the env var holding the GitHub token, never the token |
| `--yes` | flag, off | rotate_key, teardown | Required to act; without it, print a preview and exit 1 |
| `--aws_region`, `--iam_user_name`, `--path_access_key_json`, `--github_user_name`, `--github_repo_name`, `--github_secret_name_*` | str | all | Override that config key. A relative `--path_access_key_json` is relative to the current folder. Other keys cannot be overridden |

---

## Commands

| Command | Does | Needs token | Needs `--yes` |
| :--- | :--- | :--- | :--- |
| `setup` | Create user, policies, key, secrets; print a workflow snippet. Idempotent, also repairs | yes | no |
| `update_policy` | Make the user's policies match the config. Key and secrets unchanged | no | no |
| `rotate_key` | Delete every key, create one, save locally, update secrets | yes | yes |
| `teardown` | Delete secrets, keys, policies, user. Local key file kept | yes | yes |

```bash
simple-gh-aws-creds setup --config .github/simple_gh_aws_creds.json --aws_profile my-profile
simple-gh-aws-creds update_policy --config .github/simple_gh_aws_creds.json --aws_profile my-profile
simple-gh-aws-creds rotate_key --config .github/simple_gh_aws_creds.json --aws_profile my-profile --yes
simple-gh-aws-creds teardown --config .github/simple_gh_aws_creds.json --aws_profile my-profile   # preview only
```

To pass the token without typing it, run the command with an environment that already has it, for example `mise exec -- simple-gh-aws-creds setup ...` when `mise.toml` `[env]` sets `GITHUB_TOKEN` from a secret store.

---

## Verify end to end

Run after `setup` and after `rotate_key`. Each step changes nothing in AWS; the workflow run is the only GitHub action.

**1. Check the key locally,** with every other credential source removed, printing results only (never the key). New keys can take seconds to work, so it retries. Replace the key file path and the denied call with ones that fit your policy:

```bash
env -u AWS_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
    AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null \
    python -c "
import json, time, boto3, botocore.exceptions as E
d = json.load(open('my_access_key.json'))
s = boto3.Session(aws_access_key_id=d['access_key'], aws_secret_access_key=d['secret_key'], region_name='us-east-1')
for _ in range(12):
    try:
        print('caller:', s.client('sts').get_caller_identity()['Arn']); break
    except E.ClientError:
        time.sleep(5)
iam = s.client('iam')
for label, fn in [('allowed: get own user', lambda: iam.get_user()), ('denied: list users', lambda: iam.list_users())]:
    try:
        fn(); print(label, '-> ALLOWED')
    except E.ClientError as e:
        print(label, '->', e.response['Error']['Code'])
"
```

Expect the caller ARN to be the new IAM user, the allowed call to pass, and the denied call to give `AccessDenied`.

**2. Run a workflow** that uses the secrets, for example `.github/workflows/test-aws-creds.yml`:

```yaml
name: test-aws-creds
on:
  workflow_dispatch:
permissions:
  contents: read
jobs:
  test-aws-creds:
    runs-on: ubuntu-latest
    env:
      AWS_DEFAULT_REGION: ${{ secrets.AWS_DEFAULT_REGION }}
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
    steps:
      - run: aws sts get-caller-identity
```

```bash
gh workflow run test-aws-creds.yml --repo my-user/my-repo
gh run watch --repo my-user/my-repo $(gh run list --repo my-user/my-repo --workflow test-aws-creds.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```

A green run proves the GitHub secrets match the key in AWS. A failure right after `setup` or `rotate_key` may be IAM propagation: re-run once. Secrets are not passed to workflows triggered by pull requests from forks.
