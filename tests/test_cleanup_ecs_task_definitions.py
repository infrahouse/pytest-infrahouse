"""
Integration tests of the ECS task definition cleanup behind the
``cleanup_ecs_task_definitions`` fixture. They register real task
definitions in ECS.
"""

import logging
from secrets import token_hex
from typing import List

import boto3
import pytest
from botocore.client import BaseClient

from pytest_infrahouse import plugin

# More than ECS_DELETE_TASK_DEFINITIONS_BATCH_SIZE, so deletion takes two batches.
REVISION_COUNT = 13
INACTIVE_REVISION_COUNT = 4
SIBLING_REVISION_COUNT = 2
# DeleteTaskDefinitions API limit. Kept separate from the plugin's constant so the
# test's own cleanup does not depend on the code under test.
DELETE_BATCH_SIZE = 10
# Leftover revisions can be found by this tag if a test run's cleanup fails.
TAGS = [
    {
        "key": "created_by_test",
        "value": "infrahouse/pytest-infrahouse/test_cleanup_ecs_task_definitions",
    }
]


@pytest.fixture()
def ecs_client(boto3_session, aws_region) -> BaseClient:
    return boto3_session.client(
        "ecs", region_name=aws_region, config=plugin.ECS_CLIENT_CONFIG
    )


def _register_revisions(ecs_client: BaseClient, family: str, count: int) -> List[str]:
    """
    Register tagged task definition revisions with a minimal container definition.

    :param ecs_client: boto3 ECS client.
    :param family: Task definition family name.
    :param count: Number of revisions to register.
    :return: ARNs of the registered revisions.
    """
    return [
        ecs_client.register_task_definition(
            family=family,
            containerDefinitions=[
                {"name": "main", "image": "busybox", "memory": 128, "essential": True}
            ],
            tags=TAGS,
        )["taskDefinition"]["taskDefinitionArn"]
        for _ in range(count)
    ]


def _family_arns(ecs_client: BaseClient, family: str, status: str) -> List[str]:
    """
    List revisions of exactly one family, independently of the code under test.

    :param ecs_client: boto3 ECS client.
    :param family: Task definition family name.
    :param status: Revision status, ``ACTIVE`` or ``INACTIVE``.
    :return: ARNs of the family's revisions in the given status.
    """
    paginator = ecs_client.get_paginator("list_task_definitions")
    return [
        arn
        for page in paginator.paginate(familyPrefix=family, status=status)
        for arn in page["taskDefinitionArns"]
        if f":task-definition/{family}:" in arn
    ]


def _delete_families(ecs_client: BaseClient, families: List[str]) -> None:
    """
    Delete every revision of the given families without using the code under test,
    so a regression in the helper cannot also break the test's own cleanup.

    A ``ClientError`` propagates. Raised from a ``finally`` block, Python chains it
    to the test's original exception, and pytest reports both.

    :param ecs_client: boto3 ECS client.
    :param families: Task definition family names.
    """
    for family in families:
        inactive_arns = _family_arns(ecs_client, family, "INACTIVE")
        active_arns = _family_arns(ecs_client, family, "ACTIVE")
        for arn in active_arns:
            ecs_client.deregister_task_definition(taskDefinition=arn)
        arns = active_arns + inactive_arns
        for start in range(0, len(arns), DELETE_BATCH_SIZE):
            ecs_client.delete_task_definitions(
                taskDefinitions=arns[start : start + DELETE_BATCH_SIZE]
            )


def test_cleanup_deletes_family_and_keeps_sibling(ecs_client):
    """
    ACTIVE and INACTIVE revisions of the family are deleted in two batches,
    and a family whose name starts with the same prefix is not touched.
    """
    family = f"pytest-infrahouse-cleanup-{token_hex(4)}"
    sibling_family = f"{family}-sibling"
    try:
        family_arns = _register_revisions(ecs_client, family, REVISION_COUNT)
        for arn in family_arns[:INACTIVE_REVISION_COUNT]:
            ecs_client.deregister_task_definition(taskDefinition=arn)
        sibling_arns = _register_revisions(
            ecs_client, sibling_family, SIBLING_REVISION_COUNT
        )

        assert sorted(_family_arns(ecs_client, family, "ACTIVE")) == sorted(
            family_arns[INACTIVE_REVISION_COUNT:]
        )
        assert sorted(_family_arns(ecs_client, family, "INACTIVE")) == sorted(
            family_arns[:INACTIVE_REVISION_COUNT]
        )

        plugin._cleanup_ecs_task_definitions(ecs_client, family)

        assert _family_arns(ecs_client, family, "ACTIVE") == []
        assert _family_arns(ecs_client, family, "INACTIVE") == []
        assert sorted(_family_arns(ecs_client, sibling_family, "ACTIVE")) == sorted(
            sibling_arns
        )
        assert _family_arns(ecs_client, sibling_family, "INACTIVE") == []

    finally:
        # Deletes the sibling, and whatever is left of the family if the test
        # failed half-way.
        _delete_families(ecs_client, [family, sibling_family])


def test_cleanup_missing_family(ecs_client, caplog):
    """A family without revisions is a no-op that logs no warnings."""
    family = f"pytest-infrahouse-cleanup-{token_hex(4)}"
    with caplog.at_level(logging.WARNING):
        plugin._cleanup_ecs_task_definitions(ecs_client, family)

    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []


def test_cleanup_client_error_does_not_raise(aws_region, caplog):
    """
    A ClientError that survives the retries is logged as a warning naming
    the family instead of failing the session teardown.
    """
    family = f"pytest-infrahouse-cleanup-{token_hex(4)}"
    # Credentials that AWS rejects with UnrecognizedClientException.
    ecs_client = boto3.client(
        "ecs",
        region_name=aws_region,
        aws_access_key_id="invalid",
        aws_secret_access_key="invalid",
        config=plugin.ECS_CLIENT_CONFIG,
    )
    with caplog.at_level(logging.WARNING):
        plugin._cleanup_ecs_task_definitions(ecs_client, family)

    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    assert family in warnings[0]
