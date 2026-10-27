"""CLI adapters over the shared proof, BDD, import and governance engine."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import sys
from .common import Refusal,require,read_bytes,read_json,canonical_bytes,write_json,write_output
from .proofs import prove_source,verify_source_proof
from .bdd import discover,run_feature,assess_counterexample
from .zucchini import import_report,make_junit_binding,link_junit
from .governance import freeze_basis,check_candidate
from .graph import impact
from .dossier import generate_demo,verify_dossier

ROOT=Path(__file__).resolve().parents[2]

def emit(value:dict,path:str|None=None) -> None:
    if path:
        dest=Path(path)
        if dest.exists():
            require(read_bytes(dest)==canonical_bytes(value)+b'\n','OUTPUT_EXISTS_WITH_DIFFERENT_CONTENT',detail=str(dest))
        else:write_json(dest,value)
    print(json.dumps(value if not path else {'output':str(path),**{k:v for k,v in value.items() if k in
        {'schema','status','outcome','proof_root','check_root','qualification_root','summary_root','import_root','link_root','basis_root','scope_check_root','dossier_check_root',
         'workspace_root','binding_root','selection_root','lowering_root','execution_receipt_root','comparison_root','explanation_root',
         'surface_root','plan_root','posture_root','diagnostic_root','ctr_root','court_root','self_contract_check_root'}}},sort_keys=True,indent=2))

def parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(description='Invariant Workbench v0.1. Local-only experimental candidate. No production authority.')
    sub=p.add_subparsers(dest='command',required=True)
    def output(q):q.add_argument('--out',help='Create a JSON artifact; an existing differing file is refused.')
    def source(q):q.add_argument('--contract',required=True);q.add_argument('--source',required=True)
    q=sub.add_parser('prove',help='Prove the accepted restricted Python source before executing it.');source(q);output(q)
    q=sub.add_parser('verify-proof',help='Rederive obligations and recheck all native certificates.');source(q);q.add_argument('--proof',required=True);output(q)
    q=sub.add_parser('discover',help='Validate native example expectations without running the operation.');q.add_argument('--contract',required=True);q.add_argument('--feature',required=True);output(q)
    q=sub.add_parser('test-feature',help='Execute examples against the closed pure-operation Python subset.');source(q);q.add_argument('--feature',required=True);output(q)
    q=sub.add_parser('assess-counterexample',help='Require an actual failed assertion for the named requirement.');source(q);q.add_argument('--feature',required=True);q.add_argument('--target',required=True);output(q)
    q=sub.add_parser('import-zucchini',help='Read-only 2.2.0 report import. Does not execute C++ or prove correctness.');q.add_argument('--report',required=True);output(q)
    q=sub.add_parser('bind-junit',help='Explicitly record a CALLER assertion of same-build association; not authentication.');q.add_argument('--report',required=True);q.add_argument('--junit',required=True);output(q)
    q=sub.add_parser('link-junit',help='Link results under an explicit caller binding; never infer requirement-specific failure.');q.add_argument('--report',required=True);q.add_argument('--junit',required=True);q.add_argument('--binding',required=True);output(q)
    q=sub.add_parser('freeze-basis',help='Record a local checking basis. Not an authenticated grant.');q.add_argument('--directory',required=True);q.add_argument('--policy',required=True);output(q)
    q=sub.add_parser('check-candidate',help='Read-only exact edit-scope check. Does not establish correctness.');q.add_argument('--basis',required=True);q.add_argument('--directory',required=True);q.add_argument('--expected-basis-root',required=True);output(q)
    q=sub.add_parser('impact',help='Show dependency closure while retaining full qualification for a partial graph.');q.add_argument('--graph',required=True);q.add_argument('--expected-graph-root',required=True);q.add_argument('--changed',nargs='+',required=True);output(q)
    q=sub.add_parser('demo',help='Produce a complete local proof-first demonstration and offline dossier.');q.add_argument('--out',required=True,help='New output directory, not an existing directory.')
    q=sub.add_parser('verify-dossier',help='Verify dossier bytes and replay proofs against its source snapshots.');q.add_argument('--directory',required=True);output(q)
    q=sub.add_parser('gui',help='Open the actual Mosaic Foundry WIN32 read-only viewer.');q.add_argument('--directory',required=True)
    q=sub.add_parser('self-test',help='Run builder regression tests and unchanged inherited native-proof tests.');output(q)
    q=sub.add_parser('preflight',help='Observe local tool availability. No network or installation.');output(q)
    q=sub.add_parser('snapshot',help='Pin an exported, reviewed source directory without executing it.');q.add_argument('--directory',required=True);output(q)
    q=sub.add_parser('lifecycle-demo',help='Execute the pure sequential work-order reference model.');output(q)
    q=sub.add_parser('explore-lifecycle',help='Exhaust the declared finite workflow graph, not arbitrary workflows.');output(q)
    q=sub.add_parser('headless-ui',help='Exercise the actual Mosaic semantic runtime without claiming Windows execution.');output(q)
    q=sub.add_parser('ucm-fixture',help='Exercise the unchanged UCM work manager with explicitly non-authoritative fixture identities.');q.add_argument('--out',required=True)
    q=sub.add_parser('proposal-request',help='Create a proposal-only request pinned to a current checking basis.');source(q);q.add_argument('--target',required=True);q.add_argument('--basis-root',required=True);q.add_argument('--budget',type=int,default=3);output(q)
    q=sub.add_parser('review-proposal',help='Validate model text and reproduce target-specific observations. No specification approval.');source(q);q.add_argument('--request',required=True);q.add_argument('--response',required=True);q.add_argument('--expected-request-root',required=True);q.add_argument('--basis-root',required=True);output(q)
    q=sub.add_parser('ollama-propose',help='Explicit opt-in loopback-only model request. No tools or source edits.');q.add_argument('--request',required=True);q.add_argument('--model',required=True);q.add_argument('--port',type=int,default=11434);q.add_argument('--allow-local-model',action='store_true');q.add_argument('--out',required=True)
    q=sub.add_parser('explain-change',help='Explain changed meaning/code; never infer semantic equivalence.');q.add_argument('--old-contract',required=True);q.add_argument('--new-contract',required=True);q.add_argument('--old-source',required=True);q.add_argument('--new-source',required=True);output(q)
    q=sub.add_parser('run-zucchini',help='Execute explicitly trusted, source-pinned upstream CMake input. Not an OS sandbox.');q.add_argument('--source-directory',required=True);q.add_argument('--expected-source-root',required=True);q.add_argument('--upstream-commit',required=True);q.add_argument('--build-config',default='Release');q.add_argument('--generator');q.add_argument('--cmake-define',action='append',default=[]);q.add_argument('--accept-report',action='append',default=[]);q.add_argument('--step-timeout',type=int,default=600);q.add_argument('--allow-trusted-build',action='store_true');q.add_argument('--out',required=True)
    q=sub.add_parser('postgres-live',help='Opt-in acceptance against a dedicated disposable DB using MIW_TEST_PG_DSN.');q.add_argument('--allow-disposable-database',action='store_true');q.add_argument('--out',required=True)
    q=sub.add_parser('cpp-probe',help='Compile builder-authored finite correspondence probe. This is NOT Zucchini or formal C++ verification.');q.add_argument('--allow-trusted-compile',action='store_true');q.add_argument('--out',required=True)
    q=sub.add_parser('integration-demo',help='Generate deterministic lifecycle/proposal/maintenance records and fixture custody evidence.');q.add_argument('--out',required=True)
    q=sub.add_parser('validate-realization-space',help='Validate the local invariant-evidence contract, registry and capability dictionary.')
    q.add_argument('--contract',default=str(ROOT/'schemas/INVARIANT-EVIDENCE-SPACE-CONTRACT.json'))
    q.add_argument('--registry',default=str(ROOT/'schemas/INVARIANT-WORKBENCH-REALIZER-REGISTRY.json'))
    q.add_argument('--dictionary',default=str(ROOT/'schemas/INVARIANT-WORKBENCH-CAPABILITY-DICTIONARY.json'));output(q)
    q=sub.add_parser('workbench-open',help='Build a rooted obligation ledger from an exact dossier without promoting evidence classes.')
    q.add_argument('--directory',required=True);q.add_argument('--bindings');output(q)
    q=sub.add_parser('workbench-bind',help='Create a proposed MIW/Zucchini requirement binding; no semantic equivalence or approval is inferred.')
    q.add_argument('--workspace',required=True);q.add_argument('--requirement',required=True);q.add_argument('--zucchini-tag',required=True)
    q.add_argument('--relation',choices=['CANDIDATE_CORRESPONDENCE','SUPPORTS_TEST_DESIGN','EXACT_TAG_MATCH'],required=True)
    q.add_argument('--rationale',required=True);output(q)
    q=sub.add_parser('workbench-select',help='Select one exact obligation and evidence lane.')
    q.add_argument('--workspace',required=True);q.add_argument('--requirement',required=True)
    q.add_argument('--lane',choices=['INSPECT','PROOF_RECHECK','BDD_RERUN','ZUCCHINI_REVIEW','CONFORMANCE_WITNESS'],required=True);output(q)
    q=sub.add_parser('workbench-lower',help='Lower a selection to a bounded plan or typed refusal.')
    q.add_argument('--workspace',required=True);q.add_argument('--selection',required=True)
    q.add_argument('--target',choices=['PROOF_RECHECK','BDD_RERUN','ZUCCHINI_REVIEW','CONFORMANCE_WITNESS','DOSSIER_VERIFY'],required=True);output(q)
    q=sub.add_parser('workbench-run',help='Execute a lowered local-only check after an explicit opt-in; external targets refuse.')
    q.add_argument('--lowering',required=True);q.add_argument('--directory',required=True)
    q.add_argument('--workspace',help='Exact rooted workspace used to create the lowering; required when bindings alter its root.')
    q.add_argument('--allow-local-check',action='store_true');output(q)
    q=sub.add_parser('workbench-compare',help='Compare two exact workspaces without inferring semantic equivalence.')
    q.add_argument('--left',required=True);q.add_argument('--right',required=True);output(q)
    q=sub.add_parser('workbench-explain',help='Explain one obligation, its evidence classes and open assumptions.')
    q.add_argument('--workspace',required=True);q.add_argument('--requirement',required=True);output(q)
    operation_registry=str(ROOT/'constitutional/OPERATION-REGISTRY.json')
    q=sub.add_parser('capability-surface',help='Export the closed agent-readable operation and capability surface.')
    q.add_argument('--registry',default=operation_registry);output(q)
    q=sub.add_parser('compile-operation',help='Compile one declared operation into five independent commitments; grants no authority.')
    q.add_argument('--registry',default=operation_registry);q.add_argument('--operation',required=True)
    q.add_argument('--subject',required=True);q.add_argument('--inputs',required=True);q.add_argument('--requester',default='LOCAL_OPERATOR');output(q)
    q=sub.add_parser('cgp-posture',help='Derive bounded ESA/EVS/COP/SRSA posture from exact local evidence.')
    q.add_argument('--registry',default=operation_registry);q.add_argument('--workspace')
    q.add_argument('--proof-receipt');q.add_argument('--bdd-receipt');q.add_argument('--headless-receipt');output(q)
    q=sub.add_parser('diagnose-workbench',help='Produce a read-only repair/debug diagnostic and suggested next observations.')
    q.add_argument('--posture',required=True);output(q)
    q=sub.add_parser('constitutional-test',help='Run the finite local constitutional court catalog (CTR).')
    q.add_argument('--plan',default=str(ROOT/'constitutional/CTR-PLAN.json'));q.add_argument('--registry',default=operation_registry)
    q.add_argument('--directory',required=True);q.add_argument('--bindings');output(q)
    q=sub.add_parser('headless-application',help='Exercise the real Mosaic semantic application/controller flow without a native window.')
    q.add_argument('--directory',required=True);q.add_argument('--bindings');output(q)
    self_contract=str(ROOT/'constitutional/SELF-CONTRACT.json')
    ctr_plan=str(ROOT/'constitutional/CTR-PLAN.json')
    q=sub.add_parser('self-contract-check',help='Validate the sealed MIW self-contract and all live enforcement references.')
    q.add_argument('--contract',default=self_contract);q.add_argument('--registry',default=operation_registry)
    q.add_argument('--plan',default=ctr_plan);output(q)
    q=sub.add_parser('explain',help='Explain one MIW guarantee, nonclaim, trusted assumption, or the complete self-contract index.')
    q.add_argument('--contract',default=self_contract);q.add_argument('--registry',default=operation_registry)
    q.add_argument('--plan',default=ctr_plan);q.add_argument('--id');output(q)
    return p

def main(argv=None) -> int:
    args=parser().parse_args(argv)
    try:
        c=args.command
        if c in {'prove','verify-proof','test-feature','assess-counterexample','proposal-request','review-proposal'}:
            contract=read_json(Path(args.contract));source=read_bytes(Path(args.source)).decode('utf-8')
        if c=='prove':
            value=prove_source(contract,source);emit(value,args.out);return 0 if value['outcome']=='CHECKED_SOURCE_PROOF' else 3
        if c=='verify-proof':
            value=verify_source_proof(contract,source,read_json(Path(args.proof)));emit(value,args.out);return 0 if value['outcome']=='CHECKED_SOURCE_PROOF' else 3
        if c=='discover':value=discover(read_json(Path(args.contract)),read_bytes(Path(args.feature)).decode())
        elif c=='test-feature':
            value=run_feature(contract,source,read_bytes(Path(args.feature)).decode());emit(value,args.out)
            return 0 if all(s['status']=='PASSED' for s in value['runs']) else 4
        elif c=='assess-counterexample':value=assess_counterexample(contract,source,read_bytes(Path(args.feature)).decode(),args.target)
        elif c=='import-zucchini':value=import_report(read_bytes(Path(args.report)))
        elif c=='bind-junit':value=make_junit_binding(read_bytes(Path(args.report)),read_bytes(Path(args.junit)))
        elif c=='link-junit':value=link_junit(read_bytes(Path(args.report)),read_bytes(Path(args.junit)),read_json(Path(args.binding)))
        elif c=='freeze-basis':
            policy=read_json(Path(args.policy));require(type(policy) is dict and set(policy)=={'protected','mutable'},'BASIS_POLICY_INVALID')
            value=freeze_basis(Path(args.directory),policy['protected'],policy['mutable'])
        elif c=='check-candidate':value=check_candidate(read_json(Path(args.basis)),Path(args.directory),args.expected_basis_root)
        elif c=='impact':value=impact(read_json(Path(args.graph)),args.changed,args.expected_graph_root)
        elif c=='demo':
            value=generate_demo(ROOT,Path(args.out));print(json.dumps(value,indent=2,sort_keys=True));return 0
        elif c=='verify-dossier':value=verify_dossier(Path(args.directory))
        elif c=='gui':
            from .foundry_view import launch
            launch(Path(args.directory));return 0
        elif c=='preflight':
            from .external_build import preflight
            value=preflight()
        elif c=='snapshot':
            from .governance import snapshot
            value=snapshot(Path(args.directory))
        elif c=='lifecycle-demo':
            from .lifecycle import lifecycle_demo
            value=lifecycle_demo()
        elif c=='explore-lifecycle':
            from .lifecycle import bounded_exploration
            value=bounded_exploration()
        elif c=='headless-ui':
            from .foundry_view import headless_smoke
            value=headless_smoke()
        elif c=='ucm-fixture':
            from .custody_bridge import fixture_campaign
            value=fixture_campaign(ROOT,Path(args.out));print(json.dumps(value,indent=2,sort_keys=True));return 0
        elif c=='proposal-request':
            from .proposals import proposal_request
            value=proposal_request(contract,source,args.target,args.basis_root,budget=args.budget)
        elif c=='review-proposal':
            from .proposals import review_proposal
            value=review_proposal(read_json(Path(args.request)),read_bytes(Path(args.response)),expected_request_root=args.expected_request_root,current_contract=contract,current_source=source,current_basis_root=args.basis_root)
        elif c=='ollama-propose':
            from .proposals import ollama_propose
            require(not Path(args.out).exists(),'OUTPUT_ALREADY_EXISTS')
            raw=ollama_propose(read_json(Path(args.request)),args.model,allow_local_model=args.allow_local_model,port=args.port)
            write_output(Path(args.out),raw);print(json.dumps({'status':'UNTRUSTED_MODEL_PROPOSAL_SAVED','output':args.out,'specification_approval':'NOT_GRANTED'}));return 0
        elif c=='explain-change':
            from .changes import explain_change
            value=explain_change(read_json(Path(args.old_contract)),read_json(Path(args.new_contract)),read_bytes(Path(args.old_source)).decode(),read_bytes(Path(args.new_source)).decode())
        elif c=='run-zucchini':
            from .external_build import run_zucchini
            value=run_zucchini(Path(args.source_directory),Path(args.out),expected_source_root=args.expected_source_root,
                upstream_commit=args.upstream_commit,build_config=args.build_config,generator=args.generator,
                cmake_definitions=args.cmake_define,accept_report_paths=args.accept_report,step_timeout=args.step_timeout,
                allow_trusted_build=args.allow_trusted_build)
            print(json.dumps(value,indent=2,sort_keys=True));return 0 if value.get('successful_acceptance') is True else 6
        elif c=='postgres-live':
            from .live_postgres import run_live
            value=run_live(Path(args.out),allow_disposable_database=args.allow_disposable_database)
            print(json.dumps(value,indent=2,sort_keys=True));return 0 if value['status']=='PASSED_LIVE_INTEGRATION_TESTS' else 6
        elif c=='cpp-probe':
            from .cpp_probe import run_probe
            value=run_probe(ROOT,Path(args.out),allow_trusted_compile=args.allow_trusted_compile)
            print(json.dumps(value,indent=2,sort_keys=True));return 0 if value['status']=='PASSED_FINITE_DIFFERENTIAL_PROBE' else 6
        elif c=='integration-demo':
            from .integration_demo import generate_integration
            value=generate_integration(ROOT,Path(args.out));print(json.dumps(value,indent=2,sort_keys=True));return 0
        elif c=='validate-realization-space':
            from .realization_space import validate_bundle
            value=validate_bundle(Path(args.contract),Path(args.registry),Path(args.dictionary))
        elif c=='workbench-open':
            from .workbench import build_workspace
            bindings=read_json(Path(args.bindings)) if args.bindings else None
            value=build_workspace(Path(args.directory),bindings)
        elif c=='workbench-bind':
            from .workbench import propose_binding
            value=propose_binding(read_json(Path(args.workspace)),args.requirement,args.zucchini_tag,args.relation,args.rationale)
        elif c=='workbench-select':
            from .workbench import select_obligation
            value=select_obligation(read_json(Path(args.workspace)),args.requirement,args.lane)
        elif c=='workbench-lower':
            from .workbench import lower_obligation
            value=lower_obligation(read_json(Path(args.workspace)),read_json(Path(args.selection)),args.target)
        elif c=='workbench-run':
            from .workbench import execute_local
            workspace=read_json(Path(args.workspace)) if args.workspace else None
            value=execute_local(read_json(Path(args.lowering)),Path(args.directory),
                                allow_local_check=args.allow_local_check,
                                verified_workspace=workspace)
        elif c=='workbench-compare':
            from .workbench import compare_workspaces
            value=compare_workspaces(read_json(Path(args.left)),read_json(Path(args.right)))
        elif c=='workbench-explain':
            from .workbench import explain_obligation
            value=explain_obligation(read_json(Path(args.workspace)),args.requirement)
        elif c=='capability-surface':
            from .constitutional import capability_surface
            value=capability_surface(read_json(Path(args.registry)))
        elif c=='compile-operation':
            from .constitutional import compile_operation
            value=compile_operation(read_json(Path(args.registry)),args.operation,
                                    subject=read_json(Path(args.subject)),inputs=read_json(Path(args.inputs)),
                                    requester=args.requester)
        elif c=='cgp-posture':
            from .constitutional import cgp_posture
            optional=lambda path: read_json(Path(path)) if path else None
            value=cgp_posture(read_json(Path(args.registry)),optional(args.workspace),
                              optional(args.proof_receipt),optional(args.bdd_receipt),optional(args.headless_receipt))
        elif c=='diagnose-workbench':
            from .constitutional import diagnose
            value=diagnose(read_json(Path(args.posture)))
        elif c=='constitutional-test':
            from .constitutional import run_ctr
            value=run_ctr(read_json(Path(args.plan)),read_json(Path(args.registry)),ROOT,
                          Path(args.directory),Path(args.bindings) if args.bindings else None)
            emit(value,args.out);return 0 if value['status']=='PASSED' else 5
        elif c=='headless-application':
            from .headless_runner import application_court
            value=application_court(Path(args.directory),Path(args.bindings) if args.bindings else None)
        elif c=='self-contract-check':
            from .self_contract import validate_self_contract
            value=validate_self_contract(read_json(Path(args.contract)),ROOT,
                                         read_json(Path(args.registry)),read_json(Path(args.plan)))
        elif c=='explain':
            from .self_contract import explain_self_contract
            value=explain_self_contract(read_json(Path(args.contract)),ROOT,
                                        read_json(Path(args.registry)),read_json(Path(args.plan)),args.id)
        elif c=='self-test':
            from .qualification import run_tests
            value,log=run_tests(ROOT)
            print(log,file=sys.stderr);emit(value,args.out);return 0 if value['status']=='PASSED' else 5
        else:raise Refusal('COMMAND_UNSUPPORTED')
        emit(value,args.out)
        return 4 if c=='discover' and not value['discovery_success'] else 0
    except Refusal as exc:
        print(json.dumps({'status':'REFUSED','code':exc.code,'path':exc.path,'detail':exc.detail,
                          'standing':'INFORMATION_ONLY','authority_effect':'NONE'},sort_keys=True),file=sys.stderr);return 2
    except (OSError,UnicodeError,ValueError,TypeError,KeyError,RecursionError,ImportError) as exc:
        print(json.dumps({'status':'REFUSED','code':'INPUT_OR_HOST_ERROR','detail':type(exc).__name__,
                          'standing':'INFORMATION_ONLY','authority_effect':'NONE'},sort_keys=True),file=sys.stderr);return 2
