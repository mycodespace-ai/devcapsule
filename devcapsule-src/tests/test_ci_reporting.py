"""Independent failure-path and real-tool checks for hosted CI reporting."""
from __future__ import annotations

import fnmatch
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.legacy

ROOT = Path(__file__).parents[2]


def script(name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, ROOT / 'devcapsule-src/scripts' / f'{name}.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GATE = script('ci_gate')
REPORT = script('diff_coverage_annotations')


def needs(python: str = 'true', docs: str = 'true') -> dict[str, Any]:
    return {'changes': {'result': 'success', 'outputs': {'python': python, 'docs': docs}},
            'pytest': {'result': 'success'}, 'docs-build': {'result': 'success'}}


def test_gate_accepts_success_and_only_legitimate_skips() -> None:
    GATE.check(needs())
    value = needs('false', 'false')
    value['pytest']['result'] = value['docs-build']['result'] = 'skipped'
    GATE.check(value)


@pytest.mark.parametrize('job', ['changes', 'pytest', 'docs-build'])
@pytest.mark.parametrize('result', ['failure', 'cancelled', 'skipped', None])
def test_gate_rejects_missing_or_unsuccessful_required_job(job: str, result: str | None) -> None:
    value = needs()
    value[job]['result'] = result
    with pytest.raises(ValueError):
        GATE.check(value)


@pytest.mark.parametrize('route', ['python', 'docs'])
@pytest.mark.parametrize('value', ['', None, True, 'TRUE', 'unknown'])
def test_gate_rejects_invalid_routing(route: str, value: Any) -> None:
    jobs = needs()
    jobs['changes']['outputs'][route] = value
    with pytest.raises(ValueError):
        GATE.check(jobs)


def test_routing_failure_with_skipped_children_cannot_pass() -> None:
    jobs = needs('false', 'false')
    jobs['changes']['result'] = 'failure'
    jobs['pytest']['result'] = jobs['docs-build']['result'] = 'skipped'
    with pytest.raises(ValueError):
        GATE.check(jobs)


def picomatch_like(path: str, glob: str) -> bool:
    """Mirror picomatch with dot: true for the grammar .github/ci-paths.yml uses.

    Literal segments, `*` within one segment, and `**` for any number of
    segments including none, so `a/**` matches `a` itself. Checked against
    picomatch 2.3.1, the version paths-filter v3.0.4 bundles.
    """
    def match(parts: list[str], segments: list[str]) -> bool:
        if not segments:
            return not parts
        if segments[0] == '**':
            return any(match(parts[i:], segments[1:]) for i in range(len(parts) + 1))
        return bool(parts) and fnmatch.fnmatchcase(parts[0], segments[0]) and match(parts[1:], segments[1:])
    return match(path.split('/'), glob.split('/'))


@pytest.mark.parametrize(('path', 'python', 'docs'), [
    ('engineering-docs/wip/a/CURRENT-STATUS.md', False, False),
    ('engineering-docs/work-orders/new.md', False, False),
    ('CURRENT-STATUS.md', False, False),
    ('README.md', False, True),
    ('docs/guide.md', False, True),
    ('docs/README.md', False, True),
    ('docs/getting-started/first-session.md', False, True),
    ('docs/versions.yaml', True, True),  # read by tests/test_release_docs.py
    ('engineering-docs/blog/new.md', False, True),
    ('engineering-docs/blog/assets/demo/poster.png', False, True),
    ('engineering-docs/README.md', False, True),
    ('engineering-docs/releases/v0.2.14/notes.md', True, True),  # read by tests/test_release_docs.py
    ('engineering-docs/design-notes/devcapsule/competitive-comparison.md', False, True),
    ('engineering-docs/new-subtree/note.md', True, True),
    ('website', False, True),
    ('website/README.md', False, True),
    ('scripts/website.sh', False, True),
    ('devcapsule-src/devcapsule/assets/project_workflow/definition/WORKFLOW.md', True, False),
    ('devcapsule-src/tests/a.py', True, False),
    ('devcapsule-src/pyproject.toml', True, True),
    ('devcapsule-src/dev-requirements.txt', True, False),
    ('devcapsule-webconsole/devcapsule_webconsole/app.py', True, False),
    ('.gitmodules', True, True),
    ('.github/workflows/tests.yml', True, True),
    ('.github/ci-paths.yml', True, True),
    ('.ast-grep/new.yml', True, True),
    ('WORKFLOW.md', True, True),  # read by tests/test_workflow_bootstrap.py
    ('unknown/new-input', True, True),
])
def test_known_exemptions_and_conservative_unknown_paths(path: str, python: bool, docs: bool) -> None:
    filters = yaml.safe_load((ROOT / '.github/ci-paths.yml').read_text())
    for route, expected in [('python', python), ('docs', docs)]:
        patterns = filters[route]
        # Every pattern is a negation within picomatch_like's grammar.
        assert all(p.startswith('!') and not any(c in p[1:] for c in '?[]{}()!') for p in patterns)
        assert all(not picomatch_like(path, p[1:]) for p in patterns) is expected
    workflow = yaml.safe_load((ROOT / '.github/workflows/tests.yml').read_text())
    filters_step = next(s for s in workflow['jobs']['changes']['steps'] if s.get('id') == 'filter')
    assert filters_step['with']['predicate-quantifier'] == 'every'


def route_step(tmp_path: Path, **env: str) -> tuple[int, dict[str, str]]:
    """Run the workflow's route script as GitHub's bash would, returning its outputs."""
    workflow = yaml.safe_load((ROOT / '.github/workflows/tests.yml').read_text())
    step = next(s for s in workflow['jobs']['changes']['steps'] if s.get('id') == 'route')
    output = tmp_path / 'github-output'
    output.touch()
    result = subprocess.run(['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', step['run']],
                            env={'PATH': os.environ['PATH'], 'GITHUB_OUTPUT': str(output), **env},
                            capture_output=True, text=True)
    lines = output.read_text().splitlines()
    return result.returncode, dict(line.split('=', 1) for line in lines)


def test_route_step_passes_valid_filters_and_runs_everything_otherwise(tmp_path: Path) -> None:
    pr = {'EVENT_NAME': 'pull_request', 'PYTHON_CHANGED': 'false'}
    assert route_step(tmp_path, **pr, CHANGED_FILES='17', DOCS_CHANGED='true') == (
        0, {'python': 'false', 'docs': 'true'})
    assert route_step(tmp_path, **pr, CHANGED_FILES='3000', DOCS_CHANGED='false') == (
        0, {'python': 'false', 'docs': 'false'})
    # The filter never sees files beyond GitHub's 3000-file listing.
    assert route_step(tmp_path, **pr, CHANGED_FILES='3001', DOCS_CHANGED='false') == (
        0, {'python': 'true', 'docs': 'true'})
    for event in ['push', 'merge_group', 'workflow_dispatch']:
        assert route_step(tmp_path, EVENT_NAME=event, PYTHON_CHANGED='', DOCS_CHANGED='') == (
            0, {'python': 'true', 'docs': 'true'})


@pytest.mark.parametrize('env', [
    {'PYTHON_CHANGED': '', 'DOCS_CHANGED': 'true'},
    {'PYTHON_CHANGED': 'true', 'DOCS_CHANGED': 'TRUE'},
    {'PYTHON_CHANGED': 'true'},
    {'PYTHON_CHANGED': 'true', 'DOCS_CHANGED': 'true', 'CHANGED_FILES': ''},
    {'PYTHON_CHANGED': 'true', 'DOCS_CHANGED': 'true', 'CHANGED_FILES': 'many'},
])
def test_route_step_fails_without_valid_inputs(tmp_path: Path, env: dict[str, str]) -> None:
    code, outputs = route_step(tmp_path, **{'EVENT_NAME': 'pull_request', 'CHANGED_FILES': '17', **env})
    assert code == 1
    assert outputs == {}


def report(lines: list[int], covered: list[int] | None = None) -> dict[str, Any]:
    covered = covered or []
    return {'src_stats': {'devcapsule-src/devcapsule/a.py':
                         {'violation_lines': lines, 'covered_lines': covered}},
            'total_num_lines': len(lines) + len(covered), 'total_num_violations': len(lines)}


def test_uncovered_ranges_are_advisory_and_grouped() -> None:
    warnings, measured = REPORT.build_annotations(report([5, 2, 3]))
    assert measured == 3
    assert len(warnings) == 2
    assert 'line=2,endLine=3' in warnings[0]
    assert 'line=5,endLine=5' in warnings[1]
    assert all(w.startswith('::warning ') for w in warnings)


@pytest.mark.parametrize('bad', [{}, {'src_stats': {}}, report([0]), report([True]), report([2, 2])])
def test_invalid_report_is_not_misreported_as_covered(bad: Any) -> None:
    with pytest.raises(ValueError):
        REPORT.build_annotations(bad)


def test_totals_overlap_and_unsafe_paths_are_rejected() -> None:
    data = report([2], [2])
    with pytest.raises(ValueError, match='overlap'):
        REPORT.build_annotations(data)
    data = report([2]); data['total_num_lines'] = 10
    with pytest.raises(ValueError, match='totals'):
        REPORT.build_annotations(data)
    for name in ['../a.py', '/tmp/a.py', 'devcapsule/a.py', 'devcapsule-src/devcapsule/../a.py']:
        data = report([2]); data['src_stats'][name] = data['src_stats'].pop('devcapsule-src/devcapsule/a.py')
        with pytest.raises(ValueError, match='path'):
            REPORT.build_annotations(data)


def test_workflow_command_properties_are_escaped() -> None:
    assert REPORT.escape('a%,:\r\n.py', property_value=True) == 'a%25%2C%3A%0D%0A.py'


def test_warning_budget_and_full_report_preserved(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    data = report(list(range(1, 28, 2)))
    source, md, summary = (tmp_path / n for n in ['report.json', 'report.md', 'summary.md'])
    source.write_text(json.dumps(data)); md.write_text('Complete table\n')
    REPORT.publish(source, md, summary)
    assert capsys.readouterr().out.count('::warning ') == 10
    assert '10 of 14' in summary.read_text()
    assert 'Complete table' in summary.read_text()
    assert json.loads(source.read_text()) == data


def test_not_applicable_is_explicit(tmp_path: Path) -> None:
    source, md, summary = (tmp_path / n for n in ['report.json', 'report.md', 'summary.md'])
    source.write_text(json.dumps(report([]))); md.write_text('No lines\n')
    REPORT.publish(source, md, summary)
    assert 'Not applicable' in summary.read_text()


def test_missing_report_fails_cli(tmp_path: Path) -> None:
    result = subprocess.run([sys.executable, str(ROOT / 'devcapsule-src/scripts/diff_coverage_annotations.py')],
                            cwd=tmp_path, env={**os.environ, 'GITHUB_STEP_SUMMARY': str(tmp_path/'summary')},
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert 'reporting failed' in result.stderr


def test_real_diff_cover_json_paths_and_advisory_exit(tmp_path: Path) -> None:
    """Use actual coverage + diff-cover on an unexecuted changed line in a nested package path."""
    root = tmp_path / 'repo'; root.mkdir()
    package = root / 'devcapsule-src/devcapsule/nested'; package.mkdir(parents=True)
    env = {**os.environ, 'GIT_AUTHOR_NAME': 'Test', 'GIT_COMMITTER_NAME': 'Test',
           'GIT_AUTHOR_EMAIL': 'test@example.invalid', 'GIT_COMMITTER_EMAIL': 'test@example.invalid'}
    def run(*args: str, cwd: Path = root) -> subprocess.CompletedProcess[str]:
        return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True, check=True)
    run('git', 'init', '-b', 'main')
    (package.parent / '__init__.py').write_text(''); (package / '__init__.py').write_text('')
    source = package / 'sample.py'; source.write_text('x = 0\n')
    run('git', 'add', '.'); run('git', 'commit', '-m', 'base')
    base = run('git', 'rev-parse', 'HEAD').stdout.strip()
    source.write_text('x = 0\nif x:\n    print("not run")\n')
    run('git', 'add', '.'); run('git', 'commit', '-m', 'change')
    working = root / 'devcapsule-src'
    run(sys.executable, '-m', 'coverage', 'run', '--branch', '--source=devcapsule',
        'devcapsule/nested/sample.py', cwd=working)
    run(sys.executable, '-m', 'coverage', 'xml', cwd=working)
    run(sys.executable, '-m', 'diff_cover.diff_cover_tool', 'coverage.xml',
        f'--compare-branch={base}', '--format=json:diff-cover.json,markdown:diff-cover.md', cwd=working)
    data = json.loads((working / 'diff-cover.json').read_text())
    warnings, _ = REPORT.build_annotations(data)
    assert any('file=devcapsule-src/devcapsule/nested/sample.py,line=3,endLine=3' in w for w in warnings)
    assert data['total_percent_covered'] < 85
