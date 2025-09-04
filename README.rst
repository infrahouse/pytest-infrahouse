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
  * ``ses`` - Simple Email Service configuration
  * ``probe_role`` - IAM role with limited permissions
  * ``subzone`` - Route53 DNS subzone for testing

* **Terraform Integration**: Seamless integration with Terraform via ``terraform_apply`` context manager
* **Resource Management**: Automatic cleanup of AWS resources after tests (configurable)
* **Multi-Region Support**: Test across different AWS regions
* **IAM Role Support**: Assume roles for testing in different AWS accounts

Requirements
------------

* Python 3.10+
* pytest 8.3+
* Terraform installed and in PATH
* AWS credentials configured
* boto3 and botocore

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
    pytest --keep-after                         # Don't destroy resources after tests

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
* ``ses`` - Simple Email Service setup
* ``probe_role`` - IAM role with limited permissions
* ``subzone`` - Route53 DNS subzone for testing

**Configuration Fixtures:**

* ``aws_region`` - AWS region for tests
* ``test_role_arn`` - IAM role ARN to assume
* ``test_zone_name`` - Route53 zone name
* ``keep_after`` - Whether to keep resources after tests

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
