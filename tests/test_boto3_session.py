import boto3
import pytest
from botocore.credentials import RefreshableCredentials


def test_boto3_session_no_role_arn_smoke(aws_region):
    """
    With no --test-role-arn, fixture (or a direct minimal session) should work
    and be able to call STS.
    """
    # Use a plain session to avoid depending on user fixture wiring.
    session = boto3.Session(region_name=aws_region)
    who = session.client("sts").get_caller_identity()
    assert "Account" in who and "Arn" in who


def test_boto3_session_clients_work(boto3_session, aws_region):
    """
    Sanity: clients from the session can call AWS APIs (read-only).
    """
    session = boto3_session
    sts = session.client("sts", region_name=aws_region)
    out = sts.get_caller_identity()
    assert "UserId" in out and "Account" in out


def test_boto3_session_refreshable_credentials_live(
    boto3_session, test_role_arn, aws_region
):
    """
    Asserts that the session returned by the fixture uses RefreshableCredentials
    when a role is provided, and that a refresh call actually obtains new metadata.
    (Non-destructive: STS only.)
    """
    if not test_role_arn:
        pytest.skip("--test-role-arn not provided")

    session = boto3_session
    # Grab botocore credentials object
    creds = session._session.get_credentials()
    # If your fixture set up refreshable creds, this should be RefreshableCredentials
    assert isinstance(creds, RefreshableCredentials)

    # Force a refresh (calls STS AssumeRole) and validate structure
    new_meta = creds._refresh_using()  # internal, but safe/non-destructive
    assert {"access_key", "secret_key", "token", "expiry_time"} <= set(new_meta.keys())
    assert new_meta["expiry_time"].endswith("Z") or new_meta["expiry_time"].endswith(
        "+00:00"
    )
