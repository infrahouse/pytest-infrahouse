import pytest


def test_elasticsearch_fixture_structure(elasticsearch):
    """
    Test that the elasticsearch fixture returns expected terraform outputs.
    """
    # Check that we have a valid terraform output structure
    assert "elasticsearch_url" in elasticsearch
