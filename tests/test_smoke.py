import importlib


def test_package_is_importable():
    assert importlib.import_module("smartflow")


def test_tornado_is_installed():
    tornado = importlib.import_module("tornado")
    assert tornado.version_info >= (6, 5)
