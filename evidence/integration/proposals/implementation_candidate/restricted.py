"""Closed, loop-free Python subset -> exhaustive symbolic execution paths.

This frontend is trusted new code, not a formally proved compiler. It parses
source as data. No subject Python executes during lowering or proof checking.
"""
from __future__ import annotations
import ast
from copy import deepcopy
from itertools import product
from typing import Any
from .common import Refusal, require, identifier

MAX_NODES = 1000
MAX_PATHS = 128
MAX_DEPTH = 24
MAX_LITERAL = 10**9

def parse(text: str, mode: str = 'eval') -> ast.AST:
    require(type(text) is str and len(text.encode('utf-8')) <= 64_000, 'SOURCE_SIZE_LIMIT')
    try:
        tree = ast.parse(text, mode=mode)
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise Refusal('SOURCE_PARSE_FAILED', detail=type(exc).__name__) from exc
    nodes = list(ast.walk(tree))
    require(len(nodes) <= MAX_NODES, 'SOURCE_NODE_LIMIT')
    todo = [(tree, 0)]
    while todo:
        node, depth = todo.pop()
        require(depth <= MAX_DEPTH, 'SOURCE_DEPTH_LIMIT')
        todo.extend((child, depth+1) for child in ast.iter_child_nodes(node))
    return tree

def int_term(n: int) -> dict:
    require(type(n) is int and abs(n) <= MAX_LITERAL, 'LITERAL_OUT_OF_RANGE')
    return {'op': 'INT', 'value': n}

def term(node: ast.AST, names: set[str]) -> dict:
    if isinstance(node, ast.Name):
        require(node.id in names, 'UNKNOWN_VARIABLE', detail=node.id)
        return {'op': 'VAR', 'name': node.id}
    if isinstance(node, ast.Constant):
        return int_term(node.value)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        inner = term(node.operand, names)
        return inner if isinstance(node.op, ast.UAdd) else {'op': 'MUL_CONST', 'coefficient': -1, 'arg': inner}
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, (ast.Add, ast.Sub)):
            return {'op': 'ADD' if isinstance(node.op, ast.Add) else 'SUB',
                    'args': [term(node.left, names), term(node.right, names)]}
        if isinstance(node.op, ast.Mult):
            left, right = term(node.left, names), term(node.right, names)
            require(left['op'] == 'INT' or right['op'] == 'INT', 'NONLINEAR_UNSUPPORTED')
            constant, arg = (left, right) if left['op'] == 'INT' else (right, left)
            return {'op': 'MUL_CONST', 'coefficient': constant['value'], 'arg': arg}
    raise Refusal('TERM_UNSUPPORTED', detail=type(node).__name__)

def parse_term(text: str, names: set[str]) -> dict:
    return term(parse(text).body, names)

def _cross(parts: list[list[list[dict]]]) -> list[list[dict]]:
    out = [[]]
    for part in parts:
        require(len(out)*len(part) <= MAX_PATHS, 'PATH_LIMIT_EXCEEDED')
        out = [a+b for a in out for b in part]
    return out

def dnf(node: ast.AST, names: set[str], negate: bool = False) -> list[list[dict]]:
    """A Boolean expression as disjunction of conjunctions; integer semantics."""
    if isinstance(node, ast.Constant) and type(node.value) is bool:
        return [[]] if node.value != negate else []
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return dnf(node.operand, names, not negate)
    if isinstance(node, ast.BoolOp) and isinstance(node.op, (ast.And, ast.Or)):
        parts = [dnf(x, names, negate) for x in node.values]
        conjunctive = isinstance(node.op, ast.And) != negate
        out = _cross(parts) if conjunctive else [clause for part in parts for clause in part]
        require(len(out) <= MAX_PATHS, 'PATH_LIMIT_EXCEEDED')
        return out
    if isinstance(node, ast.Compare):
        require(len(node.ops) == len(node.comparators) == 1, 'CHAINED_COMPARISON_UNSUPPORTED')
        ops = {ast.Lt: 'LT', ast.LtE: 'LE', ast.Gt: 'GT', ast.GtE: 'GE', ast.Eq: 'EQ', ast.NotEq: 'NE'}
        op = ops.get(type(node.ops[0]))
        require(op is not None, 'COMPARISON_UNSUPPORTED')
        if negate:
            op = {'LT':'GE', 'LE':'GT', 'GT':'LE', 'GE':'LT', 'EQ':'NE', 'NE':'EQ'}[op]
        args = [term(node.left, names), term(node.comparators[0], names)]
        if op == 'NE':
            return [[{'op':'LT','args':args}], [{'op':'GT','args':deepcopy(args)}]]
        return [[{'op':op,'args':args}]]
    raise Refusal('CONDITION_UNSUPPORTED', detail=type(node).__name__)

def parse_dnf(text: str, names: set[str], negate: bool = False) -> list[list[dict]]:
    return dnf(parse(text).body, names, negate)

def conjunction(atoms: list[dict]) -> dict:
    if not atoms:
        return {'op':'TRUE'}
    if len(atoms) == 1:
        return deepcopy(atoms[0])
    require(len(atoms) <= 64, 'FORMULA_ARITY_LIMIT')
    return {'op':'AND', 'args':deepcopy(atoms)}

def sub_term(value: dict, values: dict[str,dict]) -> dict:
    if value['op'] == 'VAR': return deepcopy(values.get(value['name'], value))
    if value['op'] == 'INT': return deepcopy(value)
    if value['op'] == 'MUL_CONST':
        return {**value, 'arg':sub_term(value['arg'], values)}
    return {**value, 'args':[sub_term(x, values) for x in value['args']]}

def sub_atom(value: dict, values: dict[str,dict]) -> dict:
    return {**value, 'args':[sub_term(x, values) for x in value['args']]}

def evaluate_term(value: dict, values: dict[str,int]) -> int:
    op = value['op']
    if op == 'VAR': return values[value['name']]
    if op == 'INT': return value['value']
    if op == 'MUL_CONST': return value['coefficient'] * evaluate_term(value['arg'], values)
    left, right = (evaluate_term(x, values) for x in value['args'])
    return left+right if op == 'ADD' else left-right

def evaluate_atom(atom: dict, values: dict[str,int]) -> bool:
    a,b = (evaluate_term(x, values) for x in atom['args'])
    op = atom['op']
    return {'LT':a<b,'LE':a<=b,'GT':a>b,'GE':a>=b,'EQ':a==b}[op]

def evaluate_dnf(clauses: list[list[dict]], values: dict[str,int]) -> bool:
    return any(all(evaluate_atom(x, values) for x in clause) for clause in clauses)

def lower_source(text: str, function: str, parameters: list[str], state: list[str]) -> dict:
    tree = parse(text, 'exec')
    require(len(tree.body) == 1 and isinstance(tree.body[0], ast.FunctionDef), 'ONE_FUNCTION_REQUIRED')
    f = tree.body[0]
    require(f.name == function and not f.decorator_list and f.returns is None and not f.type_comment,
            'FUNCTION_SIGNATURE_INVALID')
    require(not getattr(f,'type_params',[]), 'TYPE_PARAMETERS_UNSUPPORTED')
    args = f.args
    require([x.arg for x in args.args] == parameters and not args.posonlyargs and not args.kwonlyargs
            and not args.defaults and not args.kw_defaults and args.vararg is None and args.kwarg is None
            and all(x.annotation is None for x in args.args), 'FUNCTION_PARAMETERS_MISMATCH')
    names = set(parameters)
    def validate(statements):
        require(bool(statements), 'EMPTY_BODY')
        for s in statements:
            if isinstance(s, ast.If):
                dnf(s.test, names); dnf(s.test, names, True)
                validate(s.body)
                if s.orelse: validate(s.orelse)
            elif isinstance(s, ast.Return):
                require(isinstance(s.value, ast.Tuple) and len(s.value.elts) == len(state)+1, 'RETURN_SHAPE_INVALID')
                flag = s.value.elts[0]
                require(isinstance(flag, ast.Constant) and type(flag.value) is bool, 'RETURN_FLAG_MUST_BE_LITERAL_BOOL')
                for val in s.value.elts[1:]: term(val, names)
            else:
                raise Refusal('STATEMENT_UNSUPPORTED', detail=type(s).__name__)
    validate(f.body)
    paths = []
    def visit(statements, guards):
        require(bool(statements), 'MISSING_RETURN')
        first, rest = statements[0], statements[1:]
        if isinstance(first, ast.Return):
            paths.append({'path_id':f'p{len(paths):03d}', 'guards':deepcopy(guards),
                          'accepted':first.value.elts[0].value,
                          'outputs':{name:term(val,names) for name,val in zip(state,first.value.elts[1:],strict=True)},
                          'return_line':first.lineno})
            require(len(paths) <= MAX_PATHS, 'PATH_LIMIT_EXCEEDED')
            return
        for clause in dnf(first.test,names): visit(first.body+rest,guards+clause)
        for clause in dnf(first.test,names,True): visit(first.orelse+rest,guards+clause)
    visit(f.body,[])
    require(bool(paths), 'NO_EXECUTION_PATHS')
    return {'language':'MIW_PYTHON_LINEAR_IF_RETURN_V1','function':function,'parameters':parameters,'state':state,
            'paths':paths,'termination':'STRUCTURAL_LOOP_FREE','source_execution':'NONE'}
