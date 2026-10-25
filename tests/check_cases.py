#!/usr/bin/env python3
"""Own tests for Assignment 3.

Run from the repository root:
    python tests/check_cases.py                # run every check, exit code 1 on failure
    python tests/check_cases.py --skip-large   # only small hand-justified cases
    python tests/check_cases.py --report       # also (re)write tests/my_cases.jsonl,
                                               # tests/actual_outputs.jsonl and tests/TESTS.md

How answers are judged
  * Hand cases carry an expected value that was derived by hand (see the `why` text).
  * Because several answers are not unique, every answer is ALSO checked semantically by
    validators below.  The validators use reference algorithms that differ from the ones
    being tested: brute force over edge subsets, Tarjan (not Kosaraju), Kahn (not DFS),
    small-to-large set merging (not DSU).
  * `validator_selftest` shows that each validator accepts an alternative valid answer and
    rejects invalid witnesses.
"""
import argparse
import itertools
import json
import pathlib
import random
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run as launcher  # noqa: E402  (tools/run.py: build() and execute())

TESTS = ROOT / 'tests'


# ------------------------------------------------------------------ reference helpers

def components_of(n, edges):
    """Connected components of an undirected graph by iterative DFS."""
    adj = [[] for _ in range(n)]
    for e in edges:
        adj[e[0]].append(e[1])
        adj[e[1]].append(e[0])
    comp = [-1] * n
    count = 0
    for s in range(n):
        if comp[s] != -1:
            continue
        comp[s] = count
        stack = [s]
        while stack:
            x = stack.pop()
            for y in adj[x]:
                if comp[y] == -1:
                    comp[y] = count
                    stack.append(y)
        count += 1
    return comp, count


def make_finder(n):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    return parent, find


def ref_kruskal_cost(n, edges):
    parent, find = make_finder(n)
    cost = 0
    for u, v, w in sorted(edges, key=lambda e: e[2]):
        a, b = find(u), find(v)
        if a != b:
            parent[a] = b
            cost += w
    return cost


def brute_mst_cost(n, edges):
    """Exact optimum by trying every subset of n-c edges (tiny graphs only)."""
    _, c = components_of(n, edges)
    best = None
    for subset in itertools.combinations(range(len(edges)), n - c):
        parent, find = make_finder(n)
        ok, total = True, 0
        for i in subset:
            a, b = find(edges[i][0]), find(edges[i][1])
            if a == b:
                ok = False
                break
            parent[a] = b
            total += edges[i][2]
        if ok and (best is None or total < best):
            best = total
    return best


def kahn(n, edges):
    indeg = [0] * n
    adj = [[] for _ in range(n)]
    for e in edges:
        adj[e[0]].append(e[1])
        indeg[e[1]] += 1
    order = [v for v in range(n) if indeg[v] == 0]
    i = 0
    while i < len(order):
        v = order[i]
        i += 1
        for u in adj[v]:
            indeg[u] -= 1
            if indeg[u] == 0:
                order.append(u)
    return len(order) == n, order


def tarjan_labels(n, edges):
    """Iterative Tarjan SCC (a different algorithm from the Kosaraju being tested)."""
    adj = [[] for _ in range(n)]
    for e in edges:
        adj[e[0]].append(e[1])
    index = [-1] * n
    low = [0] * n
    on_stack = [False] * n
    stack, comp = [], [-1] * n
    counter = count = 0
    for s in range(n):
        if index[s] != -1:
            continue
        index[s] = low[s] = counter
        counter += 1
        stack.append(s)
        on_stack[s] = True
        work = [(s, 0)]
        while work:
            v, i = work.pop()
            if i < len(adj[v]):
                work.append((v, i + 1))
                w = adj[v][i]
                if index[w] == -1:
                    index[w] = low[w] = counter
                    counter += 1
                    stack.append(w)
                    on_stack[w] = True
                    work.append((w, 0))
                elif on_stack[w]:
                    low[v] = min(low[v], index[w])
            else:
                if low[v] == index[v]:
                    while True:
                        w = stack.pop()
                        on_stack[w] = False
                        comp[w] = count
                        if w == v:
                            break
                    count += 1
                if work:
                    p = work[-1][0]
                    low[p] = min(low[p], low[v])
    return comp


def canon(labels):
    """Relabel every group by its smallest vertex, so partitions can be compared."""
    first, result = {}, []
    for v, label in enumerate(labels):
        first.setdefault(label, v)
        result.append(first[label])
    return result


def ref_dsu_states(n, ops):
    """Small-to-large set merging: an independent way to get the DSU states."""
    comp = list(range(n))
    members = {i: [i] for i in range(n)}
    count = n
    largest = 1 if n else 0
    states = []
    for u, v in ops:
        a, b = comp[u], comp[v]
        if a != b:
            if len(members[a]) < len(members[b]):
                a, b = b, a
            for x in members[b]:
                comp[x] = a
            members[a].extend(members.pop(b))
            count -= 1
            largest = max(largest, len(members[a]))
        states.append([count, largest])
    return states


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


# ----------------------------------------------------------------------- validators
# Every validator returns (ok, message).

def check_dsu(inp, out, expect=None):
    if 'states' not in out:
        return False, 'missing states'
    want = ref_dsu_states(inp['n'], inp['operations'])
    if out['states'] != want:
        return False, 'states differ from reference'
    if expect and out['states'] != expect['states']:
        return False, 'states differ from hand-derived expectation'
    return True, 'ok'


def check_mst(inp, out, expect=None):
    n, edges = inp['n'], inp['edges']
    for key in ('cost', 'edge_ids', 'components'):
        if key not in out:
            return False, 'missing ' + key
    ids = out['edge_ids']
    if not all(is_int(i) and 0 <= i < len(edges) for i in ids):
        return False, 'edge id out of range'
    if len(set(ids)) != len(ids):
        return False, 'repeated edge id'
    _, c = components_of(n, edges)
    if out['components'] != c:
        return False, f'components {out["components"]} != {c}'
    if len(ids) != n - c:
        return False, f'selected {len(ids)} edges, a spanning forest needs {n - c}'
    parent, find = make_finder(n)
    for i in ids:
        u, v, _ = edges[i]
        if u == v:
            return False, 'self-loop selected'
        a, b = find(u), find(v)
        if a == b:
            return False, 'selected edges contain a cycle'
        parent[a] = b
    total = sum(edges[i][2] for i in ids)
    if out['cost'] != total:
        return False, f'cost {out["cost"]} != sum of selected weights {total}'
    optimum = brute_mst_cost(n, edges) if len(edges) <= 12 else ref_kruskal_cost(n, edges)
    if total != optimum:
        return False, f'forest cost {total} is not optimal ({optimum})'
    if expect:
        if 'cost' in expect and out['cost'] != expect['cost']:
            return False, 'cost differs from hand-derived expectation'
        if 'components' in expect and out['components'] != expect['components']:
            return False, 'components differ from hand-derived expectation'
        if 'edge_ids_sorted' in expect and sorted(ids) != expect['edge_ids_sorted']:
            return False, 'edge ids differ from the unique optimum'
    return True, 'ok'


def check_scc(inp, out, expect=None):
    n, edges = inp['n'], inp['edges']
    if 'component' not in out or 'condensation' not in out:
        return False, 'missing component or condensation'
    lab = out['component']
    if len(lab) != n or not all(is_int(x) and x >= 0 for x in lab):
        return False, 'labels must be n non-negative integers'
    if canon(lab) != canon(tarjan_labels(n, edges)):
        return False, 'partition differs from the strongly connected components'
    if expect and 'partition' in expect:
        hand = [0] * n
        for group in expect['partition']:
            for v in group:
                hand[v] = min(group)
        if canon(lab) != hand:
            return False, 'partition differs from hand-derived expectation'
    pairs = [tuple(p) for p in out['condensation']]
    if any(len(p) != 2 for p in pairs):
        return False, 'condensation rows must be pairs'
    if len(set(pairs)) != len(pairs):
        return False, 'duplicate condensation pair'
    want = {(lab[e[0]], lab[e[1]]) for e in edges if lab[e[0]] != lab[e[1]]}
    if set(pairs) != want:
        return False, 'condensation is not exactly the set of cross-component pairs'
    return True, 'ok'


def check_topo(inp, out, expect=None):
    n, edges = inp['n'], inp['edges']
    if 'acyclic' not in out or 'order' not in out:
        return False, 'missing acyclic or order'
    acyclic, _ = kahn(n, edges)
    if out['acyclic'] is not acyclic:
        return False, f'acyclic should be {acyclic}'
    if expect and 'acyclic' in expect and expect['acyclic'] is not out['acyclic']:
        return False, 'acyclic differs from hand-derived expectation'
    order = out['order']
    if not acyclic:
        return (order == [], 'cyclic graph must return an empty order') if order != [] else (True, 'ok')
    if sorted(order) != list(range(n)):
        return False, 'order is not a permutation of all vertices'
    pos = {v: i for i, v in enumerate(order)}
    for e in edges:
        if pos[e[0]] >= pos[e[1]]:
            return False, f'edge {e[0]}->{e[1]} goes backwards'
    return True, 'ok'


def check_dag(inp, out, expect=None):
    n, edges, source = inp['n'], inp['edges'], inp['source']
    for key in ('acyclic', 'distance', 'parent_edge'):
        if key not in out:
            return False, 'missing ' + key
    acyclic, order = kahn(n, edges)
    if out['acyclic'] is not acyclic:
        return False, f'acyclic should be {acyclic}'
    if not acyclic:
        if out['distance'] != [] or out['parent_edge'] != []:
            return False, 'cyclic graph needs two empty arrays'
        return True, 'ok'
    dist_out, parent = out['distance'], out['parent_edge']
    if len(dist_out) != n or len(parent) != n:
        return False, 'arrays must have length n'
    adj = [[] for _ in range(n)]
    for e in edges:
        adj[e[0]].append((e[1], e[2]))
    dist = [None] * n
    dist[source] = 0
    for v in order:
        if dist[v] is None:
            continue
        for u, w in adj[v]:
            if dist[u] is None or dist[v] + w < dist[u]:
                dist[u] = dist[v] + w
    if dist_out != dist:
        return False, 'distances differ from the reference'
    if expect:
        if 'distance' in expect and dist_out != expect['distance']:
            return False, 'distance differs from hand-derived expectation'
        if 'parent_edge' in expect and parent != expect['parent_edge']:
            return False, 'parent_edge differs from the unique shortest-path tree'
    good = [False] * n
    good[source] = True
    for v in order:
        if v == source:
            if parent[v] != -1:
                return False, 'source parent_edge must be -1'
            continue
        if dist[v] is None:
            if parent[v] != -1:
                return False, 'unreachable vertex must have parent_edge -1'
            continue
        e = parent[v]
        if not is_int(e) or not 0 <= e < len(edges):
            return False, f'bad parent edge for vertex {v}'
        tail, head, w = edges[e]
        if head != v:
            return False, f'parent edge {e} does not end at vertex {v}'
        if dist[tail] is None or dist[tail] + w != dist[v]:
            return False, f'parent edge {e} is not on a shortest path to {v}'
        if not good[tail]:
            return False, f'parent chain of {v} does not reach the source'
        good[v] = True
    return True, 'ok'


VALIDATORS = {'dsu': check_dsu, 'kruskal': check_mst, 'prim': check_mst,
              'scc': check_scc, 'topo': check_topo, 'dag': check_dag}


def validate(inp, out, expect=None):
    if inp['task'] == 'ping':
        return out == {'status': 'ready'}, 'ping'
    return VALIDATORS[inp['task']](inp, out, expect)


# ------------------------------------------------------- hand-justified small cases

CASES = []


def case(name, inp, expect, why):
    CASES.append({'name': name, 'input': inp, 'expect': expect, 'why': why})


def both(name, n, edges, expect, why):
    case('kruskal_' + name, {'task': 'kruskal', 'n': n, 'edges': edges}, expect, why)
    case('prim_' + name, {'task': 'prim', 'n': n, 'edges': edges}, expect, why)


M = 10 ** 9

case('dsu_empty', {'task': 'dsu', 'n': 0, 'operations': []}, {'states': []},
     'n=0 has no operations, so there are no states.')
case('dsu_no_operations', {'task': 'dsu', 'n': 3, 'operations': []}, {'states': []},
     'No operations means no states; the initial state is not reported.')
case('dsu_self_and_repeat', {'task': 'dsu', 'n': 3, 'operations': [[0, 0], [0, 1], [1, 0], [2, 2]]},
     {'states': [[3, 1], [2, 2], [2, 2], [2, 2]]},
     '[0,0] changes nothing: 3 components, largest 1. [0,1] merges two vertices: 2 components, '
     'largest 2. [1,0] repeats it and [2,2] is a self-union: both leave [2,2].')
case('dsu_chain', {'task': 'dsu', 'n': 5, 'operations': [[0, 1], [2, 3], [1, 2], [3, 4]]},
     {'states': [[4, 2], [3, 2], [2, 4], [1, 5]]},
     '{0,1}: 4 comps, max 2. {2,3}: 3 comps, max 2. 1-2 joins them: {0,1,2,3}: 2 comps, max 4. '
     '3-4 adds vertex 4: 1 comp, max 5.')

both('empty', 0, [], {'cost': 0, 'components': 0, 'edge_ids_sorted': []},
     'n=0: no vertices, no components, nothing selected.')
both('isolates_loops_parallel', 5, [[0, 1, 5], [0, 1, 2], [1, 2, -3], [2, 2, -100], [3, 3, 1]],
     {'cost': -1, 'components': 3, 'edge_ids_sorted': [1, 2]},
     'Components {0,1,2}, {3} (only a loop) and {4} (isolated) = 3, so n-c = 2 edges. The loops '
     '(ids 3,4) are never chosen. Between 0 and 1 the cheaper parallel edge (id 1, weight 2) beats id 0; '
     'edge 2 (weight -3) is the only link to 2. Cost 2 + (-3) = -1.')
both('tied_triangle', 3, [[0, 1, 1], [1, 2, 1], [0, 2, 1]], {'cost': 2, 'components': 1},
     'All weights equal, so any 2 of the 3 edges are optimal: cost 2 (alternative answers expected).')
both('disconnected_negative', 6, [[0, 1, -5], [1, 0, -6], [2, 3, 4], [3, 4, -1], [2, 4, 2]],
     {'cost': -5, 'components': 3, 'edge_ids_sorted': [1, 3, 4]},
     'Components {0,1}, {2,3,4}, {5}. In {0,1} take the cheaper parallel edge (id 1, -6). In {2,3,4} '
     'drop the heaviest triangle edge (id 2, weight 4): keep ids 3 and 4, cost -1 + 2 = 1. Total -5.')
both('sum_above_32_bits', 4, [[0, 1, M], [1, 2, M], [2, 3, M]],
     {'cost': 3 * M, 'components': 1, 'edge_ids_sorted': [0, 1, 2]},
     'A path has a unique spanning tree; 3 * 10^9 = 3000000000 does not fit in 32 bits.')
both('sum_below_32_bits', 4, [[0, 1, -M], [1, 2, -M], [2, 3, -M]],
     {'cost': -3 * M, 'components': 1, 'edge_ids_sorted': [0, 1, 2]},
     'Unique tree again; -3000000000 does not fit in a signed 32-bit int.')

case('scc_empty', {'task': 'scc', 'n': 0, 'edges': []}, {'partition': []},
     'n=0: both output arrays are empty.')
case('scc_readme_example', {'task': 'scc', 'n': 4, 'edges': [[0, 1], [1, 0], [1, 2], [0, 2], [2, 3]]},
     {'partition': [[0, 1], [2], [3]]},
     '0<->1 is a cycle; 2 and 3 are single vertices. Edges 1->2 and 0->2 give ONE pair (A,{2}); 2->3 gives '
     '({2},{3}), so the condensation has exactly 2 pairs.')
case('scc_loops_duplicates', {'task': 'scc', 'n': 3, 'edges': [[0, 0], [0, 1], [0, 1], [1, 2], [2, 1]]},
     {'partition': [[0], [1, 2]]},
     'The loop on 0 is internal and dropped; the duplicated edge 0->1 gives one pair ({0},{1,2}); '
     '1<->2 is one SCC.')
case('scc_cycle_and_tail', {'task': 'scc', 'n': 5, 'edges': [[0, 1], [1, 2], [2, 0], [2, 3], [3, 4]]},
     {'partition': [[0, 1, 2], [3], [4]]},
     'Triangle 0->1->2->0 is one SCC; 3 and 4 follow it as singletons: condensation (T,{3}), ({3},{4}).')
case('scc_isolates', {'task': 'scc', 'n': 3, 'edges': []}, {'partition': [[0], [1], [2]]},
     'Isolated vertices are separate SCCs; no condensation pairs.')

case('topo_empty', {'task': 'topo', 'n': 0, 'edges': []}, {'acyclic': True}, 'n=0 is acyclic with order [].')
case('topo_diamond', {'task': 'topo', 'n': 4, 'edges': [[0, 1], [0, 2], [1, 3], [2, 3]]}, {'acyclic': True},
     'Diamond DAG: 0 first, 3 last, 1 and 2 in either order (two valid answers).')
case('topo_self_loop', {'task': 'topo', 'n': 2, 'edges': [[1, 1]]}, {'acyclic': False},
     'A self-loop is a directed cycle: acyclic=false and order=[].')
case('topo_cycle_in_2nd_component',
     {'task': 'topo', 'n': 5, 'edges': [[0, 1], [2, 3], [3, 4], [4, 2]]}, {'acyclic': False},
     'The first component is a DAG, the cycle 2->3->4->2 lies in another one: every component must be checked.')
case('topo_forward_edges_to_finished',
     {'task': 'topo', 'n': 4, 'edges': [[0, 1], [0, 2], [1, 2], [2, 3], [0, 3]]}, {'acyclic': True},
     'Edges 0->2 and 0->3 reach vertices that may already be finished; that is not a cycle.')

case('dag_singleton', {'task': 'dag', 'n': 1, 'source': 0, 'edges': []},
     {'acyclic': True, 'distance': [0], 'parent_edge': [-1]}, 'Only the source: distance 0, parent -1.')
case('dag_readme_example',
     {'task': 'dag', 'n': 5, 'source': 0, 'edges': [[0, 1, 3], [0, 2, 8], [1, 2, -7], [2, 3, 4]]},
     {'acyclic': True, 'distance': [0, 3, -4, 0, None], 'parent_edge': [-1, 0, 2, 3, -1]},
     'd(1)=3. To vertex 2: via edge 0 then 2 costs 3-7=-4, better than the direct 8. d(3)=-4+4=0. '
     'Vertex 4 has no incoming path: null and -1. The tree is unique, so parents are checked exactly.')
case('dag_unreachable_vs_minus_one',
     {'task': 'dag', 'n': 3, 'source': 0, 'edges': [[0, 1, -1]]},
     {'acyclic': True, 'distance': [0, -1, None], 'parent_edge': [-1, 0, -1]},
     'Vertex 1 is reachable with the finite distance -1; vertex 2 is unreachable and must be null, not -1.')
case('dag_cycle_unreachable_from_source',
     {'task': 'dag', 'n': 4, 'source': 0, 'edges': [[0, 1, 1], [2, 3, 1], [3, 2, 1]]},
     {'acyclic': False}, 'The cycle 2<->3 cannot be reached from 0, but the whole graph is checked: false, [], [].')
case('dag_self_loop', {'task': 'dag', 'n': 2, 'source': 0, 'edges': [[1, 1, 0]]}, {'acyclic': False},
     'A self-loop (even unreachable, even weight 0) makes the graph cyclic.')
case('dag_tied_and_parallel',
     {'task': 'dag', 'n': 3, 'source': 0, 'edges': [[0, 1, 2], [0, 1, 2], [1, 2, 1], [0, 2, 3]]},
     {'acyclic': True, 'distance': [0, 2, 3]},
     'Edges 0 and 1 are parallel with equal weight, edge 3 ties with 0->1->2: d=[0,2,3]. parent_edge[1] may be '
     '0 or 1 and parent_edge[2] may be 2 or 3: checked semantically.')
case('dag_source_in_the_middle',
     {'task': 'dag', 'n': 4, 'source': 2, 'edges': [[0, 1, 5], [2, 3, 1], [1, 2, 1]]},
     {'acyclic': True, 'distance': [None, None, 0, 1], 'parent_edge': [-1, -1, -1, 1]},
     'Vertices 0 and 1 precede the source and cannot be reached; only 2->3 (edge 1) is used.')
case('dag_positive_64_bit',
     {'task': 'dag', 'n': 4, 'source': 0, 'edges': [[0, 1, M], [1, 2, M], [2, 3, M]]},
     {'acyclic': True, 'distance': [0, M, 2 * M, 3 * M], 'parent_edge': [-1, 0, 1, 2]},
     'Distances 10^9, 2*10^9 and 3*10^9 overflow 32 bits; the tree of a path is unique.')
case('dag_negative_64_bit',
     {'task': 'dag', 'n': 4, 'source': 0, 'edges': [[0, 1, -M], [1, 2, -M], [2, 3, -M]]},
     {'acyclic': True, 'distance': [0, -M, -2 * M, -3 * M], 'parent_edge': [-1, 0, 1, 2]},
     'Same path with negative weights: -3000000000 needs 64 bits.')


# ------------------------------------------------------------------ validator selftest

def validator_selftest():
    """Each validator must accept an alternative valid answer and reject invalid witnesses."""
    tri = {'task': 'kruskal', 'n': 3, 'edges': [[0, 1, 1], [1, 2, 1], [0, 2, 1]]}
    loop = {'task': 'kruskal', 'n': 2, 'edges': [[0, 0, -5], [0, 1, 3]]}
    scc_in = {'task': 'scc', 'n': 3, 'edges': [[0, 1], [1, 0], [1, 2]]}
    topo_in = {'task': 'topo', 'n': 3, 'edges': [[0, 2], [1, 2]]}
    dag_in = {'task': 'dag', 'n': 3, 'source': 0, 'edges': [[0, 1, 2], [0, 1, 2], [1, 2, 1]]}
    t = []  # (label, validator, input, answer, should_accept)
    t += [('mst: optimal forest {0,1}', check_mst, tri, {'cost': 2, 'edge_ids': [0, 1], 'components': 1}, True),
          ('mst: ALTERNATIVE optimal forest {1,2}', check_mst, tri,
           {'cost': 2, 'edge_ids': [2, 1], 'components': 1}, True),
          ('mst: cycle (3 edges) rejected', check_mst, tri, {'cost': 3, 'edge_ids': [0, 1, 2], 'components': 1}, False),
          ('mst: repeated id rejected', check_mst, tri, {'cost': 2, 'edge_ids': [0, 0], 'components': 1}, False),
          ('mst: too few edges rejected', check_mst, tri, {'cost': 1, 'edge_ids': [0], 'components': 1}, False),
          ('mst: wrong cost rejected', check_mst, tri, {'cost': 5, 'edge_ids': [0, 1], 'components': 1}, False),
          ('mst: wrong component count rejected', check_mst, tri,
           {'cost': 2, 'edge_ids': [0, 1], 'components': 2}, False),
          ('mst: self-loop selected rejected', check_mst, loop,
           {'cost': -5, 'edge_ids': [0], 'components': 1}, False),
          ('mst: valid forest that is not optimal rejected', check_mst,
           {'task': 'kruskal', 'n': 3, 'edges': [[0, 1, 1], [1, 2, 1], [0, 2, 7]]},
           {'cost': 8, 'edge_ids': [0, 2], 'components': 1}, False)]
    t += [('scc: labels 7,7,3', check_scc, scc_in, {'component': [7, 7, 3], 'condensation': [[7, 3]]}, True),
          ('scc: ALTERNATIVE labels 0,0,1', check_scc, scc_in,
           {'component': [0, 0, 1], 'condensation': [[0, 1]]}, True),
          ('scc: SCC split rejected', check_scc, scc_in,
           {'component': [0, 1, 2], 'condensation': [[0, 1], [1, 0], [1, 2]]}, False),
          ('scc: wrongly merged rejected', check_scc, scc_in, {'component': [0, 0, 0], 'condensation': []}, False),
          ('scc: missing condensation pair rejected', check_scc, scc_in,
           {'component': [0, 0, 1], 'condensation': []}, False),
          ('scc: duplicate pair rejected', check_scc, scc_in,
           {'component': [0, 0, 1], 'condensation': [[0, 1], [0, 1]]}, False),
          ('scc: reversed pair rejected', check_scc, scc_in,
           {'component': [0, 0, 1], 'condensation': [[1, 0]]}, False)]
    t += [('topo: order 0,1,2', check_topo, topo_in, {'acyclic': True, 'order': [0, 1, 2]}, True),
          ('topo: ALTERNATIVE order 1,0,2', check_topo, topo_in, {'acyclic': True, 'order': [1, 0, 2]}, True),
          ('topo: backwards edge rejected', check_topo, topo_in, {'acyclic': True, 'order': [2, 0, 1]}, False),
          ('topo: not a permutation rejected', check_topo, topo_in, {'acyclic': True, 'order': [0, 0, 2]}, False),
          ('topo: false on a DAG rejected', check_topo, topo_in, {'acyclic': False, 'order': []}, False),
          ('topo: cyclic graph with non-empty order rejected', check_topo,
           {'task': 'topo', 'n': 2, 'edges': [[0, 1], [1, 0]]}, {'acyclic': False, 'order': [0, 1]}, False)]
    good = {'acyclic': True, 'distance': [0, 2, 3]}
    t += [('dag: parents [-1,0,2]', check_dag, dag_in, dict(good, parent_edge=[-1, 0, 2]), True),
          ('dag: ALTERNATIVE tied parents [-1,1,2]', check_dag, dag_in, dict(good, parent_edge=[-1, 1, 2]), True),
          ('dag: parent edge not ending at vertex rejected', check_dag, dag_in,
           dict(good, parent_edge=[-1, 2, 2]), False),
          ('dag: parent edge of another vertex rejected', check_dag, dag_in,
           dict(good, parent_edge=[-1, 0, 0]), False),
          ('dag: wrong distance rejected', check_dag, dag_in,
           {'acyclic': True, 'distance': [0, 2, 4], 'parent_edge': [-1, 0, 2]}, False),
          ('dag: source parent not -1 rejected', check_dag, dag_in, dict(good, parent_edge=[0, 0, 2]), False),
          ('dag: acyclic=false on a DAG rejected', check_dag, dag_in,
           {'acyclic': False, 'distance': [], 'parent_edge': []}, False),
          ('dag: unreachable vertex with a parent rejected', check_dag,
           {'task': 'dag', 'n': 2, 'source': 0, 'edges': []},
           {'acyclic': True, 'distance': [0, None], 'parent_edge': [-1, 0]}, False)]
    t += [('dsu: correct states', check_dsu, {'task': 'dsu', 'n': 3, 'operations': [[0, 1], [0, 1]]},
           {'states': [[2, 2], [2, 2]]}, True),
          ('dsu: repeated union counted twice rejected', check_dsu,
           {'task': 'dsu', 'n': 3, 'operations': [[0, 1], [0, 1]]}, {'states': [[2, 2], [1, 2]]}, False)]
    rows = []
    for label, fn, inp, answer, should in t:
        ok, msg = fn(inp, answer)
        rows.append({'label': label, 'accepted': ok, 'expected_accept': should,
                     'result': 'PASS' if ok == should else 'FAIL', 'message': msg})
    return rows


# ------------------------------------------------------------------- large / stress

def large_cases(seed=2026):
    rng = random.Random(seed)
    N, EDGES = 100000, 250000
    out = []

    def rnd_pairs(n, m):
        return [[rng.randrange(n), rng.randrange(n)] for _ in range(m)]

    def rnd_weighted(n, m):
        return [[rng.randrange(n), rng.randrange(n), rng.randint(-M, M)] for _ in range(m)]

    def forward_dag(n, m, weighted):
        rows = []
        while len(rows) < m:
            a, b = rng.randrange(n), rng.randrange(n)
            if a == b:
                continue
            u, v = min(a, b), max(a, b)
            rows.append([u, v, rng.randint(-M, M)] if weighted else [u, v])
        return rows

    chain = [[i, i + 1] for i in range(N - 1)]
    chain_w = [[i, i + 1, rng.randint(-M, M)] for i in range(N - 1)]
    out.append(('dsu_n100000_q250000_random',
                {'task': 'dsu', 'n': N, 'operations': rnd_pairs(N, EDGES)}))
    out.append(('dsu_n100000_chain_unions',
                {'task': 'dsu', 'n': N, 'operations': [[i, i + 1] for i in range(N - 1)]}))
    mst = rnd_weighted(N, EDGES)
    out.append(('kruskal_n100000_m250000_random', {'task': 'kruskal', 'n': N, 'edges': mst}))
    out.append(('prim_n100000_m250000_random', {'task': 'prim', 'n': N, 'edges': mst}))
    out.append(('kruskal_n100000_path_extreme_weights',
                {'task': 'kruskal', 'n': N, 'edges': [[i, i + 1, M] for i in range(N - 1)]}))
    out.append(('prim_n100000_path_extreme_weights',
                {'task': 'prim', 'n': N, 'edges': [[i, i + 1, -M] for i in range(N - 1)]}))
    out.append(('scc_n100000_m250000_random', {'task': 'scc', 'n': N, 'edges': rnd_pairs(N, EDGES)}))
    out.append(('scc_deep_chain_100000', {'task': 'scc', 'n': N, 'edges': chain}))
    out.append(('scc_one_cycle_100000', {'task': 'scc', 'n': N, 'edges': chain + [[N - 1, 0]]}))
    out.append(('topo_deep_chain_100000', {'task': 'topo', 'n': N, 'edges': chain}))
    out.append(('topo_deep_chain_with_back_edge', {'task': 'topo', 'n': N, 'edges': chain + [[N - 1, 0]]}))
    out.append(('topo_random_dag_m250000', {'task': 'topo', 'n': N, 'edges': forward_dag(N, EDGES, False)}))
    out.append(('dag_deep_chain_100000', {'task': 'dag', 'n': N, 'source': 0, 'edges': chain_w}))
    out.append(('dag_random_dag_m250000',
                {'task': 'dag', 'n': N, 'source': 0, 'edges': forward_dag(N, EDGES, True)}))
    cyc = forward_dag(N - 2, EDGES - 2, True) + [[N - 2, N - 1, 1], [N - 1, N - 2, 1]]
    out.append(('dag_m250000_cycle_unreachable_from_source', {'task': 'dag', 'n': N, 'source': 0, 'edges': cyc}))
    return out


def mixed_batch(seed=7):
    """A batch of mid-size requests of every task, used for the state-reset test."""
    rng = random.Random(seed)
    n, m = 2000, 6000
    pairs = [[rng.randrange(n), rng.randrange(n)] for _ in range(m)]
    weighted = [[rng.randrange(n), rng.randrange(n), rng.randint(-M, M)] for _ in range(m)]
    dag_edges = []
    while len(dag_edges) < m:
        a, b = rng.randrange(n), rng.randrange(n)
        if a != b:
            dag_edges.append([min(a, b), max(a, b), rng.randint(-1000, 1000)])
    return [
        {'task': 'ping'},
        {'task': 'dsu', 'n': n, 'operations': pairs},
        {'task': 'kruskal', 'n': n, 'edges': weighted},
        {'task': 'prim', 'n': n, 'edges': weighted},
        {'task': 'scc', 'n': n, 'edges': pairs},
        {'task': 'topo', 'n': n, 'edges': [e[:2] for e in dag_edges]},
        {'task': 'topo', 'n': n, 'edges': pairs},
        {'task': 'dag', 'n': n, 'source': 0, 'edges': dag_edges},
        {'task': 'dag', 'n': n, 'source': 5, 'edges': dag_edges + [[1999, 0, 1]]},
    ]


# -------------------------------------------------------------------------- runner

def run_one(command, inp):
    start = time.perf_counter()
    answer = launcher.execute(command, [inp])[0]
    return answer, time.perf_counter() - start


def md(text):
    return str(text).replace('|', '\\|').replace('\n', ' ')


def fmt(value, limit=260):
    text = json.dumps(value, separators=(',', ':'))
    return text if len(text) <= limit else text[:limit] + '...'


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--language', choices=launcher.LANGUAGES)
    parser.add_argument('--skip-large', action='store_true', help='skip the 100000-vertex cases')
    parser.add_argument('--report', action='store_true',
                        help='write tests/my_cases.jsonl, tests/actual_outputs.jsonl and tests/TESTS.md')
    args = parser.parse_args()

    command = launcher.build(launcher.select_language(args.language))
    failures = 0
    report = {'hand': [], 'selftest': [], 'large': [], 'reset': []}

    # 1. hand cases, one request per process-line batch
    answers = launcher.execute(command, [c['input'] for c in CASES])
    for c, answer in zip(CASES, answers):
        ok, msg = validate(c['input'], answer, c['expect'])
        print(('PASS' if ok else 'FAIL') + ' hand: ' + c['name'] + ('' if ok else ' - ' + msg))
        failures += not ok
        report['hand'].append({'case': c, 'answer': answer, 'ok': ok, 'msg': msg})

    # 2. validators accept alternative valid answers and reject invalid witnesses
    for row in validator_selftest():
        print(row['result'] + ' selftest: ' + row['label'])
        failures += row['result'] != 'PASS'
        report['selftest'].append(row)

    # 3. repeated mixed requests in a single process (state reset)
    batch = mixed_batch()
    shuffled = list(range(len(batch)))
    random.Random(1).shuffle(shuffled)
    requests = batch + [batch[i] for i in shuffled] + batch
    answers = launcher.execute(command, requests)
    reset_ok = True
    for index, (req, answer) in enumerate(zip(requests, answers)):
        ok, msg = validate(req, answer)
        if not ok:
            reset_ok = False
            print(f'FAIL state reset: request {index} ({req["task"]}): {msg}')
    first, third = answers[:len(batch)], answers[-len(batch):]
    if first != third:
        reset_ok = False
        print('FAIL state reset: the same request gave different answers in a later pass')
    second = answers[len(batch):2 * len(batch)]
    if any(second[k] != first[shuffled[k]] for k in range(len(batch))):
        reset_ok = False
        print('FAIL state reset: answers depend on the order of requests')
    print(('PASS' if reset_ok else 'FAIL') + f' state reset: {len(requests)} mixed requests in one process')
    failures += not reset_ok
    report['reset'].append({'requests': len(requests), 'ok': reset_ok})

    # 4. full-limit and deep-chain cases
    if not args.skip_large:
        costs = {}
        for name, inp in large_cases():
            try:
                answer, seconds = run_one(command, inp)
                ok, msg = validate(inp, answer)
            except Exception as error:  # timeout, crash, bad JSON ...
                answer, seconds, ok, msg = {}, 0.0, False, str(error)[:200]
            if ok and inp['task'] in ('kruskal', 'prim') and 'random' in name:
                costs.setdefault(id(inp['edges']), []).append(answer['cost'])
            print(('PASS' if ok else 'FAIL') + f' large: {name} ({seconds:.2f} s incl. JVM start)'
                  + ('' if ok else ' - ' + msg))
            failures += not ok
            m = len(inp.get('edges', inp.get('operations', [])))
            report['large'].append({'name': name, 'n': inp['n'], 'm': m, 'seconds': seconds,
                                    'ok': ok, 'msg': msg, 'task': inp['task']})
        for found in costs.values():
            agree = len(set(found)) == 1
            print(('PASS' if agree else 'FAIL') + ' large: Kruskal and Prim agree on the same 250000-edge graph')
            failures += not agree

    if args.report:
        write_report(report, command)
    print('\nALL CHECKS PASSED' if not failures else f'\n{failures} CHECK(S) FAILED')
    return 1 if failures else 0


def write_report(report, command):
    with open(TESTS / 'my_cases.jsonl', 'w', encoding='utf-8') as stream:
        for c in CASES:
            stream.write(json.dumps(c['input'], separators=(',', ':')) + '\n')
    with open(TESTS / 'actual_outputs.jsonl', 'w', encoding='utf-8') as stream:
        for row in report['hand']:
            stream.write(json.dumps(row['answer'], separators=(',', ':')) + '\n')
    lines = [
        '# Own tests',
        '',
        'Everything below was produced by running the program; reproduce it from the repository root:',
        '',
        '```sh',
        'python tools/run.py --check                      # 36 public cases + state reset',
        'python tests/check_cases.py --report             # this file, my_cases.jsonl, actual_outputs.jsonl',
        'python tools/run.py --input tests/my_cases.jsonl # raw actual output of the hand cases',
        'javac --release 17 -d .build/tests src/Java/*.java tests/RouteTest.java tests/Bench.java',
        'java -cp .build/tests RouteTest                  # route-helper calls',
        '```',
        '',
        'The files `my_cases.jsonl` (inputs) and `actual_outputs.jsonl` (actual outputs, same line order) ',
        'belong to the hand cases below. Expected values were derived by hand (column *Why*); every answer ',
        'is additionally checked semantically because many answers are not unique.',
        '',
        '## Hand-justified cases',
        '',
        '| # | Case | Input | Why this is the right answer | Actual output | Result |',
        '|---|------|-------|------------------------------|---------------|--------|',
    ]
    for i, row in enumerate(report['hand'], 1):
        c = row['case']
        lines.append(f'| {i} | `{c["name"]}` | `{md(fmt(c["input"], 200))}` | {md(c["why"])} | '
                     f'`{md(fmt(row["answer"], 200))}` | {"PASS" if row["ok"] else "FAIL"} |')
    lines += ['', '## Non-unique answers: valid alternatives accepted, invalid witnesses rejected', '',
              'The validators in `tests/check_cases.py` are fed hand-made answers directly (no program run).', '',
              '| Check | Validator verdict | Expected | Result |', '|---|---|---|---|']
    for row in report['selftest']:
        lines.append(f'| {md(row["label"])} | {"accepted" if row["accepted"] else "rejected"} | '
                     f'{"accepted" if row["expected_accept"] else "rejected"} | {row["result"]} |')
    lines += ['', '## Full limits and deep chains', '',
              'Inputs are generated with `random.Random(2026)` (see `large_cases` in `tests/check_cases.py`). '
              'Each request is run in its own process and checked by the validators (reference: Tarjan, Kahn, '
              'small-to-large merging, reference Kruskal). Time includes JVM start, JSON parsing and output.', '',
              '| Case | n | m or q | Time (s) | Result |', '|---|---:|---:|---:|---|']
    for row in report['large']:
        lines.append(f'| `{row["name"]}` | {row["n"]} | {row["m"]} | {row["seconds"]:.2f} | '
                     f'{"PASS" if row["ok"] else "FAIL " + md(row["msg"])} |')
    if not report['large']:
        lines.append('| (skipped with --skip-large) | | | | |')
    lines += ['', '## State reset', '',
              'A batch of 9 mid-size requests (ping, dsu, kruskal, prim, scc, 2 x topo, 2 x dag) is sent three '
              'times in one process: in the original order, in a shuffled order and again in the original order. '
              'Every answer is validated, and identical requests must produce identical answers.', '']
    for row in report['reset']:
        lines.append(f'* {row["requests"]} requests in one process: {"PASS" if row["ok"] else "FAIL"}')
    (TESTS / 'TESTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Wrote tests/my_cases.jsonl, tests/actual_outputs.jsonl, tests/TESTS.md')


if __name__ == '__main__':
    sys.exit(main())
