from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

from devcapsule.launch.command_output import preparation_diagnostics, render_command

pytestmark = pytest.mark.legacy


def test_shell_rendering_preserves_arguments_without_evaluating_them(tmp_path):
    marker = tmp_path / 'must-not-exist'
    values = ['', 'two words', "single'quote", 'line\nbreak', '# comment',
              f'$(touch {marker})', f'`touch {marker}`', '; exit 9', 'trailing\\']
    command = [sys.executable, '-c', 'import json,sys; print(json.dumps(sys.argv[1:]))', *values]
    script = render_command(command, ['ordinary note', 'path\nnot a command'])
    subprocess.run(['sh', '-n'], input=script, text=True, check=True)
    output = subprocess.run(['sh'], input=script, text=True, capture_output=True, check=True)
    assert json.loads(output.stdout) == values
    assert not marker.exists()


def test_preparation_output_including_children_uses_stderr_and_restores_on_failure(capfd):
    with pytest.raises(ValueError):
        with preparation_diagnostics():
            print('python progress')
            subprocess.run([sys.executable, '-c', "print('child progress')"], check=True)
            os.write(1, b'fd progress\n')
            raise ValueError('preparation failed')
    print('subsequent stdout')
    captured = capfd.readouterr()
    assert captured.out == 'subsequent stdout\n'
    assert all(message in captured.err for message in ('python progress', 'child progress', 'fd progress'))
