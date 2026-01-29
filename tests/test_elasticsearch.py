import pytest


# pytest -xvvs --keep-after --test-role-arn=arn:aws:iam::303467602807:role/pytest-tester --aws-region=us-west-2 tests/test_elasticsearch.py
def test_elasticsearch_fixture_structure(elasticsearch):
    """
    Test that the elasticsearch fixture returns expected terraform outputs.
    """
    # Check that we have a valid terraform output structure
    assert "elasticsearch_url" in elasticsearch
