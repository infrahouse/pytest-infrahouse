from os import path as osp

from pytest_infrahouse import terraform_apply


def test_service_network(keep_after):
    module_path = "src/pytest_infrahouse/data/service-network"
    with open(osp.join(module_path, "terraform.tfvars"), "w") as fp:
        fp.write('region = "us-west-1"')

    with terraform_apply(module_path, destroy_after=not keep_after) as tf_output:
        assert len(tf_output["subnet_public_ids"]["value"]) == 3
        assert len(tf_output["subnet_private_ids"]["value"]) == 3
