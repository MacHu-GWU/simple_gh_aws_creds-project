---
description: "The integration test of simple_gh_aws_creds against a real AWS account and this GitHub repository: the AWS profile and IAM user, the committed config and workflow, running the CLI through mise exec, the local key check, and triggering the workflow. Read before running the CLI against real AWS or GitHub, or when changing the config or workflow it uses."
---

# Integration Test

Unit tests prove the logic against mocks (`04-unit-tests.md`). Only this test proves that the real AWS and GitHub APIs accept the calls. **Every step changes a real service: run each one only after the user's yes; one yes covers one step.**

---

## 1. The pieces

| Piece | Value |
| :--- | :--- |
| AWS account | `878625312159`, through the AWS profile `bmt_app_dev_us_east_1` |
| IAM user | `pypi-simple_gh_aws_creds`, following the maintainer's naming rule for the IAM user of an open source Python project's GitHub repository: `pypi-<package_name>` |
| Config file | `.github/simple_gh_aws_creds.json` (committed) |
| Local key file | `pypi_access_key.json` at the repo root, from the config's `"path_access_key_json": "../pypi_access_key.json"` |
| GitHub repository | `MacHu-GWU/simple_gh_aws_creds-project` |
| GitHub secrets | `AWS_DEFAULT_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` (the defaults) |
| Workflow | `.github/workflows/test-aws-creds.yml` |

The user's only permission is `iam:GetUser` on `arn:aws:iam::*:user/${aws:username}`, itself. `sts:GetCallerIdentity` needs no permission. So the test proves the key works and is scoped, while the key can do almost nothing if it leaks.

---

## 2. The local key file

`pypi_access_key.json` holds the only copy of the real secret key.

- It is git-ignored by `*access_key.json` in `.gitignore`, and `.claude/settings.json` denies `Read(**/*access_key.json)` and `Edit(**/*access_key.json)`.
- Never open, print, or copy it. A check that needs the key (section 4) loads it inside a script and prints only results.
- Never name a real key file `dev_access_key.json`, and never point a unit test at the repo root (`05-known-traps.md`).

---

## 3. Running the CLI: `mise exec --`

```bash
mise exec -- .venv/bin/simple-gh-aws-creds setup \
    --config .github/simple_gh_aws_creds.json \
    --aws_profile bmt_app_dev_us_east_1
```

- **Why `mise exec --`:** the `[env]` block of `mise.toml` sets `GITHUB_TOKEN` from `$HOME/home_secret.toml` (through `uvx --from home-secret-toml hst get github.accounts.sh.users.sh.secrets.dev.value`). `mise exec` runs the command with that environment, so the token reaches the CLI's default `--github_token_env_name GITHUB_TOKEN` without ever being read, printed, or typed. A plain shell has no `GITHUB_TOKEN`, and `setup` fails with "Environment variable 'GITHUB_TOKEN' is not set or empty."
- `.venv/bin/simple-gh-aws-creds` runs the working tree's code (installed editable by `mise run inst`), not the PyPI release.
- The same pattern runs the other commands: `update_policy` (needs no token, so `mise exec` is optional), `rotate_key --yes`, `teardown --yes`. Without `--yes`, `rotate_key` and `teardown` only print what they would do and exit 1: a safe preview to show the user before asking for the yes.

```bash
# replace the key (part of the routine, section 6)
mise exec -- .venv/bin/simple-gh-aws-creds rotate_key --config .github/simple_gh_aws_creds.json --aws_profile bmt_app_dev_us_east_1 --yes

# preview what teardown would delete; changes nothing
mise exec -- .venv/bin/simple-gh-aws-creds teardown --config .github/simple_gh_aws_creds.json --aws_profile bmt_app_dev_us_east_1
```

---

## 4. Checking the key locally

After `setup` or `rotate_key`, check the new key with every other credential source removed, printing only results. New IAM keys can take a few seconds to work, so retry:

```bash
env -u AWS_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
    AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null \
    .venv/bin/python - <<'EOF'
import json, time, boto3, botocore.exceptions as E
d = json.load(open("pypi_access_key.json"))
s = boto3.Session(aws_access_key_id=d["access_key"], aws_secret_access_key=d["secret_key"], region_name="us-east-1")
for _ in range(12):
    try:
        print("caller:", s.client("sts").get_caller_identity()["Arn"]); break
    except E.ClientError:
        time.sleep(5)
iam = s.client("iam")
for label, fn in [("get own user", lambda: iam.get_user()), ("list users", lambda: iam.list_users())]:
    try:
        fn(); print(label, "-> ALLOWED")
    except E.ClientError as e:
        print(label, "->", e.response["Error"]["Code"])
EOF
```

Expected: the caller is `arn:aws:iam::878625312159:user/pypi-simple_gh_aws_creds`, "get own user" is allowed, "list users" is `AccessDenied`.

---

## 5. The workflow

`test-aws-creds.yml` maps the three secrets to the AWS environment variables, then runs `aws sts get-caller-identity` and `aws iam get-user`. It runs on `workflow_dispatch`, and on a push to `main` that changes the workflow or `.github/simple_gh_aws_creds.json`.

Trigger it, wait a few seconds for the run to appear, then watch the newest run. `gh` also goes through `mise exec --`, like the CLI:

```bash
mise exec -- gh workflow run test-aws-creds.yml --repo MacHu-GWU/simple_gh_aws_creds-project
mise exec -- gh run watch --repo MacHu-GWU/simple_gh_aws_creds-project $(mise exec -- gh run list --repo MacHu-GWU/simple_gh_aws_creds-project --workflow test-aws-creds.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```

A green run, both steps passed, proves the secrets in GitHub match the key in AWS. A run that fails right after `setup` or `rotate_key` may be IAM propagation; re-run it once before debugging.

---

## 6. When to run it, and the routine

**Before each release**, run the whole routine below. It was run end to end by the maintainer on 2026-10-25 (0.2.0 work), with every check green.

1. `mise run cov`: unit tests first; stop if they fail.
2. `setup` (section 3). On the existing user this exercises the repeat path: tags synced, policies reconciled, the saved key reused, the secrets rewritten with the same values.
3. Check the key locally (section 4).
4. Run the workflow (section 5).
5. `rotate_key --yes` (section 3).
6. Check the new key locally (section 4).
7. Run the workflow again (section 5): proves the new key reached GitHub.

`teardown` is not part of the routine: the test user and its secrets stay in place between releases. Show only its preview (no `--yes`) when checking the command.
