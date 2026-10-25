---
description: "Traps already hit while maintaining simple_gh_aws_creds: test key files overwriting a real key, teardown deleting another user's secrets, PyGithub and python-fire behaviors, and the docfly hidden-toctree workaround. Read when a change touches key files, GitHub secret names, PyGithub calls, CLI arguments, or the docs home page."
---

# Known Traps

---

## 1. A test overwrote the real key file

Until 0.2.0, `tests/test_impl.py` wrote its moto key to `dev_access_key.json` at the repo root, the same name the old `setup_dev_account.py` used for the real key. The first test run replaced the real secret with a fake one, and the real secret was lost. Fix: tests use `tmp_path` (`04-unit-tests.md`), and the real key file is `pypi_access_key.json`.

---

## 2. Teardown deletes secrets by name, not by owner

`s21_delete_github_secrets` deletes the secrets named by the three `github_secret_name_*` fields, whoever created them. Tearing down another IAM user (such as the old `gh-ci-simple_gh_aws_creds`) with the default names would delete the `AWS_*` secrets of `pypi-simple_gh_aws_creds`. Pass that user's own secret names as overrides (`--github_secret_name_aws_access_key_id ...` and the other two), and show the `teardown` preview (no `--yes`) to the user first.

---

## 3. PyGithub

- `Repository.delete_secret()` returns `False` for a missing secret instead of raising; `s21` checks the return value.
- `from github import Repository` imports a **module**. The class is `from github.Repository import Repository`.
- `Github(token)` with a positional token is deprecated; use `Github(auth=Auth.Token(token))`.

---

## 4. python-fire

- **Return values are printed.** Every `Command` method returns `None` (`02-invariants.md`).
- **Arguments are parsed as Python literals:** `--github_repo_name 123` arrives as an `int`. `build_setup()` converts overrides with `str()`.
- **`fire.Fire(Command)` on the class** makes `--help` show the constructor instead of the commands; `main()` passes an instance, `Command()`.
- Hyphens work in place of underscores: `--aws-profile`.

---

## 5. docfly drops `:hidden:` on `autotoctree`

In docfly 3.0.x, `AutoTocTree.derive_toctree_rst` skips options whose value is `None`, and a flag option such as `:hidden:` always has the value `None`, so it never reaches the toctree. `docs/source/index.rst` therefore marks the `autotoctree` with `.. rst-class:: hidden-toctree`, and `docs/source/_static/css/custom-style.css` hides `.hidden-toctree`; the sidebar is unaffected. Once docfly checks `if opt in self.options`, use `:hidden:` and delete the CSS rule.
