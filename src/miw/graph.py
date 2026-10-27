"""Explicit dependency maps. Unknown or incomplete edges never narrow checking."""
from __future__ import annotations
from .common import BOUNDARY, require, seal, check_seal, exact_keys

def make_graph(nodes:list[dict],edges:list[dict],scope:str) -> dict:
    require(type(scope) is str and bool(scope),'GRAPH_SCOPE_REQUIRED')
    ids=[]
    for n in nodes:
        exact_keys(n,{'id','kind','root'})
        require(all(type(n[k]) is str and n[k] for k in n),'GRAPH_NODE_INVALID');ids.append(n['id'])
    require(ids and len(ids)==len(set(ids)),'GRAPH_NODE_IDS_INVALID');known=set(ids)
    for e in edges:
        exact_keys(e,{'dependency','dependent','relation'})
        require(e['dependency'] in known and e['dependent'] in known,'GRAPH_EDGE_UNRESOLVED')
        require(e['relation'] in {'DEPENDS_ON','CHECKS','IMPLEMENTS','OBSERVES'},'GRAPH_RELATION_INVALID')
    require(len({(e['dependency'],e['dependent'],e['relation']) for e in edges})==len(edges),'GRAPH_EDGE_DUPLICATE')
    return seal({'schema':'miw.dependency_graph.v1',**BOUNDARY,'scope':scope,'complete':False,
        'completeness':'DECLARED_SCOPE_WITH_UNRESOLVED_EXTERNAL_BOUNDARIES',
        'nodes':sorted(nodes,key=lambda n:n['id']),
        'edges':sorted(edges,key=lambda e:(e['dependency'],e['dependent'],e['relation']))},'graph_root')

def impact(graph:dict,changed:list[str],expected_graph_root:str) -> dict:
    check_seal(graph,'graph_root');require(graph['graph_root']==expected_graph_root,'GRAPH_EXTERNAL_PIN_MISMATCH')
    expected=make_graph(graph['nodes'],graph['edges'],graph['scope'])
    require(graph==expected,'GRAPH_BOUNDARY_MISMATCH')
    require(type(changed) is list and changed and all(type(x) is str and x for x in changed)
            and len(changed)==len(set(changed)),'CHANGES_INVALID')
    known={n['id'] for n in graph['nodes']};reachable=set(changed)&known
    while True:
        prior=set(reachable)
        reachable|={e['dependent'] for e in graph['edges'] if e['dependency'] in reachable}
        if reachable==prior:break
    return seal({'schema':'miw.impact.v1',**BOUNDARY,'graph_root':graph['graph_root'],
        'changed':sorted(changed),'known_dependency_closure':sorted(reachable),
        'unknown_changes':sorted(set(changed)-known),'required_requalification':sorted(known),
        'mode':'FULL_REQUALIFICATION','reason':'This candidate has no admitted complete dependency model; closure is advisory only'},'impact_root')
