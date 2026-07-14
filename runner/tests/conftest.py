"""Pytest fixtures for the CEOps runner."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from ceops_runner.app import create_app

from helpers import BASE_URL, make_config


@pytest.fixture
def config():
    return make_config()


@pytest.fixture
def client(config):
    return TestClient(create_app(config), base_url=BASE_URL)
