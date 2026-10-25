---
description: "The behaviors of simple_gh_aws_creds that every change must keep: config-as-truth policy reconciliation, one access key per user, the local key file saved before GitHub, errors raised and never swallowed, and no secret ever printed or passed on the command line. Read before changing a step method or a CLI command."
---

# Invariants

Each rule names the code that implements it and the test that guards it. Break one only with the user's yes, and record it as a Breaking Change.

---

## 1. Every step is idempotent, and the config is the truth

- `s12_put_iam_policy` makes the user's policies exactly match `policy_document` and `attached_policy_arn_list`: it deletes inline policies with other names and detaches unlisted managed policies. Guarded by the hot-update part of `TestSetupGitHubRepo.test_edge_cases`.
- `s23_delete_iam_policy` lists first, then deletes every policy, whatever its name, so `s24_delete_iam_user` cannot hit `DeleteConflict` over a leftover policy.
- Every delete step treats "already gone" (`NoSuchEntity`, a missing secret) as success. `test_workflows` runs `setup_all()` and `teardown_all()` twice each.
- The inline policy name contains `aws_region` (`SetupGitHubRepo.policy_document_name`). Changing that format orphans the policies of existing users on their next `s12`; keep it.

---

## 2. One access key per user, and its secret is never lost

- AWS returns a secret key only from `create_access_key`. So `s13_create_or_get_access_key` writes the new key to `path_access_key_json` before anything else can fail, after creating its folder, and sets the file to mode `0o600`.
- `s13` reuses a key only if the key ID in the local file is one of the user's keys in AWS; otherwise it raises `RuntimeError` pointing to `rotate_key`. It never creates a second key on its own.
- `s31_rotate_access_key` deletes every key first (`s22`), then creates one (`s13`), then writes GitHub (`s14`). The local file is written before GitHub, so a failed `s14` is repaired by `setup`.

---

## 3. Failures are raised

- `s14_setup_github_secrets` and `s21_delete_github_secrets` print the error, then re-raise it. Swallowing it made `setup` exit 0 with half-written secrets (fixed in 0.2.0). Guarded by the `FailingRepo` part of `test_workflows`.
- AWS errors other than the handled codes are re-raised with a bare `raise`.

---

## 4. No secret on the command line or in the output

- **CLI commands return `None`.** python-fire prints a command's return value; `s13` returns the secret key, so a command that returned it would print it.
- **Secrets come from environment variables by name:** every option that carries a secret ends in `_env_name` (`--github_token_env_name`, default `GITHUB_TOKEN`). `read_env_var()` errors name the variable, never the value. AWS credentials are never options: only `--aws_profile`, or the boto3 credential chain.
- **Printed keys are masked** with `mask_value()`; the secret key is never printed.
- **Destructive commands need `--yes`:** `teardown` and `rotate_key` without it print `describe_teardown()` / `describe_rotate_key()` and exit 1, building the object with `need_github=False`, so the preview needs no token.
- **`update_policy` needs no GitHub token** (`need_github=False`): it never calls GitHub.
