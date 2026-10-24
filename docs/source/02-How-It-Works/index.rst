.. _how-it-works:

How It Works
==============================================================================
``simple_gh_aws_creds`` manages a small, fixed set of resources for one GitHub repository. Every step makes AWS and GitHub match the config, so each one is safe to run again.


What gets created
------------------------------------------------------------------------------
.. list-table::
    :header-rows: 1
    :widths: 20 30 50

    * - Where
      - Resource
      - Notes
    * - AWS IAM
      - One IAM user
      - Named ``iam_user_name``, tagged with ``tags``. IAM is global, so the user is not tied to a region.
    * - AWS IAM
      - One inline policy
      - Named ``iam-user-{aws_region}-{iam_user_name}-inline-policy`` (:attr:`SetupGitHubRepo.policy_document_name <simple_gh_aws_creds.impl.SetupGitHubRepo.policy_document_name>`), with ``policy_document`` as its content.
    * - AWS IAM
      - Managed policies (optional)
      - The existing policies in ``attached_policy_arn_list``, attached to the user. They are never created or deleted, only attached and detached.
    * - AWS IAM
      - One access key
      - The user holds exactly one key managed by this library.
    * - Your machine
      - The local key file
      - ``path_access_key_json``, the only copy of the secret key, in plain text, readable only by you. Keep it out of git.
    * - GitHub
      - Three Actions secrets
      - The region, the access key ID, and the secret access key, named ``AWS_DEFAULT_REGION``, ``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY`` by default.

The local key file exists because AWS shows a secret key only once, when it is created. With the file, a later ``setup`` can write the same key to GitHub again; without it, the key must be replaced (see :ref:`troubleshooting`).


The steps
------------------------------------------------------------------------------
Each command line command, and each method of :class:`~simple_gh_aws_creds.impl.SetupGitHubRepo`, runs some of these steps:

.. list-table::
    :header-rows: 1
    :widths: 35 65

    * - Step
      - What it does
    * - :meth:`s11_create_iam_user <simple_gh_aws_creds.impl.SetupGitHubRepo.s11_create_iam_user>`
      - Create the IAM user, or sync its tags if it exists.
    * - :meth:`s12_put_iam_policy <simple_gh_aws_creds.impl.SetupGitHubRepo.s12_put_iam_policy>`
      - Make the user's policies exactly match the config: overwrite the inline policy, delete any other inline policy, attach the listed managed policies and detach the others.
    * - :meth:`s13_create_or_get_access_key <simple_gh_aws_creds.impl.SetupGitHubRepo.s13_create_or_get_access_key>`
      - Create the access key and save it locally, or reuse the saved one.
    * - :meth:`s14_setup_github_secrets <simple_gh_aws_creds.impl.SetupGitHubRepo.s14_setup_github_secrets>`
      - Write the three GitHub secrets, overwriting old values.
    * - :meth:`s21_delete_github_secrets <simple_gh_aws_creds.impl.SetupGitHubRepo.s21_delete_github_secrets>`
      - Delete the three GitHub secrets.
    * - :meth:`s22_delete_access_key <simple_gh_aws_creds.impl.SetupGitHubRepo.s22_delete_access_key>`
      - Delete every access key of the user.
    * - :meth:`s23_delete_iam_policy <simple_gh_aws_creds.impl.SetupGitHubRepo.s23_delete_iam_policy>`
      - Detach every managed policy and delete every inline policy of the user.
    * - :meth:`s24_delete_iam_user <simple_gh_aws_creds.impl.SetupGitHubRepo.s24_delete_iam_user>`
      - Delete the user.
    * - :meth:`s31_rotate_access_key <simple_gh_aws_creds.impl.SetupGitHubRepo.s31_rotate_access_key>`
      - Delete every key, create a new one, save it locally, then write it to GitHub.

And the commands that run them:

.. list-table::
    :header-rows: 1
    :widths: 25 35 40

    * - Command
      - Python method
      - Steps
    * - ``setup``
      - :meth:`~simple_gh_aws_creds.impl.SetupGitHubRepo.setup_all`
      - s11, s12, s13, s14
    * - ``update_policy``
      - :meth:`~simple_gh_aws_creds.impl.SetupGitHubRepo.s12_put_iam_policy`
      - s12
    * - ``rotate_key``
      - :meth:`~simple_gh_aws_creds.impl.SetupGitHubRepo.s31_rotate_access_key`
      - s22, s13, s14
    * - ``teardown``
      - :meth:`~simple_gh_aws_creds.impl.SetupGitHubRepo.teardown_all`
      - s21, s22, s23, s24


The config is the source of truth
------------------------------------------------------------------------------
The steps do not add to what is there; they make it match the config:

- **Permissions:** edit ``policy_document`` or ``attached_policy_arn_list`` and run ``update_policy``. A policy that is no longer in the config is removed. The user, the access key, and the GitHub secrets stay as they are, so running workflows keep working with the new permissions.
- **Region:** the region is part of the inline policy name. After a region change, ``update_policy`` creates the policy under the new name and deletes the old one.
- **Tags:** ``setup`` sets the tags in the config on an existing user. Tags that are not in the config are left alone.

So keep the config file in the repository, and change the user's permissions by changing the file, not by hand in the console: a policy added by hand is removed by the next ``setup`` or ``update_policy``.


Security trade-off
------------------------------------------------------------------------------
An IAM user's access key is a **long-lived credential**: it works until it is deleted, and anyone who reads it can use it. This library limits the risk, but cannot remove it:

- one IAM user per repository, with only the permissions in its config;
- the key lives in two places only: GitHub's encrypted secrets, and your local key file, readable only by you;
- ``rotate_key`` replaces the key in one command, and ``teardown`` removes everything.

`OpenID Connect (OIDC) <https://docs.github.com/en/actions/concepts/security/openid-connect>`_ avoids long-lived keys altogether: each workflow run gets short-lived credentials for an IAM role. It needs more setup (an identity provider, a role, and a trust policy per repository). Prefer OIDC for production accounts and sensitive permissions; use this library when speed and simplicity matter more, such as for open source CI, test accounts, and experiments.
