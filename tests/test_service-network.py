from os import path as osp

from pytest_infrahouse import terraform_apply


def test_service_network(service_network):
    assert len(service_network["subnet_public_ids"]["value"]) == 2
    assert len(service_network["subnet_private_ids"]["value"]) == 2
