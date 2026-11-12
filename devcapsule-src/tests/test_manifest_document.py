"""The manifest as a document: schema versions, the owner's vocabulary, the one writer."""

from __future__ import annotations

import tomllib

import pytest

from devcapsule.configuration.file_formats import ConfigurationFileKind, ProjectConfigurationError, validate_file_format
from devcapsule.configuration.manifest_schemas import read_manifest
from devcapsule.configuration.manifest_document import (
    EnvironmentPolicy,
    Recommendations,
    capability_table,
    manifest_preamble,
    render_manifest,
)
from devcapsule.configuration.capabilities import CapabilityPolicy
from devcapsule.configuration.values import normalize_memory_size
from pathlib import Path

pytestmark = pytest.mark.legacy


def document(**extra) -> dict:
    return {
        "devcapsule-schema-version": 2,
        "project": {"name": "AI Learning", "slug": "ai-learning", "creator": "https://github.com/ccozianu",
                    "mount": "/workspace/ai-learning"},
        "capabilities": {"required": ["node", "postgresql-client"]},
        **extra,
    }


def test_writer_uses_bare_keys_owner_order_and_omits_what_says_nothing() -> None:
    text = render_manifest(document(
        workflow={"definition": "devcapsule", "version": "0.3.0", "mode": "single-stream"},
        recommendations={"ide": "frontend-ide", "memory": "6GiB", "reasons": {"memory": "the index"}},
        environment={"required": {"POSTGRES_HOST": {"reason": "the owner supplies the database"}},
                     "optional": {"SMTP_HOST": {}}},
        configuration={"values": {"db.url": {"type": "string", "description": "where"}}},
        host={"network": {"mode": {"recommended": {"value": "host", "justification": "ports"}}}},
    ))
    lines = text.splitlines()
    assert lines[0] == "devcapsule-schema-version = 2"
    headers = [line for line in lines if line.startswith("[")]
    assert headers == [
        "[project]", "[capabilities]", "[environment.required.POSTGRES_HOST]", "[environment.optional.SMTP_HOST]",
        "[recommendations]", "[recommendations.reasons]", "[host.network.mode.recommended]",
        '[configuration.values."db.url"]', "[workflow]",
    ]
    assert '"required"' not in text and "optional = []" not in text and "sdk-major" not in text
    parsed = tomllib.loads(text)
    assert parsed["environment"]["optional"]["SMTP_HOST"] == {}
    assert parsed["configuration"]["values"]["db.url"]["type"] == "string"
    read_manifest(parsed, Path("manifest"))


def test_writer_keeps_the_leading_comment_block_and_nothing_else() -> None:
    text = "# AI Learning\n# the owner's note\n\ndevcapsule-schema-version = 1\n[project]\nname = \"x\" # inline\n"
    assert manifest_preamble(text) == "# AI Learning\n# the owner's note\n"
    assert manifest_preamble("devcapsule-schema-version = 1\n") == ""
    rendered = render_manifest(document(), preamble=manifest_preamble(text))
    assert rendered.startswith("# AI Learning\n# the owner's note\n\ndevcapsule-schema-version = 2\n")
    assert "# inline" not in rendered


def test_writer_round_trips_through_the_reader() -> None:
    source = document(environment={"required": {"A_1": {"reason": "why"}}}, recommendations={"cpus": 4})
    assert tomllib.loads(render_manifest(source)) == source


@pytest.mark.parametrize("key", ["db.url", "with spaces", 'a"b', "line\nfeed", "café", "delete\x7f", ""])
def test_writer_quotes_keys_and_values_without_changing_them(key: str) -> None:
    source = document(configuration={"values": {key: {"type": "string", "description": 'a "quote"\nnext\t\\end\x7f'}}},
                      environment={"optional": {"EMPTY": {}}})
    assert tomllib.loads(render_manifest(source)) == source


def test_writer_preserves_tolerated_root_fields_and_extension_types() -> None:
    source = document(workflow={"mode": "multiple-streams"})
    source.update(tomllib.loads('''generator = "a newer launcher"
[extension]
ratio = 1.5
date = 2026-10-24
time = 12:30:00
timestamp = 2026-10-24T12:30:00Z
entries = [{ "a.b" = {}, value = "x" }]
'''))
    read_manifest(source, Path("manifest"))
    rendered = render_manifest(source)
    assert tomllib.loads(rendered) == source
    assert rendered.index("[extension]") < rendered.index("# The project's workflow choice.") < rendered.index("[workflow]")


def test_preamble_keeps_comment_whitespace_and_unicode_line_separators() -> None:
    comment = "# note  \n# first\u2028second\n"
    assert manifest_preamble(comment + '\n[project]\n# not leading\n') == comment


def test_capability_table_says_only_what_is_so() -> None:
    policy = CapabilityPolicy(("node", "python"), (), (("python", "3"),))
    assert capability_table(policy, {"node": "", "python": "the backend", "gone": "dropped"}) == {
        "required": ["node", "python>=3"], "reasons": {"python": "the backend"},
    }
    assert capability_table(CapabilityPolicy(("node",))) == {"required": ["node"]}


@pytest.mark.parametrize("version, accepted", [(1, True), (2, True), (3, False), ("2", False), (True, False)])
def test_manifest_schema_versions_one_and_two_are_read(version, accepted) -> None:
    manifest = {**document(), "devcapsule-schema-version": version}
    if accepted:
        validate_file_format(manifest, ConfigurationFileKind.manifest, "m")
    else:
        with pytest.raises(ProjectConfigurationError, match="requires devcapsule-schema-version = 1 or 2"):
            validate_file_format(manifest, ConfigurationFileKind.manifest, "m")


def test_other_file_kinds_stay_at_version_one() -> None:
    with pytest.raises(ProjectConfigurationError, match="= 1\\."):
        validate_file_format({"devcapsule-lock-format-version": 2}, ConfigurationFileKind.lock, "l")


def test_environment_policy_reads_reasons_and_refuses_overlap_and_bad_names() -> None:
    policy = EnvironmentPolicy.read(document(environment={
        "required": {"POSTGRES_HOST": {"reason": "db"}, "AUTH_SECRET": {}}, "optional": {"SMTP_HOST": {"reason": "mail"}},
    }))
    assert policy.required == {"AUTH_SECRET": "", "POSTGRES_HOST": "db"}
    assert policy.optional == {"SMTP_HOST": "mail"}
    assert policy.names() == ("AUTH_SECRET", "POSTGRES_HOST", "SMTP_HOST")
    assert policy.document() == {"required": {"AUTH_SECRET": {}, "POSTGRES_HOST": {"reason": "db"}},
                                 "optional": {"SMTP_HOST": {"reason": "mail"}}}
    with pytest.raises(ProjectConfigurationError, match="both required and optional"):
        EnvironmentPolicy.read(document(environment={"required": {"A": {}}, "optional": {"A": {}}}))
    with pytest.raises(ProjectConfigurationError, match="ASCII identifiers"):
        EnvironmentPolicy.read(document(environment={"required": {"9A": {}}}))
    with pytest.raises(ProjectConfigurationError, match="must be a table"):
        EnvironmentPolicy.read(document(environment={"required": {"A": "reason"}}))
    with pytest.raises(ProjectConfigurationError, match="only 'required' and 'optional'"):
        EnvironmentPolicy.read(document(environment={"needed": {}}))


def test_recommendations_read_canonicalize_and_refuse_unknowns() -> None:
    read = Recommendations.read(document(recommendations={"ide": "frontend-ide", "memory": "6g", "cpus": 2,
                                                          "reasons": {"memory": "big"}}))
    assert (read.ide, read.memory, read.cpus, read.reasons) == ("frontend-ide", "6GiB", 2, {"memory": "big"})
    assert read.document() == {"ide": "frontend-ide", "memory": "6GiB", "cpus": 2, "reasons": {"memory": "big"}}
    assert Recommendations.read(document()).document() == {}
    with pytest.raises(ProjectConfigurationError, match="known recommendations"):
        Recommendations.read(document(recommendations={"network": "host"}))
    with pytest.raises(ProjectConfigurationError, match="positive integer"):
        Recommendations.read(document(recommendations={"cpus": 0}))
    with pytest.raises(ProjectConfigurationError, match="no such recommendation"):
        Recommendations.read(document(recommendations={"reasons": {"swap": "x"}}))
    with pytest.raises(ProjectConfigurationError, match="memory size"):
        Recommendations.read(document(recommendations={"memory": "lots"}))


@pytest.mark.parametrize("typed, canonical", [
    ("6GiB", "6GiB"), ("6g", "6GiB"), ("6G", "6GiB"), ("6GB", "6GiB"), ("512m", "512MiB"), ("1024", "1024B"),
    ("2t", "2TiB"), ("3 k", "3KiB"), ("8gib", "8GiB"),
])
def test_memory_sizes_accept_docker_spellings_and_store_canonical(typed, canonical) -> None:
    assert normalize_memory_size(typed) == canonical


@pytest.mark.parametrize("bad", ["0g", "6.5g", "g", "6 gigs", "", "-1g"])
def test_memory_size_refusals_name_the_field(bad) -> None:
    with pytest.raises(ProjectConfigurationError, match="memory"):
        normalize_memory_size(bad, field_name="memory")


def test_manifest_validation_reports_environment_and_recommendation_problems_with_the_path() -> None:
    with pytest.raises(ProjectConfigurationError, match="manifest: recommendations.cpus"):
        read_manifest(document(recommendations={"cpus": -1}), Path("manifest"))
