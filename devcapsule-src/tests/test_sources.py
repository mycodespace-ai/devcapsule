"""The wrapped sources a manifest declares: the ``[sources]`` table, its validation, its round trip (work order of 2026-11-02)."""

from __future__ import annotations

import tomllib

import pytest

from devcapsule.configuration.file_formats import ProjectConfigurationError
from devcapsule.configuration.manifest_document import render_manifest
from devcapsule.configuration.manifest_schemas import ManifestV2, read_manifest
from devcapsule.configuration.sources import WrappedSource, WrappedSources, java_line, source_path

pytestmark = pytest.mark.legacy

PROJECT = {"name": "FRC learning", "slug": "frc-learning", "creator": "mailto:owner@example.test", "mount": "/workspace/frc-learning"}


def manifest(**sources: object) -> dict:
    return {"devcapsule-schema-version": 2, "project": dict(PROJECT), "capabilities": {"required": ["java"]}, "sources": sources}


def test_sources_are_read_sorted_with_their_keys_and_intent() -> None:
    sources = WrappedSources.read(manifest(Second={"upstream": "https://example.test/up", "java": "21"}, RobotCode2025Public={"java": "17"}))
    assert sources.paths == ("RobotCode2025Public", "Second")
    first, second = sources.entries
    assert first == WrappedSource("RobotCode2025Public", None, "17")
    assert first.intent.startswith("learn from it")
    assert second == WrappedSource("Second", "https://example.test/up", "21")
    assert second.intent.startswith("change it in your fork")
    assert sources.java_lines() == ("17", "21")
    assert sources.get("Second") is second and sources.get("Other") is None


def test_an_entry_without_a_java_line_names_no_toolchain() -> None:
    sources = WrappedSources.read(manifest(docs={}))
    assert sources.entries == (WrappedSource("docs"),)
    assert sources.java_lines() == ()
    assert sources.document() == {"docs": {}}


@pytest.mark.parametrize("path", ["", "/abs", "../out", "a/../b", ".", "a//b", "a/", "back\\slash", "a\nb", "tab\tbed", "nul\x00"])
def test_source_paths_stay_inside_the_wrapper_in_posix_form(path: str) -> None:
    with pytest.raises(ProjectConfigurationError, match="source path"):
        source_path(path, field_name="source path")


def test_nested_paths_are_allowed() -> None:
    assert source_path("vendor/robot", field_name="p") == "vendor/robot"


@pytest.mark.parametrize("value", ["", "0", "17.0", 17, "jdk-17", "017"])
def test_a_java_line_is_a_feature_release_number_as_a_string(value: object) -> None:
    with pytest.raises(ProjectConfigurationError, match="Java line"):
        java_line(value, field_name="sources.x.java")


@pytest.mark.parametrize("entry, message", [
    ("17", "must be a table"),
    ({"upstream": ""}, "upstream"),
    ({"upstream": 3}, "upstream"),
    ({"upstream": "https://x\ny"}, "on one line"),
    ({"java": 17}, "Java line"),
])
def test_malformed_entries_are_refused_by_name(entry: object, message: str) -> None:
    with pytest.raises(ProjectConfigurationError, match=message):
        WrappedSources.read(manifest(robot=entry))


def test_unknown_keys_inside_an_entry_are_tolerated_and_carried_by_the_document() -> None:
    document = manifest(robot={"java": "17", "future": {"keep": True}})
    sources = WrappedSources.read(document)
    assert sources.entries == (WrappedSource("robot", None, "17"),)
    assert sources.document(previous=document["sources"]) == {"robot": {"java": "17", "future": {"keep": True}}}
    assert sources.document() == {"robot": {"java": "17"}}


def test_schema_two_reads_sources_as_its_own_table_and_renders_it_after_capabilities() -> None:
    document = manifest(**{"vendor/robot": {"java": "17"}})
    value = read_manifest(document, "manifest")
    assert isinstance(value, ManifestV2)
    assert value.sources == {"vendor/robot": {"java": "17"}}
    assert value.extensions == {}
    assert value.wrapped_sources.entries == (WrappedSource("vendor/robot", None, "17"),)
    text = render_manifest(value.document())
    assert text.index("[capabilities]") < text.index('[sources."vendor/robot"]')
    assert 'java = "17"' in text
    assert read_manifest(tomllib.loads(text), "rendered") == value


def test_schema_two_refuses_a_bad_source_naming_the_file() -> None:
    with pytest.raises(ProjectConfigurationError, match=r"manifest: sources\.robot\.java"):
        read_manifest(manifest(robot={"java": "seventeen"}), "manifest")


def test_schema_one_refuses_the_schema_two_word() -> None:
    document = {"devcapsule-schema-version": 1, "project": dict(PROJECT), "capabilities": {"need": ["java"]}, "sources": {"robot": {}}}
    with pytest.raises(ProjectConfigurationError, match=r"\[sources\], a schema-2 word"):
        read_manifest(document, "manifest")


def test_an_explicitly_empty_sources_table_survives_the_round_trip() -> None:
    value = read_manifest(manifest(), "manifest")
    assert value.document()["sources"] == {}
    assert "[sources]" in render_manifest(value.document())


@pytest.mark.parametrize("path", ['vendor/robot', 'robot.code', 'two words', 'quote"', 'tick`', 'ünïcode'])
def test_source_keys_and_unknown_fields_round_trip_through_the_manifest(path: str) -> None:
    document = manifest(**{path: {"java": "17", "future": {"key.with.dots": True}}})
    value = ManifestV2.read(document, "manifest")
    assert tomllib.loads(render_manifest(value.document())) == document


@pytest.mark.parametrize("path", [None, 17, "a/./b", "a/..", "./a", "//a", "a\x00b"])
def test_additional_non_normal_source_paths_are_refused(path: object) -> None:
    with pytest.raises(ProjectConfigurationError, match="source path"):
        source_path(path, field_name="source path")
