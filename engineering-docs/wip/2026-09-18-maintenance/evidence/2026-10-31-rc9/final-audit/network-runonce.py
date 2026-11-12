import sys,os,json,uuid,shutil
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from tests.e2e.ide_session import SURFACES,workspace_root,initialize_project,launched_ide,wait_for_ide_window,remove_project_records,command
pex=Path('/opt/devcapsule/bin/devcapsule.pex')
surface=next(x for x in SURFACES if x.name=='codium')
slug='e2e-final-network-'+uuid.uuid4().hex[:8]
workspace=workspace_root(Path('/var/tmp/maintenance-final'))/slug
workspace.mkdir()
evidence=Path('/var/tmp/maintenance-final/network-runonce')
evidence.mkdir(exist_ok=True)
try:
    initialize_project(pex,surface,workspace,evidence,slug)
    command(str(pex),'project','--path',str(workspace),'config','recommend','network','none')
    assert '[host.network' not in (workspace/'.devcapsule/devcapsule.toml').read_text()
    command(str(pex),'project','--path',str(workspace),'config','deny','network')
    with launched_ide(pex,surface,workspace,evidence,slug,run_arguments=('--authorize','network','host')) as s:
        wait_for_ide_window(s)
        network=command('docker','inspect','--format','{{.HostConfig.NetworkMode}}',s.container).stdout.strip()
        assert network=='host'
        print(json.dumps({'network_runonce':'passed','network':network,'project_recommends_network':False,'saved_network':'denied','ide_window':True}))
finally:
    shutil.rmtree(workspace,ignore_errors=True)
    remove_project_records(slug)
