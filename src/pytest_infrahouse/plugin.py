import json
import logging
from contextlib import contextmanager
from importlib.resources import as_file, files
from os import path as osp
from pathlib import Path
from textwrap import dedent

import boto3
import pytest
from botocore.exceptions import ClientError

from .terraform import terraform_apply

AWS_DEFAULT_REGION = "us-east-1"
TEST_ZONE = "ci-cd.infrahouse.com"
LOG = logging.getLogger()


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
def service_network(request, keep_after, test_role_arn, aws_region):
    calling_test = osp.basename(request.node.path)
    with as_file(
        files("pytest_infrahouse").joinpath("data/service-network")
    ) as module_dir:
        # Create service network
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            fp.write(f'calling_test = "{calling_test}"\n')
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
def instance_profile(request, keep_after, test_role_arn, aws_region):
    calling_test = osp.basename(request.node.path)
    with as_file(
        files("pytest_infrahouse").joinpath("data/instance-profile")
    ) as module_dir:
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            fp.write(f'calling_test = "{calling_test}"\n')
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
def jumphost(
    request, service_network, keep_after, aws_region, test_role_arn, test_zone_name
):
    calling_test = osp.basename(request.node.path)
    subnet_public_ids = service_network["subnet_public_ids"]["value"]
    subnet_private_ids = service_network["subnet_private_ids"]["value"]

    with as_file(files("pytest_infrahouse").joinpath("data/jumphost")) as module_dir:
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            fp.write(f'calling_test = "{calling_test}"\n')
            fp.write(f"subnet_public_ids  = {json.dumps(subnet_public_ids)}\n")
            fp.write(f"subnet_private_ids = {json.dumps(subnet_private_ids)}\n")
            fp.write(f'test_zone = "{test_zone_name}"\n')
            if test_role_arn:
                fp.write(f'role_arn = "{test_role_arn}"\n')
        with terraform_apply(
            module_dir,
            destroy_after=not keep_after,
            json_output=True,
        ) as tf_output:
            yield tf_output


@pytest.fixture(scope="session")
def elasticsearch(
    request, service_network, keep_after, aws_region, test_role_arn, test_zone_name
):
    calling_test = osp.basename(request.node.path)
    bootstrap_flag_file = ".bootstrapped"

    def cluster_bootstrapped(path: Path) -> bool:
        return path.joinpath(bootstrap_flag_file).exists()

    subnet_public_ids = service_network["subnet_public_ids"]["value"]
    internet_gateway_id = service_network["internet_gateway_id"]["value"]

    with as_file(
        files("pytest_infrahouse").joinpath("data/elasticsearch")
    ) as module_dir:
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            fp.write(f'calling_test = "{calling_test}"\n')
            fp.write(f"subnet_public_ids  = {json.dumps(subnet_public_ids)}\n")
            fp.write(f'test_zone = "{test_zone_name}"\n')
            fp.write(f'internet_gateway_id = "{internet_gateway_id}"\n')
            fp.write(
                f"bootstrap_mode = {str(not cluster_bootstrapped(module_dir)).lower()}\n"
            )
            if test_role_arn:
                fp.write(f'role_arn = "{test_role_arn}"\n')
        with terraform_apply(
            module_dir,
            destroy_after=not keep_after,
            json_output=True,
        ):
            module_dir.joinpath(bootstrap_flag_file).touch()
            with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
                fp.write(f'region = "{aws_region}"\n')
                fp.write(f'calling_test = "{calling_test}"\n')
                fp.write(f"subnet_public_ids  = {json.dumps(subnet_public_ids)}\n")
                fp.write(f'test_zone = "{test_zone_name}"\n')
                fp.write(f'internet_gateway_id = "{internet_gateway_id}"\n')
                fp.write(
                    f"bootstrap_mode = {str(not cluster_bootstrapped(module_dir)).lower()}\n"
                )
                if test_role_arn:
                    fp.write(f'role_arn = "{test_role_arn}"\n')
            with terraform_apply(
                module_dir,
                destroy_after=not keep_after,
                json_output=True,
            ) as tf_output:
                yield tf_output
                if not keep_after:
                    module_dir.joinpath(bootstrap_flag_file).unlink(missing_ok=True)


@pytest.fixture(scope="session")
def ses(request, aws_region, test_zone_name, test_role_arn, keep_after):
    calling_test = osp.basename(request.node.path)
    with as_file(files("pytest_infrahouse").joinpath("data/ses")) as module_dir:
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            fp.write(f'calling_test = "{calling_test}"\n')
            fp.write(f'test_zone = "{test_zone_name}"\n')
            if test_role_arn:
                fp.write(f'role_arn = "{test_role_arn}"\n')
    with terraform_apply(
        module_dir,
        destroy_after=not keep_after,
        json_output=True,
    ) as tf_output:
        yield tf_output


@pytest.fixture(scope="session")
def probe_role(request, aws_region, test_role_arn, keep_after):
    calling_test = osp.basename(request.node.path)
    with as_file(files("pytest_infrahouse").joinpath("data/probe-role")) as module_dir:
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(f'region       = "{aws_region}"\n')
            fp.write(f'calling_test = "{calling_test}"\n')
            if test_role_arn:
                fp.write(f'role_arn     = "{test_role_arn}"\n')
                fp.write(f'trusted_arns = ["{test_role_arn}"]\n')

    with terraform_apply(
        module_dir,
        destroy_after=not keep_after,
        json_output=True,
    ) as tf_output:
        yield tf_output


@pytest.fixture(scope="session")
def subzone(
    request, test_role_arn, aws_region, test_zone_name, keep_after, boto3_session
):
    """
    Create DNS zone
    """
    calling_test = osp.basename(request.node.path)
    zone_id = None
    with as_file(files("pytest_infrahouse").joinpath("data/subzone")) as module_dir:
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(
                dedent(
                    f"""
                    parent_zone_name = "{test_zone_name}"
                    region           = "{aws_region}"
                    calling_test     = "{calling_test}"
                    """
                )
            )
            if test_role_arn:
                fp.write(
                    dedent(
                        f"""
                        role_arn = "{test_role_arn}"
                        """
                    )
                )
    try:
        with terraform_apply(
            module_dir,
            destroy_after=not keep_after,
            json_output=True,
        ) as tf_output:
            zone_id = tf_output["subzone_id"]["value"]
            yield tf_output
            if not keep_after:
                _cleanup_dns_zone(zone_id, boto3_session.client("route53"))

    finally:
        if not keep_after and zone_id:
            _cleanup_dns_zone(zone_id, boto3_session.client("route53"))
            _delete_dns_zone(zone_id, boto3_session.client("route53"))


def _delete_dns_zone(zone_id, route53_client):
    """
    Delete the zone itself
    """
    LOG.info(f"Cleaning up DNS zone {zone_id}")

    try:
        LOG.info(f"Deleting DNS zone {zone_id}")
        route53_client.delete_hosted_zone(Id=zone_id)
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchHostedZone":
            LOG.info(f"DNS zone {zone_id} does not exist, skipping cleanup")
        else:
            LOG.error(f"Failed to cleanup DNS zone {zone_id}: {e}")
            raise e


def _cleanup_dns_zone(zone_id, route53_client):
    """
    Delete all records in the DNS zone
    """
    LOG.info(f"Cleaning up DNS zone {zone_id}")

    try:
        paginator = route53_client.get_paginator("list_resource_record_sets")
        for page in paginator.paginate(HostedZoneId=zone_id):
            for record_set in page["ResourceRecordSets"]:
                if record_set["Type"] not in ["NS", "SOA"]:
                    LOG.info(
                        f"Deleting DNS record: {record_set['Name']} ({record_set['Type']})"
                    )
                    route53_client.change_resource_record_sets(
                        HostedZoneId=zone_id,
                        ChangeBatch={
                            "Changes": [
                                {"Action": "DELETE", "ResourceRecordSet": record_set}
                            ]
                        },
                    )

    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchHostedZone":
            LOG.info(f"DNS zone {zone_id} does not exist, skipping cleanup")
        else:
            LOG.error(f"Failed to cleanup DNS zone {zone_id}: {e}")
            raise e
