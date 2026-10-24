.. _release_history:

Release and Version History
==============================================================================


x.y.z (Backlog)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

**Minor Improvements**

**Bugfixes**

**Miscellaneous**


0.2.0 (2026-10-24)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Breaking Changes**

- Require Python 3.11 or later; Python 3.9 and 3.10 are no longer supported.
- Remove ``simple_gh_aws_creds.__version__`` and the other metadata attributes of the package (``__author__``, ``__license__``, and so on). Use ``importlib.metadata.version("simple_gh_aws_creds")`` instead.
- ``SetupGitHubRepo.s12_put_iam_policy()`` now makes the IAM user's policies exactly match the config: it also deletes the user's other inline policies and detaches managed policies that are not in ``attached_policy_arn_list``. Permissions added to the user by hand are removed.
- ``SetupGitHubRepo.s14_setup_github_secrets()`` and ``SetupGitHubRepo.s21_delete_github_secrets()`` now raise when a GitHub API call fails, instead of printing the error and returning. A bad or under-privileged token is no longer reported as success.
- Add ``fire`` as a runtime dependency, for the new command line interface.

**Features and Improvements**

- Add the ``simple-gh-aws-creds`` command line tool, runnable with ``uvx simple-gh-aws-creds``, with four commands: ``setup``, ``update_policy``, ``rotate_key``, and ``teardown``. It reads a JSON config file, takes AWS credentials from an optional ``--aws_profile`` or the default boto3 credential chain, and reads the GitHub token from the environment variable named by ``--github_token_env_name`` (default ``GITHUB_TOKEN``), so no secret is passed on the command line. ``rotate_key`` and ``teardown`` require ``--yes``, and without it only print what they would do.
- Add ``SetupGitHubRepo.s31_rotate_access_key()`` to replace the IAM user's access key and update the GitHub secrets, keeping the user.
- Add ``SetupGitHubRepo.setup_all()`` and ``SetupGitHubRepo.teardown_all()`` to run the whole setup or teardown workflow.
- ``SetupGitHubRepo.s12_put_iam_policy()`` can be run on its own to hot-update the permissions of an existing user; the access key and the GitHub secrets keep working.
- Add ``SetupGitHubRepo.print_github_workflow_example()``, called after the GitHub secrets are written, which prints a workflow snippet that maps the secrets to the AWS environment variables.
- Add ``SetupGitHubRepo.iam_user_console_url``; each step now prints a link to the IAM user or the GitHub secrets page to check the result.

**Minor Improvements**

- ``SetupGitHubRepo.s11_create_iam_user()`` syncs the tags of an existing user.
- ``SetupGitHubRepo.s13_create_or_get_access_key()`` creates the folder of the local key file if needed, and makes the file readable only by its owner.
- ``SetupGitHubRepo.s24_delete_iam_user()`` explains a ``DeleteConflict`` error.
- Authenticate to GitHub with ``github.Auth.Token``, which removes PyGithub's deprecation warning.
- Support Python 3.12, 3.13, and 3.14.

**Bugfixes**

- Fix ``SetupGitHubRepo.s13_create_or_get_access_key()`` failing with ``FileNotFoundError`` when the IAM user has a key but the local key file is missing, and reusing a stale key from a local file that does not match AWS. It now raises a ``RuntimeError`` that points to ``s31_rotate_access_key()``.
- Fix ``SetupGitHubRepo.s22_delete_access_key()`` deleting only the first of the user's access keys, which made the teardown fail for a user with two keys.
- Fix ``SetupGitHubRepo.s23_delete_iam_policy()`` leaving inline policies with other names, such as one from an earlier ``aws_region``, which made the teardown fail.
- Fix ``SetupGitHubRepo.s21_delete_github_secrets()`` reporting a secret that does not exist as deleted.

**Miscellaneous**

- Move to the pywf open source template: uv, mise, setuptools, and ruff replace Poetry and the ``bin/`` scripts.
- Rewrite the documentation: a short README, and Quick Start, How It Works, CLI Reference, Python API, and Troubleshooting pages. Rewrite the docstrings of ``SetupGitHubRepo``.
- Add a GitHub Actions workflow that checks credentials created by the CLI.
- Unit tests run against moto and never reach AWS or GitHub.


0.1.1 (2025-07-13)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- Initial release of simple_gh_aws_creds library
- Automated IAM user creation and management for GitHub Actions
- Support for inline IAM policy attachment with minimal required permissions
- AWS managed policy attachment support via ``attached_policy_arn_list`` parameter
- GitHub repository secrets configuration for seamless CI/CD integration
- Complete cleanup workflow to remove all created resources
- Comprehensive parameter documentation with usage examples
- Educational example script with detailed inline comments

**Core Functionality**

- ``SetupGitHubRepo`` class with full lifecycle management:
  - ``s11_create_iam_user()`` - Create IAM user with resource tagging
  - ``s12_put_iam_policy()`` - Attach inline and managed policies
  - ``s13_create_or_get_access_key()`` - Generate or reuse access keys
  - ``s14_setup_github_secrets()`` - Configure repository secrets
  - ``s21_delete_github_secrets()`` - Remove GitHub secrets
  - ``s22_delete_access_key()`` - Delete AWS access keys
  - ``s23_delete_iam_policy()`` - Detach managed policies and delete inline policy
  - ``s24_delete_iam_user()`` - Remove IAM user
