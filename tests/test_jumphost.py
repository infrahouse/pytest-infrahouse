import json
from os import path as osp

from pytest_infrahouse import terraform_apply


def test_jumphost(service_network, keep_after, aws_region, test_role_arn, test_zone_name):
    subnet_public_ids = service_network["subnet_public_ids"]["value"]
    subnet_private_ids = service_network["subnet_private_ids"]["value"]

    module_path = "src/pytest_infrahouse/data/jumphost"
    with open(osp.join(module_path, "terraform.tfvars"), "w") as fp:
        fp.write(f'region = "{aws_region}"\n')
        fp.write(f'subnet_public_ids  = {json.dumps(subnet_public_ids)}\n')
        fp.write(f'subnet_private_ids = {json.dumps(subnet_private_ids)}\n')
        fp.write(f'test_zone = "{test_zone_name}"\n')
        if test_role_arn:
            fp.write(f'role_arn = "{test_role_arn}"')


    with terraform_apply(module_path, destroy_after=not keep_after) as tf_output:
            assert True
