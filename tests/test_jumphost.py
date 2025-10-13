import json
import socket
from os import path as osp

from pytest_infrahouse import terraform_apply


def test_jumphost(
    jumphost,
):
    hostname = jumphost["jumphost_hostname"]["value"]

    # Assert that the hostname resolves successfully
    try:
        ip_address = socket.gethostbyname(hostname)
        assert ip_address, f"Hostname {hostname} resolved but returned empty IP"
    except socket.gaierror as e:
        raise AssertionError(f"Failed to resolve hostname {hostname}: {e}")
