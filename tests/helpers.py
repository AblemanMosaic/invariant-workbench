from pathlib import Path
from copy import deepcopy
import json,os,subprocess
ROOT=Path(__file__).resolve().parents[1]

def example(name='assembly'):
    p=ROOT/'examples'/name
    c=json.loads((p/'contract.json').read_text())
    s=(p/'operation.py').read_text()
    f=next(p.glob('*.feature')).read_text()
    return c,s,f

def report():return json.loads((ROOT/'fixtures/zucchini/rules.synthetic.json').read_text())
def report_bytes():return (ROOT/'fixtures/zucchini/rules.synthetic.json').read_bytes()
def junit_bytes():return (ROOT/'fixtures/zucchini/results.synthetic.xml').read_bytes()
def raw(value):return json.dumps(value,sort_keys=True).encode()

def reseal(value,key):
    from miw.common import root
    value[key]=root({k:v for k,v in value.items() if k!=key});return value

def directory_alias(link:Path,target:Path) -> None:
    """Create a real directory alias without requiring Windows symlink privilege."""
    try:
        link.symlink_to(target,target_is_directory=True)
        return
    except OSError:
        if os.name!='nt':raise
    result=subprocess.run(['cmd.exe','/d','/c','mklink','/J',str(link),str(target)],
                          stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10)
    if result.returncode!=0:raise OSError(result.stdout.decode(errors='replace'))
