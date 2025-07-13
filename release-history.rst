.. _release_history:

Release and Version History
==============================================================================


x.y.z (Backlog)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

**Minor Improvements**

**Bugfixes**

**Miscellaneous**


0.1.1 (2025-07-13)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Features and Improvements**

- Initial release of simple_gh_aws_creds library
- Automated IAM user creation and management for GitHub Actions
- Support for inline IAM policy attachment with minimal required permissions
- AWS managed policy attachment support via ``attached_policy_arn_list`` parameter
- GitHub repository secrets configuration for seamless CI/CD integration
- Complete cleanup workflow to remove all created resources
- Comprehensive parameter documentation with usage examples
- Educational example script with detailed inline comments

**Core Functionality**

- ``SetupGitHubRepo`` class with full lifecycle management:
  - ``s11_create_iam_user()`` - Create IAM user with resource tagging
  - ``s12_put_iam_policy()`` - Attach inline and managed policies
  - ``s13_create_or_get_access_key()`` - Generate or reuse access keys
  - ``s14_setup_github_secrets()`` - Configure repository secrets
  - ``s21_delete_github_secrets()`` - Remove GitHub secrets
  - ``s22_delete_access_key()`` - Delete AWS access keys
  - ``s23_delete_iam_policy()`` - Detach managed policies and delete inline policy
  - ``s24_delete_iam_user()`` - Remove IAM user
