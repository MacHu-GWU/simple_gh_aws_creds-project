.. _cli-reference:

CLI Reference
==============================================================================
The ``simple-gh-aws-creds`` command has four commands. Each one reads a JSON config file, takes AWS credentials from the usual AWS sources, and takes the GitHub token from an environment variable, so no secret is ever typed on the command line.

.. code-block:: bash

    simple-gh-aws-creds COMMAND --config PATH [OPTIONS]

Run it with ``uvx simple-gh-aws-creds ...`` without installing it, or install it with ``pip install simple-gh-aws-creds``. ``simple-gh-aws-creds --help`` lists the commands, and ``simple-gh-aws-creds COMMAND --help`` the options of one.


.. _cli-config-file:

Config file
------------------------------------------------------------------------------
A JSON object. It holds no secret, so it can be committed with the repository.

.. list-table::
    :header-rows: 1
    :widths: 32 14 54

    * - Key
      - Required
      - Meaning
    * - ``aws_region``
      - yes
      - Region written to the region secret. Also part of the inline policy name.
    * - ``iam_user_name``
      - yes
      - Name of the IAM user, one per repository.
    * - ``policy_document``
      - yes
      - The user's inline policy, a standard `IAM policy document <https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_grammar.html>`_.
    * - ``path_access_key_json``
      - yes
      - Local file for the access key. Relative to the config file's folder. Keep it out of git.
    * - ``github_user_name``
      - yes
      - Owner (user or organization) of the repository.
    * - ``github_repo_name``
      - yes
      - Name of the repository.
    * - ``tags``
      - no, ``{}``
      - Tags of the IAM user, as ``{"key": "value"}``.
    * - ``attached_policy_arn_list``
      - no, ``[]``
      - ARNs of existing managed policies to attach, AWS or customer managed.
    * - ``github_secret_name_aws_default_region``
      - no
      - Secret name for the region. Default ``AWS_DEFAULT_REGION``.
    * - ``github_secret_name_aws_access_key_id``
      - no
      - Secret name for the access key ID. Default ``AWS_ACCESS_KEY_ID``.
    * - ``github_secret_name_aws_secret_access_key``
      - no
      - Secret name for the secret access key. Default ``AWS_SECRET_ACCESS_KEY``.

An unknown key is an error, so a typo does not go unnoticed. The keys are the fields of :class:`~simple_gh_aws_creds.impl.SetupGitHubRepo`, described in its API reference.

Example:

.. literalinclude:: ../../../.github/simple_gh_aws_creds.json
    :language: json


Options of every command
------------------------------------------------------------------------------
.. list-table::
    :header-rows: 1
    :widths: 32 68

    * - Option
      - Meaning
    * - ``--config PATH``
      - The config file. Required.
    * - ``--aws_profile NAME``
      - AWS profile to use. Without it, boto3 looks for credentials in its usual order: environment variables, the default profile, SSO, an instance role.
    * - ``--github_token_env_name NAME``
      - Name of the environment variable that holds the GitHub token. Default ``GITHUB_TOKEN``. Not on ``update_policy``, which does not call GitHub.
    * - ``--KEY VALUE``
      - Override one plain value of the config file, for example ``--aws_region us-west-2``. Only these keys can be overridden: ``aws_region``, ``iam_user_name``, ``path_access_key_json``, ``github_user_name``, ``github_repo_name``, and the three ``github_secret_name_*`` keys. A relative ``path_access_key_json`` given here is relative to the current folder.

Every option also works as ``--key=value``, and with hyphens instead of underscores (``--aws-profile``).

.. note::

    Options that end in ``_env_name`` take the **name** of an environment variable, never its value. This keeps secrets out of the shell history and out of the prompts of AI agents that run the command. An error names the variable, never its value.


Commands
------------------------------------------------------------------------------

setup
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Create the IAM user, its policies, its access key, and the three GitHub secrets, then print a workflow snippet that uses them.

.. code-block:: bash

    simple-gh-aws-creds setup --config .github/simple_gh_aws_creds.json --aws_profile my-aws-profile

Safe to run again: what is already right is left alone, so it also repairs a partial setup.

update_policy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Make the IAM user's policies match the config file. The user, the access key, and the GitHub secrets stay as they are, and no GitHub token is needed.

.. code-block:: bash

    simple-gh-aws-creds update_policy --config .github/simple_gh_aws_creds.json --aws_profile my-aws-profile

rotate_key
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Replace the access key: delete every key of the user, create a new one, save it to ``path_access_key_json``, and write it to the GitHub secrets. Requires ``--yes``.

.. code-block:: bash

    simple-gh-aws-creds rotate_key --config .github/simple_gh_aws_creds.json --aws_profile my-aws-profile --yes

The old key stops working at once, so a workflow running during those few seconds fails. The new key is saved locally before GitHub is updated: if the GitHub step fails, fix the cause and run ``setup`` to finish.

teardown
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Delete the three GitHub secrets, every access key and policy of the user, and the user. Requires ``--yes``.

.. code-block:: bash

    simple-gh-aws-creds teardown --config .github/simple_gh_aws_creds.json --aws_profile my-aws-profile --yes

The local key file is not deleted; delete it yourself once the key is gone. Safe to run again: what is already gone is skipped.

Without ``--yes``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
``rotate_key`` and ``teardown`` only print what they would do, then exit with status 1. Nothing is changed and no GitHub token is needed, so it is a safe preview:

.. code-block:: text

    $ simple-gh-aws-creds teardown --config .github/simple_gh_aws_creds.json
    teardown permanently deletes:
      - GitHub secrets AWS_DEFAULT_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY of MacHu-GWU/simple_gh_aws_creds-project
      - every access key and policy of IAM User 'pypi-simple_gh_aws_creds'
      - IAM User 'pypi-simple_gh_aws_creds'
    Run it again with --yes to proceed.


Common tasks
------------------------------------------------------------------------------
.. list-table::
    :header-rows: 1
    :widths: 40 60

    * - Task
      - How
    * - Give the workflows more or fewer permissions
      - Edit ``policy_document`` or ``attached_policy_arn_list``, then ``update_policy``.
    * - Replace a leaked or old key
      - ``rotate_key --yes``.
    * - The local key file was lost
      - ``rotate_key --yes``: the old secret key cannot be recovered from AWS.
    * - Change the region
      - Edit ``aws_region``, then ``setup``: it renames the inline policy and updates the region secret.
    * - Use other secret names
      - Set the ``github_secret_name_*`` keys, then ``setup``. The secrets under the old names are not deleted; remove them in the repository settings.
    * - Remove everything
      - ``teardown --yes``, then delete the local key file.
