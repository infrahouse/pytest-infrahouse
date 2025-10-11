import logging

import pytest

pytest_plugins = "pytester"

LOG = logging.getLogger(__name__)


@pytest.fixture
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
