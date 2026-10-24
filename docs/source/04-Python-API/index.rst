.. _python-api:

Python API
==============================================================================
Everything the command line does is also available from Python, through :class:`~simple_gh_aws_creds.impl.SetupGitHubRepo`. Use it to keep the setup in a Python script, or to pass in a ``boto3`` session and a token you already have.

.. code-block:: python

    import simple_gh_aws_creds.api as simple_gh_aws_creds


Create the object
------------------------------------------------------------------------------
The constructor takes the same values as the :ref:`config file <cli-config-file>`, plus a ``boto3`` session and the GitHub token:

.. code-block:: python

    import os
    from pathlib import Path

    import boto3

    import simple_gh_aws_creds.api as simple_gh_aws_creds

    setup = simple_gh_aws_creds.SetupGitHubRepo(
        boto_ses=boto3.Session(profile_name="my-aws-profile"),
        aws_region="us-east-1",
        iam_user_name="gh-ci-my-project",
        tags={"github_repo_name": "my-project"},
        policy_document={
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": ["s3:ListBucket"],
                    "Resource": "*",
                },
            ],
        },
        attached_policy_arn_list=[],
        path_access_key_json=Path("my_access_key.json"),
        github_user_name="my-github-user",
        github_repo_name="my-project",
        github_token=os.environ["GITHUB_TOKEN"],
    )

The three secret names default to ``AWS_DEFAULT_REGION``, ``AWS_ACCESS_KEY_ID``, and ``AWS_SECRET_ACCESS_KEY``; pass ``github_secret_name_aws_default_region``, ``github_secret_name_aws_access_key_id``, or ``github_secret_name_aws_secret_access_key`` to change them.


Run a workflow
------------------------------------------------------------------------------
.. code-block:: python

    # create the IAM user, policies, access key, and GitHub secrets
    setup.setup_all()

    # after editing setup.policy_document or setup.attached_policy_arn_list
    setup.s12_put_iam_policy()

    # replace the access key
    setup.s31_rotate_access_key()

    # delete everything
    setup.teardown_all()

.. list-table::
    :header-rows: 1
    :widths: 40 60

    * - Method
      - Same as
    * - :meth:`SetupGitHubRepo.setup_all <simple_gh_aws_creds.impl.SetupGitHubRepo.setup_all>`
      - ``simple-gh-aws-creds setup``
    * - :meth:`SetupGitHubRepo.s12_put_iam_policy <simple_gh_aws_creds.impl.SetupGitHubRepo.s12_put_iam_policy>`
      - ``simple-gh-aws-creds update_policy``
    * - :meth:`SetupGitHubRepo.s31_rotate_access_key <simple_gh_aws_creds.impl.SetupGitHubRepo.s31_rotate_access_key>`
      - ``simple-gh-aws-creds rotate_key --yes``
    * - :meth:`SetupGitHubRepo.teardown_all <simple_gh_aws_creds.impl.SetupGitHubRepo.teardown_all>`
      - ``simple-gh-aws-creds teardown --yes``

The Python methods do not ask for confirmation: ``s31_rotate_access_key`` and ``teardown_all`` act at once.


Run one step
------------------------------------------------------------------------------
Each step is a method of its own, listed in :ref:`how-it-works`. They are useful when you script something the commands do not cover:

.. code-block:: python

    # the access key, created if the user has none
    access_key_id, secret_access_key = setup.s13_create_or_get_access_key()

    # print the workflow snippet again
    setup.print_github_workflow_example()

    # links to check the result
    print(setup.iam_user_console_url)
    print(setup.github_secrets_url)

Every public name is in the :class:`~simple_gh_aws_creds.impl.SetupGitHubRepo` API reference.


Errors
------------------------------------------------------------------------------
- :meth:`~simple_gh_aws_creds.impl.SetupGitHubRepo.s13_create_or_get_access_key` raises :class:`RuntimeError` when the user has a key whose secret is not in the local key file. Replace the key with :meth:`~simple_gh_aws_creds.impl.SetupGitHubRepo.s31_rotate_access_key`.
- :meth:`~simple_gh_aws_creds.impl.SetupGitHubRepo.s31_rotate_access_key` raises :class:`RuntimeError` when the IAM user does not exist.
- A failed GitHub call (for example, a token without permission) is raised as the error PyGithub reports.
- Other AWS errors are raised as ``botocore.exceptions.ClientError``.

See :ref:`troubleshooting` for the fixes.
