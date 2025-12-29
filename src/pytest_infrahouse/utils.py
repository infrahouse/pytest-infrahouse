"""
Utility functions for pytest-infrahouse tests.

This module provides helper functions for common AWS operations
in infrastructure tests, such as waiting for ASG instance refreshes.
"""

import time

from . import DEFAULT_PROGRESS_INTERVAL, LOG

__all__ = ["wait_for_instance_refresh"]


def wait_for_instance_refresh(
    asg_name: str,
    autoscaling_client,
    timeout: int = 3600,
    poll_interval: int = DEFAULT_PROGRESS_INTERVAL,
) -> None:
    """
    Wait for any in-progress ASG instance refreshes to complete.

    FIX: Treats "Cancelled" as a completed state (not a failure).
    If user manually cancels a refresh, we just continue - there's nothing to wait for.

    Example:
        >>> from pytest_infrahouse.utils import wait_for_instance_refresh
        >>> wait_for_instance_refresh(
        ...     asg_name="my-jumphost-asg",
        ...     autoscaling_client=autoscaling_client,
        ...     timeout=600,
        ...     poll_interval=5
        ... )

    :param asg_name: Name of the Auto Scaling Group
    :param autoscaling_client: boto3 autoscaling client
    :param timeout: Maximum time to wait in seconds (default 3600 = 1 hour)
    :param poll_interval: How often to poll in seconds (default 10)
    :raises TimeoutError: If timeout is reached with pending refreshes
    :raises RuntimeError: If any refresh fails or ASG is not found
    :raises Exception: On unexpected errors
    """
    LOG.info("=" * 80)
    LOG.info("Checking for in-progress ASG instance refreshes for %s", asg_name)
    LOG.info("=" * 80)

    start_time = time.time()
    seen_statuses = {}  # Track per refresh_id to avoid duplicate logs

    while time.time() - start_time < timeout:
        try:
            response = autoscaling_client.describe_instance_refreshes(
                AutoScalingGroupName=asg_name, MaxRecords=10
            )

            instance_refreshes = response.get("InstanceRefreshes", [])

            # Check for ACTUAL failures (not cancelled)
            # Cancelled means user manually cancelled - not a failure, just done
            failed_states = ["Failed", "RollbackSuccessful"]
            failed = [ir for ir in instance_refreshes if ir["Status"] in failed_states]
            if failed:
                failed_details = [
                    f"{ir['InstanceRefreshId']}: {ir['Status']} - {ir.get('StatusReason', 'No reason provided')}"
                    for ir in failed
                ]
                error_msg = (
                    f"Instance refresh failed for ASG '{asg_name}'. "
                    f"Failed refreshes: {'; '.join(failed_details)}"
                )
                LOG.error(error_msg)
                LOG.info("=" * 80)
                raise RuntimeError(error_msg)

            # Log cancelled refreshes as informational (not errors)
            cancelled = [ir for ir in instance_refreshes if ir["Status"] == "Cancelled"]
            for ir in cancelled:
                refresh_id = ir["InstanceRefreshId"]
                if refresh_id not in seen_statuses:
                    LOG.info(
                        "Instance refresh %s was cancelled by user - continuing",
                        refresh_id
                    )
                    seen_statuses[refresh_id] = "Cancelled"

            in_progress = [
                ir
                for ir in instance_refreshes
                if ir["Status"]
                in ["Pending", "InProgress", "Cancelling", "RollbackInProgress"]
            ]

            if not in_progress:
                if seen_statuses:
                    LOG.info("All instance refreshes completed")
                else:
                    LOG.info("No in-progress instance refreshes found")
                LOG.info("=" * 80)
                return

            # Log status changes for each in-progress refresh
            for refresh in in_progress:
                refresh_id = refresh["InstanceRefreshId"]
                status = refresh["Status"]
                percentage = refresh.get("PercentageComplete", 0)
                status_msg = f"{status} ({percentage}% complete)"

                if seen_statuses.get(refresh_id) != status_msg:
                    LOG.info("Instance refresh %s: %s", refresh_id, status_msg)
                    seen_statuses[refresh_id] = status_msg

            time.sleep(poll_interval)

        except autoscaling_client.exceptions.ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code == "ValidationError":
                error_msg = f"ASG '{asg_name}' not found"
                LOG.error(error_msg)
                LOG.info("=" * 80)
                raise RuntimeError(error_msg) from e
            LOG.warning("AWS API error: %s - retrying...", e)
            time.sleep(poll_interval)

        except Exception as e:
            LOG.error(
                "Unexpected error waiting for instance refresh: %s", e, exc_info=True
            )
            raise

    # Timeout occurred - gather details about pending refreshes
    response = autoscaling_client.describe_instance_refreshes(
        AutoScalingGroupName=asg_name, MaxRecords=10
    )
    instance_refreshes = response.get("InstanceRefreshes", [])
    in_progress = [
        ir
        for ir in instance_refreshes
        if ir["Status"] in ["Pending", "InProgress", "Cancelling", "RollbackInProgress"]
    ]
    pending_details = [
        f"{ir['InstanceRefreshId']}: {ir['Status']} ({ir.get('PercentageComplete', 0)}% complete)"
        for ir in in_progress
    ]

    elapsed = time.time() - start_time
    error_msg = (
        f"Timeout after {elapsed:.1f} seconds waiting for instance refresh on ASG '{asg_name}'. "
        f"Pending refreshes: {'; '.join(pending_details) if pending_details else 'None'}"
    )
    LOG.error(error_msg)
    LOG.info("=" * 80)
    raise TimeoutError(error_msg)
