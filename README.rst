
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

``simple_gh_aws_creds`` is a Python library that automates the setup of AWS credentials for GitHub Actions workflows. It provides a simple, streamlined approach to grant your GitHub repositories the AWS permissions they need for CI/CD operations.


Overview
------------------------------------------------------------------------------
Using GitHub Actions for CI/CD is incredibly popular in the developer community, and deploying applications to AWS is equally common. But how do you give GitHub Actions the necessary AWS permissions? This library provides a simple, automated solution.

The library automates the complete workflow:

1. **Creates IAM User** - Dedicated user for your GitHub repository
2. **Attaches IAM Policies** - Minimal required permissions (inline + managed policies)
3. **Generates Access Keys** - AWS credentials for authentication
4. **Configures GitHub Secrets** - Automatically uploads credentials to your repository

For cleanup, the process reverses: removes GitHub secrets, deletes access keys, detaches policies, and removes the IAM user.


When to Use This Library
------------------------------------------------------------------------------
**✅ Ideal Use Cases:**

- **Small to Medium Projects** - Perfect for personal projects, prototypes, and small team applications
- **Rapid Development** - Need to quickly set up AWS access without complex configuration
- **Temporary Projects** - Projects with short lifecycles that need quick setup and teardown
- **Learning & Testing** - Educational projects or when experimenting with AWS services
- **Open Source Projects** - Simple automation for contributors without complex OIDC setup
- **Quick Prototyping** - When you need AWS access immediately for proof-of-concepts

**❌ When NOT to Use:**

- **Enterprise Production** - Large-scale production environments with strict security requirements
- **Long-lived Credentials** - If you need credentials that persist for months/years
- **Complex Permission Management** - When you need sophisticated IAM role hierarchies
- **Compliance Requirements** - Environments requiring audit trails, temporary credentials, or specific security standards
- **Multi-Account Strategies** - Complex AWS Organizations with cross-account access patterns

**🏆 Recommended Alternative for Production:**

For enterprise applications, **OIDC (OpenID Connect) with GitHub Actions** is the gold standard. It provides:

- Temporary, short-lived credentials
- No long-lived secrets to manage
- Better audit trails and security
- Fine-grained permission control

However, OIDC setup is more complex and requires deeper AWS knowledge. This library bridges the gap for scenarios where you need quick, automated setup with simpler requirements.


Security Considerations
------------------------------------------------------------------------------
This library trades some security for simplicity and automation:

**Security Features:**
- Principle of least privilege (minimal required permissions)
- Secure credential storage in GitHub Secrets (encrypted at rest)
- Complete cleanup capabilities to prevent credential sprawl
- Automated resource tagging for tracking and management

**Security Trade-offs:**
- Uses long-lived IAM user credentials (less secure than OIDC temporary tokens)
- Stores credentials in GitHub Secrets (still secure, but not as robust as OIDC)
- Simpler setup means less granular control over permissions


Quick Start Example
------------------------------------------------------------------------------
Here's a complete example showing how to set up AWS credentials for your GitHub repository:

.. code-block:: python

    # -*- coding: utf-8 -*-

    """
    AWS Credentials Setup for GitHub Actions - Complete Example

    This script demonstrates how to automatically set up AWS credentials for GitHub Actions
    using the simple_gh_aws_creds library. It creates an IAM user with minimal permissions,
    generates access keys, and configures GitHub repository secrets.

    Prerequisites
    ------------------------------------------------------------------------------
    1. AWS CLI configured with appropriate credentials (or use AWS profile)
    2. GitHub personal access token with 'repo' scope permissions
    3. Python dependencies installed:
       - simple-gh-aws-creds
       - boto-session-manager
       - home-secret (for secure token management)

    What this script does
    ------------------------------------------------------------------------------
    - Creates an IAM user specifically for GitHub Actions
    - Attaches minimal IAM permissions (inline policy + optional managed policies)
    - Generates AWS access keys and stores them locally
    - Configures GitHub repository secrets for CI/CD workflows
    - Provides cleanup functionality to remove all resources

    Security considerations
    ------------------------------------------------------------------------------
    - Uses principle of least privilege (minimal required permissions)
    - Stores credentials securely in GitHub Secrets (encrypted)
    - Provides complete cleanup to avoid credential sprawl
    - Access keys are long-lived (consider OIDC for production)

    Usage
    ------------------------------------------------------------------------------
    1. Customize the configuration parameters below
    2. Run setup_all() to create resources
    3. Run teardown_all() to clean up everything
    4. Switch between setup/teardown by commenting/uncommenting at the bottom
    """

    from pathlib import Path
    from boto_session_manager import BotoSesManager
    from home_secret.api import hs
    from simple_gh_aws_creds.api import SetupGitHubRepo

    # =============================================================================
    # Configuration Parameters - Customize these for your project
    # =============================================================================

    # AWS region where IAM user will be created and used
    # Choose the region closest to your infrastructure or where your main AWS resources are located
    aws_region = "us-east-1"

    # GitHub repository information
    # Replace with your actual GitHub username/organization and repository name
    github_user_name = "MacHu-GWU"  # Your GitHub username or organization name
    github_repo_name = "simple_gh_aws_creds-project"  # Your repository name

    # Create the SetupGitHubRepo instance with all configuration
    setup = SetupGitHubRepo(
        # AWS Session Configuration
        # BotoSesManager handles AWS authentication - replace profile_name with your AWS profile
        # Alternative: Use default credentials, environment variables, or IAM roles
        boto_ses=BotoSesManager(
            profile_name="bmt_app_dev_us_east_1",  # Replace with your AWS CLI profile name
            region_name=aws_region,
        ).boto_ses,

        # AWS Region (same as above for consistency)
        aws_region=aws_region,

        # IAM User Configuration
        # This will be the name of the IAM user created for GitHub Actions
        # Use a descriptive name that identifies its purpose and project
        iam_user_name="gh-ci-simple_gh_aws_creds",  # Format: gh-ci-{project-name}

        # Resource Tags (for AWS cost tracking and resource management)
        # These tags help you identify and manage resources in the AWS console
        tags={
            "tech:use_case": "for GitHub Action to list Account aliases",  # Describe what this user does
            "github_user_name": github_user_name,  # Link back to GitHub owner
            "github_repo_name": github_repo_name,  # Link back to GitHub repo
            "automation_script": f"https://github.com/{github_user_name}/{github_repo_name}/blob/main/docs/source/01-Examples/setup_dev_account.py",
        },

        # IAM Inline Policy Document
        # Define the minimal permissions needed for your GitHub Actions
        # This example allows listing account aliases - customize for your needs
        policy_document={
            "Version": "2012-10-17",  # Current IAM policy version
            "Statement": [
                {
                    "Sid": "VisualEditor1",  # Statement identifier
                    "Effect": "Allow",      # Grant permission
                    "Action": [
                        "iam:ListAccountAliases",  # Replace with actions your workflow needs
                        # Add more actions as needed:
                        # "s3:GetObject", "s3:PutObject",  # For S3 operations
                        # "lambda:InvokeFunction",         # For Lambda operations
                        # "ssm:GetParameter",              # For Parameter Store
                    ],
                    "Resource": "*",  # Scope to specific resources in production
                },
            ],
        },

        # AWS Managed Policies (optional)
        # List of existing AWS managed policy ARNs to attach to the IAM user
        # These provide pre-defined permission sets for common use cases
        attached_policy_arn_list=[
            "arn:aws:iam::aws:policy/IAMReadOnlyAccess",  # Example: Read-only IAM access
            # Common managed policies you might need:
            # "arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess",
            # "arn:aws:iam::aws:policy/AWSLambdaExecute",
            # "arn:aws:iam::aws:policy/CloudWatchLogsFullAccess",
        ],

        # Local Storage for Access Keys
        # File where AWS access keys will be stored locally for reuse
        # This file should be added to .gitignore to avoid committing credentials
        path_access_key_json=(
            Path(__file__).absolute().parent.joinpath("dev_access_key.json")
        ),

        # GitHub Repository Details (repeated for clarity)
        github_user_name=github_user_name,
        github_repo_name=github_repo_name,

        # GitHub Personal Access Token
        # This example uses home_secret library for secure token storage
        # Alternative methods:
        # - Environment variable: os.environ["GITHUB_TOKEN"]
        # - Direct string: "ghp_your_token_here" (NOT recommended for production)
        # - External secret manager integration
        github_token=hs.v("providers.github.accounts.sh.users.sh.secrets.dev.value"),

        # GitHub Secrets Configuration
        # These are the names that will be used for the GitHub repository secrets
        # Your GitHub Actions workflows will use these exact names to access AWS credentials
        github_secret_name_aws_default_region="DEV_ACC_AWS_REGION",        # AWS region secret name
        github_secret_name_aws_access_key_id="DEV_ACC_AWS_ACCESS_KEY_ID",   # AWS access key ID secret name
        github_secret_name_aws_secret_access_key="DEV_ACC_AWS_SECRET_ACCESS_KEY",  # AWS secret key secret name
    )

    # =============================================================================
    # Execution Functions - Choose setup or teardown
    # =============================================================================

    if __name__ == "__main__":

        def setup_all():
            """
            Complete setup workflow - Creates all AWS and GitHub resources

            This function runs the full setup process in the correct order:
            1. Creates IAM user in AWS
            2. Attaches IAM policies (inline + managed policies)
            3. Generates AWS access keys and stores them locally
            4. Configures GitHub repository secrets for CI/CD

            Run this function when you want to set up AWS credentials for a new project
            or when you need to recreate the credentials from scratch.

            Prerequisites:
            - AWS credentials configured (CLI profile, environment variables, or IAM role)
            - GitHub personal access token with 'repo' scope
            - Proper permissions to create IAM users and attach policies
            """
            print("🚀 Starting complete AWS credentials setup for GitHub Actions...")
            print("=" * 70)

            setup.s11_create_iam_user()          # Step 1: Create IAM user
            setup.s12_put_iam_policy()           # Step 2: Attach policies
            setup.s13_create_or_get_access_key()  # Step 3: Generate access keys
            setup.s14_setup_github_secrets()     # Step 4: Configure GitHub secrets

            print("=" * 70)
            print("✅ Setup complete! Your GitHub Actions can now use AWS credentials.")
            print(f"🔗 Check your GitHub secrets at: https://github.com/{github_user_name}/{github_repo_name}/settings/secrets/actions")
            print("📝 Example GitHub Actions workflow:")
            print("""
            name: AWS Example
            on: [push]
            jobs:
              aws-job:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v4
                  - name: Configure AWS credentials
                    uses: aws-actions/configure-aws-credentials@v4
                    with:
                      aws-access-key-id: ${{ secrets.DEV_ACC_AWS_ACCESS_KEY_ID }}
                      aws-secret-access-key: ${{ secrets.DEV_ACC_AWS_SECRET_ACCESS_KEY }}
                      aws-region: ${{ secrets.DEV_ACC_AWS_REGION }}
                  - name: Test AWS access
                    run: aws iam list-account-aliases
            """)

        def teardown_all():
            """
            Complete cleanup workflow - Removes all AWS and GitHub resources

            This function runs the full cleanup process in the correct order:
            1. Removes GitHub repository secrets
            2. Deletes AWS access keys
            3. Detaches and deletes IAM policies
            4. Deletes IAM user

            Run this function when you want to:
            - Clean up after testing
            - Rotate credentials completely
            - Decommission a project
            - Remove unused credentials for security

            ⚠️  WARNING: This will permanently delete all AWS credentials and GitHub secrets!
            Make sure your GitHub Actions workflows don't depend on these credentials before running.
            """
            print("🗑️  Starting complete cleanup of AWS credentials and GitHub secrets...")
            print("=" * 70)

            setup.s21_delete_github_secrets()  # Step 1: Remove GitHub secrets
            setup.s22_delete_access_key()      # Step 2: Delete AWS access keys
            setup.s23_delete_iam_policy()      # Step 3: Detach/delete policies
            setup.s24_delete_iam_user()        # Step 4: Delete IAM user

            print("=" * 70)
            print("✅ Cleanup complete! All AWS resources and GitHub secrets have been removed.")
            print("🔒 Your AWS account is now clean of automation credentials.")

        # =============================================================================
        # Main Execution - Choose one option below
        # =============================================================================

        # Option 1: Set up everything (uncomment to run)
        setup_all()

        # Option 2: Clean up everything (uncomment to run, comment setup_all() above)
        # teardown_all()

        # Option 3: Run individual steps (for testing or partial operations)
        # setup.s11_create_iam_user()          # Create just the IAM user
        # setup.s12_put_iam_policy()           # Attach just the policies
        # setup.s13_create_or_get_access_key()  # Generate just the access keys
        # setup.s14_setup_github_secrets()     # Configure just the GitHub secrets

        # Individual cleanup steps:
        # setup.s21_delete_github_secrets()    # Remove just GitHub secrets
        # setup.s22_delete_access_key()        # Delete just access keys
        # setup.s23_delete_iam_policy()        # Detach just policies
        # setup.s24_delete_iam_user()          # Delete just IAM user


The example above demonstrates:

- Complete configuration for a real project
- Minimal IAM permissions (``iam:ListAccountAliases``)
- Optional AWS managed policy attachment
- GitHub secrets configuration
- Both setup and teardown workflows

After running the setup, your GitHub Actions can use the credentials like this:

.. code-block:: yaml

    name: AWS Example
    on: [push]
    jobs:
      aws-job:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v4
          - name: Configure AWS credentials
            uses: aws-actions/configure-aws-credentials@v4
            with:
              aws-access-key-id: ${{ secrets.DEV_ACC_AWS_ACCESS_KEY_ID }}
              aws-secret-access-key: ${{ secrets.DEV_ACC_AWS_SECRET_ACCESS_KEY }}
              aws-region: ${{ secrets.DEV_ACC_AWS_REGION }}
          - name: Test AWS access
            run: aws iam list-account-aliases


.. _install:

Install
------------------------------------------------------------------------------

``simple_gh_aws_creds`` is released on PyPI, so all you need is to:

.. code-block:: console

    $ pip install simple-gh-aws-creds

To upgrade to latest version:

.. code-block:: console

    $ pip install --upgrade simple-gh-aws-creds
