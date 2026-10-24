.. _troubleshooting:

Troubleshooting
==============================================================================

.. dropdown:: "already has access key ..., but its secret key is not in ..."
    :icon: question
    :color: info

    The IAM user has an access key, but the local key file (``path_access_key_json``) is missing, or holds a different key. AWS shows a secret key only when it is created, so the old secret cannot be recovered.

    Replace the key. The GitHub secrets are updated too:

    .. code-block:: bash

        simple-gh-aws-creds rotate_key --config .github/simple_gh_aws_creds.json --aws_profile my-aws-profile --yes

    This happens after a move to another machine, or when the key file was deleted. To work from several machines, copy the key file over a secure channel, or rotate the key on the new machine.

.. dropdown:: "IAM User ... does not exist" from rotate_key
    :icon: question
    :color: info

    ``rotate_key`` replaces the key of an existing user. Create the user first with ``setup``.

.. dropdown:: teardown fails with DeleteConflict
    :icon: question
    :color: info

    AWS refuses to delete an IAM user that still has access keys, policies, or other attachments. ``teardown`` deletes every access key and policy first, so this means the user has something else that this library does not manage, such as a login profile, an MFA device, a signing certificate, or a group membership, usually added by hand in the console. Remove it in the IAM console, then run ``teardown --yes`` again.

.. dropdown:: The GitHub step fails with "Bad credentials" or "Resource not accessible"
    :icon: question
    :color: info

    The GitHub token is missing, expired, or cannot write the repository's Actions secrets. Check that:

    - the environment variable named by ``--github_token_env_name`` (``GITHUB_TOKEN`` by default) holds the token;
    - a fine-grained token has access to this repository with "Secrets: Read and write"; a classic token has the ``repo`` scope;
    - ``github_user_name`` and ``github_repo_name`` in the config name the right repository.

    The access key is already saved locally at this point. Once the token is fixed, run ``setup`` again to write the secrets.

.. dropdown:: The workflow cannot see the secrets
    :icon: question
    :color: info

    - GitHub does not pass secrets to workflows triggered by pull requests from forks, so ``secrets.AWS_ACCESS_KEY_ID`` is empty there.
    - The names in the workflow must match the secret names, ``AWS_DEFAULT_REGION``, ``AWS_ACCESS_KEY_ID``, ``AWS_SECRET_ACCESS_KEY`` by default, or the ``github_secret_name_*`` keys of the config.

    See `Using secrets in GitHub Actions <https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets>`_.

.. dropdown:: The workflow gets AccessDenied
    :icon: question
    :color: info

    The credentials work, but the IAM user lacks the permission. Add the action to ``policy_document``, or a policy ARN to ``attached_policy_arn_list``, then run ``update_policy``. The key and the secrets stay the same.

    A new key can also take a few seconds to work after ``setup`` or ``rotate_key``, while IAM propagates it. Re-run the workflow.

.. dropdown:: What happens when I change aws_region?
    :icon: question
    :color: info

    The IAM user is global, so it stays. The region is part of the inline policy name, so the next ``setup`` or ``update_policy`` creates the policy under the new name and deletes the old one, and ``setup`` writes the new region to the region secret.

.. dropdown:: The AWS credentials are not found
    :icon: question
    :color: info

    Without ``--aws_profile``, boto3 looks for credentials in environment variables, then in the default profile of ``~/.aws/credentials`` and ``~/.aws/config``, then elsewhere (SSO, an instance role). Pass ``--aws_profile`` to pick a named profile, and check it with:

    .. code-block:: bash

        aws sts get-caller-identity --profile my-aws-profile
