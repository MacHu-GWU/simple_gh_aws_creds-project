
.. image:: https://readthedocs.org/projects/simple-gh-aws-creds/badge/?version=latest
    :target: https://simple-gh-aws-creds.readthedocs.io/en/latest/
    :alt: Documentation Status

.. image:: https://github.com/MacHu-GWU/simple_gh_aws_creds-project/actions/workflows/main.yml/badge.svg
    :target: https://github.com/MacHu-GWU/simple_gh_aws_creds-project/actions?query=workflow:CI

.. image:: https://codecov.io/gh/MacHu-GWU/simple_gh_aws_creds-project/branch/main/graph/badge.svg
    :target: https://codecov.io/gh/MacHu-GWU/simple_gh_aws_creds-project

.. image:: https://img.shields.io/pypi/v/simple-gh-aws-creds.svg
    :target: https://pypi.python.org/pypi/simple-gh-aws-creds

.. image:: https://img.shields.io/pypi/l/simple-gh-aws-creds.svg
    :target: https://pypi.python.org/pypi/simple-gh-aws-creds

.. image:: https://img.shields.io/pypi/pyversions/simple-gh-aws-creds.svg
    :target: https://pypi.python.org/pypi/simple-gh-aws-creds

.. image:: https://img.shields.io/badge/✍️_Release_History!--None.svg?style=social&logo=github
    :target: https://github.com/MacHu-GWU/simple_gh_aws_creds-project/blob/main/release-history.rst

.. image:: https://img.shields.io/badge/⭐_Star_me_on_GitHub!--None.svg?style=social&logo=github
    :target: https://github.com/MacHu-GWU/simple_gh_aws_creds-project

------

.. image:: https://img.shields.io/badge/Link-API-blue.svg
    :target: https://simple-gh-aws-creds.readthedocs.io/en/latest/py-modindex.html

.. image:: https://img.shields.io/badge/Link-Install-blue.svg
    :target: `install`_

.. image:: https://img.shields.io/badge/Link-GitHub-blue.svg
    :target: https://github.com/MacHu-GWU/simple_gh_aws_creds-project

.. image:: https://img.shields.io/badge/Link-Submit_Issue-blue.svg
    :target: https://github.com/MacHu-GWU/simple_gh_aws_creds-project/issues

.. image:: https://img.shields.io/badge/Link-Request_Feature-blue.svg
    :target: https://github.com/MacHu-GWU/simple_gh_aws_creds-project/issues

.. image:: https://img.shields.io/badge/Link-Download-blue.svg
    :target: https://pypi.org/pypi/simple-gh-aws-creds#files



Welcome to ``simple_gh_aws_creds`` Documentation
==============================================================================
.. image:: https://simple-gh-aws-creds.readthedocs.io/en/latest/_static/simple_gh_aws_creds-logo.png
    :target: https://simple-gh-aws-creds.readthedocs.io/en/latest/

``simple_gh_aws_creds`` gives a GitHub repository its own AWS IAM user, and stores that user's access key as the repository's GitHub Actions secrets. One command sets it up, one command tears it down, and each step is safe to run again.

It fits when you want GitHub Actions to reach AWS in a few minutes, without setting up OIDC:

- open source projects whose CI needs a small, well-scoped piece of AWS;
- test and sandbox accounts, where one IAM user per repository is easy to track;
- a quick start you may later replace with OIDC.

The access key is long-lived. For production accounts, prefer `GitHub OIDC <https://docs.github.com/en/actions/concepts/security/openid-connect>`_.


Quick Start
------------------------------------------------------------------------------
1. Describe the IAM user in a JSON config file:

.. code-block:: json

    {
        "aws_region": "us-east-1",
        "iam_user_name": "gh-ci-my-project",
        "policy_document": {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "*"}
            ]
        },
        "path_access_key_json": "my_access_key.json",
        "github_user_name": "my-github-user",
        "github_repo_name": "my-project"
    }

2. Create the IAM user, its access key, and the GitHub secrets. AWS credentials come from your AWS profile; the GitHub token from the ``GITHUB_TOKEN`` environment variable:

.. code-block:: bash

    uvx simple-gh-aws-creds setup --config config.json --aws_profile my-profile

3. Use the secrets in a workflow:

.. code-block:: yaml

    jobs:
      aws-job:
        runs-on: ubuntu-latest
        env:
          AWS_DEFAULT_REGION: ${{ secrets.AWS_DEFAULT_REGION }}
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        steps:
          - run: aws sts get-caller-identity

Read more:

- `Quick Start <https://simple-gh-aws-creds.readthedocs.io/en/latest/01-Quick-Start/index.html>`_: the full walk-through, with prerequisites.
- `How It Works <https://simple-gh-aws-creds.readthedocs.io/en/latest/02-How-It-Works/index.html>`_: what gets created, and the security trade-off.
- `CLI Reference <https://simple-gh-aws-creds.readthedocs.io/en/latest/03-CLI-Reference/index.html>`_: the config file and every command.
- `Python API <https://simple-gh-aws-creds.readthedocs.io/en/latest/04-Python-API/index.html>`_: the same, from Python.
- `Troubleshooting <https://simple-gh-aws-creds.readthedocs.io/en/latest/05-Troubleshooting/index.html>`_: common errors and how to fix them.


.. _install:

Install
------------------------------------------------------------------------------
``simple_gh_aws_creds`` is released on PyPI. Run the command line tool without installing it:

.. code-block:: console

    $ uvx simple-gh-aws-creds --help

Or install it, for the command line tool and the Python API:

.. code-block:: console

    $ pip install simple-gh-aws-creds

To upgrade to latest version:

.. code-block:: console

    $ pip install --upgrade simple-gh-aws-creds
