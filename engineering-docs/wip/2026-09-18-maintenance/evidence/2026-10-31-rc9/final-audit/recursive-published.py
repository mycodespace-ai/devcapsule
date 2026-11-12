import sys, os, json, time, tomllib
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from tests.e2e.fresh_workspace import FreshWorkspace
from tests.e2e.test_recursive_successor_attached_launch import test_attached_successor_launch_from_a_fresh_workspace_leaves_nothing_behind
from devcapsule.runtime_configuration import CONFIGURATION_PATH, CONTEXT_PATH
pex = '/opt/devcapsule/bin/devcapsule.pex'
def cli(self, *args):
    return [pex, 'project', '--path', str(self.checkout), *args]
def configure(self):
    context=json.loads(CONTEXT_PATH.read_text())
    with (CONFIGURATION_PATH/context['checkout-file']).open('rb') as f: record=tomllib.load(f)
    answers={}
    args=['init','--regenerate','--ide','pycharm']
    for name, answer in record.get('authorization',{}).items():
        value='default' if name=='base-image' else answer['value']
        answers[name]=value
        args.extend(['--authorize',name,str(value).lower() if isinstance(value,bool) else str(value)])
    for name,value in record.get('configuration',{}).get('values',{}).items():
        answers[name]=value
        args.extend(['--set',name,str(value).lower() if isinstance(value,bool) else str(value)])
    self.run(*args)
    self.run('config','check')
    self.record_state('stage-5-resolved',source_revision=self.revision,answers=answers)
    return answers
FreshWorkspace.cli=cli
FreshWorkspace.configure_like_this_capsule=configure
start=time.monotonic()
tmp=Path('/home/devcapsule/.cache/devcapsule-release-prep/0.3.0-rc9/final-recursive')
tmp.mkdir(parents=True,exist_ok=True)
test_attached_successor_launch_from_a_fresh_workspace_leaves_nothing_behind(tmp)
print(json.dumps({'recursive_published_check':'passed','seconds':round(time.monotonic()-start,2)}))
