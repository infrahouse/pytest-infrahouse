# README Improvement Suggestions for pytest-infrahouse

## Current State Analysis

### ✅ Strengths
- Clear badges and project metadata
- Good overview and feature list
- Basic usage examples work
- Command-line options documented
- Long-running tests feature well explained

### ❌ Gaps & Improvement Opportunities

---

## Priority 1: Critical Missing Information

### 1. Fixture Details - Resources & Outputs

**Problem**: Users don't know what each fixture actually creates or returns.

**Add a comprehensive section:**

```rst
Fixture Details
---------------

service_network
~~~~~~~~~~~~~~~

**Purpose:** Creates a complete VPC with networking for testing AWS resources.

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
* ``route_table_all_ids`` - All route table IDs

**Dependencies:** None

**Estimated Cost:** ~$100-150/month (mostly NAT Gateways)

**Example:**

.. code-block:: python

    def test_vpc_configuration(service_network):
        vpc_id = service_network["vpc_id"]["value"]
        public_subnets = service_network["subnet_public_ids"]["value"]
        assert len(public_subnets) == 2

jumphost
~~~~~~~~

**Purpose:** Creates a bastion host for accessing private resources.

**Resources Created:**
* EC2 Auto Scaling Group (min: 1, max: 1)
* Network Load Balancer for SSH access
* EFS file system for persistent home directories (encrypted at rest)
* IAM instance profile with necessary permissions
* Route53 DNS record for easy access

**Outputs:**
* ``jumphost_role_arn`` - IAM role ARN
* ``jumphost_role_name`` - IAM role name
* ``jumphost_hostname`` - DNS hostname for SSH access
* ``jumphost_asg_name`` - Auto Scaling Group name

**Dependencies:**
* ``service_network`` (requires VPC and subnets)
* ``subzone`` (for DNS record)

**Estimated Cost:** ~$50-80/month (EC2 + NLB + EFS)

elasticsearch
~~~~~~~~~~~~~

**Purpose:** Deploys a functional Elasticsearch cluster for testing.

**Resources Created:**
* 3 master nodes (for quorum)
* 1 data node
* Application Load Balancers (master + data)
* Security groups
* IAM roles and policies
* S3 bucket for snapshots
* Route53 DNS records

**Outputs:**
* ``elastic_password`` - Elastic superuser password (sensitive)
* ``cluster_name`` - Name of the cluster
* ``cluster_master_url`` - URL to access master nodes
* ``master_load_balancer_arn`` - Master LB ARN
* ``data_load_balancer_arn`` - Data LB ARN
* ``snapshots_bucket`` - S3 bucket for backups

**Dependencies:**
* ``service_network``
* ``subzone``

**Bootstrap Mode:** Requires two terraform applies (handled automatically)

**Estimated Cost:** ~$200-300/month (4 EC2 instances + LBs + EBS)

[Continue for all fixtures...]
```

### 2. Cost Warning & Estimation

**Problem**: Users don't realize tests create REAL resources that COST MONEY.

**Add prominent warning:**

```rst
⚠️ Cost Warning
---------------

**IMPORTANT:** This plugin creates REAL AWS infrastructure that incurs REAL costs.

**Estimated Monthly Costs (if left running):**

* service_network: ~$100-150 (NAT Gateways)
* jumphost: ~$50-80 (EC2, NLB, EFS)
* elasticsearch: ~$200-300 (4 EC2 instances, LBs)
* All fixtures combined: ~$400-600/month

**Cost Reduction Strategies:**

1. **Always use** ``--keep-after`` flag cautiously (destroys by default)
2. Run tests in smaller AWS regions (pricing varies)
3. Use smaller EC2 instance types where possible
4. Clean up orphaned resources regularly:

   .. code-block:: bash

       # Check for resources tagged with created_by_test
       aws resourcegroupstaggingapi get-resources \
           --tag-filters Key=created_by_test,Values=test_*

5. Set AWS budgets and alerts

**Test Duration Impact:**

* Short test (<5 minutes): ~$0.10-0.50
* Medium test (1 hour): ~$1-2
* Long test (8 hours): ~$5-10
```

### 3. Prerequisites & Setup

**Problem**: Assumes users know AWS/Terraform setup.

**Add detailed prerequisites:**

```rst
Prerequisites & Setup
---------------------

AWS Configuration
~~~~~~~~~~~~~~~~~

1. **AWS Account**: You need an AWS account with billing enabled

2. **AWS Credentials**: Configure credentials using one of these methods:

   .. code-block:: bash

       # Option 1: AWS CLI (recommended)
       aws configure

       # Option 2: Environment variables
       export AWS_ACCESS_KEY_ID=your_key
       export AWS_SECRET_ACCESS_KEY=your_secret
       export AWS_DEFAULT_REGION=us-east-1

       # Option 3: AWS credentials file
       cat ~/.aws/credentials
       [default]
       aws_access_key_id = your_key
       aws_secret_access_key = your_secret

3. **IAM Permissions**: Your AWS user/role needs extensive permissions:

   * EC2 (VPC, subnets, instances, security groups)
   * IAM (roles, policies, instance profiles)
   * Route53 (hosted zones, records)
   * ELB (application and network load balancers)
   * ElastiCache, RDS, S3, CloudWatch
   * **Recommendation**: Start with PowerUserAccess, refine later

4. **Route53 Hosted Zone**: Tests require a Route53 zone:

   .. code-block:: bash

       # Create a test zone (or use existing)
       aws route53 create-hosted-zone \
           --name test.example.com \
           --caller-reference $(date +%s)

Terraform Installation
~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # macOS
    brew install terraform

    # Linux (Ubuntu/Debian)
    wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
    sudo apt update && sudo apt install terraform

    # Verify
    terraform version

Python Environment
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    # Create virtual environment
    python -m venv venv
    source venv/bin/activate  # or `venv\Scripts\activate` on Windows

    # Install pytest-infrahouse
    pip install pytest-infrahouse

    # Verify installation
    pytest --version
    pytest --help | grep infrahouse
```

---

## Priority 2: Enhanced Examples & Use Cases

### 4. Real-World Testing Scenarios

**Problem**: Basic examples don't show real testing patterns.

**Add section:**

```rst
Real-World Examples
-------------------

Testing a Custom Terraform Module
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** You have a custom Terraform module that creates an RDS database
in a VPC. You want to verify it works correctly.

.. code-block:: python

    import pytest
    from pytest_infrahouse import terraform_apply

    def test_rds_module_creates_database(
        service_network,
        aws_region,
        test_role_arn,
        rds_client,
        request
    ):
        """Test that our RDS module creates a functional database."""

        # Get VPC info from service_network fixture
        vpc_id = service_network["vpc_id"]["value"]
        private_subnets = service_network["subnet_private_ids"]["value"]

        # Write terraform.tfvars for our custom module
        module_path = "tests/terraform/rds-module"
        with open(f"{module_path}/terraform.tfvars", "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            fp.write(f'vpc_id = "{vpc_id}"\n')
            fp.write(f'subnet_ids = {private_subnets}\n')
            if test_role_arn:
                fp.write(f'role_arn = "{test_role_arn}"\n')

        # Apply Terraform and test
        with terraform_apply(module_path, destroy_after=True) as outputs:
            db_instance_id = outputs["db_instance_id"]["value"]
            db_endpoint = outputs["db_endpoint"]["value"]

            # Verify database was created
            response = rds_client.describe_db_instances(
                DBInstanceIdentifier=db_instance_id
            )
            assert len(response["DBInstances"]) == 1
            assert response["DBInstances"][0]["DBInstanceStatus"] == "available"

            # Verify it's in the correct VPC
            assert response["DBInstances"][0]["DBSubnetGroup"]["VpcId"] == vpc_id

Testing Infrastructure Dependencies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Test that a Lambda function can access resources in your VPC.

.. code-block:: python

    def test_lambda_vpc_access(
        service_network,
        instance_profile,
        aws_region
    ):
        """Test Lambda function has correct VPC access."""

        vpc_id = service_network["vpc_id"]["value"]
        private_subnets = service_network["subnet_private_ids"]["value"]

        # Your test logic here...
        # The fixtures ensure proper networking is in place

Cross-Account Testing
~~~~~~~~~~~~~~~~~~~~~

**Scenario:** Test that your infrastructure works when deployed to a different
AWS account via role assumption.

.. code-block:: bash

    # Run tests assuming a role in another account
    pytest tests/test_cross_account.py \
        --test-role-arn arn:aws:iam::987654321098:role/CrossAccountTestRole \
        --aws-region us-west-2
```

### 5. Troubleshooting Section

**Problem**: No guidance when things go wrong.

```rst
Troubleshooting
---------------

Common Issues
~~~~~~~~~~~~~

**Problem:** ``terraform not found in PATH``

**Solution:**

.. code-block:: bash

    # Check if Terraform is installed
    which terraform

    # Install if missing
    brew install terraform  # macOS
    # or download from https://www.terraform.io/downloads

**Problem:** ``AWS credential errors``

**Solution:**

.. code-block:: bash

    # Verify credentials
    aws sts get-caller-identity

    # Check credential configuration
    cat ~/.aws/credentials
    cat ~/.aws/config

**Problem:** ``Route53 zone not found``

**Solution:**

.. code-block:: bash

    # List your hosted zones
    aws route53 list-hosted-zones

    # Use correct zone name
    pytest --test-zone-name your-zone.example.com

**Problem:** ``Resources not cleaned up after test failure``

**Solution:**

.. code-block:: bash

    # Manually destroy if needed
    cd src/pytest_infrahouse/data/service-network
    terraform destroy -auto-approve

    # Find orphaned resources by tag
    aws resourcegroupstaggingapi get-resources \
        --tag-filters Key=created_by_fixture,Values=infrahouse*

**Problem:** ``Elasticsearch bootstrap mode timeout``

**Explanation:** Elasticsearch fixture requires two terraform applies. This is
normal and handled automatically. First apply creates the cluster, second
configures it.

**Problem:** ``ChainedRole error: Cannot assume role from temporary credentials``

**Solution:** When role chaining, AWS limits sessions to 1 hour. The plugin
handles this automatically by refreshing credentials. If you see this error,
it means you're calling AssumeRole directly without using the plugin's
credential refresh mechanism.

Debugging Tests
~~~~~~~~~~~~~~~

.. code-block:: bash

    # Run with verbose output
    pytest -vv tests/test_my_infrastructure.py

    # Keep resources after test for inspection
    pytest --keep-after tests/test_my_infrastructure.py

    # Run single test
    pytest tests/test_my_infrastructure.py::test_specific_function

    # Show Terraform output
    TF_LOG=DEBUG pytest tests/
```

---

## Priority 3: Advanced Topics

### 6. Best Practices Section

```rst
Best Practices
--------------

Test Organization
~~~~~~~~~~~~~~~~~

.. code-block:: python

    # tests/conftest.py - shared fixtures and configuration
    import pytest

    @pytest.fixture(scope="session")
    def custom_config():
        return {"instance_type": "t3.micro"}

    # tests/test_networking.py - network-focused tests
    def test_vpc_configuration(service_network):
        ...

    # tests/test_compute.py - compute-focused tests
    def test_jumphost_access(jumphost, service_network):
        ...

Fixture Scoping
~~~~~~~~~~~~~~~

Fixtures are session-scoped by default (created once per test session).
This is efficient but means:

* Tests should not modify shared infrastructure
* Tests run in parallel may interfere with each other
* Use ``--keep-after`` for debugging, but remember to clean up

Cost Management
~~~~~~~~~~~~~~~

1. **Run tests in CI/CD with automatic cleanup**

   .. code-block:: yaml

       # GitHub Actions example
       - name: Run infrastructure tests
         run: |
           pytest tests/
           # Cleanup happens automatically unless --keep-after is used

2. **Use AWS Organizations and dedicated test account**

3. **Set up AWS Budgets** for test accounts

4. **Tag all resources** (done automatically by fixtures)

Security Considerations
~~~~~~~~~~~~~~~~~~~~~~~

1. **Never commit AWS credentials to git**
2. **Use IAM roles with least privilege**
3. **Rotate test credentials regularly**
4. **Use separate AWS accounts for testing**
5. **Review security group rules** created by tests

Performance Tips
~~~~~~~~~~~~~~~~

1. **Reuse fixtures across tests** (they're session-scoped)
2. **Run slow tests separately**: Use pytest marks

   .. code-block:: python

       @pytest.mark.slow
       def test_elasticsearch_cluster(elasticsearch):
           # This test takes 15+ minutes
           ...

   .. code-block:: bash

       # Run only fast tests
       pytest -m "not slow"

3. **Parallelize with pytest-xdist** (carefully!)

   .. code-block:: bash

       pip install pytest-xdist
       pytest -n 4  # Use with caution - fixtures are shared!
```

---

## Priority 4: Documentation Structure

### 7. Add Table of Contents

```rst
Table of Contents
-----------------

* `Overview`_
* `Features`_
* `⚠️ Cost Warning`_
* `Prerequisites & Setup`_
* `Installation`_
* `Quick Start`_
* `Usage`_

  * `Basic Example`_
  * `Using Custom Terraform Modules`_
  * `Command Line Options`_
  * `Long-Running Tests`_

* `Available Fixtures`_

  * `AWS Client Fixtures`_
  * `Infrastructure Fixtures`_
  * `Configuration Fixtures`_

* `Fixture Details`_ (NEW)

  * `service_network`_
  * `jumphost`_
  * `elasticsearch`_
  * `instance_profile`_
  * `ses`_
  * `probe_role`_
  * `subzone`_

* `Real-World Examples`_ (NEW)
* `Best Practices`_ (NEW)
* `Troubleshooting`_ (NEW)
* `FAQ`_ (NEW)
* `Contributing`_
* `License`_
```

### 8. Add FAQ Section

```rst
Frequently Asked Questions
--------------------------

**Q: How much do tests cost to run?**

A: Short tests (<5 min) cost $0.10-0.50. A full test suite might cost $5-10
per run. See `⚠️ Cost Warning`_ for details.

**Q: Can I run tests in parallel?**

A: Yes, but with caution. Fixtures are session-scoped and shared. Use
pytest-xdist carefully or run tests in isolated AWS accounts.

**Q: How long do tests take?**

A: Depends on fixtures used:

* service_network: ~3-5 minutes
* jumphost: ~5-7 minutes
* elasticsearch: ~15-20 minutes (bootstrap mode)

**Q: Why does Elasticsearch take so long?**

A: The elasticsearch fixture uses bootstrap mode, requiring two Terraform
applies. This is necessary to properly configure the cluster.

**Q: Can I use this for production infrastructure?**

A: **No!** This plugin is designed for testing only. The fixtures create
ephemeral infrastructure with minimal security and no high availability.

**Q: What happens if a test fails?**

A: By default, resources are destroyed even if tests fail (unless
``--keep-after`` is used). This prevents orphaned resources.

**Q: Can I customize fixture configurations?**

A: The fixtures use opinionated configurations suitable for testing. For
custom configurations, write your own Terraform modules and use the
``terraform_apply`` context manager.

**Q: Which AWS regions are supported?**

A: All AWS regions are supported. Use ``--aws-region`` to specify.

**Q: Do I need to install Terraform separately?**

A: Yes, Terraform must be installed and available in your PATH.
```

---

## Additional Suggestions

### 9. Add Architecture Diagram

Create a simple ASCII or include an image:

```rst
Architecture
------------

.. code-block:: text

    ┌─────────────────────────────────────────────────────────┐
    │                     pytest Test Suite                    │
    ├─────────────────────────────────────────────────────────┤
    │                                                           │
    │  ┌───────────────┐      ┌────────────────┐             │
    │  │ Test Function │─────▶│ Fixture (e.g., │             │
    │  │               │      │ service_network)│             │
    │  └───────────────┘      └────────┬────────┘             │
    │                                   │                       │
    └───────────────────────────────────┼───────────────────────┘
                                        │
                                        ▼
                         ┌──────────────────────────┐
                         │   Terraform Module       │
                         │   (embedded in plugin)   │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                          ┌───────────────────────┐
                          │     AWS Account       │
                          │  ┌─────────────────┐  │
                          │  │ VPC             │  │
                          │  │ EC2 Instances   │  │
                          │  │ Load Balancers  │  │
                          │  │ etc.            │  │
                          │  └─────────────────┘  │
                          └───────────────────────┘
```

### 10. Add Migration/Upgrade Guide

```rst
Upgrading
---------

From 0.19.x to 0.20.x
~~~~~~~~~~~~~~~~~~~~~

**Breaking Changes:**

* None

**New Features:**

* Added additional outputs to fixtures
* Improved Ubuntu LTS version management
* Enhanced documentation

**Recommended Actions:**

1. Update your requirements.txt:

   .. code-block:: bash

       pytest-infrahouse>=0.20.0

2. Review new fixture outputs (see `Fixture Details`_)

3. No code changes required for existing tests
```

---

## Summary of Recommended Changes

### High Priority (Do First)
1. ✅ Add **Cost Warning** section
2. ✅ Add **Fixture Details** with resources, outputs, dependencies
3. ✅ Add **Prerequisites & Setup** section
4. ✅ Add **Troubleshooting** section

### Medium Priority
5. ✅ Add **Real-World Examples**
6. ✅ Add **Best Practices** section
7. ✅ Add **FAQ** section
8. ✅ Add **Table of Contents**

### Nice to Have
9. ✅ Add Architecture Diagram
10. ✅ Add Upgrade/Migration Guide

### Format Improvements
- Add more code examples with expected outputs
- Add "Copy to clipboard" hints for commands
- Use consistent formatting for all fixture descriptions
- Add visual separators between major sections

---

## Implementation Strategy

1. **Phase 1 (Critical)**: Add cost warning, fixture details, prerequisites
2. **Phase 2 (Important)**: Add troubleshooting, real-world examples
3. **Phase 3 (Polish)**: Add FAQ, best practices, diagrams
4. **Phase 4 (Maintain)**: Keep updated with each release

Would you like me to help implement any of these sections?