.. _quick-start:

Quick Start
==============================================================================
This page gives a GitHub repository its own IAM user, and lets its GitHub Actions workflows use that user's access key. It takes about five minutes.

The example is the one this project uses to test itself: the IAM user ``pypi-simple_gh_aws_creds`` for the repository `MacHu-GWU/simple_gh_aws_creds-project <https://github.com/MacHu-GWU/simple_gh_aws_creds-project>`_.


Prerequisites
------------------------------------------------------------------------------
- **AWS credentials that can manage IAM users** in the target account: create users, put and attach user policies, create and delete access keys. Any source the AWS CLI understands works: a named profile, environment variables, SSO.
- **A GitHub token that can write the repository's Actions secrets,** in an environment variable (``GITHUB_TOKEN`` by default):

  - a fine-grained personal access token with the repository permission "Secrets: Read and write", or
  - a classic personal access token with the ``repo`` scope.

- `uv <https://docs.astral.sh/uv/>`_ to run the command line tool, or ``pip`` to install it.


1. Install
------------------------------------------------------------------------------
.. tab-set::

    .. tab-item:: uvx
        :sync: uvx

        Nothing to install: ``uvx`` downloads and runs the tool.

        .. code-block:: bash

            uvx simple-gh-aws-creds --help

    .. tab-item:: pip
        :sync: pip

        .. code-block:: bash

            pip install simple-gh-aws-creds
            simple-gh-aws-creds --help


2. Write the config file
------------------------------------------------------------------------------
The config file describes the IAM user, its permissions, and the repository. It holds no secret, so you can commit it with the repository:

.. literalinclude:: ../../../.github/simple_gh_aws_creds.json
    :language: json
    :caption: .github/simple_gh_aws_creds.json

- ``policy_document`` is the user's only inline policy. This one allows nothing but ``iam:GetUser`` on the user itself; give your user exactly what its workflows need.
- ``path_access_key_json`` is where the new access key is saved. A relative path is relative to the config file, so this key lands in the repository root as ``pypi_access_key.json``. It is the only copy of the secret key: **keep it out of git**, for example with ``*access_key.json`` in ``.gitignore``.

Every key is described in :ref:`cli-config-file`.


3. Run setup
------------------------------------------------------------------------------
.. tab-set::

    .. tab-item:: uvx
        :sync: uvx

        .. code-block:: bash

            uvx simple-gh-aws-creds setup \
                --config .github/simple_gh_aws_creds.json \
                --aws_profile my-aws-profile

    .. tab-item:: pip
        :sync: pip

        .. code-block:: bash

            simple-gh-aws-creds setup \
                --config .github/simple_gh_aws_creds.json \
                --aws_profile my-aws-profile

It runs four steps and prints a link to check each one:

.. code-block:: text

    🆕Step 1.1: Create IAM User 'pypi-simple_gh_aws_creds'
      ✅Successfully created IAM User.
    🆕Step 1.2: Put IAM Policy 'iam-user-us-east-1-pypi-simple_gh_aws_creds-inline-policy'
      ✅Successfully put IAM inline policy.
    🆕Step 1.3: Create or get access key
      ✅Successfully created new access key 'AKIA...BASC'
    🆕Step 1.4: Setup GitHub Secrets
      ✅Successfully created GitHub Secret 'AWS_DEFAULT_REGION'
      ✅Successfully created GitHub Secret 'AWS_ACCESS_KEY_ID'
      ✅Successfully created GitHub Secret 'AWS_SECRET_ACCESS_KEY'

The access key is always masked, and the secret key is never printed. Running ``setup`` again changes nothing that is already right, so it is also the way to repair a partial setup.


4. Use the secrets in a workflow
------------------------------------------------------------------------------
Map the three secrets to the environment variables that the AWS CLI and SDKs read. This workflow checks the new credentials:

.. literalinclude:: ../../../.github/workflows/test-aws-creds.yml
    :language: yaml
    :caption: .github/workflows/test-aws-creds.yml

Run it from the repository's Actions tab. ``aws sts get-caller-identity`` prints the new IAM user's ARN.

.. note::

    GitHub does not pass secrets to workflows triggered by pull requests from forks. See `Using secrets in GitHub Actions <https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets>`_.


Next steps
------------------------------------------------------------------------------
- Change the permissions later with ``update_policy``, replace the key with ``rotate_key``, remove everything with ``teardown``: :ref:`cli-reference`.
- What exactly was created, and when to prefer OIDC: :ref:`how-it-works`.

.. button-ref:: how-it-works
    :ref-type: ref
    :color: primary
    :shadow:

    How It Works
