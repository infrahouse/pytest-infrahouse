#!/usr/bin/env python3
"""
Find all AWS resources in a region with a specific tag value.

Usage:
    python find_tagged_resources.py --tag-key <key> --tag-value <value> [--region <region>]
    python find_tagged_resources.py --tag-key <key> --tag-value <value> --delete  # Interactive deletion

Example:
    python find_tagged_resources.py --tag-key Environment --tag-value production
    python find_tagged_resources.py --tag-key created_by_fixture --tag-value "infrahouse/pytest-infrahouse/elasticsearch" --region us-west-2
    python find_tagged_resources.py --tag-key created_by_fixture --tag-value "infrahouse/pytest-infrahouse/elasticsearch" --delete
"""

import argparse
import re

import boto3
from botocore.exceptions import ClientError


def parse_arn(arn: str) -> dict:
    """
    Parse an ARN into its components.

    ARN format: arn:partition:service:region:account-id:resource-type/resource-id
    or: arn:partition:service:region:account-id:resource-type:resource-id
    """
    pattern = r"^arn:(?P<partition>[^:]+):(?P<service>[^:]+):(?P<region>[^:]*):(?P<account>[^:]*):(?P<resource>.+)$"
    match = re.match(pattern, arn)
    if not match:
        return None

    result = match.groupdict()

    # Parse resource part (can be type/id, type:id, or just id)
    # Some ARNs use : as separator (e.g., log-group:/aws/lambda/foo)
    # Some ARNs use / as separator (e.g., instance/i-12345)
    # Need to check which delimiter comes first
    resource = result["resource"]
    colon_pos = resource.find(":")
    slash_pos = resource.find("/")

    if colon_pos != -1 and (slash_pos == -1 or colon_pos < slash_pos):
        # Colon comes first or no slash: split on colon
        parts = resource.split(":", 1)
        result["resource_type"] = parts[0]
        result["resource_id"] = parts[1]
    elif slash_pos != -1:
        # Slash comes first: split on slash
        parts = resource.split("/", 1)
        result["resource_type"] = parts[0]
        result["resource_id"] = parts[1]
    else:
        result["resource_type"] = None
        result["resource_id"] = resource

    return result


def verify_resource_exists(session: boto3.Session, arn: str) -> bool:
    """
    Verify that a resource actually exists by making a direct API call.

    Returns True if resource exists, False if it doesn't or can't be verified.
    """
    parsed = parse_arn(arn)
    if not parsed:
        return True  # Can't parse, assume it exists

    service = parsed["service"]
    resource_type = parsed["resource_type"]
    resource_id = parsed["resource_id"]
    region = parsed["region"]

    try:
        if service == "ec2":
            client = session.client("ec2", region_name=region)
            if resource_type == "instance":
                resp = client.describe_instances(InstanceIds=[resource_id])
                instances = resp.get("Reservations", [])
                if not instances:
                    return False
                state = instances[0]["Instances"][0]["State"]["Name"]
                return state not in ["terminated", "shutting-down"]
            elif resource_type == "security-group":
                client.describe_security_groups(GroupIds=[resource_id])
            elif resource_type == "security-group-rule":
                client.describe_security_group_rules(SecurityGroupRuleIds=[resource_id])
            elif resource_type == "vpc":
                client.describe_vpcs(VpcIds=[resource_id])
            elif resource_type == "subnet":
                client.describe_subnets(SubnetIds=[resource_id])
            elif resource_type == "internet-gateway":
                client.describe_internet_gateways(InternetGatewayIds=[resource_id])
            elif resource_type == "route-table":
                client.describe_route_tables(RouteTableIds=[resource_id])
            elif resource_type == "network-acl":
                client.describe_network_acls(NetworkAclIds=[resource_id])
            elif resource_type == "key-pair":
                client.describe_key_pairs(KeyPairIds=[resource_id])
            elif resource_type == "volume":
                client.describe_volumes(VolumeIds=[resource_id])
            elif resource_type == "snapshot":
                client.describe_snapshots(SnapshotIds=[resource_id])
            elif resource_type == "image":
                client.describe_images(ImageIds=[resource_id])
            elif resource_type == "elastic-ip" or resource_type == "eip-allocation":
                # EIP ARN format: arn:aws:ec2:region:account:elastic-ip/eipalloc-xxx
                client.describe_addresses(AllocationIds=[resource_id])
            elif resource_type == "natgateway":
                resp = client.describe_nat_gateways(NatGatewayIds=[resource_id])
                if resp.get("NatGateways"):
                    state = resp["NatGateways"][0]["State"]
                    return state not in ["deleted", "deleting"]
                return False
            elif resource_type == "network-interface":
                client.describe_network_interfaces(NetworkInterfaceIds=[resource_id])
            elif resource_type == "vpc-endpoint":
                client.describe_vpc_endpoints(VpcEndpointIds=[resource_id])
            elif resource_type == "vpc-flow-log":
                resp = client.describe_flow_logs(FlowLogIds=[resource_id])
                return len(resp.get("FlowLogs", [])) > 0
            else:
                return True  # Unknown EC2 resource type, assume exists

        elif service == "rds":
            client = session.client("rds", region_name=region)
            if resource_type == "db":
                client.describe_db_instances(DBInstanceIdentifier=resource_id)
            elif resource_type == "cluster":
                client.describe_db_clusters(DBClusterIdentifier=resource_id)
            elif resource_type == "subgrp":
                client.describe_db_subnet_groups(DBSubnetGroupName=resource_id)
            elif resource_type == "pg":
                client.describe_db_parameter_groups(DBParameterGroupName=resource_id)
            elif resource_type == "secgrp":
                client.describe_db_security_groups(DBSecurityGroupName=resource_id)
            else:
                return True

        elif service == "elasticloadbalancing":
            client = session.client("elbv2", region_name=region)
            if resource_type == "loadbalancer":
                client.describe_load_balancers(LoadBalancerArns=[arn])
            elif resource_type == "targetgroup":
                client.describe_target_groups(TargetGroupArns=[arn])
            elif resource_type == "listener":
                client.describe_listeners(ListenerArns=[arn])
            else:
                return True

        elif service == "lambda":
            client = session.client("lambda", region_name=region)
            if resource_type == "function":
                client.get_function(FunctionName=resource_id)
            else:
                return True

        elif service == "dynamodb":
            client = session.client("dynamodb", region_name=region)
            if resource_type == "table":
                client.describe_table(TableName=resource_id)
            else:
                return True

        elif service == "s3":
            # S3 is global, don't pass region (ARN region field is empty for S3)
            client = session.client("s3")
            # For S3, resource_id is the bucket name
            client.head_bucket(Bucket=resource_id)

        elif service == "secretsmanager":
            client = session.client("secretsmanager", region_name=region)
            if resource_type == "secret":
                client.describe_secret(SecretId=arn)
            else:
                return True

        elif service == "iam":
            client = session.client("iam")  # IAM is global
            if resource_type == "role":
                client.get_role(RoleName=resource_id)
            elif resource_type == "policy":
                client.get_policy(PolicyArn=arn)
            elif resource_type == "instance-profile":
                client.get_instance_profile(InstanceProfileName=resource_id)
            elif resource_type == "user":
                client.get_user(UserName=resource_id)
            else:
                return True

        elif service == "logs":
            client = session.client("logs", region_name=region)
            if resource_type == "log-group":
                resp = client.describe_log_groups(logGroupNamePrefix=resource_id)
                # Check if exact match exists
                for lg in resp.get("logGroups", []):
                    if lg["logGroupName"] == resource_id:
                        return True
                return False
            else:
                return True

        elif service == "events":
            client = session.client("events", region_name=region)
            if resource_type == "rule":
                client.describe_rule(Name=resource_id)
            else:
                return True

        elif service == "sns":
            client = session.client("sns", region_name=region)
            # SNS topics use the full ARN
            client.get_topic_attributes(TopicArn=arn)

        elif service == "sqs":
            client = session.client("sqs", region_name=region)
            # Get queue URL from ARN
            account = parsed["account"]
            queue_name = resource_id
            queue_url = f"https://sqs.{region}.amazonaws.com/{account}/{queue_name}"
            client.get_queue_attributes(QueueUrl=queue_url, AttributeNames=["All"])

        elif service == "autoscaling":
            client = session.client("autoscaling", region_name=region)
            if resource_type == "autoScalingGroup":
                resp = client.describe_auto_scaling_groups(AutoScalingGroupNames=[resource_id])
                return len(resp.get("AutoScalingGroups", [])) > 0
            elif resource_type == "launchConfiguration":
                resp = client.describe_launch_configurations(LaunchConfigurationNames=[resource_id])
                return len(resp.get("LaunchConfigurations", [])) > 0
            else:
                return True

        elif service == "route53":
            client = session.client("route53")  # Route53 is global
            if resource_type == "hostedzone":
                client.get_hosted_zone(Id=resource_id)
            else:
                return True

        elif service == "kms":
            client = session.client("kms", region_name=region)
            if resource_type == "key":
                resp = client.describe_key(KeyId=resource_id)
                state = resp["KeyMetadata"]["KeyState"]
                return state not in ["PendingDeletion", "Disabled"]
            else:
                return True

        elif service == "elasticache":
            client = session.client("elasticache", region_name=region)
            if resource_type == "cluster":
                client.describe_cache_clusters(CacheClusterId=resource_id)
            elif resource_type == "subnetgroup":
                client.describe_cache_subnet_groups(CacheSubnetGroupName=resource_id)
            else:
                return True

        elif service == "es" or service == "opensearch":
            client = session.client("opensearch", region_name=region)
            if resource_type == "domain":
                client.describe_domain(DomainName=resource_id)
            else:
                return True

        else:
            # Unknown service, assume resource exists
            return True

        return True

    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        # These error codes indicate the resource doesn't exist
        not_found_codes = [
            "ResourceNotFoundException",
            "NotFoundException",
            "NoSuchEntity",
            "InvalidParameterValue",
            "DBInstanceNotFound",
            "DBClusterNotFoundFault",
            "DBSubnetGroupNotFoundFault",
            "LoadBalancerNotFound",
            "TargetGroupNotFound",
            "InvalidGroup.NotFound",
            "InvalidSecurityGroupRuleId.NotFound",
            "InvalidVpcID.NotFound",
            "InvalidSubnetID.NotFound",
            "InvalidInternetGatewayID.NotFound",
            "InvalidRouteTableID.NotFound",
            "InvalidNetworkAclID.NotFound",
            "InvalidKeyPair.NotFound",
            "InvalidVolume.NotFound",
            "InvalidSnapshot.NotFound",
            "InvalidAMIID.NotFound",
            "InvalidAllocationID.NotFound",
            "NatGatewayNotFound",
            "InvalidNetworkInterfaceID.NotFound",
            "InvalidVpcEndpointId.NotFound",
            "NoSuchBucket",
            "NoSuchHostedZone",
            "CacheClusterNotFound",
            "CacheSubnetGroupNotFoundFault",
            "ResourceNotFoundFault",
            "404",
        ]
        if error_code in not_found_codes:
            return False
        # For other errors, assume resource exists (could be permissions issue)
        return True
    except Exception:
        # For unexpected errors, assume resource exists
        return True


def delete_resource(session: boto3.Session, arn: str) -> tuple[bool, str]:
    """
    Delete a resource by ARN.

    Returns tuple of (success: bool, message: str)
    """
    parsed = parse_arn(arn)
    if not parsed:
        return False, "Cannot parse ARN"

    service = parsed["service"]
    resource_type = parsed["resource_type"]
    resource_id = parsed["resource_id"]
    region = parsed["region"]

    try:
        if service == "ec2":
            client = session.client("ec2", region_name=region)
            if resource_type == "instance":
                client.terminate_instances(InstanceIds=[resource_id])
                return True, "Instance termination initiated"
            elif resource_type == "security-group":
                client.delete_security_group(GroupId=resource_id)
                return True, "Security group deleted"
            elif resource_type == "security-group-rule":
                # Security group rules can't be deleted individually by ID easily
                # They need the security group ID and the rule specification
                return False, "Security group rules must be deleted via security group"
            elif resource_type == "vpc":
                client.delete_vpc(VpcId=resource_id)
                return True, "VPC deleted"
            elif resource_type == "subnet":
                client.delete_subnet(SubnetId=resource_id)
                return True, "Subnet deleted"
            elif resource_type == "internet-gateway":
                # Need to detach first, but we don't know the VPC
                return False, "Internet gateway must be detached from VPC first"
            elif resource_type == "route-table":
                client.delete_route_table(RouteTableId=resource_id)
                return True, "Route table deleted"
            elif resource_type == "network-acl":
                client.delete_network_acl(NetworkAclId=resource_id)
                return True, "Network ACL deleted"
            elif resource_type == "key-pair":
                client.delete_key_pair(KeyPairId=resource_id)
                return True, "Key pair deleted"
            elif resource_type == "volume":
                client.delete_volume(VolumeId=resource_id)
                return True, "Volume deleted"
            elif resource_type == "snapshot":
                client.delete_snapshot(SnapshotId=resource_id)
                return True, "Snapshot deleted"
            elif resource_type == "image":
                client.deregister_image(ImageId=resource_id)
                return True, "AMI deregistered"
            elif resource_type == "elastic-ip" or resource_type == "eip-allocation":
                client.release_address(AllocationId=resource_id)
                return True, "Elastic IP released"
            elif resource_type == "natgateway":
                client.delete_nat_gateway(NatGatewayId=resource_id)
                return True, "NAT Gateway deletion initiated"
            elif resource_type == "network-interface":
                client.delete_network_interface(NetworkInterfaceId=resource_id)
                return True, "Network interface deleted"
            elif resource_type == "vpc-endpoint":
                client.delete_vpc_endpoints(VpcEndpointIds=[resource_id])
                return True, "VPC endpoint deleted"
            elif resource_type == "vpc-flow-log":
                client.delete_flow_logs(FlowLogIds=[resource_id])
                return True, "VPC flow log deleted"
            else:
                return False, f"Unknown EC2 resource type: {resource_type}"

        elif service == "rds":
            client = session.client("rds", region_name=region)
            if resource_type == "db":
                client.delete_db_instance(
                    DBInstanceIdentifier=resource_id,
                    SkipFinalSnapshot=True,
                    DeleteAutomatedBackups=True
                )
                return True, "RDS instance deletion initiated"
            elif resource_type == "cluster":
                client.delete_db_cluster(
                    DBClusterIdentifier=resource_id,
                    SkipFinalSnapshot=True
                )
                return True, "RDS cluster deletion initiated"
            elif resource_type == "subgrp":
                client.delete_db_subnet_group(DBSubnetGroupName=resource_id)
                return True, "DB subnet group deleted"
            elif resource_type == "pg":
                client.delete_db_parameter_group(DBParameterGroupName=resource_id)
                return True, "DB parameter group deleted"
            else:
                return False, f"Unknown RDS resource type: {resource_type}"

        elif service == "elasticloadbalancing":
            client = session.client("elbv2", region_name=region)
            if resource_type == "loadbalancer":
                client.delete_load_balancer(LoadBalancerArn=arn)
                return True, "Load balancer deleted"
            elif resource_type == "targetgroup":
                client.delete_target_group(TargetGroupArn=arn)
                return True, "Target group deleted"
            elif resource_type == "listener":
                client.delete_listener(ListenerArn=arn)
                return True, "Listener deleted"
            else:
                return False, f"Unknown ELB resource type: {resource_type}"

        elif service == "lambda":
            client = session.client("lambda", region_name=region)
            if resource_type == "function":
                client.delete_function(FunctionName=resource_id)
                return True, "Lambda function deleted"
            else:
                return False, f"Unknown Lambda resource type: {resource_type}"

        elif service == "dynamodb":
            client = session.client("dynamodb", region_name=region)
            if resource_type == "table":
                client.delete_table(TableName=resource_id)
                return True, "DynamoDB table deleted"
            else:
                return False, f"Unknown DynamoDB resource type: {resource_type}"

        elif service == "s3":
            # S3 is global, don't pass region (ARN region field is empty for S3)
            client = session.client("s3")
            bucket_name = resource_id

            # Count objects first
            object_count = 0
            paginator = client.get_paginator("list_object_versions")
            for page in paginator.paginate(Bucket=bucket_name):
                object_count += len(page.get("Versions", []))
                object_count += len(page.get("DeleteMarkers", []))

            if object_count > 0:
                confirm = input(f"  Bucket contains {object_count} objects/versions. Empty and delete? [y/n]: ").strip().lower()
                if confirm not in ["y", "yes"]:
                    return False, "Bucket deletion cancelled by user"

                # Delete all object versions and delete markers
                paginator = client.get_paginator("list_object_versions")
                for page in paginator.paginate(Bucket=bucket_name):
                    objects_to_delete = []
                    for version in page.get("Versions", []):
                        objects_to_delete.append({
                            "Key": version["Key"],
                            "VersionId": version["VersionId"]
                        })
                    for marker in page.get("DeleteMarkers", []):
                        objects_to_delete.append({
                            "Key": marker["Key"],
                            "VersionId": marker["VersionId"]
                        })
                    if objects_to_delete:
                        client.delete_objects(
                            Bucket=bucket_name,
                            Delete={"Objects": objects_to_delete}
                        )

            # Now delete the empty bucket
            client.delete_bucket(Bucket=bucket_name)
            return True, f"Bucket deleted (removed {object_count} objects/versions)"

        elif service == "secretsmanager":
            client = session.client("secretsmanager", region_name=region)
            if resource_type == "secret":
                client.delete_secret(SecretId=arn, ForceDeleteWithoutRecovery=True)
                return True, "Secret deleted"
            else:
                return False, f"Unknown Secrets Manager resource type: {resource_type}"

        elif service == "iam":
            client = session.client("iam")
            if resource_type == "role":
                # First, detach all managed policies
                policies_detached = 0
                paginator = client.get_paginator("list_attached_role_policies")
                for page in paginator.paginate(RoleName=resource_id):
                    for policy in page.get("AttachedPolicies", []):
                        client.detach_role_policy(
                            RoleName=resource_id,
                            PolicyArn=policy["PolicyArn"]
                        )
                        policies_detached += 1

                # Delete all inline policies
                inline_deleted = 0
                paginator = client.get_paginator("list_role_policies")
                for page in paginator.paginate(RoleName=resource_id):
                    for policy_name in page.get("PolicyNames", []):
                        client.delete_role_policy(
                            RoleName=resource_id,
                            PolicyName=policy_name
                        )
                        inline_deleted += 1

                # Remove role from all instance profiles
                profiles_removed = 0
                paginator = client.get_paginator("list_instance_profiles_for_role")
                for page in paginator.paginate(RoleName=resource_id):
                    for profile in page.get("InstanceProfiles", []):
                        client.remove_role_from_instance_profile(
                            InstanceProfileName=profile["InstanceProfileName"],
                            RoleName=resource_id
                        )
                        profiles_removed += 1

                # Now delete the role
                client.delete_role(RoleName=resource_id)
                return True, f"IAM role deleted (detached {policies_detached} policies, deleted {inline_deleted} inline policies, removed from {profiles_removed} instance profiles)"
            elif resource_type == "policy":
                client.delete_policy(PolicyArn=arn)
                return True, "IAM policy deleted"
            elif resource_type == "instance-profile":
                # First, remove all roles from the instance profile
                roles_removed = 0
                try:
                    resp = client.get_instance_profile(InstanceProfileName=resource_id)
                    for role in resp.get("InstanceProfile", {}).get("Roles", []):
                        client.remove_role_from_instance_profile(
                            InstanceProfileName=resource_id,
                            RoleName=role["RoleName"]
                        )
                        roles_removed += 1
                except ClientError:
                    pass  # Instance profile might not have roles

                client.delete_instance_profile(InstanceProfileName=resource_id)
                return True, f"Instance profile deleted (removed {roles_removed} roles)"
            else:
                return False, f"Unknown IAM resource type: {resource_type}"

        elif service == "logs":
            client = session.client("logs", region_name=region)
            if resource_type == "log-group":
                client.delete_log_group(logGroupName=resource_id)
                return True, "Log group deleted"
            else:
                return False, f"Unknown CloudWatch Logs resource type: {resource_type}"

        elif service == "events":
            client = session.client("events", region_name=region)
            if resource_type == "rule":
                # First, list and remove all targets
                targets_removed = 0
                paginator = client.get_paginator("list_targets_by_rule")
                try:
                    for page in paginator.paginate(Rule=resource_id):
                        target_ids = [t["Id"] for t in page.get("Targets", [])]
                        if target_ids:
                            client.remove_targets(Rule=resource_id, Ids=target_ids)
                            targets_removed += len(target_ids)
                except ClientError:
                    pass  # Rule might not have targets

                # Now delete the rule
                client.delete_rule(Name=resource_id)
                return True, f"EventBridge rule deleted (removed {targets_removed} targets)"
            else:
                return False, f"Unknown EventBridge resource type: {resource_type}"

        elif service == "sns":
            client = session.client("sns", region_name=region)
            client.delete_topic(TopicArn=arn)
            return True, "SNS topic deleted"

        elif service == "sqs":
            client = session.client("sqs", region_name=region)
            account = parsed["account"]
            queue_name = resource_id
            queue_url = f"https://sqs.{region}.amazonaws.com/{account}/{queue_name}"
            client.delete_queue(QueueUrl=queue_url)
            return True, "SQS queue deleted"

        elif service == "autoscaling":
            client = session.client("autoscaling", region_name=region)
            if resource_type == "autoScalingGroup":
                client.delete_auto_scaling_group(
                    AutoScalingGroupName=resource_id,
                    ForceDelete=True
                )
                return True, "Auto Scaling group deletion initiated"
            elif resource_type == "launchConfiguration":
                client.delete_launch_configuration(LaunchConfigurationName=resource_id)
                return True, "Launch configuration deleted"
            else:
                return False, f"Unknown Auto Scaling resource type: {resource_type}"

        elif service == "route53":
            client = session.client("route53")
            if resource_type == "hostedzone":
                # First, delete all non-NS/SOA records
                records_deleted = 0
                paginator = client.get_paginator("list_resource_record_sets")
                for page in paginator.paginate(HostedZoneId=resource_id):
                    changes = []
                    for record in page.get("ResourceRecordSets", []):
                        # Skip NS and SOA records at zone apex - AWS manages these
                        if record["Type"] in ["NS", "SOA"]:
                            continue
                        changes.append({
                            "Action": "DELETE",
                            "ResourceRecordSet": record
                        })
                    if changes:
                        client.change_resource_record_sets(
                            HostedZoneId=resource_id,
                            ChangeBatch={"Changes": changes}
                        )
                        records_deleted += len(changes)

                # Now delete the hosted zone
                client.delete_hosted_zone(Id=resource_id)
                return True, f"Hosted zone deleted (removed {records_deleted} records)"
            else:
                return False, f"Unknown Route53 resource type: {resource_type}"

        elif service == "kms":
            client = session.client("kms", region_name=region)
            if resource_type == "key":
                client.schedule_key_deletion(KeyId=resource_id, PendingWindowInDays=7)
                return True, "KMS key scheduled for deletion (7 days)"
            else:
                return False, f"Unknown KMS resource type: {resource_type}"

        elif service == "elasticache":
            client = session.client("elasticache", region_name=region)
            if resource_type == "cluster":
                client.delete_cache_cluster(CacheClusterId=resource_id)
                return True, "ElastiCache cluster deletion initiated"
            elif resource_type == "subnetgroup":
                client.delete_cache_subnet_group(CacheSubnetGroupName=resource_id)
                return True, "ElastiCache subnet group deleted"
            else:
                return False, f"Unknown ElastiCache resource type: {resource_type}"

        elif service == "es" or service == "opensearch":
            client = session.client("opensearch", region_name=region)
            if resource_type == "domain":
                client.delete_domain(DomainName=resource_id)
                return True, "OpenSearch domain deletion initiated"
            else:
                return False, f"Unknown OpenSearch resource type: {resource_type}"

        else:
            return False, f"Unknown service: {service}"

    except ClientError as e:
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        return False, f"AWS Error: {error_msg}"
    except Exception as e:
        return False, f"Error: {str(e)}"


def find_iam_roles_by_tag(session: boto3.Session, tag_key: str, tag_value: str) -> list[dict]:
    """
    Find IAM roles by tag using direct IAM API (fallback for Resource Groups Tagging API gaps).

    Returns list of resources with ARN, tags, and exists=True
    """
    client = session.client("iam")
    roles = []

    paginator = client.get_paginator("list_roles")
    for page in paginator.paginate():
        for role in page.get("Roles", []):
            role_name = role["RoleName"]
            try:
                # Get tags for this role
                tag_response = client.list_role_tags(RoleName=role_name)
                role_tags = {t["Key"]: t["Value"] for t in tag_response.get("Tags", [])}

                # Check if the tag matches
                if role_tags.get(tag_key) == tag_value:
                    roles.append({
                        "arn": role["Arn"],
                        "tags": role_tags,
                        "exists": True
                    })
            except ClientError:
                continue  # Skip roles we can't read tags for

    return roles


def find_resources_by_tag(tag_key: str, tag_value: str, region: str = None, verify: bool = True) -> list[dict]:
    """
    Find all resources with a specific tag key/value pair using the Resource Groups Tagging API.

    Args:
        tag_key: The tag key to search for
        tag_value: The tag value to match
        region: AWS region (uses default if not specified)
        verify: If True, verify each resource still exists

    Returns:
        List of resources with their ARNs, tags, and existence status
    """
    session = boto3.Session(region_name=region)
    client = session.client("resourcegroupstaggingapi")

    resources = []
    seen_arns = set()

    # First, find IAM roles directly (they're often missed by Resource Groups Tagging API)
    # We want roles first so they can be deleted before policies
    print("Searching IAM roles directly...")
    iam_roles = find_iam_roles_by_tag(session, tag_key, tag_value)
    for role in iam_roles:
        resources.append(role)
        seen_arns.add(role["arn"])

    # Now search via Resource Groups Tagging API
    print("Searching via Resource Groups Tagging API...")
    paginator = client.get_paginator("get_resources")

    for page in paginator.paginate(
        TagFilters=[
            {
                "Key": tag_key,
                "Values": [tag_value]
            }
        ]
    ):
        for resource in page.get("ResourceTagMappingList", []):
            arn = resource["ResourceARN"]
            # Skip if already found via direct IAM search
            if arn in seen_arns:
                continue
            exists = verify_resource_exists(session, arn) if verify else True
            resources.append({
                "arn": arn,
                "tags": {tag["Key"]: tag["Value"] for tag in resource.get("Tags", [])},
                "exists": exists
            })
            seen_arns.add(arn)

    return resources


def main():
    parser = argparse.ArgumentParser(
        description="Find AWS resources by tag key/value"
    )
    parser.add_argument(
        "--tag-key", "-k",
        required=True,
        help="Tag key to search for"
    )
    parser.add_argument(
        "--tag-value", "-v",
        required=True,
        help="Tag value to match"
    )
    parser.add_argument(
        "--region", "-r",
        default=None,
        help="AWS region (uses default if not specified)"
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Skip verification of resource existence (faster but may show stale results)"
    )
    parser.add_argument(
        "--show-deleted",
        action="store_true",
        help="Also show resources that no longer exist (cached/stale entries)"
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Interactively prompt to delete each existing resource"
    )

    args = parser.parse_args()

    print(f"Searching for resources with tag {args.tag_key}={args.tag_value}")
    if args.region:
        print(f"Region: {args.region}")
    if not args.no_verify:
        print("Verifying resource existence...")
    print()

    session = boto3.Session(region_name=args.region)

    resources = find_resources_by_tag(
        args.tag_key,
        args.tag_value,
        args.region,
        verify=not args.no_verify
    )

    if not resources:
        print("No resources found.")
        return

    existing = [r for r in resources if r["exists"]]
    deleted = [r for r in resources if not r["exists"]]

    print(f"Found {len(existing)} existing resource(s)")
    if deleted:
        print(f"Found {len(deleted)} stale/deleted resource(s) in cache")
    print()

    if existing:
        if args.delete:
            print("=== INTERACTIVE DELETION MODE ===\n")
            for i, resource in enumerate(existing, 1):
                print(f"[{i}/{len(existing)}] Resource:")
                print(f"  ARN: {resource['arn']}")
                print("  Tags:")
                for key, value in resource["tags"].items():
                    print(f"    {key}: {value}")
                print()

                while True:
                    response = input("Delete this resource? [y/n/q] (y=yes, n=no, q=quit): ").strip().lower()
                    if response in ["y", "yes"]:
                        print("  Deleting...")
                        success, message = delete_resource(session, resource["arn"])
                        if success:
                            print(f"  SUCCESS: {message}")
                        else:
                            print(f"  FAILED: {message}")
                        print()
                        break
                    elif response in ["n", "no"]:
                        print("  Skipped.")
                        print()
                        break
                    elif response in ["q", "quit"]:
                        print("  Quitting deletion mode.")
                        return
                    else:
                        print("  Please enter 'y', 'n', or 'q'.")
        else:
            print("=== EXISTING RESOURCES ===\n")
            for resource in existing:
                print(f"ARN: {resource['arn']}")
                print("Tags:")
                for key, value in resource["tags"].items():
                    print(f"  {key}: {value}")
                print()

    if args.show_deleted and deleted:
        print("=== STALE/DELETED RESOURCES (cached) ===\n")
        for resource in deleted:
            print(f"ARN: {resource['arn']} [DELETED]")
            print()


if __name__ == "__main__":
    main()