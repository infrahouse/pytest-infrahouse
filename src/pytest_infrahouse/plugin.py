import json
import logging
import time
from contextlib import contextmanager
from datetime import timezone
from importlib.resources import as_file, files
from os import path as osp
from pathlib import Path
from textwrap import dedent

import boto3
import pytest
from botocore.credentials import RefreshableCredentials
from botocore.exceptions import ClientError
from botocore.session import Session as BotocoreSession

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
        "--test-role-duration",
        action="store",
        default=3600,
        help=(
            "Duration in seconds for the assumed role session. "
            "Max is 12h when assuming from long-term creds; "
            "if role chaining, AWS hard-limits to 3600 (1h)."
        ),
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
def test_role_duration(request):
    return int(request.config.getoption("--test-role-duration"))


@pytest.fixture(scope="session")
def test_zone_name(request):
    return request.config.getoption("--test-zone-name")


@pytest.fixture(scope="session")
def aws_region(request):
    return request.config.getoption("--aws-region")


@pytest.fixture(scope="session")
def boto3_session(test_role_arn, test_role_duration, aws_region):
    """
    Create a boto3 session with automatic credential refresh for long-running tests.

    If test_role_arn is provided, this will create a session that automatically
    refreshes credentials when they expire, allowing tests to run longer than
    the 1-hour limit imposed by role chaining.

    If starting from *chained* (temporary) credentials, caps DurationSeconds at 3600.

    Pins STS to the provided region and sets session region.
    """
    if not test_role_arn:
        # No role specified, use default credentials
        return boto3.Session(region_name=aws_region)

    # Helper: are we already using temp creds (i.e., chaining)?
    base_sts = boto3.client("sts", region_name=aws_region)
    caller = base_sts.get_caller_identity()  # does not require permissions beyond STS
    # Arn looks like: arn:aws:sts::<acct>:assumed-role/RoleName/SessionName
    arn = caller.get("Arn", "")
    is_chaining = ":assumed-role/" in arn

    # Enforce AWS limit under chaining
    max_allowed = 3600 if is_chaining else test_role_duration
    requested = int(test_role_duration)
    duration = min(requested, max_allowed)

    def _session_name() -> str:
        base = test_role_arn.split("/")[-1] or "pytest"
        # keep <=64 chars, add entropy
        suffix = str(int(time.time()))
        name = f"{base[:48]}-{suffix}"
        return name[:64]

    # Create a refresh function that will be called when credentials expire
    def refresh_credentials():
        LOG.info(
            "Refreshing credentials for role=%s (requested=%ss, chaining=%s → using=%ss)",
            test_role_arn,
            requested,
            is_chaining,
            duration,
        )
        resp = base_sts.assume_role(
            RoleArn=test_role_arn,
            RoleSessionName=_session_name(),
            DurationSeconds=duration,
        )
        credentials = resp["Credentials"]
        # Normalize to RFC3339 UTC with trailing Z
        exp = (
            credentials["Expiration"]
            .astimezone(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z")
        )
        return {
            "access_key": credentials["AccessKeyId"],
            "secret_key": credentials["SecretAccessKey"],
            "token": credentials["SessionToken"],
            "expiry_time": exp,
        }

    # Create refreshable credentials
    session_credentials = RefreshableCredentials.create_from_metadata(
        metadata=refresh_credentials(),
        refresh_using=refresh_credentials,
        method="sts-assume-role",
    )

    botocore_session = BotocoreSession()
    # Prefer explicit config vs defaults
    botocore_session.set_config_variable("region", aws_region)
    botocore_session.set_config_variable("sts_regional_endpoints", "regional")
    # Attach credentials (yes, this is private; stable in practice)
    botocore_session._credentials = session_credentials

    return boto3.Session(botocore_session=botocore_session, region_name=aws_region)


@pytest.fixture(scope="session")
def ec2_client(boto3_session, aws_region):
    return boto3_session.client("ec2", region_name=aws_region)


@pytest.fixture(scope="session")
def ec2_client_map(boto3_session):
    cache = {}

    def get(region):
        if region not in cache:
            cache[region] = boto3_session.client("ec2", region_name=region)
        return cache[region]

    return get


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
    request,
    service_network,
    keep_after,
    aws_region,
    subzone,
    test_role_arn,
):
    calling_test = osp.basename(request.node.path)
    subnet_public_ids = service_network["subnet_public_ids"]["value"]
    subnet_private_ids = service_network["subnet_private_ids"]["value"]
    test_zone_id = subzone["subzone_id"]["value"]

    with as_file(files("pytest_infrahouse").joinpath("data/jumphost")) as module_dir:
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            fp.write(f'calling_test = "{calling_test}"\n')
            fp.write(f"subnet_public_ids  = {json.dumps(subnet_public_ids)}\n")
            fp.write(f"subnet_private_ids = {json.dumps(subnet_private_ids)}\n")
            fp.write(f'test_zone_id = "{test_zone_id}"\n')
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
    request, service_network, keep_after, aws_region, test_role_arn, subzone
):
    calling_test = osp.basename(request.node.path)
    bootstrap_flag_file = ".bootstrapped"

    def cluster_bootstrapped(path: Path) -> bool:
        return path.joinpath(bootstrap_flag_file).exists()

    subnet_public_ids = service_network["subnet_public_ids"]["value"]
    internet_gateway_id = service_network["internet_gateway_id"]["value"]

    test_zone_id = subzone["subzone_id"]["value"]
    subdomain = subzone["subdomain"]["value"]

    with as_file(
        files("pytest_infrahouse").joinpath("data/elasticsearch")
    ) as module_dir:
        try:
            with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
                fp.write(f'region = "{aws_region}"\n')
                fp.write(f'calling_test = "{calling_test}"\n')
                fp.write(f"subnet_public_ids  = {json.dumps(subnet_public_ids)}\n")
                fp.write(f'test_zone_id = "{test_zone_id}"\n')
                fp.write(f'internet_gateway_id = "{internet_gateway_id}"\n')
                fp.write(f'cluster_name = "main-cluster-{subdomain}"\n')
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
                    fp.write(f'test_zone_id = "{test_zone_id}"\n')
                    fp.write(f'internet_gateway_id = "{internet_gateway_id}"\n')
                    fp.write(f'cluster_name = "main-cluster-{subdomain}"\n')
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
        finally:
            if not keep_after:
                module_dir.joinpath(bootstrap_flag_file).unlink(missing_ok=True)


@pytest.fixture(scope="session")
def postgres(request, service_network, keep_after, aws_region, test_role_arn):
    """
    Create a PostgreSQL RDS instance for testing database operations.

    This fixture provides a fully configured PostgreSQL RDS instance running
    in private subnets with proper security group configuration.

    Returns:
        dict: Terraform outputs including:
            - endpoint: Full connection endpoint (host:port)
            - address: Database hostname
            - port: Database port
            - database_name: Default database name
            - master_username: Master username
            - master_password: Master password (sensitive)
            - secret_arn: ARN of Secrets Manager secret with credentials
            - connection_string: PostgreSQL connection URI (sensitive)
    """
    calling_test = osp.basename(request.node.path)
    with as_file(files("pytest_infrahouse").joinpath("data/postgres")) as module_dir:
        with open(osp.join(module_dir, "terraform.tfvars"), "w") as fp:
            fp.write(f'region = "{aws_region}"\n')
            fp.write(f'calling_test = "{calling_test}"\n')
            fp.write(
                f'subnet_private_ids = {json.dumps(service_network["subnet_private_ids"]["value"])}\n'
            )
            fp.write(f'environment = "test"\n')
            if test_role_arn:
                fp.write(f'role_arn = "{test_role_arn}"\n')

        with terraform_apply(
            module_dir,
            destroy_after=not keep_after,
            json_output=True,
        ) as tf_output:
            yield tf_output


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


@pytest.fixture(scope="session")
def cleanup_ecs_task_definitions(boto3_session, aws_region, keep_after):
    """Fixture to track and cleanup ECS task definitions created during tests."""
    task_families = set()

    def register_task_family(family_name):
        """Register a task family for cleanup."""
        task_families.add(family_name)

    # Provide the registration function to the test
    yield register_task_family

    # Cleanup: Deregister and delete all task definitions for tracked families
    if task_families and not keep_after:
        ecs = boto3_session.client("ecs", region_name=aws_region)
        for family in task_families:
            LOG.info(f"Cleaning up task definitions for family: {family}")

            # Collect all task definitions (ACTIVE and INACTIVE)
            all_task_defs = []
            for status in ["ACTIVE", "INACTIVE"]:
                response = ecs.list_task_definitions(
                    familyPrefix=family, status=status, sort="DESC"
                )
                all_task_defs.extend(response.get("taskDefinitionArns", []))

            # Deregister and delete each task definition
            for task_def_arn in all_task_defs:
                ecs.deregister_task_definition(taskDefinition=task_def_arn)
                LOG.info(f"Deregistered task definition: {task_def_arn}")
                ecs.delete_task_definitions(taskDefinitions=[task_def_arn])
                LOG.info(f"Deleted task definition: {task_def_arn}")
