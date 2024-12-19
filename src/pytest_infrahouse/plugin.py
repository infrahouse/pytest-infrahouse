import json
from contextlib import contextmanager
from importlib.resources import files, as_file
from os import path as osp
from textwrap import dedent

from .terraform import terraform_apply


import boto3
import pytest

AWS_DEFAULT_REGION = "us-east-1"
TEST_ZONE = "ci-cd.infrahouse.com"


def pytest_addoption(parser):
    parser.addoption(
        "--keep-after",
        action="store_true",
        default=False,
        help="If specified, don't destroy Terraform resources.",
    )
    parser.addoption(
        "--test-role-arn",
        action="store",
        default=None,
        help=f"AWS IAM role ARN that will create resources. By default, don't assume any role.",
    )
    parser.addoption(
        "--test-zone-name",
        action="store",
        default=TEST_ZONE,
        help=f"Route53 DNS zone name. Needed for some fixtures like jumphost.",
    )
    parser.addoption(
        "--aws-region",
        action="store",
        default=AWS_DEFAULT_REGION,
        help=f"AWS regions. By default, {AWS_DEFAULT_REGION}.",
    )


@pytest.fixture(scope="session")
def keep_after(request):
    """
    Do not destroy Terraform resources after a test.
    """
    return request.config.getoption("--keep-after")


@pytest.fixture(scope="session")
def test_role_arn(request):
    return request.config.getoption("--test-role-arn")

@pytest.fixture(scope="session")
def test_zone_name(request):
    return request.config.getoption("--test-zone-name")

@pytest.fixture(scope="session")
def aws_region(request):
    return request.config.getoption("--aws-region")


@pytest.fixture(scope="session")
def aws_iam_role(test_role_arn):
    return (
        boto3.client("sts").assume_role(
            RoleArn=test_role_arn, RoleSessionName=test_role_arn.split("/")[1]
        )
        if test_role_arn
        else None
    )


@pytest.fixture(scope="session")
def boto3_session(aws_iam_role):
    kwargs = {}
    if aws_iam_role:
        kwargs = {
            "aws_access_key_id": aws_iam_role["Credentials"]["AccessKeyId"],
            "aws_secret_access_key": aws_iam_role["Credentials"]["SecretAccessKey"],
            "aws_session_token": aws_iam_role["Credentials"]["SessionToken"],
        }
    return boto3.Session(**kwargs)


@pytest.fixture(scope="session")
def ec2_client(boto3_session, aws_region):
    return boto3_session.client("ec2", region_name=aws_region)


@pytest.fixture(scope="session")
def ec2_client_map(ec2_client, boto3_session):
    regions = [reg["RegionName"] for reg in ec2_client.describe_regions()["Regions"]]
    ec2_map = {reg: boto3_session.client("ec2", region_name=reg) for reg in regions}

    return ec2_map


@pytest.fixture()
def route53_client(boto3_session, aws_region):
    return boto3_session.client("route53", region_name=aws_region)


@pytest.fixture()
def elbv2_client(boto3_session, aws_region):
    return boto3_session.client("elbv2", region_name=aws_region)


@pytest.fixture()
def autoscaling_client(boto3_session, aws_region):
    return boto3_session.client("autoscaling", region_name=aws_region)


@pytest.fixture()
def iam_client(boto3_session, aws_region):
    return boto3_session.client("iam", region_name=aws_region)


@pytest.fixture()
def secretsmanager_client(boto3_session, aws_region):
    return boto3_session.client("secretsmanager", region_name=aws_region)


@contextmanager
def terraform_data():
    with as_file(files("pytest_infrahouse.data.").joinpath("")) as datadir_path:
        yield datadir_path


@pytest.fixture(scope="session")
def service_network(keep_after, test_role_arn, aws_region):
    with as_file(
        files("pytest_infrahouse").joinpath("data/service-network")
    ) as module_dir:
        # Create service network
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            if test_role_arn:
                fp.write(f'role_arn = "{test_role_arn}"\n')
        with terraform_apply(
            module_dir,
            destroy_after=not keep_after,
            json_output=True,
            enable_trace=False,
        ) as tf_output:
            yield tf_output


@pytest.fixture(scope="session")
def instance_profile(keep_after, test_role_arn, aws_region):
    with as_file(
        files("pytest_infrahouse").joinpath("data/instance-profile")
    ) as module_dir:
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            if test_role_arn:
                fp.write(f'role_arn = "{test_role_arn}"\n')

        with terraform_apply(
            module_dir,
            destroy_after=not keep_after,
            json_output=True,
            enable_trace=False,
        ) as tf_output:
            yield tf_output


@pytest.fixture(scope="session")
def jumphost(service_network, keep_after, aws_region, test_role_arn, test_zone_name):
    subnet_public_ids = service_network["subnet_public_ids"]["value"]
    subnet_private_ids = service_network["subnet_private_ids"]["value"]

    with as_file(
            files("pytest_infrahouse").joinpath("data/jumphost")
    ) as module_dir:
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            fp.write(f'subnet_public_ids  = {json.dumps(subnet_public_ids)}\n')
            fp.write(f'subnet_private_ids = {json.dumps(subnet_private_ids)}\n')
            fp.write(f'test_zone = "{test_zone_name}"\n')
            if test_role_arn:
                fp.write(f'role_arn = "{test_role_arn}"\n')
        with terraform_apply(
                module_dir,
                destroy_after=not keep_after,
                json_output=True,
        ) as tf_output:
            yield tf_output
