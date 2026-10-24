# -*- coding: utf-8 -*-

"""
AWS IAM User Setup Library for Open Source Projects

This module provides automated IAM user credential setup for open source projects
that need AWS access in their CI/CD pipelines. While OIDC (OpenID Connect) is the
most secure approach for AWS authentication from GitHub Actions, this library
offers a simpler, more automated alternative that's suitable for rapid deployment
and testing scenarios.

The primary motivation for this approach is to provide:

- Automated IAM user creation with minimal required permissions
- Seamless integration with GitHub Secrets for CI/CD workflows
- Quick setup for open source projects without complex OIDC configuration
- Proper cleanup capabilities to avoid resource accumulation

Security considerations:

- IAM users have long-lived credentials (less secure than temporary OIDC tokens)
- Permissions are scoped to the minimum required for the specific use case
- Access keys are stored securely in GitHub Secrets (encrypted at rest)
- Cleanup methods ensure resources don't persist unnecessarily

This approach trades some security for simplicity and automation, making it ideal
for open source projects that need quick AWS integration without the overhead
of OIDC setup and management.
"""

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
from github import Repository

printer = print


def mask_value(v: str) -> str:  # pragma: no cover
    if len(v) < 12:
        raise ValueError(f"{v} is too short")
    return f"{v[:4]}...{v[-4:]}"


@dataclass
class SetupGitHubRepo:
    """
    Automated IAM User Setup for GitHub Actions Integration

    This class orchestrates the complete lifecycle of IAM user credentials for
    open source projects. It addresses the common challenge of securely providing
    AWS access to GitHub Actions workflows without the complexity of OIDC setup.

    The automation handles both setup and cleanup phases, ensuring that credentials
    are properly managed throughout their lifecycle. This is particularly important
    for open source projects where multiple contributors may need to manage AWS
    resources but shouldn't have access to long-lived credentials.

    Key automation benefits:

    - Eliminates manual IAM user creation and policy attachment
    - Automatically configures GitHub Secrets with proper naming conventions
    - Provides idempotent operations (safe to run multiple times)
    - Includes comprehensive cleanup to prevent credential sprawl

    Security design principles:

    - Principle of least privilege (minimal required permissions only)
    - Automated credential rotation capability through recreate operations
    - Clear separation between setup and teardown operations
    - GitHub Secrets integration for secure credential storage

    :param boto_ses: Boto3 session instance for AWS API interactions, should be configured
        with appropriate credentials and region for IAM operations
    :param aws_region: AWS region identifier (e.g., 'us-east-1') where the IAM user will be created
        and used for GitHub Actions
    :param iam_user_name: Name for the IAM user that will be created for GitHub Actions automation.
        Should follow AWS naming conventions and be descriptive of its purpose
    :param tags: Dictionary of key-value pairs for tagging the IAM user, useful for resource
        management, cost tracking, and identifying the automation source
    :param policy_document: IAM policy document as a dictionary defining the minimal permissions
        required for your GitHub Actions. Should follow principle of least privilege
    :param attached_policy_arn_list: List of AWS managed policy ARNs to attach to the IAM user
        in addition to the inline policy. Use empty list if only inline policy is needed
    :param path_access_key_json: Path object pointing to a local JSON file where AWS access key
        credentials will be stored for reuse across multiple runs
    :param github_user_name: GitHub username or organization name that owns the repository
    :param github_repo_name: Name of the GitHub repository where secrets will be configured
    :param github_token: GitHub personal access token with 'repo' scope permissions to manage
        repository secrets. Should have write access to the target repository
    :param github_secret_name_aws_default_region: Name for the GitHub secret that will store
        the AWS region value (default: "AWS_DEFAULT_REGION")
    :param github_secret_name_aws_access_key_id: Name for the GitHub secret that will store
        the AWS access key ID (default: "AWS_ACCESS_KEY_ID")
    :param github_secret_name_aws_secret_access_key: Name for the GitHub secret that will store
        the AWS secret access key (default: "AWS_SECRET_ACCESS_KEY")

    .. note::
        This tool does not create IAM policies - it only attaches existing AWS managed policies
        specified in ``attached_policy_arn_list``. Policy creation is out of scope for this
        simple automation tool designed for rapid IAM user setup. If your use case requires
        complex permissions beyond a single inline policy, consider using dedicated IAM
        management tools instead. This library is optimized for simple, come-and-go scenarios
        where one inline policy should be sufficient.

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
    """

    # fmt: off
    boto_ses: boto3.Session = field()
    aws_region: str = field()
    iam_user_name: str = field()
    tags: dict[str, str] = field()
    policy_document: dict[str, T.Any] = field()
    attached_policy_arn_list: list[str] = field()
    path_access_key_json: Path = field()
    github_user_name: str = field()
    github_repo_name: str = field()
    github_token: str = field()
    github_secret_name_aws_default_region: str = field(default="AWS_DEFAULT_REGION")
    github_secret_name_aws_access_key_id: str = field(default="AWS_ACCESS_KEY_ID")
    github_secret_name_aws_secret_access_key: str = field(default="AWS_SECRET_ACCESS_KEY")

    # fmt: on

    @cached_property
    def iam_client(self):
        return self.boto_ses.client("iam")

    @property
    def policy_document_name(self) -> str:
        return f"iam-user-{self.aws_region}-{self.iam_user_name}-inline-policy"

    @property
    def github_secrets_url(self) -> str:
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
        return Github(auth=Auth.Token(self.github_token))

    @cached_property
    def repo(self) -> Repository:  # pragma: no cover
        return self.gh.get_repo(f"{self.github_user_name}/{self.github_repo_name}")

    def s11_create_iam_user(self):
        """
        Create IAM user with proper tagging for resource management.

        This method creates an IAM user specifically for CI/CD automation, eliminating
        the need for human users to share or manage AWS credentials. The tagging strategy
        enables proper resource tracking and cost attribution, which is essential for
        open source projects that may have multiple automated workflows.

        The idempotent design ensures this operation is safe to repeat, addressing
        the common scenario where setup scripts may be run multiple times during
        project configuration or troubleshooting.
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
                raise e
        printer(f"  👀Preview at {self.iam_user_console_url}")

    def s12_put_iam_policy(self):
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
        Generate or retrieve access key credentials for the IAM user.

        This method handles the critical security balance between automation and
        credential management. It reuses existing access keys when available to
        avoid key proliferation, but creates new ones when needed. The local
        storage of credentials enables consistent automation while keeping sensitive
        data out of version control.

        The design addresses the common problem of credential lifecycle management
        in CI/CD scenarios, where regenerating keys frequently would break existing
        workflows, but never rotating them poses security risks.

        Returns:
            tuple[str, str]: Access key ID and secret access key for AWS authentication
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
            response = self.iam_client.create_access_key(UserName=self.iam_user_name)
            access_key = response["AccessKey"]["AccessKeyId"]
            secret_key = response["AccessKey"]["SecretAccessKey"]
            data = {"access_key": access_key, "secret_key": secret_key}
            self.path_access_key_json.write_text(json.dumps(data, indent=4))
            if verbose:
                printer(
                    f"  ✅Successfully created new access key {mask_value(access_key)!r}"
                )
        if verbose:
            printer(
                f"  👀Preview at {self.iam_user_console_url}?section=security_credentials"
            )
        return access_key, secret_key

    def s14_setup_github_secrets(self):  # pragma: no cover
        """
        Configure GitHub repository secrets for seamless CI/CD integration.

        This method automates the GitHub Secrets configuration, eliminating the
        manual step of copying credentials between AWS and GitHub. This automation
        is crucial for open source projects where multiple contributors need to
        be able to set up CI/CD without having direct access to AWS credentials.

        The standardized secret naming convention ensures consistency across
        projects and follows GitHub Actions best practices. The automated approach
        reduces human error and ensures that all required environment variables
        are properly configured for AWS SDK authentication.

        GitHub Secrets provide secure storage with encryption at rest and in transit,
        making them suitable for storing AWS credentials in open source repositories.
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
                return
        self.print_github_workflow_example()

    def print_github_workflow_example(self):
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

    def s21_delete_github_secrets(self):  # pragma: no cover
        """
        Remove GitHub secrets to prevent credential accumulation.

        This cleanup method addresses the important security practice of removing
        unused credentials from GitHub repositories. Leaving old credentials in
        GitHub Secrets creates unnecessary security exposure and can lead to
        confusion about which credentials are currently active.

        The automated cleanup is particularly valuable for open source projects
        where manual credential management across multiple repositories becomes
        error-prone and inconsistent. This method ensures a clean slate for
        credential rotation or project decommissioning.
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

    def s22_delete_access_key(self):
        """
        Remove AWS access key to complete credential lifecycle management.

        This method ensures that AWS access keys are properly deactivated and
        removed when no longer needed. Proper access key cleanup is essential
        for security hygiene and compliance, preventing the accumulation of
        unused long-lived credentials that could be compromised.

        The method handles the common scenario where access keys may have already
        been deleted through other means, making the cleanup process robust and
        idempotent. This reliability is crucial for automated workflows that may
        be run multiple times or in different sequences.
        """
        printer(f"🗑Step 2.2: Delete access key")
        try:
            res = self.iam_client.list_access_keys(UserName=self.iam_user_name)
        except botocore.exceptions.ClientError as e:  # pragma: no cover
            if e.response["Error"]["Code"] == "NoSuchEntity":
                printer("  ✅IAM User does not exist, nothing to delete.")
                return
            else:  # pragma: no cover
                raise e
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

    def s23_delete_iam_policy(self):
        """
        Remove every policy from the IAM user, so that :meth:`s24_delete_iam_user`
        can delete it.

        - Every managed policy attached to the user is detached.
        - Every inline policy on the user is deleted, not only
          :attr:`policy_document_name`: an inline policy left over from an earlier
          ``aws_region`` or added by hand would otherwise block the user deletion.
        """
        printer(f"🗑Step 2.3: Delete IAM Policies")

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
                raise e

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

    def s24_delete_iam_user(self):
        """
        Remove IAM user to complete the full cleanup cycle.

        This final cleanup method removes the IAM user itself, completing the
        full lifecycle management of the credential automation. This step is
        essential for preventing IAM user sprawl in AWS accounts and maintaining
        good security hygiene.

        The complete cleanup capability allows projects to be easily decommissioned
        or to rotate credentials entirely by running the full teardown followed
        by a fresh setup. This approach is particularly valuable for open source
        projects with varying activity levels and contributor access patterns.
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
                raise e
            else:  # pragma: no cover
                raise e

    def s31_rotate_access_key(self):
        """
        Replace the IAM user's access key with a new one, keeping the IAM user.

        Each IAM user holds exactly one access key managed by this library, so
        this method:

        1. deletes every access key of the user (:meth:`s22_delete_access_key`),
        2. creates a new key and writes it to ``path_access_key_json`` right away
           (:meth:`s13_create_or_get_access_key`),
        3. writes the new key to the GitHub secrets (:meth:`s14_setup_github_secrets`).

        The new key is saved locally before GitHub is touched: if step 3 fails,
        :meth:`setup_all` finishes the job with the saved key. The old key stops
        working at step 1, so workflows running during the few seconds before
        step 3 fail.
        """
        printer(f"🔄Step 3.1: Rotate access key of IAM User {self.iam_user_name!r}")
        try:
            self.iam_client.get_user(UserName=self.iam_user_name)
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                raise RuntimeError(
                    f"IAM User {self.iam_user_name!r} does not exist, "
                    f"run setup first (setup_all() in Python)."
                ) from e
            else:  # pragma: no cover
                raise e
        self.s22_delete_access_key()
        self.s13_create_or_get_access_key()
        self.s14_setup_github_secrets()

    def setup_all(self):
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

    def teardown_all(self):
        """
        Run the teardown workflow: :meth:`s21_delete_github_secrets`,
        :meth:`s22_delete_access_key`, :meth:`s23_delete_iam_policy`, and
        :meth:`s24_delete_iam_user`.
        """
        self.s21_delete_github_secrets()
        self.s22_delete_access_key()
        self.s23_delete_iam_policy()
        self.s24_delete_iam_user()
