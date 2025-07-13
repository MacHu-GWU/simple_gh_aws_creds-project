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
from dataclasses import dataclass, field
from pathlib import Path
from functools import cached_property

import botocore.exceptions
import boto3
from github import Github, Repository

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

    # printer(f"Preview at {url}")
    @cached_property
    def gh(self) -> Github:  # pragma: no cover
        return Github(self.github_token)

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
                printer("  ✅IAM User already exists, do nothing.")
            else:  # pragma: no cover
                raise e

    def s12_put_iam_policy(self):
        """
        Attach minimal-privilege inline policy and AWS managed policies to the IAM user.

        This method implements the principle of least privilege by attaching only
        the specific permissions required for the intended use case. Inline policies
        are used instead of managed policies to ensure tight coupling between the
        user and their permissions, making cleanup more reliable and preventing
        permission drift.

        Additionally, this method attaches any AWS managed policies specified in
        attached_policy_arn_list. It checks for existing attachments to avoid
        duplicate policy attachments.

        The approach prevents the common security anti-pattern of using overly
        broad permissions for automation, reducing the blast radius if credentials
        are ever compromised.
        """
        printer(f"🆕Step 1.2: Put IAM Policy {self.policy_document_name!r}")

        # Attach inline policy
        self.iam_client.put_user_policy(
            UserName=self.iam_user_name,
            PolicyName=self.policy_document_name,
            PolicyDocument=json.dumps(self.policy_document),
        )
        printer("  ✅Successfully put IAM inline policy.")

        # Attach AWS managed policies if specified
        if self.attached_policy_arn_list:
            for policy_arn in self.attached_policy_arn_list:
                self.iam_client.attach_user_policy(
                    UserName=self.iam_user_name,
                    PolicyArn=policy_arn,
                )
                printer(f"  ✅Successfully attached policy {policy_arn}")

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
            data = json.loads(self.path_access_key_json.read_text())
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
                self.repo.delete_secret(secret_name)
                printer(f"  ✅Successfully deleted GitHub Secret {secret_name!r}")
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
            access_key = access_key_list[0]["AccessKeyId"]
            self.iam_client.delete_access_key(
                UserName=self.iam_user_name,
                AccessKeyId=access_key,
            )
            printer(f"  ✅Successfully deleted access key {mask_value(access_key)!r}")
        else:
            printer("  ✅Access key does not exist, nothing to delete.")

    def s23_delete_iam_policy(self):
        """
        Remove IAM policies to clean up permissions and enable user deletion.

        This method removes both the inline policy and any attached AWS managed policies
        from the IAM user, which is a prerequisite for user deletion in AWS IAM.
        The cleanup of all policies prevents permission artifacts from remaining in
        the AWS account and ensures that the IAM user can be completely removed.

        The systematic approach to policy cleanup is important for maintaining
        a clean AWS environment and avoiding the common issue of orphaned policies
        that can accumulate over time in active development environments.
        """
        printer(f"🗑Step 2.3: Delete IAM Policies")

        # First, detach all managed policies
        try:
            res = self.iam_client.list_attached_user_policies(
                UserName=self.iam_user_name
            )
            attached_policies = res.get("AttachedPolicies", [])

            for policy in attached_policies:
                policy_arn = policy["PolicyArn"]
                try:
                    self.iam_client.detach_user_policy(
                        UserName=self.iam_user_name, PolicyArn=policy_arn
                    )
                    printer(f"  ✅Successfully detached managed policy {policy_arn}")
                except botocore.exceptions.ClientError as e:  # pragma: no cover
                    printer(f"  ❌Failed to detach managed policy {policy_arn}: {e}")

        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                printer("  ✅IAM User does not exist, no managed policies to detach.")
            else:  # pragma: no cover
                printer(f"  ❌Failed to list attached policies: {e}")

        # Then, delete the inline policy
        try:
            self.iam_client.delete_user_policy(
                UserName=self.iam_user_name,
                PolicyName=self.policy_document_name,
            )
            printer(
                f"  ✅Successfully deleted inline policy {self.policy_document_name!r}."
            )
        except botocore.exceptions.ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchEntity":
                printer(
                    f"  ✅Inline policy {self.policy_document_name!r} does not exist, nothing to delete."
                )
            else:  # pragma: no cover
                raise e

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
            else:  # pragma: no cover
                raise e
