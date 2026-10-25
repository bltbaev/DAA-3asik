# Own tests

Everything below was produced by running the program; reproduce it from the repository root:

```sh
python tools/run.py --check                      # 36 public cases + state reset
python tests/check_cases.py --report             # this file, my_cases.jsonl, actual_outputs.jsonl
python tools/run.py --input tests/my_cases.jsonl # raw actual output of the hand cases
javac --release 17 -d .build/tests src/Java/*.java tests/RouteTest.java tests/Bench.java
java -cp .build/tests RouteTest                  # route-helper calls
```

The files `my_cases.jsonl` (inputs) and `actual_outputs.jsonl` (actual outputs, same line order) 
belong to the hand cases below. Expected values were derived by hand (column *Why*); every answer 
is additionally checked semantically because many answers are not unique.

## Hand-justified cases

| # | Case | Input | Why this is the right answer | Actual output | Result |
|---|------|-------|------------------------------|---------------|--------|
| 1 | `dsu_empty` | `{"task":"dsu","n":0,"operations":[]}` | n=0 has no operations, so there are no states. | `{"states":[]}` | PASS |
| 2 | `dsu_no_operations` | `{"task":"dsu","n":3,"operations":[]}` | No operations means no states; the initial state is not reported. | `{"states":[]}` | PASS |
| 3 | `dsu_self_and_repeat` | `{"task":"dsu","n":3,"operations":[[0,0],[0,1],[1,0],[2,2]]}` | [0,0] changes nothing: 3 components, largest 1. [0,1] merges two vertices: 2 components, largest 2. [1,0] repeats it and [2,2] is a self-union: both leave [2,2]. | `{"states":[[3,1],[2,2],[2,2],[2,2]]}` | PASS |
| 4 | `dsu_chain` | `{"task":"dsu","n":5,"operations":[[0,1],[2,3],[1,2],[3,4]]}` | {0,1}: 4 comps, max 2. {2,3}: 3 comps, max 2. 1-2 joins them: {0,1,2,3}: 2 comps, max 4. 3-4 adds vertex 4: 1 comp, max 5. | `{"states":[[4,2],[3,2],[2,4],[1,5]]}` | PASS |
| 5 | `kruskal_empty` | `{"task":"kruskal","n":0,"edges":[]}` | n=0: no vertices, no components, nothing selected. | `{"cost":0,"edge_ids":[],"components":0}` | PASS |
| 6 | `prim_empty` | `{"task":"prim","n":0,"edges":[]}` | n=0: no vertices, no components, nothing selected. | `{"cost":0,"edge_ids":[],"components":0}` | PASS |
| 7 | `kruskal_isolates_loops_parallel` | `{"task":"kruskal","n":5,"edges":[[0,1,5],[0,1,2],[1,2,-3],[2,2,-100],[3,3,1]]}` | Components {0,1,2}, {3} (only a loop) and {4} (isolated) = 3, so n-c = 2 edges. The loops (ids 3,4) are never chosen. Between 0 and 1 the cheaper parallel edge (id 1, weight 2) beats id 0; edge 2 (weight -3) is the only link to 2. Cost 2 + (-3) = -1. | `{"cost":-1,"edge_ids":[2,1],"components":3}` | PASS |
| 8 | `prim_isolates_loops_parallel` | `{"task":"prim","n":5,"edges":[[0,1,5],[0,1,2],[1,2,-3],[2,2,-100],[3,3,1]]}` | Components {0,1,2}, {3} (only a loop) and {4} (isolated) = 3, so n-c = 2 edges. The loops (ids 3,4) are never chosen. Between 0 and 1 the cheaper parallel edge (id 1, weight 2) beats id 0; edge 2 (weight -3) is the only link to 2. Cost 2 + (-3) = -1. | `{"cost":-1,"edge_ids":[1,2],"components":3}` | PASS |
| 9 | `kruskal_tied_triangle` | `{"task":"kruskal","n":3,"edges":[[0,1,1],[1,2,1],[0,2,1]]}` | All weights equal, so any 2 of the 3 edges are optimal: cost 2 (alternative answers expected). | `{"cost":2,"edge_ids":[0,1],"components":1}` | PASS |
| 10 | `prim_tied_triangle` | `{"task":"prim","n":3,"edges":[[0,1,1],[1,2,1],[0,2,1]]}` | All weights equal, so any 2 of the 3 edges are optimal: cost 2 (alternative answers expected). | `{"cost":2,"edge_ids":[2,0],"components":1}` | PASS |
| 11 | `kruskal_disconnected_negative` | `{"task":"kruskal","n":6,"edges":[[0,1,-5],[1,0,-6],[2,3,4],[3,4,-1],[2,4,2]]}` | Components {0,1}, {2,3,4}, {5}. In {0,1} take the cheaper parallel edge (id 1, -6). In {2,3,4} drop the heaviest triangle edge (id 2, weight 4): keep ids 3 and 4, cost -1 + 2 = 1. Total -5. | `{"cost":-5,"edge_ids":[1,3,4],"components":3}` | PASS |
| 12 | `prim_disconnected_negative` | `{"task":"prim","n":6,"edges":[[0,1,-5],[1,0,-6],[2,3,4],[3,4,-1],[2,4,2]]}` | Components {0,1}, {2,3,4}, {5}. In {0,1} take the cheaper parallel edge (id 1, -6). In {2,3,4} drop the heaviest triangle edge (id 2, weight 4): keep ids 3 and 4, cost -1 + 2 = 1. Total -5. | `{"cost":-5,"edge_ids":[1,4,3],"components":3}` | PASS |
| 13 | `kruskal_sum_above_32_bits` | `{"task":"kruskal","n":4,"edges":[[0,1,1000000000],[1,2,1000000000],[2,3,1000000000]]}` | A path has a unique spanning tree; 3 * 10^9 = 3000000000 does not fit in 32 bits. | `{"cost":3000000000,"edge_ids":[0,1,2],"components":1}` | PASS |
| 14 | `prim_sum_above_32_bits` | `{"task":"prim","n":4,"edges":[[0,1,1000000000],[1,2,1000000000],[2,3,1000000000]]}` | A path has a unique spanning tree; 3 * 10^9 = 3000000000 does not fit in 32 bits. | `{"cost":3000000000,"edge_ids":[0,1,2],"components":1}` | PASS |
| 15 | `kruskal_sum_below_32_bits` | `{"task":"kruskal","n":4,"edges":[[0,1,-1000000000],[1,2,-1000000000],[2,3,-1000000000]]}` | Unique tree again; -3000000000 does not fit in a signed 32-bit int. | `{"cost":-3000000000,"edge_ids":[0,1,2],"components":1}` | PASS |
| 16 | `prim_sum_below_32_bits` | `{"task":"prim","n":4,"edges":[[0,1,-1000000000],[1,2,-1000000000],[2,3,-1000000000]]}` | Unique tree again; -3000000000 does not fit in a signed 32-bit int. | `{"cost":-3000000000,"edge_ids":[0,1,2],"components":1}` | PASS |
| 17 | `scc_empty` | `{"task":"scc","n":0,"edges":[]}` | n=0: both output arrays are empty. | `{"component":[],"condensation":[]}` | PASS |
| 18 | `scc_readme_example` | `{"task":"scc","n":4,"edges":[[0,1],[1,0],[1,2],[0,2],[2,3]]}` | 0<->1 is a cycle; 2 and 3 are single vertices. Edges 1->2 and 0->2 give ONE pair (A,{2}); 2->3 gives ({2},{3}), so the condensation has exactly 2 pairs. | `{"component":[0,0,1,2],"condensation":[[0,1],[1,2]]}` | PASS |
| 19 | `scc_loops_duplicates` | `{"task":"scc","n":3,"edges":[[0,0],[0,1],[0,1],[1,2],[2,1]]}` | The loop on 0 is internal and dropped; the duplicated edge 0->1 gives one pair ({0},{1,2}); 1<->2 is one SCC. | `{"component":[0,1,1],"condensation":[[0,1]]}` | PASS |
| 20 | `scc_cycle_and_tail` | `{"task":"scc","n":5,"edges":[[0,1],[1,2],[2,0],[2,3],[3,4]]}` | Triangle 0->1->2->0 is one SCC; 3 and 4 follow it as singletons: condensation (T,{3}), ({3},{4}). | `{"component":[0,0,0,1,2],"condensation":[[0,1],[1,2]]}` | PASS |
| 21 | `scc_isolates` | `{"task":"scc","n":3,"edges":[]}` | Isolated vertices are separate SCCs; no condensation pairs. | `{"component":[2,1,0],"condensation":[]}` | PASS |
| 22 | `topo_empty` | `{"task":"topo","n":0,"edges":[]}` | n=0 is acyclic with order []. | `{"acyclic":true,"order":[]}` | PASS |
| 23 | `topo_diamond` | `{"task":"topo","n":4,"edges":[[0,1],[0,2],[1,3],[2,3]]}` | Diamond DAG: 0 first, 3 last, 1 and 2 in either order (two valid answers). | `{"acyclic":true,"order":[0,1,2,3]}` | PASS |
| 24 | `topo_self_loop` | `{"task":"topo","n":2,"edges":[[1,1]]}` | A self-loop is a directed cycle: acyclic=false and order=[]. | `{"acyclic":false,"order":[]}` | PASS |
| 25 | `topo_cycle_in_2nd_component` | `{"task":"topo","n":5,"edges":[[0,1],[2,3],[3,4],[4,2]]}` | The first component is a DAG, the cycle 2->3->4->2 lies in another one: every component must be checked. | `{"acyclic":false,"order":[]}` | PASS |
| 26 | `topo_forward_edges_to_finished` | `{"task":"topo","n":4,"edges":[[0,1],[0,2],[1,2],[2,3],[0,3]]}` | Edges 0->2 and 0->3 reach vertices that may already be finished; that is not a cycle. | `{"acyclic":true,"order":[0,1,2,3]}` | PASS |
| 27 | `dag_singleton` | `{"task":"dag","n":1,"source":0,"edges":[]}` | Only the source: distance 0, parent -1. | `{"acyclic":true,"distance":[0],"parent_edge":[-1]}` | PASS |
| 28 | `dag_readme_example` | `{"task":"dag","n":5,"source":0,"edges":[[0,1,3],[0,2,8],[1,2,-7],[2,3,4]]}` | d(1)=3. To vertex 2: via edge 0 then 2 costs 3-7=-4, better than the direct 8. d(3)=-4+4=0. Vertex 4 has no incoming path: null and -1. The tree is unique, so parents are checked exactly. | `{"acyclic":true,"distance":[0,3,-4,0,null],"parent_edge":[-1,0,2,3,-1]}` | PASS |
| 29 | `dag_unreachable_vs_minus_one` | `{"task":"dag","n":3,"source":0,"edges":[[0,1,-1]]}` | Vertex 1 is reachable with the finite distance -1; vertex 2 is unreachable and must be null, not -1. | `{"acyclic":true,"distance":[0,-1,null],"parent_edge":[-1,0,-1]}` | PASS |
| 30 | `dag_cycle_unreachable_from_source` | `{"task":"dag","n":4,"source":0,"edges":[[0,1,1],[2,3,1],[3,2,1]]}` | The cycle 2<->3 cannot be reached from 0, but the whole graph is checked: false, [], []. | `{"acyclic":false,"distance":[],"parent_edge":[]}` | PASS |
| 31 | `dag_self_loop` | `{"task":"dag","n":2,"source":0,"edges":[[1,1,0]]}` | A self-loop (even unreachable, even weight 0) makes the graph cyclic. | `{"acyclic":false,"distance":[],"parent_edge":[]}` | PASS |
| 32 | `dag_tied_and_parallel` | `{"task":"dag","n":3,"source":0,"edges":[[0,1,2],[0,1,2],[1,2,1],[0,2,3]]}` | Edges 0 and 1 are parallel with equal weight, edge 3 ties with 0->1->2: d=[0,2,3]. parent_edge[1] may be 0 or 1 and parent_edge[2] may be 2 or 3: checked semantically. | `{"acyclic":true,"distance":[0,2,3],"parent_edge":[-1,1,3]}` | PASS |
| 33 | `dag_source_in_the_middle` | `{"task":"dag","n":4,"source":2,"edges":[[0,1,5],[2,3,1],[1,2,1]]}` | Vertices 0 and 1 precede the source and cannot be reached; only 2->3 (edge 1) is used. | `{"acyclic":true,"distance":[null,null,0,1],"parent_edge":[-1,-1,-1,1]}` | PASS |
| 34 | `dag_positive_64_bit` | `{"task":"dag","n":4,"source":0,"edges":[[0,1,1000000000],[1,2,1000000000],[2,3,1000000000]]}` | Distances 10^9, 2*10^9 and 3*10^9 overflow 32 bits; the tree of a path is unique. | `{"acyclic":true,"distance":[0,1000000000,2000000000,3000000000],"parent_edge":[-1,0,1,2]}` | PASS |
| 35 | `dag_negative_64_bit` | `{"task":"dag","n":4,"source":0,"edges":[[0,1,-1000000000],[1,2,-1000000000],[2,3,-1000000000]]}` | Same path with negative weights: -3000000000 needs 64 bits. | `{"acyclic":true,"distance":[0,-1000000000,-2000000000,-3000000000],"parent_edge":[-1,0,1,2]}` | PASS |

## Non-unique answers: valid alternatives accepted, invalid witnesses rejected

The validators in `tests/check_cases.py` are fed hand-made answers directly (no program run).

| Check | Validator verdict | Expected | Result |
|---|---|---|---|
| mst: optimal forest {0,1} | accepted | accepted | PASS |
| mst: ALTERNATIVE optimal forest {1,2} | accepted | accepted | PASS |
| mst: cycle (3 edges) rejected | rejected | rejected | PASS |
| mst: repeated id rejected | rejected | rejected | PASS |
| mst: too few edges rejected | rejected | rejected | PASS |
| mst: wrong cost rejected | rejected | rejected | PASS |
| mst: wrong component count rejected | rejected | rejected | PASS |
| mst: self-loop selected rejected | rejected | rejected | PASS |
| mst: valid forest that is not optimal rejected | rejected | rejected | PASS |
| scc: labels 7,7,3 | accepted | accepted | PASS |
| scc: ALTERNATIVE labels 0,0,1 | accepted | accepted | PASS |
| scc: SCC split rejected | rejected | rejected | PASS |
| scc: wrongly merged rejected | rejected | rejected | PASS |
| scc: missing condensation pair rejected | rejected | rejected | PASS |
| scc: duplicate pair rejected | rejected | rejected | PASS |
| scc: reversed pair rejected | rejected | rejected | PASS |
| topo: order 0,1,2 | accepted | accepted | PASS |
| topo: ALTERNATIVE order 1,0,2 | accepted | accepted | PASS |
| topo: backwards edge rejected | rejected | rejected | PASS |
| topo: not a permutation rejected | rejected | rejected | PASS |
| topo: false on a DAG rejected | rejected | rejected | PASS |
| topo: cyclic graph with non-empty order rejected | rejected | rejected | PASS |
| dag: parents [-1,0,2] | accepted | accepted | PASS |
| dag: ALTERNATIVE tied parents [-1,1,2] | accepted | accepted | PASS |
| dag: parent edge not ending at vertex rejected | rejected | rejected | PASS |
| dag: parent edge of another vertex rejected | rejected | rejected | PASS |
| dag: wrong distance rejected | rejected | rejected | PASS |
| dag: source parent not -1 rejected | rejected | rejected | PASS |
| dag: acyclic=false on a DAG rejected | rejected | rejected | PASS |
| dag: unreachable vertex with a parent rejected | rejected | rejected | PASS |
| dsu: correct states | accepted | accepted | PASS |
| dsu: repeated union counted twice rejected | rejected | rejected | PASS |

## Full limits and deep chains

Inputs are generated with `random.Random(2026)` (see `large_cases` in `tests/check_cases.py`). Each request is run in its own process and checked by the validators (reference: Tarjan, Kahn, small-to-large merging, reference Kruskal). Time includes JVM start, JSON parsing and output.

| Case | n | m or q | Time (s) | Result |
|---|---:|---:|---:|---|
| `dsu_n100000_q250000_random` | 100000 | 250000 | 1.20 | PASS |
| `dsu_n100000_chain_unions` | 100000 | 99999 | 0.63 | PASS |
| `kruskal_n100000_m250000_random` | 100000 | 250000 | 0.62 | PASS |
| `prim_n100000_m250000_random` | 100000 | 250000 | 0.79 | PASS |
| `kruskal_n100000_path_extreme_weights` | 100000 | 99999 | 0.39 | PASS |
| `prim_n100000_path_extreme_weights` | 100000 | 99999 | 0.39 | PASS |
| `scc_n100000_m250000_random` | 100000 | 250000 | 0.60 | PASS |
| `scc_deep_chain_100000` | 100000 | 99999 | 0.53 | PASS |
| `scc_one_cycle_100000` | 100000 | 100000 | 0.39 | PASS |
| `topo_deep_chain_100000` | 100000 | 99999 | 0.37 | PASS |
| `topo_deep_chain_with_back_edge` | 100000 | 100000 | 0.33 | PASS |
| `topo_random_dag_m250000` | 100000 | 250000 | 0.53 | PASS |
| `dag_deep_chain_100000` | 100000 | 99999 | 0.46 | PASS |
| `dag_random_dag_m250000` | 100000 | 250000 | 0.66 | PASS |
| `dag_m250000_cycle_unreachable_from_source` | 100000 | 250000 | 0.48 | PASS |

## State reset

A batch of 9 mid-size requests (ping, dsu, kruskal, prim, scc, 2 x topo, 2 x dag) is sent three times in one process: in the original order, in a shuffled order and again in the original order. Every answer is validated, and identical requests must produce identical answers.

* 27 requests in one process: PASS
