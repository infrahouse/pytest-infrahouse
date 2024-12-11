from os import path as osp

from pytest_infrahouse import terraform_apply


def test_instance_profile(keep_after):
    module_path = "src/pytest_infrahouse/data/instance-profile"
    with open(osp.join(module_path, "terraform.tfvars"), "w") as fp:
        fp.write('region = "us-west-1"')

    with terraform_apply(module_path, destroy_after=not keep_after) as tf_output:
        assert tf_output["instance_profile_name"]["value"] == "website-pod-profile"
        assert tf_output["instance_role_name"]["value"].startswith("website-pod-profile")
