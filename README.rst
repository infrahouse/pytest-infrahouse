=================
pytest-infrahouse
=================

.. image:: https://img.shields.io/pypi/v/pytest-infrahouse.svg
    :target: https://pypi.org/project/pytest-infrahouse
    :alt: PyPI version

.. image:: https://img.shields.io/pypi/pyversions/pytest-infrahouse.svg
    :target: https://pypi.org/project/pytest-infrahouse
    :alt: Python versions

.. image:: https://github.com/infrahouse/pytest-infrahouse/actions/workflows/python-CD.yml/badge.svg
    :target: https://github.com/infrahouse/pytest-infrahouse/actions/workflows/python-CD.yml
    :alt: See Build Status on GitHub Actions

A pytest plugin that provides Terraform fixtures for testing AWS infrastructure with pytest.
This plugin enables you to write unit tests that verify the actual behavior of Terraform providers,
particularly the AWS provider, by creating and managing real AWS resources during test execution.

----

Table of Contents
-----------------

* `Overview`_
* `Features`_
* `⚠️ Cost Warning`_
* `Prerequisites & Setup`_

  * `AWS Configuration`_
  * `Terraform Installation`_
  * `Python Environment`_

* `Installation`_
* `Usage`_

  * `Basic Example`_
  * `Using Custom Terraform Modules`_
  * `Command Line Options`_
  * `Long-Running Tests`_
  * `Available Fixtures`_

* `Real-World Examples`_

  * `Testing a Custom Terraform Module`_
  * `Testing Infrastructure Dependencies`_
  * `Testing Multi-Region Deployments`_
  * `Cross-Account Testing`_
  * `Testing with Multiple Fixtures`_
  * `Integration Testing Best Practices`_

* `Fixture Details`_

  * `service_network`_
  * `jumphost`_
  * `elasticsearch`_
  * `postgres`_
  * `instance_profile`_
  * `probe_role`_
  * `ses`_
  * `subzone`_
  * `Cost Summary`_

* `Troubleshooting`_

  * `Understanding State File Locations`_
  * `Manual Terraform Operations`_
  * `Common Issues`_
  * `Cross-Platform Considerations (Windows/WSL)`_
  * `Debugging Tests`_
  * `Getting Help`_

* `Best Practices`_

  * `Test Organization`_
  * `Fixture Scoping and Reuse`_
  * `Cost Management`_
  * `Security Considerations`_
  * `Performance Optimization`_
  * `Testing in CI/CD`_
  * `Documentation and Maintenance`_

* `Contributing`_
* `License`_
* `Issues`_

----

Overview
--------

This repository implements a pytest plugin with Terraform fixtures specifically designed
for pytest Terraform unit tests.
The Terraform tests allow you to verify actual behavior of Terraform providers, namely AWS, by:

* Creating real AWS infrastructure during tests
* Providing reusable fixtures for common AWS resources
* Managing resource lifecycle (creation and cleanup)
* Supporting multiple AWS regions and IAM roles
* Enabling integration testing of Terraform modules

Features
--------

* **AWS Client Fixtures**: Pre-configured boto3 clients for EC2, ELB, Route53, IAM, and more
* **Infrastructure Fixtures**: Ready-to-use fixtures for common AWS resources:

  * ``service_network`` - VPC with public/private subnets
  * ``instance_profile`` - IAM instance profile for EC2 instances
  * ``jumphost`` - EC2 jumphost with proper networking
  * ``elasticsearch`` - Elasticsearch cluster setup
  * ``postgres`` - PostgreSQL RDS instance for database testing
  * ``ses`` - Simple Email Service configuration
  * ``probe_role`` - IAM role with limited permissions
  * ``subzone`` - Route53 DNS subzone for testing

* **Terraform Integration**: Seamless integration with Terraform via ``terraform_apply`` context manager
* **Resource Management**: Automatic cleanup of AWS resources after tests (configurable)
* **Multi-Region Support**: Test across different AWS regions
* **IAM Role Support**: Assume roles for testing in different AWS accounts

⚠️ Cost Warning
---------------

**IMPORTANT:** This plugin creates REAL AWS infrastructure that incurs REAL costs.

**Estimated Monthly Costs (if resources left running 24/7):**

* ``service_network``: ~$100-150 (NAT Gateways: $32/month each)
* ``jumphost``: ~$50-80 (EC2, NLB, EFS)
* ``elasticsearch``: ~$200-300 (4 EC2 instances, Load Balancers, EBS)
* **All fixtures combined**: ~$350-530/month

**Actual Test Costs (typical runs):**

* Short test (<5 minutes): ~$0.10-0.50
* Medium test (1 hour): ~$1-2
* Long test (8 hours): ~$5-10

**Cost Reduction Strategies:**

1. **Resources are destroyed automatically** after tests complete (default behavior)
2. **Use** ``--keep-after`` **flag cautiously** - only when debugging, remember to clean up manually
3. Run tests in cost-effective AWS regions (us-east-1 is typically cheapest)
4. Monitor and clean up orphaned resources regularly:

   .. code-block:: bash

       # Find resources created by tests
       aws resourcegroupstaggingapi get-resources \
           --tag-filters Key=created_by_test,Values=test_*

       # Check for specific fixture resources
       aws resourcegroupstaggingapi get-resources \
           --tag-filters Key=created_by_fixture,Values=infrahouse*

5. **Set up AWS Budgets** and billing alerts for your test account
6. **Use a dedicated AWS account** for testing with spend limits

**Best Practices:**

* Review the `Fixture Details`_ section to understand what each fixture creates
* Run tests in isolated AWS accounts when possible
* Clean up failed test resources promptly
* Monitor your AWS billing console regularly

Prerequisites & Setup
---------------------

Before using pytest-infrahouse, ensure you have the following prerequisites configured.

AWS Configuration
~~~~~~~~~~~~~~~~~

1. **AWS Account**

   You need an AWS account with billing enabled. If you don't have one, create an account at https://aws.amazon.com/

2. **AWS Credentials**

   Configure AWS credentials using one of these methods:

   .. code-block:: bash

       # Option 1: AWS CLI (recommended)
       aws configure
       # Follow prompts to enter Access Key ID, Secret Access Key, and default region

       # Option 2: Environment variables
       export AWS_ACCESS_KEY_ID=your_access_key_id
       export AWS_SECRET_ACCESS_KEY=your_secret_access_key
       export AWS_DEFAULT_REGION=us-east-1

       # Option 3: AWS credentials file (~/.aws/credentials)
       [default]
       aws_access_key_id = your_access_key_id
       aws_secret_access_key = your_secret_access_key

   Verify your credentials:

   .. code-block:: bash

       aws sts get-caller-identity

3. **IAM Permissions**

   Your AWS user/role needs extensive permissions to create infrastructure:

   * **EC2**: VPC, subnets, instances, security groups, key pairs
   * **IAM**: roles, policies, instance profiles
   * **Route53**: hosted zones, DNS records
   * **ELB**: Application and Network Load Balancers, target groups
   * **S3**: buckets for logs and snapshots
   * **Auto Scaling**: Auto Scaling groups and launch configurations
   * **CloudWatch**: log groups (for VPC Flow logs)

   **Recommendation**: For testing, start with the ``PowerUserAccess`` AWS managed policy, then refine permissions as needed.

4. **Route53 Hosted Zone** (Required)

   The plugin requires a Route53 hosted zone for DNS records. Create one if you don't have it:

   .. code-block:: bash

       # Create a test zone
       aws route53 create-hosted-zone \
           --name test.example.com \
           --caller-reference $(date +%s)

       # Or list existing zones
       aws route53 list-hosted-zones

   You'll pass this zone name via ``--test-zone-name`` when running tests.

Terraform Installation
~~~~~~~~~~~~~~~~~~~~~~

Install Terraform on your system:

.. code-block:: bash

    # macOS (using Homebrew)
    brew tap hashicorp/tap
    brew install hashicorp/tap/terraform

    # Linux (Ubuntu/Debian)
    wget -O- https://apt.releases.hashicorp.com/gpg | \
        sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
        https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
        sudo tee /etc/apt/sources.list.d/hashicorp.list
    sudo apt update && sudo apt install terraform

    # Windows (using Chocolatey)
    choco install terraform

    # Verify installation
    terraform version

**Required Terraform version**: 1.0+

Python Environment
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Ensure Python 3.10+ is installed
    python --version

    # Create a virtual environment (recommended)
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

    # Verify pytest is available
    pytest --version

Installation
------------

You can install "pytest-infrahouse" via `pip`_ from `PyPI`_::

    $ pip install pytest-infrahouse

For development::

    $ pip install -e .

Usage
-----

Basic Example
~~~~~~~~~~~~~

.. code-block:: python

    def test_my_vpc(service_network, aws_region):
        """Test that creates a VPC and verifies its configuration."""
        vpc_id = service_network["vpc_id"]["value"]
        assert vpc_id.startswith("vpc-")

Using Custom Terraform Modules
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from pytest_infrahouse import terraform_apply

    def test_custom_infrastructure(aws_region, test_role_arn, request):
        module_path = "path/to/terraform/module"
        
        # Write terraform.tfvars
        with open(f"{module_path}/terraform.tfvars", "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            if test_role_arn:
                fp.write(f'role_arn = "{test_role_arn}"\n')
        
        # Apply Terraform and test
        with terraform_apply(module_path, destroy_after=True) as tf_output:
            assert tf_output["resource_name"]["value"] == "expected_value"

Command Line Options
~~~~~~~~~~~~~~~~~~~~

The plugin adds several command-line options::

    pytest --test-zone-name example.com          # Set DNS zone for tests
    pytest --aws-region us-west-2               # Set AWS region
    pytest --test-role-arn arn:aws:iam::123:role/test-role  # Set IAM role
    pytest --test-role-duration 3600            # Session duration in seconds (default: 3600)
    pytest --keep-after                         # Don't destroy resources after tests

Long-Running Tests
~~~~~~~~~~~~~~~~~~

For long-running Terraform tests (>1 hour), the plugin automatically refreshes AWS credentials:

* When ``--test-role-arn`` is specified, credentials are automatically refreshed before expiration
* Works around the 1-hour AWS limit for chained role assumptions
* Allows tests to run indefinitely without credential expiration errors
* The ``--test-role-duration`` option sets the duration for each credential refresh (default: 3600 seconds)

**Note:** When role chaining (assuming a role from temporary credentials), AWS enforces
a hard 1-hour maximum per session. The plugin detects this and automatically caps the
duration at 3600 seconds, then refreshes credentials as needed.

Available Fixtures
~~~~~~~~~~~~~~~~~~

**AWS Client Fixtures:**

* ``boto3_session`` - Configured boto3 session
* ``ec2_client`` - EC2 client
* ``route53_client`` - Route53 client  
* ``elbv2_client`` - ELBv2 client
* ``iam_client`` - IAM client
* ``autoscaling_client`` - Auto Scaling client

**Infrastructure Fixtures:**

* ``service_network`` - VPC with public/private subnets, internet gateway
* ``instance_profile`` - IAM instance profile for EC2
* ``jumphost`` - EC2 jumphost in the service network
* ``elasticsearch`` - Elasticsearch cluster
* ``postgres`` - PostgreSQL RDS instance
* ``ses`` - Simple Email Service setup
* ``probe_role`` - IAM role with limited permissions
* ``subzone`` - Route53 DNS subzone for testing

**Configuration Fixtures:**

* ``aws_region`` - AWS region for tests
* ``test_role_arn`` - IAM role ARN to assume
* ``test_role_duration`` - Duration in seconds for assumed role sessions (default: 3600)
* ``test_zone_name`` - Route53 zone name
* ``keep_after`` - Whether to keep resources after tests

Real-World Examples
-------------------

This section demonstrates practical testing scenarios using pytest-infrahouse fixtures.

Testing a Custom Terraform Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** You have a custom Terraform module that creates an RDS database in a VPC,
and you want to verify it works correctly.

.. code-block:: python

    import pytest
    from pytest_infrahouse import terraform_apply

    def test_rds_module_creates_database(
        service_network,
        aws_region,
        test_role_arn,
        request
    ):
        """Test that our RDS module creates a functional database."""
        # Get VPC info from service_network fixture
        vpc_id = service_network["vpc_id"]["value"]
        private_subnets = service_network["subnet_private_ids"]["value"]

        # Configure our custom Terraform module
        module_path = "tests/terraform/rds-module"
        with open(f"{module_path}/terraform.tfvars", "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            fp.write(f'vpc_id = "{vpc_id}"\n')
            fp.write(f'subnet_ids = {private_subnets}\n')
            if test_role_arn:
                fp.write(f'role_arn = "{test_role_arn}"\n')

        # Apply Terraform and verify
        with terraform_apply(module_path, destroy_after=True) as outputs:
            db_instance_id = outputs["db_instance_id"]["value"]
            db_endpoint = outputs["db_endpoint"]["value"]

            # Verify database was created
            import boto3
            rds = boto3.client('rds', region_name=aws_region)
            response = rds.describe_db_instances(
                DBInstanceIdentifier=db_instance_id
            )

            assert len(response["DBInstances"]) == 1
            assert response["DBInstances"][0]["DBInstanceStatus"] == "available"
            assert response["DBInstances"][0]["DBSubnetGroup"]["VpcId"] == vpc_id

Testing Infrastructure Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Verify that a Lambda function can access resources in your VPC.

.. code-block:: python

    def test_lambda_vpc_access(
        service_network,
        instance_profile,
        aws_region
    ):
        """Test Lambda function has correct VPC configuration."""
        vpc_id = service_network["vpc_id"]["value"]
        private_subnets = service_network["subnet_private_ids"]["value"]
        role_arn = instance_profile["test_role_arn"]["value"]

        # Your Lambda function should be able to:
        # 1. Run in the private subnets
        # 2. Have network access within the VPC
        # 3. Use the instance profile for permissions

        assert len(private_subnets) >= 2  # Multiple AZs for HA
        assert vpc_id.startswith("vpc-")
        assert "arn:aws:iam::" in role_arn

Testing Multi-Region Deployments
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Test that your infrastructure works correctly when deployed to multiple AWS regions.

.. code-block:: python

    import pytest

    @pytest.mark.parametrize("region", ["us-east-1", "us-west-2", "eu-west-1"])
    def test_multi_region_deployment(region):
        """Test infrastructure deployment across multiple regions."""
        # Use pytest's parametrize to run the same test in different regions
        # Pass --aws-region via command line or use region parameter
        pass

Run with:

.. code-block:: bash

    # Test in specific region
    pytest tests/test_multi_region.py --aws-region us-west-2

    # Test across multiple regions (run separately)
    for region in us-east-1 us-west-2 eu-west-1; do
        pytest tests/test_multi_region.py --aws-region $region
    done

Cross-Account Testing
~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Test that your infrastructure works when deployed to a different AWS account via role assumption.

.. code-block:: python

    def test_cross_account_deployment(
        service_network,
        test_role_arn,
        aws_region
    ):
        """Test infrastructure in a different AWS account."""
        # The test_role_arn fixture will contain the assumed role
        # All AWS API calls will use the assumed role's credentials

        assert test_role_arn  # Verify role was assumed

        # Infrastructure created by fixtures will be in the target account
        vpc_id = service_network["vpc_id"]["value"]

        # Verify we're in the correct account
        import boto3
        sts = boto3.client('sts', region_name=aws_region)
        identity = sts.get_caller_identity()

        # The account ID should match the role's account
        expected_account = test_role_arn.split(":")[4]
        assert identity["Account"] == expected_account

Run with:

.. code-block:: bash

    pytest tests/test_cross_account.py \
        --test-role-arn arn:aws:iam::987654321098:role/CrossAccountTestRole \
        --aws-region us-west-2

Testing with Multiple Fixtures
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Test a complete application stack using multiple fixtures together.

.. code-block:: python

    def test_complete_application_stack(
        service_network,
        jumphost,
        elasticsearch,
        ses,
        aws_region
    ):
        """Test a complete application stack with all components."""
        # Network layer
        vpc_id = service_network["vpc_id"]["value"]
        private_subnets = service_network["subnet_private_ids"]["value"]

        # Compute layer (jumphost for access)
        jumphost_hostname = jumphost["jumphost_hostname"]["value"]

        # Data layer (Elasticsearch)
        es_url = elasticsearch["cluster_master_url"]["value"]
        es_password = elasticsearch["elastic_password"]["value"]

        # Communication layer (SES)
        email_domain = ses["domain"]["value"]

        # Verify all components are in the same VPC
        assert vpc_id.startswith("vpc-")
        assert len(private_subnets) >= 2

        # Verify connectivity (jumphost can reach Elasticsearch)
        assert jumphost_hostname
        assert es_url.startswith("https://")

        # Verify email domain is configured
        assert "." in email_domain

    # Note: This test will take 20-30 minutes due to Elasticsearch bootstrap
    # Mark it as slow to run separately
    import pytest
    pytestmark = pytest.mark.slow

Integration Testing Best Practices
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Organize tests by component:**

.. code-block:: python

    # tests/test_networking.py - Network-focused tests
    def test_vpc_configuration(service_network):
        """Verify VPC is properly configured."""
        pass

    # tests/test_compute.py - Compute-focused tests
    def test_jumphost_access(jumphost, service_network):
        """Verify jumphost is accessible."""
        pass

    # tests/test_data.py - Data layer tests
    def test_elasticsearch_cluster(elasticsearch):
        """Verify Elasticsearch cluster is healthy."""
        pass

**Use pytest marks for test organization:**

.. code-block:: python

    import pytest

    @pytest.mark.slow
    def test_elasticsearch_full_cluster(elasticsearch):
        """Long-running test for Elasticsearch."""
        pass

    @pytest.mark.smoke
    def test_basic_connectivity(service_network):
        """Quick smoke test."""
        pass

Run specific test categories:

.. code-block:: bash

    # Run only fast tests
    pytest -m "not slow"

    # Run only smoke tests
    pytest -m smoke

    # Run slow tests separately (e.g., in nightly CI)
    pytest -m slow

Fixture Details
---------------

This section provides comprehensive documentation for each infrastructure fixture,
including resources created, outputs available, dependencies, and estimated costs.

service_network
~~~~~~~~~~~~~~~

**Purpose:** Creates a complete VPC with networking infrastructure for testing AWS resources.

**Resources Created:**

* VPC with configurable CIDR block
* 2 public subnets across 2 availability zones
* 2 private subnets across 2 availability zones
* Internet Gateway
* NAT Gateways (one per AZ)
* Route tables with proper routing
* VPC Flow logs (optional)

**Outputs:**

* ``vpc_id`` - The VPC identifier
* ``subnet_public_ids`` - List of public subnet IDs
* ``subnet_private_ids`` - List of private subnet IDs
* ``internet_gateway_id`` - Internet Gateway ID
* ``vpc_cidr_block`` - VPC CIDR block
* ``management_cidr_block`` - Management VPC CIDR block
* ``route_table_all_ids`` - All route table IDs
* ``subnet_all_ids`` - All subnet IDs (public + private)
* ``vpc_flow_bucket_name`` - S3 bucket for VPC Flow logs

**Dependencies:** None (foundational fixture)

**Estimated Cost:** ~$100-150/month (mostly NAT Gateways: $32/month each + data transfer)

**Example:**

.. code-block:: python

    def test_vpc_configuration(service_network):
        """Verify VPC is created with correct subnet configuration."""
        vpc_id = service_network["vpc_id"]["value"]
        public_subnets = service_network["subnet_public_ids"]["value"]
        private_subnets = service_network["subnet_private_ids"]["value"]

        assert vpc_id.startswith("vpc-")
        assert len(public_subnets) == 2
        assert len(private_subnets) == 2

jumphost
~~~~~~~~

**Purpose:** Creates a bastion host for accessing private resources in the VPC.

**Resources Created:**

* EC2 Auto Scaling Group (min: 1, max: 1)
* Network Load Balancer for SSH access
* EFS file system for persistent home directories (encrypted at rest, mandatory)
* IAM instance profile with necessary permissions
* Route53 DNS record for easy access
* Security groups for jumphost access

**Outputs:**

* ``jumphost_role_arn`` - IAM role ARN
* ``jumphost_role_name`` - IAM role name
* ``jumphost_hostname`` - DNS hostname for SSH access
* ``jumphost_instance_profile_arn`` - Instance profile ARN
* ``jumphost_instance_profile_name`` - Instance profile name
* ``jumphost_asg_name`` - Auto Scaling Group name

**Dependencies:**

* ``service_network`` (requires VPC and subnets)
* ``subzone`` (for DNS record)

**Estimated Cost:** ~$50-80/month (t3.micro EC2 ~$8 + NLB ~$16 + EFS ~$0.30/GB + data transfer)

**Example:**

.. code-block:: python

    def test_jumphost_ssh_access(jumphost, service_network):
        """Test jumphost is accessible and in correct VPC."""
        hostname = jumphost["jumphost_hostname"]["value"]
        role_arn = jumphost["jumphost_role_arn"]["value"]

        assert hostname.endswith(".example.com")
        assert "jumphost" in role_arn

elasticsearch
~~~~~~~~~~~~~

**Purpose:** Deploys a functional Elasticsearch cluster for testing search and analytics features.

**Resources Created:**

* 3 master nodes (for quorum/consensus)
* 1 data node (testing purposes, no redundancy)
* Application Load Balancers (master + data)
* Security groups for cluster communication
* IAM roles and policies
* S3 bucket for snapshots
* Route53 DNS records

**Outputs:**

* ``elastic_password`` - Elastic superuser password (sensitive)
* ``kibana_system_password`` - Kibana system password (sensitive)
* ``cluster_name`` - Name of the Elasticsearch cluster
* ``cluster_master_url`` - URL to access master nodes
* ``zone_id`` - Route53 zone ID
* ``subnet_ids`` - Subnet IDs where nodes are deployed
* ``master_load_balancer_arn`` - Master node load balancer ARN
* ``master_target_group_arn`` - Master target group ARN
* ``data_load_balancer_arn`` - Data node load balancer ARN
* ``data_target_group_arn`` - Data target group ARN
* ``snapshots_bucket`` - S3 bucket name for backups
* ``master_instance_role_arn`` - Master node IAM role ARN
* ``data_instance_role_arn`` - Data node IAM role ARN

**Dependencies:**

* ``service_network`` (requires VPC and subnets)
* ``subzone`` (for DNS records)

**Bootstrap Mode:** This fixture requires two Terraform applies (handled automatically by the plugin):

1. First apply creates the cluster infrastructure
2. Second apply configures the cluster settings

**Estimated Cost:** ~$200-300/month (4x t3.medium EC2 ~$120 + 2x ALB ~$32 + EBS volumes ~$40 + S3)

**Example:**

.. code-block:: python

    def test_elasticsearch_cluster(elasticsearch):
        """Test Elasticsearch cluster is functional."""
        cluster_url = elasticsearch["cluster_master_url"]["value"]
        password = elasticsearch["elastic_password"]["value"]

        # Cluster URL should be accessible
        assert cluster_url.startswith("https://")
        assert password  # Password should be generated

postgres
~~~~~~~~

**Purpose:** Creates a PostgreSQL RDS instance for testing database operations and integrations.

**Resources Created:**

* PostgreSQL RDS instance (configurable version and instance class)
* DB subnet group for multi-AZ deployment
* Security group with PostgreSQL access rules
* Secrets Manager secret for credentials storage
* IAM role for Enhanced Monitoring (optional)
* Random password generation with secure storage
* Time delay to ensure database is ready

**Outputs:**

* ``endpoint`` - Full connection endpoint (host:port)
* ``address`` - Database hostname
* ``port`` - Database port (5432)
* ``database_name`` - Default database name
* ``master_username`` - Master username
* ``master_password`` - Master password (sensitive)
* ``secret_arn`` - ARN of Secrets Manager secret with credentials
* ``secret_name`` - Name of Secrets Manager secret
* ``instance_id`` - RDS resource ID (internal AWS identifier like db-XXX)
* ``instance_identifier`` - RDS instance identifier (user-defined name)
* ``instance_arn`` - RDS instance ARN
* ``instance_class`` - Instance type (default: db.t3.micro)
* ``engine_version`` - PostgreSQL version
* ``security_group_id`` - Security group ID
* ``db_subnet_group_name`` - DB subnet group name
* ``availability_zone`` - Deployment AZ
* ``connection_string`` - PostgreSQL connection URI (sensitive)
* ``jdbc_connection_string`` - JDBC connection string

**Dependencies:**

* ``service_network`` (requires VPC and private subnets for RDS subnet group)

**Estimated Cost:** ~$15-25/month (db.t3.micro ~$13 + storage ~$2-5 + optional backups)

**Configuration Options:**

* PostgreSQL version (default: 16.6)
* Instance class (default: db.t3.micro)
* Storage size (default: 20GB, autoscaling to 100GB)
* Performance Insights (enabled by default for PMM integration)
* Enhanced Monitoring (enabled by default for comprehensive metrics)
* CloudWatch logs export (enabled by default: postgresql, upgrade logs)

**Example:**

.. code-block:: python

    def test_postgres_database(postgres, secretsmanager_client):
        """Test PostgreSQL RDS instance is functional."""
        # Connection details
        endpoint = postgres["endpoint"]["value"]
        database = postgres["database_name"]["value"]
        username = postgres["master_username"]["value"]

        # Verify database is accessible
        assert endpoint  # host:port format
        assert database == "testdb"
        assert username == "pytest_admin"

        # Get password from Secrets Manager
        secret_arn = postgres["secret_arn"]["value"]
        secret = secretsmanager_client.get_secret_value(SecretId=secret_arn)

        # Use psycopg2 or SQLAlchemy to connect
        connection_string = postgres["connection_string"]["value"]
        assert connection_string.startswith("postgresql://")

instance_profile
~~~~~~~~~~~~~~~~

**Purpose:** Creates an IAM instance profile with basic STS permissions for EC2 instances.

**Resources Created:**

* IAM role with trust policy for EC2
* IAM policy with ``sts:GetCallerIdentity`` permission
* IAM instance profile

**Outputs:**

* ``instance_profile_arn`` - Instance profile ARN
* ``instance_profile_name`` - Instance profile name
* ``test_role_arn`` - IAM role ARN
* ``test_role_name`` - IAM role name

**Dependencies:** None

**Estimated Cost:** $0 (IAM resources are free)

**Example:**

.. code-block:: python

    def test_instance_profile(instance_profile):
        """Verify instance profile has correct permissions."""
        profile_arn = instance_profile["instance_profile_arn"]["value"]
        role_arn = instance_profile["test_role_arn"]["value"]

        assert "instance-profile" in profile_arn
        assert "role" in role_arn

probe_role
~~~~~~~~~~

**Purpose:** Creates an IAM role with limited permissions for testing role assumption and permissions.

**Resources Created:**

* IAM role with trust policy (assumes current caller's role)
* IAM policy with ``sts:GetCallerIdentity`` permission
* Named resources for easy identification (``pytest-probe-*``)

**Outputs:**

* ``test_role_arn`` - IAM role ARN
* ``test_role_name`` - IAM role name

**Dependencies:** None

**Estimated Cost:** $0 (IAM resources are free)

**Example:**

.. code-block:: python

    def test_probe_role_assumption(probe_role, boto3_session):
        """Test we can assume the probe role."""
        role_arn = probe_role["test_role_arn"]["value"]

        # Attempt to assume the role
        sts = boto3_session.client('sts')
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName='test-session'
        )
        assert response['Credentials']

ses
~~~

**Purpose:** Configures AWS Simple Email Service for testing email functionality.

**Resources Created:**

* SES domain identity
* SES domain verification records in Route53
* DKIM configuration
* Email sending policies

**Outputs:**

* ``domain`` - Verified domain name
* ``zone_id`` - Route53 zone ID

**Dependencies:**

* ``subzone`` (requires Route53 zone for domain verification)

**Estimated Cost:** ~$0-1/month (SES is $0.10 per 1,000 emails, minimal during testing)

**Example:**

.. code-block:: python

    def test_ses_domain_verified(ses, aws_region):
        """Test SES domain is verified and ready."""
        domain = ses["domain"]["value"]

        # Domain should be configured
        assert domain
        assert "." in domain  # Should be a valid domain

subzone
~~~~~~~

**Purpose:** Creates a Route53 DNS subzone for test isolation and DNS record management.

**Resources Created:**

* Route53 hosted zone (subdomain)
* NS record delegation in parent zone
* Random subdomain prefix for test isolation

**Outputs:**

* ``zone_id`` - Route53 hosted zone ID
* ``name_servers`` - List of authoritative name servers
* ``subzone_name`` - Full subdomain name

**Dependencies:**

* Requires parent Route53 zone (specified via ``--test-zone-name``)

**Estimated Cost:** ~$0.50/month ($0.50 per hosted zone + $0.40 per million queries)

**Example:**

.. code-block:: python

    def test_subzone_delegation(subzone):
        """Test DNS subzone is properly delegated."""
        zone_id = subzone["zone_id"]["value"]
        subzone_name = subzone["subzone_name"]["value"]
        name_servers = subzone["name_servers"]["value"]

        assert zone_id.startswith("Z")
        assert len(name_servers) == 4  # AWS provides 4 name servers

Cost Summary
~~~~~~~~~~~~

**Total estimated monthly cost if all fixtures run continuously:**

* service_network: ~$100-150
* jumphost: ~$50-80
* elasticsearch: ~$200-300
* postgres: ~$15-25
* instance_profile: $0
* probe_role: $0
* ses: ~$0-1
* subzone: ~$0.50

**Total: ~$365-555/month**

**Important Notes:**

* These are estimates for resources running 24/7 for a full month
* Actual test costs are much lower (typically $0.10-$2 per test run)
* Resources are automatically destroyed after tests (unless ``--keep-after`` is used)
* NAT Gateways and Load Balancers are the most expensive components
* Use ``--keep-after`` cautiously to avoid unexpected charges

Troubleshooting
---------------

Understanding State File Locations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When using pytest-infrahouse fixtures, Terraform state files are stored in the Python site-packages
directory where the plugin is installed. This is important for manual debugging and resource cleanup.

**State File Location Pattern:**

.. code-block:: bash

    <python-site-packages>/pytest_infrahouse/data/<fixture-name>/terraform.tfstate

**Finding Your State Files:**

.. code-block:: bash

    # Find your Python site-packages directory
    python -c "import pytest_infrahouse; import os; print(os.path.dirname(pytest_infrahouse.__file__))"

    # Example output: /home/user/.virtualenvs/myproject/lib/python3.12/site-packages/pytest_infrahouse

    # State files are in the data subdirectory
    # For service_network fixture:
    ls ~/.virtualenvs/myproject/lib/python3.12/site-packages/pytest_infrahouse/data/service-network/

**Real-World Example:**

If you're developing a module ``terraform-aws-pmm-ecs`` and using the ``service_network`` fixture:

.. code-block:: bash

    # Your test file (Windows host)
    C:\Users\username\code\terraform-aws-pmm-ecs\tests\test_basic.py

    # Virtual environment (WSL/Linux)
    /home/username/.virtualenvs/terraform-aws-pmm-ecs/bin/python

    # State file location
    /home/username/.virtualenvs/terraform-aws-pmm-ecs/lib/python3.12/site-packages/pytest_infrahouse/data/service-network/terraform.tfstate

Manual Terraform Operations
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once you know where the state file is, you can perform manual Terraform operations:

**Inspect Resources:**

.. code-block:: bash

    # Navigate to fixture directory
    cd ~/.virtualenvs/myproject/lib/python3.12/site-packages/pytest_infrahouse/data/service-network

    # List all resources in state
    terraform state list

    # Example output:
    # data.aws_availability_zones.available
    # data.aws_caller_identity.this
    # module.service-network.aws_vpc.main
    # module.service-network.aws_subnet.public[0]
    # module.service-network.aws_nat_gateway.main[0]

    # Show detailed resource information
    terraform state show module.service-network.aws_vpc.main

**Taint Resources (force recreation on next apply):**

.. code-block:: bash

    cd ~/.virtualenvs/myproject/lib/python3.12/site-packages/pytest_infrahouse/data/service-network
    terraform taint module.service-network.aws_nat_gateway.main[0]

**Manually Destroy Resources:**

.. code-block:: bash

    cd ~/.virtualenvs/myproject/lib/python3.12/site-packages/pytest_infrahouse/data/service-network
    terraform destroy -auto-approve

    # Or destroy specific resources
    terraform destroy -target=module.service-network.aws_nat_gateway.main[0] -auto-approve

**Import Existing Resources:**

.. code-block:: bash

    cd ~/.virtualenvs/myproject/lib/python3.12/site-packages/pytest_infrahouse/data/service-network
    terraform import module.service-network.aws_vpc.main vpc-12345678

Common Issues
~~~~~~~~~~~~~

**Problem:** ``terraform not found in PATH``

**Solution:**

.. code-block:: bash

    # Check if Terraform is installed
    which terraform  # Linux/macOS
    where terraform  # Windows

    # Install if missing (see Prerequisites & Setup section)
    brew install terraform  # macOS
    # or download from https://www.terraform.io/downloads

**Problem:** ``AWS credential errors`` or ``Unable to locate credentials``

**Solution:**

.. code-block:: bash

    # Verify credentials are configured
    aws sts get-caller-identity

    # Check credential configuration
    cat ~/.aws/credentials
    cat ~/.aws/config

    # Set credentials via environment variables
    export AWS_ACCESS_KEY_ID=your_key_id
    export AWS_SECRET_ACCESS_KEY=your_secret_key
    export AWS_DEFAULT_REGION=us-east-1

**Problem:** ``Route53 zone not found`` or ``InvalidInput: Invalid domain name``

**Solution:**

.. code-block:: bash

    # List your hosted zones
    aws route53 list-hosted-zones

    # Verify zone name format (must match exactly, including trailing dot if present)
    pytest --test-zone-name example.com tests/

**Problem:** ``Resources not cleaned up after test failure``

**Solution:**

.. code-block:: bash

    # Find the state file location
    python -c "import pytest_infrahouse; import os; print(os.path.dirname(pytest_infrahouse.__file__))"

    # Navigate to fixture directory and manually destroy
    cd <site-packages>/pytest_infrahouse/data/service-network
    terraform destroy -auto-approve

    # Or find orphaned resources by tags
    aws resourcegroupstaggingapi get-resources \
        --tag-filters Key=created_by_fixture,Values=infrahouse*

    # Delete specific resources via AWS CLI
    aws ec2 delete-nat-gateway --nat-gateway-id nat-12345678
    aws ec2 delete-subnet --subnet-id subnet-12345678

**Problem:** ``Elasticsearch bootstrap mode timeout`` or ``Error waiting for Elasticsearch cluster``

**Explanation:** The elasticsearch fixture requires two Terraform applies (bootstrap mode):

1. First apply creates the cluster infrastructure
2. Second apply configures the cluster settings

This is normal and handled automatically by the plugin. The process takes 15-20 minutes.

**Solution:** If it times out, check:

.. code-block:: bash

    # Check Elasticsearch cluster health
    curl -u elastic:<password> https://<cluster-url>/_cluster/health

    # Manually run second apply if needed
    cd <site-packages>/pytest_infrahouse/data/elasticsearch
    terraform apply -auto-approve

**Problem:** ``ChainedRole error: Cannot assume role from temporary credentials``

**Explanation:** When role chaining (assuming a role from temporary credentials), AWS enforces
a hard 1-hour maximum per session.

**Solution:** The plugin handles this automatically by refreshing credentials. If you see this error:

.. code-block:: bash

    # Verify your role ARN is correct
    aws sts get-caller-identity

    # Check role trust policy allows assumption
    aws iam get-role --role-name YourRoleName

    # Use shorter duration if needed
    pytest --test-role-duration 1800 tests/  # 30 minutes

**Problem:** ``State file is locked`` or ``Error locking state``

**Solution:**

.. code-block:: bash

    # If using remote backend, wait for lock to clear
    # Or force unlock (use with caution!)
    cd <site-packages>/pytest_infrahouse/data/service-network
    terraform force-unlock <lock-id>

    # If using local state, ensure no other processes are running
    ps aux | grep terraform
    kill <pid>  # if necessary

**Problem:** ``Module not found`` or ``Could not load plugin``

**Solution:**

.. code-block:: bash

    # Re-initialize Terraform in the fixture directory
    cd <site-packages>/pytest_infrahouse/data/service-network
    terraform init -upgrade

    # Or reinstall pytest-infrahouse
    pip install --force-reinstall pytest-infrahouse

Cross-Platform Considerations (Windows/WSL)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you're using Windows with WSL (Windows Subsystem for Linux):

**Path Differences:**

* **Windows host:** ``C:\Users\username\code\myproject``
* **WSL Linux:** ``/home/username/.virtualenvs/myproject``

**State files are in WSL if pytest runs in WSL:**

.. code-block:: bash

    # From Windows PowerShell, access WSL filesystem
    cd \\wsl$\Ubuntu\home\username\.virtualenvs\myproject\lib\python3.12\site-packages\pytest_infrahouse\data\service-network

    # Or from WSL, navigate directly
    cd ~/.virtualenvs/myproject/lib/python3.12/site-packages/pytest_infrahouse/data/service-network

**AWS Credentials:**

* Ensure AWS credentials are configured in the environment where pytest runs
* If running in WSL, configure credentials in WSL (not Windows)

.. code-block:: bash

    # In WSL
    aws configure
    aws sts get-caller-identity  # Verify

Debugging Tests
~~~~~~~~~~~~~~~

**Run with Verbose Output:**

.. code-block:: bash

    # Verbose pytest output
    pytest -vv tests/test_my_infrastructure.py

    # Show test setup/teardown
    pytest -vv --setup-show tests/

**Keep Resources After Test for Inspection:**

.. code-block:: bash

    # Keep resources to debug
    pytest --keep-after tests/test_my_infrastructure.py

    # Inspect resources manually
    cd <site-packages>/pytest_infrahouse/data/service-network
    terraform state list
    terraform show

    # Don't forget to clean up afterward!
    terraform destroy -auto-approve

**Run Single Test:**

.. code-block:: bash

    # Run specific test function
    pytest tests/test_my_infrastructure.py::test_specific_function

    # Run tests matching pattern
    pytest -k "test_network" tests/

**Show Terraform Debug Output:**

.. code-block:: bash

    # Enable Terraform debug logging
    export TF_LOG=DEBUG
    pytest tests/

    # Or for specific log levels
    export TF_LOG=TRACE  # Most verbose
    export TF_LOG=INFO   # Less verbose

**Capture Fixture State:**

.. code-block:: python

    def test_debug_fixture(service_network):
        """Print fixture outputs for debugging."""
        import json
        print(json.dumps(service_network, indent=2))

        # Outputs will appear in pytest output with -s flag
        # pytest -s tests/test_debug_fixture.py

**Check AWS Resources Directly:**

.. code-block:: bash

    # List VPCs created by tests
    aws ec2 describe-vpcs --filters "Name=tag:created_by_fixture,Values=infrahouse*"

    # List all resources with test tags
    aws resourcegroupstaggingapi get-resources \
        --tag-filters Key=created_by_test,Values=test_*

**Enable Python Debugging:**

.. code-block:: bash

    # Run pytest with Python debugger
    pytest --pdb tests/test_my_infrastructure.py

    # Or add breakpoint in test
    def test_my_feature(service_network):
        breakpoint()  # Python 3.7+
        # Or: import pdb; pdb.set_trace()

Getting Help
~~~~~~~~~~~~

If you encounter issues not covered here:

1. **Check fixture state files** in ``<site-packages>/pytest_infrahouse/data/<fixture-name>/``
2. **Review Terraform logs** with ``TF_LOG=DEBUG``
3. **Verify AWS resources** directly using AWS CLI or Console
4. **Search existing issues** at https://github.com/infrahouse/pytest-infrahouse/issues
5. **Create a new issue** with:

   * pytest version: ``pytest --version``
   * Plugin version: ``pip show pytest-infrahouse``
   * Python version: ``python --version``
   * Terraform version: ``terraform version``
   * Error messages and full stack traces
   * Steps to reproduce

Best Practices
--------------

This section provides recommendations for organizing tests, managing costs, ensuring security, and optimizing performance when using pytest-infrahouse.

Test Organization
~~~~~~~~~~~~~~~~~

**Organize tests by component or layer:**

.. code-block:: python

    # tests/conftest.py - Shared fixtures and configuration
    import pytest

    @pytest.fixture(scope="session")
    def custom_config():
        """Custom configuration for your test suite."""
        return {
            "instance_type": "t3.micro",
            "enable_monitoring": True
        }

    # tests/test_networking.py - Network layer tests
    def test_vpc_configuration(service_network):
        """Verify VPC is properly configured."""
        vpc_id = service_network["vpc_id"]["value"]
        assert vpc_id.startswith("vpc-")

    def test_subnet_count(service_network):
        """Verify correct number of subnets."""
        public_subnets = service_network["subnet_public_ids"]["value"]
        private_subnets = service_network["subnet_private_ids"]["value"]
        assert len(public_subnets) == 2
        assert len(private_subnets) == 2

    # tests/test_compute.py - Compute layer tests
    def test_jumphost_accessible(jumphost, service_network):
        """Verify jumphost is accessible."""
        hostname = jumphost["jumphost_hostname"]["value"]
        assert hostname

    # tests/test_data.py - Data layer tests
    def test_elasticsearch_cluster_healthy(elasticsearch):
        """Verify Elasticsearch cluster is healthy."""
        cluster_url = elasticsearch["cluster_master_url"]["value"]
        assert cluster_url.startswith("https://")

**Benefits:**

* Clear separation of concerns
* Easier to navigate test suite
* Faster to identify failing component
* Better test maintenance

Fixture Scoping and Reuse
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Understanding Fixture Scope:**

Fixtures in pytest-infrahouse are session-scoped by default, meaning they're created once per test session and shared across all tests.

.. code-block:: python

    # ✅ Good - Reuse fixtures across multiple tests
    def test_vpc_exists(service_network):
        """First test using service_network."""
        assert service_network["vpc_id"]["value"]

    def test_subnets_exist(service_network):
        """Second test reuses the same service_network."""
        assert service_network["subnet_public_ids"]["value"]

    # ❌ Avoid - Don't modify shared infrastructure
    def test_bad_practice(service_network):
        """Don't modify resources created by fixtures!"""
        vpc_id = service_network["vpc_id"]["value"]
        # DON'T DO THIS - modifying shared resource
        # ec2.modify_vpc_attribute(VpcId=vpc_id, EnableDnsHostnames={'Value': False})

**Best Practices:**

* **Treat fixture resources as read-only** - Multiple tests share the same infrastructure
* **Don't modify fixture-created resources** - Changes affect other tests
* **Use custom resources for mutable tests** - Create your own resources if you need to modify them
* **Session scope is efficient** - Fixtures are created once, saving time and money

Cost Management
~~~~~~~~~~~~~~~

**Strategy 1: Automatic Cleanup (Default)**

Resources are automatically destroyed after tests complete:

.. code-block:: bash

    # Default behavior - resources cleaned up automatically
    pytest tests/

**Strategy 2: Development Workflow with --keep-after**

During development, use ``--keep-after`` to iterate on your tests without recreating infrastructure each time:

.. code-block:: bash

    # Run test with --keep-after to keep resources for inspection
    pytest --keep-after tests/test_my_feature.py

    # Make changes to your test or module, run again with --keep-after
    pytest --keep-after tests/test_my_feature.py

    # Once development is complete, run WITHOUT --keep-after to clean up
    pytest tests/test_my_feature.py
    # Resources are automatically destroyed after this run

**This is the recommended development workflow:**

1. Run test with ``--keep-after`` multiple times during development
2. Infrastructure stays up between runs (faster iterations)
3. Run test once without ``--keep-after`` when done - automatic cleanup!

**Manual cleanup only needed when Terraform fails:**

If Terraform fails badly and leaves orphaned resources:

.. code-block:: bash

    # Option 1: Navigate to fixture directory and destroy manually
    cd ~/.virtualenvs/myproject/lib/python3.12/site-packages/pytest_infrahouse/data/service-network
    terraform destroy -auto-approve

    # Option 2: Use AWS Tag Editor to find orphaned resources
    # Go to AWS Console > Resource Groups & Tag Editor
    # Search for tags: created_by_fixture=infrahouse*
    # Manually delete resources through console

**Strategy 3: Run Tests in CI/CD with Automatic Cleanup**

.. code-block:: yaml

    # GitHub Actions example
    name: Infrastructure Tests
    on: [push, pull_request]

    jobs:
      test:
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3

          - name: Configure AWS Credentials
            uses: aws-actions/configure-aws-credentials@v2
            with:
              aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
              aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
              aws-region: us-east-1

          - name: Run Infrastructure Tests
            run: |
              pip install pytest-infrahouse
              pytest tests/
              # Cleanup happens automatically unless --keep-after is used

**Strategy 4: Use Dedicated AWS Account for Testing**

* Set up AWS Organizations with a dedicated test account
* Set spending limits and budgets
* Configure billing alerts
* Easier to track test costs separately

**Strategy 5: Monitor and Clean Up Orphaned Resources**

.. code-block:: bash

    # Check for resources created by tests
    aws resourcegroupstaggingapi get-resources \
        --tag-filters Key=created_by_fixture,Values=infrahouse*

    # Check for old VPCs
    aws ec2 describe-vpcs \
        --filters "Name=tag:created_by_fixture,Values=infrahouse*"

    # Clean up if needed
    cd ~/.virtualenvs/myproject/lib/python3.12/site-packages/pytest_infrahouse/data/service-network
    terraform destroy -auto-approve

Security Considerations
~~~~~~~~~~~~~~~~~~~~~~~

**1. Never Commit AWS Credentials to Git**

.. code-block:: bash

    # Add to .gitignore
    .aws/
    *.tfvars
    terraform.tfstate*
    .env

**2. Use IAM Roles with Least Privilege**

Start with ``PowerUserAccess`` for testing, then refine:

.. code-block:: json

    {
      "Version": "2012-10-17",
      "Statement": [
        {
          "Effect": "Allow",
          "Action": [
            "ec2:*",
            "elasticloadbalancing:*",
            "autoscaling:*",
            "route53:*",
            "s3:*",
            "iam:*",
            "cloudwatch:*"
          ],
          "Resource": "*",
          "Condition": {
            "StringEquals": {
              "aws:RequestedRegion": "us-east-1"
            }
          }
        }
      ]
    }

**3. Rotate Test Credentials Regularly**

.. code-block:: bash

    # Rotate access keys every 90 days
    aws iam create-access-key --user-name test-user
    aws iam delete-access-key --user-name test-user --access-key-id OLD_KEY

**4. Use Separate AWS Accounts for Testing**

* Isolate test resources from production
* Easier to manage costs and security
* Use AWS Organizations for account management

**5. Review Security Group Rules Created by Tests**

.. code-block:: bash

    # Check security groups
    aws ec2 describe-security-groups \
        --filters "Name=tag:created_by_fixture,Values=infrahouse*"

    # Look for overly permissive rules (0.0.0.0/0)

**6. Enable CloudTrail for Audit Logging**

Track all API calls made during tests for security auditing.

Performance Optimization
~~~~~~~~~~~~~~~~~~~~~~~~

**1. Reuse Fixtures Across Tests**

Fixtures are session-scoped - leverage this for efficiency:

.. code-block:: python

    # ✅ Efficient - Multiple tests share one service_network
    def test_feature_a(service_network):
        pass

    def test_feature_b(service_network):
        pass

    def test_feature_c(service_network):
        pass

**2. Run Slow Tests Separately Using Pytest Marks**

.. code-block:: python

    import pytest

    @pytest.mark.slow
    def test_elasticsearch_full_cluster(elasticsearch):
        """This test takes 15-20 minutes."""
        cluster_url = elasticsearch["cluster_master_url"]["value"]
        # Long-running test logic...

    @pytest.mark.smoke
    def test_basic_connectivity(service_network):
        """Quick smoke test - runs in seconds."""
        assert service_network["vpc_id"]["value"]

Run specific test categories:

.. code-block:: bash

    # Run only fast tests (skip slow ones)
    pytest -m "not slow" tests/

    # Run only smoke tests for quick validation
    pytest -m smoke tests/

    # Run slow tests in nightly CI build
    pytest -m slow tests/

**3. Parallelize Tests with pytest-xdist (Use with Caution!)**

.. code-block:: bash

    # Install pytest-xdist
    pip install pytest-xdist

    # Run tests in parallel (4 workers)
    pytest -n 4 tests/

**⚠️ Warning:** Fixtures are session-scoped and shared. Parallel execution may cause:

* Race conditions if tests modify shared resources
* Interference between tests
* Unexpected test failures

**Recommendation:** Use parallel execution only if:

* Tests are truly independent
* Tests don't modify fixture-created resources
* Each test runs in an isolated AWS account (via different ``--test-role-arn``)

**4. Cache Terraform Plugins**

.. code-block:: bash

    # Set Terraform plugin cache directory
    export TF_PLUGIN_CACHE_DIR="$HOME/.terraform.d/plugin-cache"
    mkdir -p $TF_PLUGIN_CACHE_DIR

    # This speeds up terraform init across multiple fixtures

**5. Use Smaller AWS Regions for Development**

Some regions have lower latency and faster resource provisioning:

.. code-block:: bash

    # us-east-1 typically has fastest provisioning
    pytest --aws-region us-east-1 tests/

Testing in CI/CD
~~~~~~~~~~~~~~~~

**Example GitHub Actions Workflow:**

.. code-block:: yaml

    name: Infrastructure Tests
    on:
      push:
        branches: [main, develop]
      pull_request:
        branches: [main]

    jobs:
      test-fast:
        name: Fast Tests
        runs-on: ubuntu-latest
        steps:
          - uses: actions/checkout@v3

          - name: Set up Python
            uses: actions/setup-python@v4
            with:
              python-version: '3.10'

          - name: Configure AWS Credentials
            uses: aws-actions/configure-aws-credentials@v2
            with:
              aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
              aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
              aws-region: us-east-1

          - name: Install dependencies
            run: |
              pip install pytest pytest-infrahouse

          - name: Run fast tests
            run: |
              pytest -m "not slow" tests/

      test-slow:
        name: Slow Tests (Nightly)
        runs-on: ubuntu-latest
        if: github.event_name == 'schedule'
        steps:
          - uses: actions/checkout@v3

          - name: Set up Python
            uses: actions/setup-python@v4
            with:
              python-version: '3.10'

          - name: Configure AWS Credentials
            uses: aws-actions/configure-aws-credentials@v2
            with:
              aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
              aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
              aws-region: us-east-1

          - name: Run slow tests
            run: |
              pytest -m slow tests/

**Benefits:**

* Fast tests run on every push/PR
* Slow tests run on schedule (nightly)
* Automatic cleanup after tests
* No orphaned resources

Documentation and Maintenance
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**1. Document Your Test Infrastructure**

.. code-block:: python

    def test_custom_module(service_network):
        """
        Test custom RDS module deployment.

        Fixtures used:
        - service_network: Provides VPC and subnets

        Resources created:
        - RDS instance (db.t3.micro)
        - DB subnet group
        - Security group

        Estimated cost: ~$15/month if left running
        Estimated test duration: ~10 minutes
        """
        pass

**2. Keep Tests Up to Date**

* Update tests when infrastructure changes
* Review and update fixture versions regularly
* Test against latest Terraform and AWS provider versions

**3. Add Test Tags for Organization**

.. code-block:: python

    @pytest.mark.network
    @pytest.mark.smoke
    def test_vpc_basics(service_network):
        """Basic VPC connectivity test."""
        pass

**4. Monitor Test Costs**

.. code-block:: bash

    # Set up AWS Budget alerts
    aws budgets create-budget \
        --account-id 123456789012 \
        --budget file://test-budget.json

    # Review monthly costs
    aws ce get-cost-and-usage \
        --time-period Start=2025-11-01,End=2025-11-30 \
        --granularity MONTHLY \
        --metrics "UnblendedCost" \
        --filter file://test-tag-filter.json

Summary
~~~~~~~

**Key Takeaways:**

* ✅ Organize tests by component (network, compute, data)
* ✅ Treat fixture resources as read-only
* ✅ Use ``--keep-after`` during development, run without it to clean up
* ✅ Run tests in dedicated AWS accounts with budgets
* ✅ Never commit AWS credentials to git
* ✅ Use pytest marks to organize fast vs slow tests
* ✅ Leverage session-scoped fixtures for efficiency
* ✅ Run expensive tests separately (nightly builds)
* ✅ Document test infrastructure and costs
* ✅ Monitor and clean up orphaned resources

Following these best practices will help you build reliable, cost-effective, and secure infrastructure tests with pytest-infrahouse.

Frequently Asked Questions
--------------------------

**Q: How much do tests cost to run?**

A: Short tests (<5 minutes) typically cost $0.10-0.50. Medium tests (1 hour) cost $1-2. A full test suite might cost $5-10 per run depending on which fixtures are used. See the `⚠️ Cost Warning`_ section for detailed estimates.

**Q: Can I run tests in parallel?**

A: Yes, but with caution. Fixtures are session-scoped and shared across tests. Parallel execution with pytest-xdist may cause race conditions if tests modify shared resources. It's safe to run tests in parallel if they're truly independent or run in isolated AWS accounts (via different ``--test-role-arn`` values).

**Q: How long do tests take?**

A: Depends on which fixtures are used:

* service_network: ~3-5 minutes (VPC, subnets, NAT gateways)
* jumphost: ~5-7 minutes (EC2, NLB, EFS)
* elasticsearch: ~15-20 minutes (requires bootstrap mode with two Terraform applies)
* instance_profile: ~1 minute (IAM resources only)
* ses: ~2-3 minutes (domain verification)

**Q: Why does the Elasticsearch fixture take so long?**

A: The elasticsearch fixture uses bootstrap mode, which requires two Terraform applies. The first apply creates the cluster infrastructure, and the second apply configures cluster settings. This is necessary to properly configure Elasticsearch and is handled automatically by the plugin.

**Q: Can I use this plugin for production infrastructure?**

A: **No!** This plugin is designed for testing only. The fixtures create ephemeral infrastructure with minimal security configurations and no high availability. For production infrastructure, use dedicated Terraform modules with proper security hardening, backup strategies, and high availability configurations.

**Q: What happens if a test fails?**

A: By default, resources are automatically destroyed even if tests fail (unless ``--keep-after`` is used). This prevents orphaned resources and unexpected AWS charges. If you need to inspect resources after a failure, use ``--keep-after`` and remember to clean up manually afterward.

**Q: Can I customize fixture configurations?**

A: The fixtures use opinionated configurations optimized for testing (e.g., single NAT gateway, minimal instances). These configurations are intentionally fixed to provide consistent test environments. For custom configurations, write your own Terraform modules and use the ``terraform_apply`` context manager provided by the plugin.

**Q: Which AWS regions are supported?**

A: All AWS regions are supported. Use the ``--aws-region`` command-line option to specify your preferred region. Note that some regions may have different pricing or resource availability. We recommend us-east-1 for development as it typically has the fastest resource provisioning and lowest costs.

**Q: Do I need to install Terraform separately?**

A: Yes, Terraform must be installed separately and available in your PATH. The plugin does not bundle Terraform. See the `Prerequisites & Setup`_ section for installation instructions for macOS, Linux, and Windows.

**Q: How do I find where fixture state files are stored?**

A: Terraform state files are stored in your Python site-packages directory. Use this command to find them:

.. code-block:: bash

    python -c "import pytest_infrahouse; import os; print(os.path.dirname(pytest_infrahouse.__file__))"

State files are in ``<output>/data/<fixture-name>/terraform.tfstate``. See the `Understanding State File Locations`_ section in Troubleshooting for more details.

**Q: Can I reuse fixtures across multiple test files?**

A: Yes! Fixtures are session-scoped, meaning they're created once per pytest session and shared across all test files. This is efficient but means tests should treat fixture resources as read-only.

**Q: What if I need to modify resources created by fixtures?**

A: Don't modify fixture-created resources - changes will affect all other tests using that fixture. Instead, create your own resources in your test using boto3 or Terraform, or write a custom fixture with appropriate scope (function or module level).

**Q: How do I debug test failures?**

A: Use these strategies:

* Run with ``--keep-after`` to inspect resources after test
* Use ``-vv`` for verbose pytest output
* Set ``TF_LOG=DEBUG`` for Terraform debug logging
* Check fixture state with ``terraform state list`` in the fixture directory
* Review the `Debugging Tests`_ section in Troubleshooting

**Q: What credentials does the plugin use?**

A: The plugin uses your configured AWS credentials (from ``~/.aws/credentials``, environment variables, or IAM roles). When ``--test-role-arn`` is specified, the plugin assumes that role for all operations. See the `AWS Configuration`_ section for details.

**Q: Will this plugin modify my existing AWS resources?**

A: No. The plugin only creates new resources tagged with ``created_by_fixture`` and ``created_by_test`` tags. It never modifies existing AWS resources. However, always use a dedicated test AWS account to avoid any potential issues.

Contributing
------------
Contributions are very welcome. Tests can be run with `tox`_, please ensure
the coverage at least stays the same before you submit a pull request.

License
-------

Distributed under the terms of the `Apache Software License 2.0`_ license, "pytest-infrahouse" is free and open source software


Issues
------

If you encounter any problems, please `file an issue`_ along with a detailed description.

.. _`Cookiecutter`: https://github.com/audreyr/cookiecutter
.. _`@hackebrot`: https://github.com/hackebrot
.. _`MIT`: https://opensource.org/licenses/MIT
.. _`BSD-3`: https://opensource.org/licenses/BSD-3-Clause
.. _`GNU GPL v3.0`: https://www.gnu.org/licenses/gpl-3.0.txt
.. _`Apache Software License 2.0`: https://www.apache.org/licenses/LICENSE-2.0
.. _`cookiecutter-pytest-plugin`: https://github.com/pytest-dev/cookiecutter-pytest-plugin
.. _`file an issue`: https://github.com/infrahouse/pytest-infrahouse/issues
.. _`pytest`: https://github.com/pytest-dev/pytest
.. _`tox`: https://tox.readthedocs.io/en/latest/
.. _`pip`: https://pypi.org/project/pip/
.. _`PyPI`: https://pypi.org/project
