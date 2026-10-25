---
description: "How simple_gh_aws_creds unit tests reach no real service: the moto base class, replacing the GitHub repository with FakeRepo or FailingRepo, key files under tmp_path, and the offline check that proves no network call is made. Read when writing or changing a test of impl.py or cli_config.py."
---

# Unit Tests

Template rules on test layout and test writing are in `pywf-oss-base`. This file covers what is specific to this library: **unit tests never reach AWS or GitHub.**

---

## 1. AWS: moto

- `simple_gh_aws_creds/tests/mock_aws.py` defines `BaseMockAwsTest`. Its `setup_class` starts `moto.mock_aws()` and creates `cls.bsm` (a `boto_session_manager.BotoSesManager`); `teardown_class` stops moto. moto also provides fake credentials, so no AWS profile is read.
- Test classes subclass it and add fixtures in `setup_mock_post_process`. `tests/test_impl.py` creates a customer managed policy there, because moto has no AWS managed policies.
- `use_mock = False` would run against a real account with `MockAwsTestConfig.aws_profile`; no test uses it. Real-account testing is the integration test, a later reference.

---

## 2. GitHub: replace `repo`

`SetupGitHubRepo.repo` is a `cached_property`, so a test sets the instance's `__dict__` entry before the first use:

```python
repo = FakeRepo()
setup.__dict__["repo"] = repo  # replace the cached_property
```

- `FakeRepo` (in `tests/test_impl.py`) stores secrets in a dict; its `delete_secret` returns `False` for a missing secret, like PyGithub.
- `FailingRepo` raises on every call, to test that `s14` and `s21` re-raise (`02-invariants.md`).
- With `repo` replaced, `s14`, `s21`, `s31_rotate_access_key`, `setup_all()`, and `teardown_all()` run fully in tests. Only `gh` and `repo` themselves stay `# pragma: no cover`.

---

## 3. Key files go under `tmp_path`

Every test that creates an access key passes a `path_access_key_json` under pytest's `tmp_path` (see `TestSetupGitHubRepo.make_setup`), in a folder that does not exist yet, so the test also covers the folder creation in `s13`. Never point a test at the repo root: the real key file of the integration test lives there.

---

## 4. Proving the tests stay offline

To check that a change did not add a real network call, run the suite with every AWS credential source removed and sockets blocked:

```bash
env -u AWS_PROFILE -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
    AWS_CONFIG_FILE=/dev/null AWS_SHARED_CREDENTIALS_FILE=/dev/null \
    .venv/bin/python -c "
import socket, sys, pytest
def deny(self, addr, *a, **k):
    raise RuntimeError(f'network blocked: {addr}')
socket.socket.connect = deny
socket.socket.connect_ex = deny
sys.exit(pytest.main(['tests', '-q', '-p', 'no:cacheprovider']))
"
```

Every test must pass. A `network blocked` error points to the call that escaped the mocks.
