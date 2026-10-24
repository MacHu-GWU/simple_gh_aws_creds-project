# -*- coding: utf-8 -*-

"""
Create an IAM user and access key with boto3, and store the key as GitHub
Actions secrets with PyGithub. See :class:`SetupGitHubRepo`.
"""

from __future__ import annotations

import typing as T
import json
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from functools import cached_property

import botocore.exceptions
import boto3
from github import Auth
from github import Github
from github.Repository import Repository

if T.TYPE_CHECKING:  # pragma: no cover
    from mypy_boto3_iam.client import IAMClient

printer = print


def mask_value(v: str) -> str:
    """
    Mask a secret for printing, keeping its first and last four characters.
    """
    if len(v) < 12:
        raise ValueError(f"{v} is too short")
    return f"{v[:4]}...{v[-4:]}"


@dataclass
class SetupGitHubRepo:
    """
    Give one GitHub repository its own IAM user, and store the user's access
    key as the repository's GitHub Actions secrets.

    The IAM user has one inline policy, from ``policy_document``, plus the
    existing managed policies listed in ``attached_policy_arn_list``. This class
    never creates managed policies.

    Setup Workflow:

    - :meth:`s11_create_iam_user`
    - :meth:`s12_put_iam_policy`
    - :meth:`s13_create_or_get_access_key`
    - :meth:`s14_setup_github_secrets`

    Teardown Workflow:

    - :meth:`s21_delete_github_secrets`
    - :meth:`s22_delete_access_key`
    - :meth:`s23_delete_iam_policy`
    - :meth:`s24_delete_iam_user`

    Maintenance:

    - :meth:`s12_put_iam_policy`: hot-update the permissions
    - :meth:`s31_rotate_access_key`: replace the access key

    :meth:`setup_all` and :meth:`teardown_all` run each workflow in order.
    Every step is idempotent.
    """

    # fmt: off
    boto_ses: boto3.Session = field()  #: boto3 session with permission to manage IAM users in the target AWS account.
    aws_region: str = field()  #: Region written to the region secret, used in the console URL and the inline policy name. IAM itself is global.
    iam_user_name: str = field()  #: Name of the IAM user, one per GitHub repository.
    tags: dict[str, str] = field()  #: Tags of the IAM user, synced on every :meth:`s11_create_iam_user`.
    policy_document: dict[str, T.Any] = field()  #: IAM policy document of the user's inline policy.
    attached_policy_arn_list: list[str] = field()  #: ARNs of existing managed policies (AWS or customer managed) to attach.
    path_access_key_json: Path = field()  #: Local JSON file ``{"access_key": ..., "secret_key": ...}``, the only copy of the secret, in plain text. Keep it out of git.
    github_user_name: str = field()  #: Owner (user or organization) of the GitHub repository.
    github_repo_name: str = field()  #: Name of the GitHub repository.
    github_token: str = field()  #: GitHub token that can write the repository's Actions secrets: classic PAT with ``repo`` scope, or fine-grained PAT with "Secrets: read and write".
    github_secret_name_aws_default_region: str = field(default="AWS_DEFAULT_REGION")  #: Name of the GitHub secret that holds the region.
    github_secret_name_aws_access_key_id: str = field(default="AWS_ACCESS_KEY_ID")  #: Name of the GitHub secret that holds the access key ID.
    github_secret_name_aws_secret_access_key: str = field(default="AWS_SECRET_ACCESS_KEY")  #: Name of the GitHub secret that holds the secret access key.
    # fmt: on

    @cached_property
    def iam_client(self) -> IAMClient:
        """
        IAM client of :attr:`boto_ses`.
        """
        return self.boto_ses.client("iam")

    @property
    def policy_document_name(self) -> str:
        """
        Name of the user's inline policy. It includes :attr:`aws_region`, so a
        new region renames the policy, and :meth:`s12_put_iam_policy` then
        deletes the policy with the old name.
        """
        return f"iam-user-{self.aws_region}-{self.iam_user_name}-inline-policy"

    @property
    def github_secrets_url(self) -> str:
        """
        URL of the repository's Actions secrets settings page.
        """
        return f"https://github.com/{self.github_user_name}/{self.github_repo_name}/settings/secrets/actions"

    @property
    def iam_user_console_url(self) -> str:
        """
        AWS console URL of the IAM user's detail page.
        """
        return (
            f"https://{self.aws_region}.console.aws.amazon.com/iam/home"
            f"?region={self.aws_region}#/users/details/{self.iam_user_name}"
        )

    @cached_property
    def gh(self) -> Github:  # pragma: no cover
        """
        GitHub client authenticated with :attr:`github_token`.
        """
        return Github(auth=Auth.Token(self.github_token))

    @cached_property
    def repo(self) -> Repository:  # pragma: no cover
        """
        The GitHub repository whose secrets this class manages.
        """
        return self.gh.get_repo(f"{self.github_user_name}/{self.github_repo_name}")

    def s11_create_iam_user(self) -> None:
        """
        Create the IAM user with :attr:`tags`. If the user already exists, sync
        its tags instead.
        """
        printer(f"🆕Step 1.1: Create IAM User {self.iam_user_name!r}")
        try:
            self.iam_client.create_user(
                UserName=self.iam_user_name,
                Tags=[{"Key": key, "Value": value} for key, value in self.tags.items()],
            )
            printer("  ✅Successfully created IAM User.")
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "EntityAlreadyExists":
                if self.tags:
                    self.iam_client.tag_user(
                        UserName=self.iam_user_name,
                        Tags=[
                            {"Key": key, "Value": value}
                            for key, value in self.tags.items()
                        ],
                    )
                printer("  ✅IAM User already exists, synced its tags.")
            else:  # pragma: no cover
                raise
        printer(f"  👀Preview at {self.iam_user_console_url}")

    def s12_put_iam_policy(self) -> None:
        """
        Make the IAM user's permissions exactly match ``policy_document`` and
        ``attached_policy_arn_list``, overwriting whatever is there now.

        - The inline policy :attr:`policy_document_name` is overwritten with
          ``policy_document``, and any other inline policy on the user is deleted.
        - Managed policies in ``attached_policy_arn_list`` are attached, and any
          other managed policy attached to the user is detached.

        It touches only the user's policies, never the user itself or its access
        keys, so it can be run on its own to hot-update the permissions of an
        existing user: edit ``policy_document`` or ``attached_policy_arn_list``,
        then run this method again. The access key and the GitHub secrets keep
        working, with the new permissions.
        """
        printer(f"🆕Step 1.2: Put IAM Policy {self.policy_document_name!r}")

        # Inline policies: overwrite ours, delete the others
        self.iam_client.put_user_policy(
            UserName=self.iam_user_name,
            PolicyName=self.policy_document_name,
            PolicyDocument=json.dumps(self.policy_document),
        )
        printer("  ✅Successfully put IAM inline policy.")
        paginator = self.iam_client.get_paginator("list_user_policies")
        for page in paginator.paginate(UserName=self.iam_user_name):
            for policy_name in page.get("PolicyNames", []):
                if policy_name != self.policy_document_name:
                    self.iam_client.delete_user_policy(
                        UserName=self.iam_user_name,
                        PolicyName=policy_name,
                    )
                    printer(f"  ✅Deleted extra inline policy {policy_name!r}")

        # Managed policies: detach the ones not in the list, attach the missing ones
        attached_arns = set()
        paginator = self.iam_client.get_paginator("list_attached_user_policies")
        for page in paginator.paginate(UserName=self.iam_user_name):
            for policy in page.get("AttachedPolicies", []):
                attached_arns.add(policy["PolicyArn"])
        wanted_arns = set(self.attached_policy_arn_list)
        for policy_arn in sorted(attached_arns - wanted_arns):
            self.iam_client.detach_user_policy(
                UserName=self.iam_user_name,
                PolicyArn=policy_arn,
            )
            printer(f"  ✅Detached policy {policy_arn}")
        for policy_arn in self.attached_policy_arn_list:
            if policy_arn in attached_arns:
                printer(f"  ✅Policy {policy_arn} already attached")
            else:
                self.iam_client.attach_user_policy(
                    UserName=self.iam_user_name,
                    PolicyArn=policy_arn,
                )
                printer(f"  ✅Successfully attached policy {policy_arn}")
        printer(f"  👀Preview at {self.iam_user_console_url}?section=permissions")

    def s13_create_or_get_access_key(
        self,
        verbose: bool = True,
    ) -> tuple[str, str]:
        """
        Return the IAM user's access key, creating it if the user has none.

        - No key in AWS: create one and write it to :attr:`path_access_key_json`
          (its folder is created if needed, the file is made readable only by
          its owner).
        - A key in AWS whose ID matches :attr:`path_access_key_json`: return it.
        - A key in AWS but no matching local file: raise, because AWS shows a
          secret only when it is created. Use :meth:`s31_rotate_access_key`.

        :param verbose: print progress.
        :returns: ``(access_key_id, secret_access_key)``.
        :raises RuntimeError: the user has a key whose secret is not saved locally.
        """
        if verbose:
            printer("🆕Step 1.3: Create or get access key")
        res = self.iam_client.list_access_keys(UserName=self.iam_user_name)
        access_key_list = res.get("AccessKeyMetadata", [])
        if len(access_key_list):
            # AWS returns the secret key only once, at creation time, so an
            # existing key is usable only if its secret is in the local file.
            existing_access_keys = [dct["AccessKeyId"] for dct in access_key_list]
            data = {}
            if self.path_access_key_json.exists():
                data = json.loads(self.path_access_key_json.read_text())
            if data.get("access_key") not in existing_access_keys:
                masked = ", ".join(
                    repr(mask_value(key)) for key in existing_access_keys
                )
                raise RuntimeError(
                    f"IAM User {self.iam_user_name!r} already has access key {masked}, "
                    f"but its secret key is not in {str(self.path_access_key_json)!r}. "
                    f"AWS shows a secret key only when it is created, so it cannot be "
                    f"recovered. Replace it with a new key: run "
                    f"'simple-gh-aws-creds rotate_key --config <config_path> --yes', "
                    f"or call s31_rotate_access_key() in Python."
                )
            access_key = data["access_key"]
            secret_key = data["secret_key"]
            if verbose:
                printer(
                    f"  ✅Found existing access key {mask_value(access_key)!r}, using it."
                )
        else:
            # create the folder first, so a failed write cannot leave a key in
            # AWS whose secret is lost
            self.path_access_key_json.parent.mkdir(parents=True, exist_ok=True)
            response = self.iam_client.create_access_key(UserName=self.iam_user_name)
            access_key = response["AccessKey"]["AccessKeyId"]
            secret_key = response["AccessKey"]["SecretAccessKey"]
            data = {"access_key": access_key, "secret_key": secret_key}
            self.path_access_key_json.write_text(json.dumps(data, indent=4))
            self.path_access_key_json.chmod(0o600)
            if verbose:
                printer(
                    f"  ✅Successfully created new access key {mask_value(access_key)!r}"
                )
        if verbose:
            printer(
                f"  👀Preview at {self.iam_user_console_url}?section=security_credentials"
            )
        return access_key, secret_key

    def s14_setup_github_secrets(self) -> None:
        """
        Write the region, the access key ID, and the secret access key to the
        three repository secrets named by ``github_secret_name_*``, overwriting
        existing values. Then print :meth:`print_github_workflow_example`.

        The key comes from :meth:`s13_create_or_get_access_key`, so a key is
        created if the user has none.

        :raises Exception: the GitHub API call failed, for example for a token
            without permission. Secrets written before the failure keep their
            new value.
        """
        printer("🆕Step 1.4: Setup GitHub Secrets")
        printer(f"  👀Preview at {self.github_secrets_url}")
        access_key, secret_key = self.s13_create_or_get_access_key(verbose=False)
        key_value_pairs = [
            (self.github_secret_name_aws_default_region, self.aws_region),
            (self.github_secret_name_aws_access_key_id, access_key),
            (self.github_secret_name_aws_secret_access_key, secret_key),
        ]
        for secret_name, value in key_value_pairs:
            try:
                self.repo.create_secret(
                    secret_name=secret_name,
                    unencrypted_value=value,
                    secret_type="actions",
                )
                printer(f"  ✅Successfully created GitHub Secret {secret_name!r}")
            except Exception as e:
                printer(f"  ❌Failed to create GitHub Secret {secret_name!r}: {e}")
                raise
        self.print_github_workflow_example()

    def print_github_workflow_example(self) -> None:
        """
        Print a GitHub Actions workflow snippet that exposes the repository secrets
        created by :meth:`s14_setup_github_secrets` as the environment variables
        the AWS CLI and SDKs read.

        See https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets
        """
        env_secret_pairs = [
            ("AWS_DEFAULT_REGION", self.github_secret_name_aws_default_region),
            ("AWS_ACCESS_KEY_ID", self.github_secret_name_aws_access_key_id),
            ("AWS_SECRET_ACCESS_KEY", self.github_secret_name_aws_secret_access_key),
        ]
        env_lines = "\n".join(
            f"      {env_name}: ${{{{ secrets.{secret_name} }}}}"
            for env_name, secret_name in env_secret_pairs
        )
        printer("📝Use these secrets in .github/workflows/*.yml:")
        printer(
            "\n"
            "jobs:\n"
            "  aws-job:\n"
            "    runs-on: ubuntu-latest\n"
            "    env:\n"
            f"{env_lines}\n"
            "    steps:\n"
            "      - run: aws sts get-caller-identity\n"
        )
        printer(
            "  ⚠️Secrets are not passed to workflows triggered by pull requests from forks."
        )
        printer(
            "  📖Read more: https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets"
        )

    def s21_delete_github_secrets(self) -> None:
        """
        Delete the three repository secrets named by ``github_secret_name_*``.
        A secret that does not exist is skipped.

        :raises Exception: the GitHub API call failed, for example for a token
            without permission.
        """
        printer("🗑Step 2.1: Delete GitHub Secrets")
        printer(f"  👀Preview at {self.github_secrets_url}")
        key_list = [
            self.github_secret_name_aws_default_region,
            self.github_secret_name_aws_access_key_id,
            self.github_secret_name_aws_secret_access_key,
        ]
        for secret_name in key_list:
            try:
                if self.repo.delete_secret(secret_name):
                    printer(f"  ✅Successfully deleted GitHub Secret {secret_name!r}")
                else:
                    printer(
                        f"  ✅GitHub Secret {secret_name!r} does not exist, nothing to delete."
                    )
            except Exception as e:
                printer(f"  ❌Failed to delete GitHub Secret {secret_name!r}: {e}")
                raise

    def s22_delete_access_key(self) -> None:
        """
        Delete every access key of the IAM user. The local
        :attr:`path_access_key_json` is not touched. Does nothing if the user
        does not exist.
        """
        printer("🗑Step 2.2: Delete access key")
        try:
            res = self.iam_client.list_access_keys(UserName=self.iam_user_name)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                printer("  ✅IAM User does not exist, nothing to delete.")
                return
            else:  # pragma: no cover
                raise
        access_key_list = res.get("AccessKeyMetadata", [])
        if len(access_key_list):
            for dct in access_key_list:
                access_key = dct["AccessKeyId"]
                self.iam_client.delete_access_key(
                    UserName=self.iam_user_name,
                    AccessKeyId=access_key,
                )
                printer(
                    f"  ✅Successfully deleted access key {mask_value(access_key)!r}"
                )
        else:
            printer("  ✅Access key does not exist, nothing to delete.")

    def s23_delete_iam_policy(self) -> None:
        """
        Remove every policy from the IAM user, so that :meth:`s24_delete_iam_user`
        can delete it.

        - Every managed policy attached to the user is detached.
        - Every inline policy on the user is deleted, not only
          :attr:`policy_document_name`: an inline policy left over from an earlier
          ``aws_region`` or added by hand would otherwise block the user deletion.
        """
        printer("🗑Step 2.3: Delete IAM Policies")

        # List first, then delete, so the pagination is not affected by the deletes
        try:
            attached_arns = list()
            paginator = self.iam_client.get_paginator("list_attached_user_policies")
            for page in paginator.paginate(UserName=self.iam_user_name):
                for policy in page.get("AttachedPolicies", []):
                    attached_arns.append(policy["PolicyArn"])
            inline_names = list()
            paginator = self.iam_client.get_paginator("list_user_policies")
            for page in paginator.paginate(UserName=self.iam_user_name):
                inline_names.extend(page.get("PolicyNames", []))
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                printer("  ✅IAM User does not exist, no policies to delete.")
                return
            else:  # pragma: no cover
                raise

        for policy_arn in attached_arns:
            self.iam_client.detach_user_policy(
                UserName=self.iam_user_name,
                PolicyArn=policy_arn,
            )
            printer(f"  ✅Successfully detached managed policy {policy_arn}")
        for policy_name in inline_names:
            self.iam_client.delete_user_policy(
                UserName=self.iam_user_name,
                PolicyName=policy_name,
            )
            printer(f"  ✅Successfully deleted inline policy {policy_name!r}.")
        if not (attached_arns or inline_names):
            printer("  ✅IAM User has no policies, nothing to delete.")

    def s24_delete_iam_user(self) -> None:
        """
        Delete the IAM user. Does nothing if the user does not exist.

        :raises botocore.exceptions.ClientError: ``DeleteConflict``, the user
            still has access keys or policies; run :meth:`s22_delete_access_key`
            and :meth:`s23_delete_iam_policy` first.
        """
        printer(f"🗑Step 2.4: Delete IAM User {self.iam_user_name!r}")
        try:
            self.iam_client.delete_user(UserName=self.iam_user_name)
            printer("  ✅Successfully deleted IAM User.")
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                printer("  ✅IAM User does not exist, nothing to delete.")
            elif e.response["Error"]["Code"] == "DeleteConflict":
                printer(
                    "  ❌IAM User still has access keys or policies, "
                    "run s22_delete_access_key() and s23_delete_iam_policy() first."
                )
                raise
            else:  # pragma: no cover
                raise

    def s31_rotate_access_key(self) -> None:
        """
        Replace the IAM user's access key with a new one, keeping the IAM user.

        Each IAM user holds exactly one access key managed by this library, so
        this method:

        1. deletes every access key of the user (:meth:`s22_delete_access_key`),
        2. creates a new key and writes it to :attr:`path_access_key_json` right
           away (:meth:`s13_create_or_get_access_key`),
        3. writes the new key to the GitHub secrets (:meth:`s14_setup_github_secrets`).

        The new key is saved locally before GitHub is touched: if step 3 raises,
        run :meth:`setup_all` again to write the saved key to GitHub. The old key
        stops working at step 1, so workflows running during the few seconds
        before step 3 fail.

        :raises RuntimeError: the IAM user does not exist.
        """
        printer(f"🔄Step 3.1: Rotate access key of IAM User {self.iam_user_name!r}")
        try:
            self.iam_client.get_user(UserName=self.iam_user_name)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                raise RuntimeError(
                    f"IAM User {self.iam_user_name!r} does not exist. Create it "
                    f"first: run 'simple-gh-aws-creds setup --config <config_path>', "
                    f"or call setup_all() in Python."
                ) from e
            else:  # pragma: no cover
                raise
        self.s22_delete_access_key()
        self.s13_create_or_get_access_key()
        self.s14_setup_github_secrets()

    def setup_all(self) -> None:
        """
        Run the setup workflow: :meth:`s11_create_iam_user`,
        :meth:`s12_put_iam_policy`, :meth:`s13_create_or_get_access_key`, and
        :meth:`s14_setup_github_secrets`. Every step is idempotent, so running it
        again also repairs a partial setup.
        """
        self.s11_create_iam_user()
        self.s12_put_iam_policy()
        self.s13_create_or_get_access_key()
        self.s14_setup_github_secrets()

    def teardown_all(self) -> None:
        """
        Run the teardown workflow: :meth:`s21_delete_github_secrets`,
        :meth:`s22_delete_access_key`, :meth:`s23_delete_iam_policy`, and
        :meth:`s24_delete_iam_user`.
        """
        self.s21_delete_github_secrets()
        self.s22_delete_access_key()
        self.s23_delete_iam_policy()
        self.s24_delete_iam_user()
