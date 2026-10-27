"""Actual Mosaic Foundry HEADLESS/WIN32 viewer. Read-only application boundary."""
from __future__ import annotations
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from .common import Refusal,require,read_json,read_bytes,digest,seal,BOUNDARY
ROOT=Path(__file__).resolve().parents[2]
VIEWS=('overview','workbench','control','rules','proof','orders','proposals','integration')
SUN_SHA='579066ae7b048e5a56bbc99033f2d4316a8c7cdc85e161db9680525ea72639e3'

def enable_runtime():
    vendor=str(ROOT/'vendor/mosaic')
    if vendor not in sys.path:sys.path.insert(0,vendor)

def payload():
    enable_runtime()
    # Trusted generated package module; never a path from an imported report.
    spec=importlib.util.spec_from_file_location('miw_foundry_generated',ROOT/'foundry/generated/library.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return deepcopy(module.PAYLOAD)

def layout(width:int,height:int)->dict:
    width=max(1000,int(width));height=max(720,int(height))
    rows=read_json(ROOT/'foundry/source/layout.json');result={}
    for k,(x,y,w,h) in rows.items():
        # Only the authored full-width content panels stretch with the host
        # window. Workbench fields and buttons keep their bounded grid widths.
        if x==250 and w>=900:w=width-280
        # Detail panes sit at different vertical offsets. Size each one from
        # its actual origin and reserve the footer/status band, rather than
        # applying the original viewer's fixed offset to every view.
        if k.endswith('_detail'):h=height-y-90
        if k=='status':y=height-54
        if k=='build':y=height-96
        result[k]=(x,y,max(30,w),max(25,h))
    return result

def evidence_model(dossier:Path|None=None)->dict:
    """Validate the proof dossier; other local reports are visibly observations."""
    values={};tables={};details={}
    for v in VIEWS:tables[v]=[];details[v]='No report loaded.'
    tables['overview']=[['Native proof','Supported scalar operations','Trusted frontend, not a compiler theorem'],
      ['UCM manager','Fixture-signed integration','No production identity'],['PostgreSQL','Reference adapter supplied','Live server acceptance remains separate'],
      ['Zucchini','Pinned Linux lane accepted','19 successful + 16 diagnostic reports; native VS open'],['Mosaic UI','Foundry and runtime bound','Native Windows GUI acceptance open']]
    details['overview']='Turn 4 experimental candidate. Read-only viewer. A passed work plan is not requirement discharge. No deployment, network call, AI call, or database connection occurs here.'
    tables['workbench']=[['No dossier','OPEN','OPEN','UNBOUND']]
    details['workbench']='Interactive workbench operations require an exact verified dossier. External effects remain withheld.'
    from .constitutional import capability_surface
    control=capability_surface(read_json(ROOT/'constitutional/OPERATION-REGISTRY.json'))
    tables['control']=[[row['capability_id'],row['family'],str(len(row['operations']))]
                       for row in control['capabilities']]
    details['control']=json.dumps({'surface_root':control['surface_root'],
        'observability_levels':control['observability_levels'],
        'mutation_authority':control['mutation_authority'],
        'claim_ceiling':control['claim_ceiling']},indent=2)
    if dossier is not None:
        from .dossier import verify_dossier
        replay=verify_dossier(dossier)
        summary=read_json(dossier/'SUMMARY.json')
        details['proof']=json.dumps({'replay':replay,'summary':summary},indent=2)
        tables['proof']=[[str(x.get('id',x.get('name','example'))),str(x.get('proof_outcome','checked')),str(x.get('native_vc_count',''))+' native conditions'] for x in summary.get('examples',[])]
        details['rules']=(dossier/'assembly.source.py').read_text()+'\n\n'+json.dumps(read_json(dossier/'assembly.contract.json'),indent=2)
        tables['rules']=[['assembly','Exact contract + source','Restricted integer operations only']]
        from .workbench import build_workspace
        workspace=build_workspace(dossier)
        tables['workbench']=[[row['id'],row['proof_projection'],row['scenario_projection'],row['zucchini_projection']]
                             for row in workspace['obligations']]
        details['workbench']=json.dumps({'workspace_root':workspace['workspace_root'],
            'unbound_zucchini_requirements':workspace['unbound_zucchini_requirements'],
            'open_assumptions':workspace['open_assumptions'],
            'claim':workspace['claim']},indent=2)
    for v,rel in [('orders','lifecycle/SUMMARY.json'),('proposals','proposals/SUMMARY.json'),('integration','SUMMARY.json')]:
        p=ROOT/'evidence/integration'/rel
        if p.is_file():
            r=read_json(p);details[v]=json.dumps(r,indent=2)
            tables[v]=[[str(k),str(val)[:200],'Packaged builder observation'] for k,val in r.items() if not isinstance(val,(dict,list))]
    for v in VIEWS:
        values[v+'_table']=tables[v];values[v+'_detail']=details[v]
    return values


class WorkbenchController:
    """Bind native semantic intents to bounded in-memory/local MIW operations."""
    def __init__(self,runtime,dossier:Path|None):
        self.runtime=runtime;self.dossier=Path(dossier) if dossier is not None else None
        self.workspace=None;self.lowering=None
        if self.dossier is not None:
            from .workbench import build_workspace
            self.workspace=build_workspace(self.dossier)

    def _show(self,value:dict,status:str)->None:
        self.runtime.state['values']['workbench_detail']=json.dumps(value,indent=2,sort_keys=True)
        self.runtime.state['status']=status

    def _control_show(self,value:dict,status:str)->None:
        self.runtime.state['values']['control_detail']=json.dumps(value,indent=2,sort_keys=True)
        self.runtime.state['status']=status

    def dispatch(self,event:dict)->None:
        try:
            self.runtime.apply(event)
            if str(event.get('intent','')).upper()!='ACTIVATE':return
            node=self.runtime.nodes.get(str(event.get('node_id','')),{})
            operation=node.get('operation_ref','')
            if operation.startswith('control_'):
                from .constitutional import capability_surface,cgp_posture,compile_operation,diagnose
                registry=read_json(ROOT/'constitutional/OPERATION-REGISTRY.json')
                if operation=='control_refresh':
                    surface=capability_surface(registry)
                    self.runtime.state['values']['control_table']=[
                        [row['capability_id'],row['family'],str(len(row['operations']))]
                        for row in surface['capabilities']]
                    self._control_show(surface,'CAPABILITY SURFACE VALIDATED')
                elif operation=='control_compile':
                    subject={'workspace_root':self.workspace['workspace_root']} if self.workspace else {'dossier':'NOT_LOADED'}
                    self._control_show(compile_operation(registry,'workbench-open',subject=subject,inputs={},
                                                         requester='MOSAIC_CONTROL_SURFACE'),
                                       'OPERATION COMPILED | NO AUTHORITY')
                elif operation=='control_diagnose':
                    require(self.dossier is not None,'WORKBENCH_DOSSIER_REQUIRED')
                    from .workbench import build_workspace
                    self.workspace=self.workspace or build_workspace(self.dossier)
                    posture=cgp_posture(registry,self.workspace)
                    self._control_show({'posture':posture,'diagnostic':diagnose(posture)},
                                       'DIAGNOSTIC COMPLETE | NO REPAIR EFFECT')
                elif operation=='control_headless':
                    require(self.dossier is not None,'WORKBENCH_DOSSIER_REQUIRED')
                    from .headless_runner import application_court
                    self._control_show(application_court(self.dossier),'HEADLESS APPLICATION COURT PASSED')
                return
            if not operation.startswith('workbench_'):return
            require(self.dossier is not None,'WORKBENCH_DOSSIER_REQUIRED')
            from .workbench import (build_workspace,execute_local,explain_obligation,
                lower_obligation,propose_binding,select_obligation)
            if operation=='workbench_validate':
                self.workspace=build_workspace(self.dossier);self.lowering=None
                self._show({'workspace_root':self.workspace['workspace_root'],
                            'obligations':len(self.workspace['obligations']),
                            'unbound_zucchini_requirements':self.workspace['unbound_zucchini_requirements']},
                           'WORKSPACE VALIDATED')
                return
            require(self.workspace is not None,'WORKBENCH_WORKSPACE_REQUIRED')
            values=self.runtime.state['values'];requirement=values['workbench_requirement']
            if operation=='workbench_explain':
                self._show(explain_obligation(self.workspace,requirement),'OBLIGATION EXPLAINED')
            elif operation=='workbench_bind':
                proposal=propose_binding(self.workspace,requirement,values['workbench_zucchini_tag'],
                                         values['workbench_relation'],values['workbench_rationale'])
                self._show(proposal,'BINDING PROPOSED | NOT ADOPTED')
            elif operation=='workbench_lower':
                lane=values['workbench_lane']
                target={'INSPECT':'CONFORMANCE_WITNESS','CONFORMANCE_WITNESS':'CONFORMANCE_WITNESS',
                        'PROOF_RECHECK':'PROOF_RECHECK','BDD_RERUN':'BDD_RERUN',
                        'ZUCCHINI_REVIEW':'ZUCCHINI_REVIEW'}[lane]
                selection=select_obligation(self.workspace,requirement,lane)
                self.lowering=lower_obligation(self.workspace,selection,target)
                self._show(self.lowering,'LOWERED '+self.lowering['result'])
            elif operation=='workbench_run':
                require(self.lowering is not None,'WORKBENCH_LOWERING_REQUIRED')
                receipt=execute_local(self.lowering,self.dossier,allow_local_check=True,
                                      verified_workspace=self.workspace)
                self._show(receipt,'LOCAL CHECK '+receipt['outcome'])
        except Refusal as exc:
            self.runtime.state['status']=f'REFUSED {exc.code}'
            detail_key='control_detail' if str(event.get('node_id','')).startswith('control_') else 'workbench_detail'
            self.runtime.state['values'][detail_key]=json.dumps({
                'status':'REFUSED','code':exc.code,'path':exc.path,'detail':exc.detail,
                **BOUNDARY},indent=2,sort_keys=True)

def make_headless(dossier:Path|None=None):
    enable_runtime();from mosaic_ui.headless import HeadlessUI
    ui=HeadlessUI(payload(),layout);ui.state['values'].update(evidence_model(dossier))
    ui.miw_controller=WorkbenchController(ui,dossier)
    return ui

def make_native(dossier:Path|None=None):
    require(sys.platform=='win32','WIN32_HOST_REQUIRED',detail='Use headless-ui on other hosts; no replacement GUI is silently selected.')
    require(digest(read_bytes(ROOT/'assets/mosaic-sun.png'))==SUN_SHA,'SUN_ASSET_HASH_MISMATCH')
    enable_runtime()
    from dataclasses import replace
    from mosaic_ui.native_realizer import NativeSemanticUI
    from mosaic_ui.win32_image import NativeImage
    class Viewer(NativeSemanticUI):
        def __init__(self,*a,**kw):
            self.sun=NativeImage(ROOT/'assets/mosaic-sun.png')
            try:super().__init__(*a,**kw);self.window.set_icon(self.sun)
            except Exception:self.sun.close();raise
        def _build(self):
            handler=self.handlers['LABEL']
            def build(owner,item,key,rect,value):
                if item['props'].get('presentation_role')=='SUN':owner.window.image(key,owner.sun,rect,name=item['semantics']['name'])
                else:handler.build(owner,item,key,rect,value)
            def sync(owner,item,key,value):
                if item['props'].get('presentation_role')!='SUN':handler.sync(owner,item,key,value)
            self.handlers['LABEL']=replace(handler,build=build,sync=sync);super()._build()
        def close(self):
            try:super().close()
            finally:self.sun.close()
    headless=make_headless(dossier)
    viewer=Viewer(payload(),layout,width=1200,height=800,title='Invariant Workbench | v0.1 candidate',
                  headless=headless,event_dispatch=headless.miw_controller.dispatch)
    return viewer

def launch(dossier:Path|None=None)->None:
    viewer=make_native(dossier)
    try:viewer.window.run()
    finally:viewer.close()

def headless_smoke()->dict:
    ui=make_headless();observations=[]
    for width,height in [(1000,720),(1200,800),(1600,1000)]:
        for view in VIEWS:
            event={'intent':'ACTIVATE','node_id':'nav_'+view}
            ui.apply(event);projection=ui.project(width,height).as_dict()
            observations.append({'view':view,'width':width,'height':height,'projection_root':digest(json.dumps(projection,sort_keys=True).encode())})
    return seal({'schema':'miw.mosaic_headless_smoke.v1',**BOUNDARY,'status':'PASSED_HEADLESS_ONLY',
                 'projections':observations,'native_windows':'NOT_RUN','semantic_nodes':len(ui.nodes),'native_control_binding':'SEPARATE_REGRESSION_TEST_ONLY',
                 'original_sun_sha256':SUN_SHA,'actual_foundry':True,'tkinter_substitution':False})


def native_smoke(dossier:Path|None=None)->dict:
    """Real Win32 message-loop witness where available; never emulated to PASS."""
    if sys.platform!='win32':
        return seal({'schema':'miw.native_smoke.v1',**BOUNDARY,'status':'NOT_RUN',
                     'reason':'WIN32_HOST_UNAVAILABLE','actual_hwnd':False,'mosaic_foundry_bound':True})
    viewer=make_native(dossier);observations=[];failures=[]
    def step():
        try:
            if len(observations)==len(VIEWS):viewer.window.close();return
            view=VIEWS[len(observations)]
            viewer.apply({'intent':'ACTIVATE','node_id':'nav_'+view})
            require(viewer.runtime.state['active_view']==view,'NATIVE_VIEW_NOT_CHANGED')
            observations.append({'view':view,'controls':len(viewer.window.controls),
                                 'projection_root':digest(json.dumps(viewer.project(1200,800),sort_keys=True).encode())})
        except Exception as exc:
            failures.append(type(exc).__name__);viewer.window.close()
    try:
        viewer.window.set_timer(120,step);viewer.window.run()
    finally:viewer.close()
    good=not failures and len(observations)==len(VIEWS)
    return seal({'schema':'miw.native_smoke.v1',**BOUNDARY,
                 'status':'PASSED_REAL_WIN32_SMOKE' if good else 'FAILED_OR_INCOMPLETE',
                 'actual_hwnd':True,'mosaic_foundry_bound':True,'views':observations,'errors':failures,
                 'scope':'MESSAGE_LOOP_AND_VIEW_SWITCHING; NOT_FULL_HUMAN_USABILITY_OR_ACCESSIBILITY_ACCEPTANCE'})
