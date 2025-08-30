from os import path as osp

from pytest_infrahouse import terraform_apply


def test_instance_profile(test_role_arn, aws_region, keep_after, request):
    module_path = "src/pytest_infrahouse/data/instance-profile"
    with open(osp.join(module_path, "terraform.tfvars"), "w") as fp:
        fp.write(f'region = "{aws_region}"\n')
        fp.write(f'calling_test = "{request.node.name}"\n')
        if test_role_arn:
            fp.write(f'role_arn = "{test_role_arn}"\n')

    with terraform_apply(module_path, destroy_after=not keep_after) as tf_output:
        assert tf_output["instance_profile_name"]["value"] == "website-pod-profile"
        assert tf_output["instance_role_name"]["value"].startswith(
            "website-pod-profile"
        )
