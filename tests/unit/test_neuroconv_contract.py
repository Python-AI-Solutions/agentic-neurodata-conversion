import importlib.metadata

import pytest


@pytest.mark.unit
def test_neuroconv_version_pinned():
    assert importlib.metadata.version("neuroconv") == "0.8.3"


@pytest.mark.unit
def test_neuroconv_exports_cover_supported_formats_without_importing():
    from agentic_neurodata_conversion.agents.conversion.neuroconv_formats import FORMAT_TO_NEUROCONV_CLASS

    dist = importlib.metadata.distribution("neuroconv")
    pkg_root = dist.locate_file("neuroconv")

    datainterfaces_init = pkg_root / "datainterfaces" / "__init__.py"
    converters_init = pkg_root / "converters" / "__init__.py"

    datainterfaces_text = datainterfaces_init.read_text(encoding="utf-8")
    converters_text = converters_init.read_text(encoding="utf-8")

    missing: list[str] = []
    for cls_name in FORMAT_TO_NEUROCONV_CLASS.values():
        if cls_name not in datainterfaces_text and cls_name not in converters_text:
            missing.append(cls_name)

    assert not missing, f"Missing NeuroConv classes: {missing}"


@pytest.mark.unit
def test_conversion_runner_resolves_converter_classes(monkeypatch):
    import types

    from agentic_neurodata_conversion.agents.conversion.conversion_runner import resolve_neuroconv_class

    fake_datainterfaces = types.ModuleType("neuroconv.datainterfaces")
    fake_converters = types.ModuleType("neuroconv.converters")

    class FakeInterface:  # noqa: D101 - test helper
        pass

    class FakeConverter:  # noqa: D101 - test helper
        pass

    fake_datainterfaces.SomeInterface = FakeInterface
    fake_converters.SpikeGLXConverterPipe = FakeConverter

    def fake_import_module(name: str):
        if name == "neuroconv.datainterfaces":
            return fake_datainterfaces
        if name == "neuroconv.converters":
            return fake_converters
        raise ImportError(name)

    import agentic_neurodata_conversion.agents.conversion.conversion_runner as runner_mod

    monkeypatch.setattr(runner_mod, "_importlib", types.SimpleNamespace(import_module=fake_import_module))

    assert resolve_neuroconv_class("SomeInterface") is FakeInterface
    assert resolve_neuroconv_class("SpikeGLXConverterPipe") is FakeConverter
