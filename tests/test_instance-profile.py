from os import path as osp

from pytest_infrahouse import terraform_apply


def test_instance_profile(instance_profile):
    assert instance_profile["instance_profile_name"]["value"].startswith(
        "website-pod-profile"
    )
    assert instance_profile["instance_role_name"]["value"].startswith(
        "website-pod-profile"
    )
