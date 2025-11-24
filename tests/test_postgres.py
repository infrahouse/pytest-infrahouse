import boto3
import pytest
from botocore.exceptions import ClientError


# pytest -xvvs --keep-after --test-role-arn=arn:aws:iam::303467602807:role/pmm-ecs-tester --aws-region=us-west-2 tests/test_postgres.py::test_postgres_fixture_structure
def test_postgres_fixture_structure(postgres):
    """
    Test that the postgres fixture returns expected terraform outputs.
    """
    # Check that we have a valid terraform output structure with all essential fields
    assert "endpoint" in postgres
    assert "address" in postgres
    assert "port" in postgres
    assert "database_name" in postgres
    assert "master_username" in postgres
    assert "master_password" in postgres
    assert "secret_arn" in postgres
    assert "connection_string" in postgres
    assert "instance_id" in postgres
    assert "instance_identifier" in postgres
    assert "security_group_id" in postgres


def test_postgres_instance_exists(postgres, boto3_session, aws_region):
    """
    Test that the PostgreSQL RDS instance was actually created in AWS.
    """
    rds_client = boto3_session.client("rds", region_name=aws_region)

    try:
        response = rds_client.describe_db_instances(
            DBInstanceIdentifier=postgres["instance_identifier"]["value"]
        )

        assert len(response["DBInstances"]) == 1
        db_instance = response["DBInstances"][0]

        # Verify instance properties
        assert db_instance["Engine"] == "postgres"
        assert db_instance["DBInstanceStatus"] == "available"
        assert db_instance["DBName"] == postgres["database_name"]["value"]
        assert db_instance["MasterUsername"] == postgres["master_username"]["value"]
        assert db_instance["StorageEncrypted"] is True

    except ClientError as e:
        pytest.fail(f"Failed to describe RDS instance: {e}")


def test_postgres_secret_exists(postgres, secretsmanager_client):
    """
    Test that the Secrets Manager secret containing credentials was created.
    """
    try:
        response = secretsmanager_client.describe_secret(
            SecretId=postgres["secret_arn"]["value"]
        )

        assert response["ARN"] == postgres["secret_arn"]["value"]
        assert "DeletedDate" not in response  # Secret should not be deleted

        # Verify we can retrieve the secret value
        secret_value = secretsmanager_client.get_secret_value(
            SecretId=postgres["secret_arn"]["value"]
        )
        assert "SecretString" in secret_value

    except ClientError as e:
        pytest.fail(f"Failed to describe or retrieve secret: {e}")


def test_postgres_security_group(postgres, ec2_client):
    """
    Test that the security group for PostgreSQL was created with proper rules.
    """
    try:
        response = ec2_client.describe_security_groups(
            GroupIds=[postgres["security_group_id"]["value"]]
        )

        assert len(response["SecurityGroups"]) == 1
        sg = response["SecurityGroups"][0]

        # Check for PostgreSQL ingress rule
        postgres_rules = [
            rule
            for rule in sg["IpPermissions"]
            if rule.get("FromPort") == 5432 and rule.get("ToPort") == 5432
        ]
        assert len(postgres_rules) > 0, "PostgreSQL ingress rule (port 5432) not found"

        # Check egress rules (should allow all outbound)
        assert len(sg["IpPermissionsEgress"]) > 0

    except ClientError as e:
        pytest.fail(f"Failed to describe security group: {e}")


def test_postgres_connection_string_format(postgres):
    """
    Test that the connection string is properly formatted.
    """
    connection_string = postgres["connection_string"]["value"]
    jdbc_string = postgres["jdbc_connection_string"]["value"]

    # Test PostgreSQL connection string format
    assert connection_string.startswith("postgresql://")
    assert "@" in connection_string
    assert ":" in connection_string

    # Test JDBC connection string format
    assert jdbc_string.startswith("jdbc:postgresql://")
    assert postgres["address"]["value"] in jdbc_string
    assert str(postgres["port"]["value"]) in jdbc_string
    assert postgres["database_name"]["value"] in jdbc_string


def test_postgres_outputs_consistency(postgres):
    """
    Test that the outputs are internally consistent.
    """
    # Endpoint should be address:port
    endpoint = postgres["endpoint"]["value"]
    address = postgres["address"]["value"]
    port = str(postgres["port"]["value"])

    assert endpoint == f"{address}:{port}"

    # Connection string should contain the correct components
    connection_string = postgres["connection_string"]["value"]
    assert address in connection_string
    assert port in connection_string
    assert postgres["database_name"]["value"] in connection_string
    assert postgres["master_username"]["value"] in connection_string
