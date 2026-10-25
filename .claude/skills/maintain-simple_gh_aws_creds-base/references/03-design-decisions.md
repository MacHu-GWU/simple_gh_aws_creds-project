---
description: "Why simple_gh_aws_creds is built the way it is: wide dependency floors, fire as a core dependency, a JSON config file, the s3x numbering, accepted downtime during key rotation, and the scope against OIDC. Read before proposing to change one of these choices."
---

# Design Decisions

Decided with the maintainer during the 0.2.0 work. Change one only with the user's yes.

---

## 1. Dependency floors stay wide

`boto3>=1.35.0` and `PyGithub>=2.1.1` in `pyproject.toml` are far below the versions in `uv.lock`, against the template's "floor is the tested version" rule (`pywf-oss-base`, the uv and dependencies reference).

- **Why:** a library should not force its users to upgrade boto3 or PyGithub. The IAM calls used are old and stable.
- **Tested:** both floors were run against the full unit test suite (`uv run --with "boto3==1.35.0" --with "botocore==1.35.0" --with "PyGithub==2.1.1"`), and `Repository.create_secret` / `delete_secret` exist in PyGithub 2.1.1. GitHub calls are not covered by unit tests, so PyGithub's floor is checked for import and method existence only.
- The `mise` extra's `PyGithub>=2.8.0` is for `.mise/tasks/` only, not for users; uv resolves the intersection locally.

---

## 2. `fire` is a core dependency

No `[cli]` extra: `uvx simple-gh-aws-creds` must work without `--from 'simple_gh_aws_creds[cli]'`, and a missing extra would make the entry point fail with `ImportError`. `fire` is small and pure Python. The template also puts the CLI library in `dependencies` (`pywf-oss-base`, the special package files reference).

---

## 3. The CLI reads a JSON config file

`policy_document`, `tags`, and `attached_policy_arn_list` are nested values that are painful to quote on a command line. JSON, because IAM policies are JSON and can be pasted from AWS docs and the console. The file holds no secret, so it can be committed; this repo commits its own as `.github/simple_gh_aws_creds.json`.

---

## 4. Step numbering

`s1x` set up, `s2x` tear down, `s3x` maintenance operations on an existing setup (`s31_rotate_access_key`). A new step takes the next free number in its group.

---

## 5. Key rotation is not zero-downtime

`s31_rotate_access_key` deletes the old key before creating the new one. AWS would allow two keys at once, but the library keeps one key per user (`02-invariants.md`), and a rotation usually happens when the old key is already lost or meant to be revoked. The few seconds without a valid key are accepted.

---

## 6. Scope: IAM users, not OIDC

The library targets quick setups (open source CI, test accounts) with a long-lived access key, and says so in the user docs (`docs/source/02-How-It-Works/index.rst`). OIDC support is out of scope.
