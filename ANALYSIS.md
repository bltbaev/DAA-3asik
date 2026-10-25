# Assignment 3 — Graph Algorithms: Analysis

Language: **Java 17** (`submission.json` → `{"language":"Java"}`). All algorithms are in
`src/Java/Algorithms.java`; the supplied adapters (`Main`, `Input`, `Json`) are unchanged.

## 1. Build, run and test commands

Run everything from the repository root (on Windows PowerShell use `py -3` instead of `python`).

```sh
python tools/run.py --setup                      # launch check (ping)
python tools/run.py --check                      # 36 public cases + state reset (compiles with javac --release 17)
python tests/check_cases.py                      # own tests: hand cases, validator self-tests, full limits, state reset
python tests/check_cases.py --report             # same, and rewrites tests/TESTS.md, my_cases.jsonl, actual_outputs.jsonl
python tools/run.py --input tests/my_cases.jsonl # raw actual output of the hand-written cases

# route helper test and benchmark (not part of the submitted program; compiled separately)
javac --release 17 -d .build/tests src/Java/*.java tests/RouteTest.java tests/Bench.java
java -cp .build/tests RouteTest
java -cp .build/tests Bench 2026 5 3             # seed, timed runs per method, warm-up rounds
```

PowerShell does not expand `src/Java/*.java` for `javac`; use
`javac --release 17 -d .build/tests (Get-ChildItem src/Java/*.java) tests/RouteTest.java tests/Bench.java`.

## 2. Design decisions shared by all methods

* **Representation.** Graphs are stored as arrays: `head[v]` is the first arc of `v`, `next[a]` the following
  arc, and the arc index is the **original edge ID** (for undirected Prim the arcs `2i` and `2i+1` both belong
  to edge `i`, so the ID is `arc >> 1`). IDs are therefore never lost by sorting or adjacency building.
* **No recursion / deep DFS.** Every DFS (SCC passes, topological DFS) uses an explicit `int[] stack` plus a
  per-vertex cursor `cursor[v]` (the next unexamined arc of `v`). A vertex is pushed at most once, so the stack
  never exceeds `n` entries, and each arc is examined exactly once — a suspended vertex resumes where it stopped
  instead of rescanning its neighbours. A chain of 100 000 vertices therefore needs no call stack.
* **64-bit arithmetic.** Totals and distances are `long`. Kruskal packs `(w + 10^9) << 18 | id` into one `long`:
  `w + 10^9 ≤ 2·10^9 < 2^31`, so the key is below `2^49`, and `2^18 = 262 144 ≥ 250 000` edge IDs fit in the
  low bits. Sorting this one `long[]` orders edges by weight and keeps the ID.
* **State reset.** There are no static or instance fields. Every array, the `DSU` object, the heap and the sets
  are local variables created inside the method call, so nothing survives to the next request. This is checked
  by `python tools/run.py --check` (two complete public batches in one process) and by my own test that sends
  27 mixed requests in one process in original, shuffled and original order (identical requests must give
  identical answers).

## 3. Methods

### 3.1 `dsu`

*Steps.* `parent[i]=i`, `size[i]=1`, `components=n`, `largest = n>0 ? 1 : 0`. For each pair `[u,v]`:
`find` both roots (iterative, two-pass path compression); if different, attach the smaller tree to the larger,
add the sizes, `components--`, update `largest`; then append `[components, largest]`.

*Invariant.* After every operation `parent` is a forest whose trees are exactly the connected components of the
edges processed so far; `size[r]` is the number of vertices of the tree rooted at `r` (valid for roots);
`components` is the number of roots; `largest` is the maximum root size.

*Correctness.* Union by size/path compression only change tree shape, never the partition. Merging two roots
changes the partition exactly when the roots differ, which is when `components` drops by one; `largest` can only
change at the merged root, so keeping a running maximum is exact. Rank is not used, so sizes are maintained
explicitly.

*Boundary cases.* `n=0` → `states=[]`; no operations → `[]`; self-union and repeated union leave the partition
unchanged (`find(u)==find(v)`); the initial state is not reported.

*Complexity.* Time `O(n + q·α(n))` amortised; memory `O(n + q)` (arrays plus the returned states).

### 3.2 `kruskal`

*Steps.* Build the packed keys, sort them, scan in order, and accept the edge with `union(u,v)` returning
`true`. Add its weight to `cost` and its ID to `edge_ids`. `components` is the DSU component count at the end.

*Invariant.* Before each edge, the accepted edges form a forest that is contained in some minimum spanning forest
of the whole graph, and `DSU` components equal the components of that forest.

*Correctness.* An edge between two different trees is a lightest edge crossing the cut (tree, rest) among the edges
not yet examined — all lighter edges have already been accepted or rejected as joining already-connected vertices —
so by the cut property it can be added safely. An edge inside one tree would close a cycle and is skipped. At the end
every component is spanned, so the result has `n − c` edges.

*Boundary cases.* Self-loops are never accepted (`find(u)==find(u)`); parallel and tied edges are handled by the
order of keys; isolates stay as separate DSU components and are counted in `components`; negative weights need no
special treatment (shift only used for packing); `n=0` gives cost 0, no IDs, 0 components; sums exceed 32 bits
(`long`).

*Complexity.* Time `O(m log m + n + m·α(n))`; memory `O(n + m)`.

### 3.3 `prim`

*Steps.* Build undirected adjacency lists (`2m` arcs). For every unvisited vertex `s`: count a new component,
mark `s`, push its arcs into a min-heap keyed by weight. Pop the lightest arc; if its far end is already visited,
skip it (lazy deletion); otherwise visit it, add the weight and edge ID, push the new vertex's arcs. When the heap
is empty the component is complete and the loop continues with the next unvisited vertex.

*Invariant.* While a component is being built, the visited vertices of that component and the chosen edges form a
tree that is part of a minimum spanning tree of the component; the heap contains every arc leaving the tree
(plus stale arcs to visited vertices).

*Correctness.* The popped valid arc is a lightest edge crossing the cut (tree, rest of the component), so the cut
property applies. The heap becomes empty only when no edge leaves the tree, i.e. the whole component is visited.
Restarting from each unvisited vertex covers every component, and the number of restarts equals `components`.

*Boundary cases.* Isolated vertices and loop-only vertices give a component with no chosen edge; a loop arc leads
to an already visited vertex and is skipped; parallel edges compete in the heap and the cheaper one wins; negative
weights are fine because Prim only compares weights; `n=0` gives the empty result.

*Complexity.* Time `O(n + m log m)` (lazy heap, at most `2m` pushes, `log(2m) = O(log m)` each, equivalent to
`O(m log n)`); memory `O(n + m)` (arcs plus at most `2m` heap entries).

### 3.4 `scc` (Kosaraju)

*Steps.* (1) Build the graph and its transpose with arcs indexed by edge ID. (2) Iterative DFS on the original
graph; a vertex is appended to `finish` when its cursor is exhausted. (3) Process `finish` from last to first: an
unlabelled vertex starts a new label, and a traversal of the **transposed** graph labels everything reachable
that is still unlabelled. (4) For every edge with different labels add the pair `(label[u], label[v])` once,
using a `HashSet<Long>` with key `from·n + to`.

*Invariant.* The vertex with the latest finish time in the remaining graph belongs to a source component of the
condensation. Each transpose traversal from it reaches exactly the vertices of its component, because the
transposed edges leaving that component lead only to components that were already labelled.

*Correctness.* Standard Kosaraju argument: if `C → C'` is an edge between components, the maximum finish time in
`C` exceeds that in `C'`. Decreasing finish order therefore visits a source component of the remaining
condensation first, and in the transpose it cannot leave the component except into already labelled ones. The
condensation is complete because every edge is examined, and exact because internal edges (equal labels) are dropped
and duplicates are removed by the set.

*Boundary cases.* `n=0` gives two empty arrays; isolates become separate SCCs; self-loops and duplicate edges are
internal or removed as duplicates; labels are `0..k-1`, well inside the 64-bit range.

*Complexity.* `O(n + m)` expected time (hash set) and `O(n + m)` memory.

### 3.5 `topo`

*Steps.* Three states: 0 unvisited, 1 active (on the DFS stack), 2 finished. For each unvisited vertex start an
iterative DFS. An arc to a vertex in state 1 means a directed cycle (a self-loop is such an arc): stop, return
`acyclic=false`, `order=[]`. An arc to a state-0 vertex is pushed; an arc to a state-2 vertex is ignored. When a
vertex's arcs are exhausted it becomes state 2 and is appended to `finish`. If no cycle was found, `order` is
`finish` reversed.

*Invariant.* The states-1 vertices are exactly the DFS stack and form a path where each vertex has an arc to the
next. A finished vertex has all of its descendants finished.

*Correctness.* An arc to an active vertex closes a cycle with the stack path; conversely, every directed cycle
makes the DFS see such a back arc (the first visited vertex of the cycle is still active when the DFS reaches the
arc into it). For a DAG, every arc `u → v` has `v` finished before `u`, so reversing finish order puts `u` before `v`.
Every component is started, so cycles unreachable from other vertices are found.

*Boundary cases.* `n=0` → `acyclic=true`, `order=[]`; self-loop → cyclic; duplicate and parallel edges are
harmless; cycle in a later component is found; isolated vertices are included in `order`.

*Complexity.* `O(n + m)` time and memory.

### 3.6 `dag`

*Steps.* (1) Build adjacency and in-degrees. (2) Check the **whole** graph with Kahn's algorithm: process all
zero in-degree vertices; if fewer than `n` vertices are processed there is a cycle (also for self-loops and cycles
unreachable from the source) → `acyclic=false`, `distance=[]`, `parent_edge=[]`. (3) Otherwise take the Kahn queue as
topological order. Set `reached[source]=true`, `dist[source]=0`. For each vertex in that order, skip it if it is not
reached; otherwise relax every outgoing arc `v → u`: if `u` is not reached or `dist[v]+w < dist[u]`, set
`dist[u]`, `parent_edge[u] = edge ID`. (4) Unreached vertices are reported as `null` distance and `-1` parent.

*Invariant.* When vertex `v` is taken in topological order, `dist[v]` is already the shortest distance from the
source (all arcs into `v` come from earlier vertices and have been relaxed), and `parent_edge[v]` is an edge that
ends at `v` and attains it.

*Correctness.* In a DAG every path respects the topological order, so one pass of relaxations in that order is
enough, also with negative weights. `reached` (not a sentinel such as `-1` or `Long.MAX_VALUE`) separates
"unreachable" from a finite value, and no relaxation starts at an unreachable vertex, so no overflow can occur.
Following `parent_edge` from any reached vertex strictly goes back in topological order and ends at the source.

*Boundary cases.* `n=1` (source only); a cycle unreachable from the source; a self-loop; unreachable vertex whose
true distance would be `-1`-like; vertices numbered before the source; tied and parallel edges (strict `<` keeps the
first optimal edge met); distances up to `n·10^9 = 10^14` need `long`.

*Complexity.* `O(n + m)` time and memory.

### 3.7 Route helper `route(parentEdge, edges, source, target)`

Walk back from `target`: while the current vertex is not the source take `e = parentEdge[current]`; if `e == -1`
the target is unreachable and the helper returns an **empty list** (documented no-route result; the JSON `distance`
still uses `null`). Otherwise add the vertex and move to the tail `edges[e][0]`. At the source append it, then
reverse. The route to the source is `[source]`. Time and space `O(L)` for `L` vertices. Because `dag` returns edge
IDs, the helper can also report which edges were used.

Actual calls (output of `java -cp .build/tests RouteTest`, which also asserts that the route starts at the source,
ends at the target, that every edge goes from `route[k]` to `route[k+1]`, and that the sum of the edge weights equals
`distance[target]`):

| # | Case | Call | Result | Edge IDs | Total weight |
|---|------|------|--------|----------|--------------|
| 1 | Reachable target | `route([-1,0,2,3,-1], source=0, target=3)` on `0→1 (3), 0→2 (8), 1→2 (-7), 2→3 (4)` | `[0, 1, 2, 3]` | `[0, 2, 3]` | 0 = `distance[3]` |
| 2 | Source | `route([-1,0,2,3,-1], 0, 0)` | `[0]` | `[]` | 0 |
| 3 | Unreachable target | `route([-1,0,2,3,-1], 0, 4)` | `[]` (no route) | `[]` | `distance[4] = null` |
| 4a | Tied/parallel, target 3 | edges `0→1 (2), 0→1 (2), 0→2 (5), 1→2 (3), 2→3 (1)`, `parent_edge=[-1,1,2,4]` | `[0, 2, 3]` | `[2, 4]` | 6 = `distance[3]` (the route `0,1,2,3` also costs 6) |
| 4b | Parallel edges, target 1 | same graph | `[0, 1]` | `[1]` (edge 0 is equally good) | 2 = `distance[1]` |
| 5 | Negative edge | `0→1 (4), 0→2 (1), 2→1 (-2), 1→3 (1)` | `[0, 2, 1, 3]` | `[1, 2, 3]` | 0 = `distance[3]` |

## 4. Tests

Details, inputs, hand-derived justifications and actual outputs are in `tests/TESTS.md` (generated by
`python tests/check_cases.py --report`). Summary:

* **Hand-justified cases** (`tests/my_cases.jsonl`): empty and disconnected graphs, isolates, repeated and
  self unions, loops, parallel and tied edges, negative weights, totals beyond 32 bits, unreachable vertices,
  cycles outside the source's reach, a source in the middle of the vertex range.
* **Non-unique answers** are judged by validators written independently of the tested code: brute force over edge
  subsets for tiny graphs and a reference Kruskal for large ones (forest feasibility and optimum), Tarjan for
  SCC partitions and exact condensation, Kahn plus precedence check for topological orders, and a topological
  DP plus parent-chain check for DAG distances and witnesses. A self-test shows that the validators **accept
  alternative valid answers** (another optimal forest, relabelled SCCs, another order, another tied parent) and
  **reject invalid witnesses** (cycle, repeated ID, wrong cost, split/merged SCC, backward edge, parent edge that
  does not end at the vertex, wrong distance, ...).
* **Full limits and deep chains:** `n = 100 000` with `m = q = 250 000` for every task, chains of 100 000 vertices
  for `scc`, `topo` and `dag` (plus a chain closed into a cycle), a 250 000-edge DAG with a cycle unreachable from
  the source, and Kruskal versus Prim on the same random graph (equal cost).
* **State reset:** 27 mixed requests in one process (original, shuffled, original order).

All 36 public checks and all own tests (python tests/check_cases.py) passed
## 5. Benchmark: Kruskal versus Prim

**Graphs.** Random multigraphs (self-loops and parallel edges allowed), vertices uniform in `[0, n)`, weights
uniform in `[-10^9, 10^9]`, generated by `java.util.Random` with **seed 2026**. Each size uses **one** edge list
that is given to both methods. Sizes: `(n, m) = (1 000, 4 000)`, `(10 000, 40 000)`, `(100 000, 250 000)`.
Before timing, both results are checked: the selected edges form a forest without self-loops, the cost is the
sum of their weights, the component count matches, and Kruskal and Prim report the same cost and component count.

**Procedure.** 3 warm-up rounds per size (one Kruskal and one Prim call each), then 5 timed runs per method,
alternating Kruskal and Prim. Timer: `System.nanoTime()`. **Timing boundary (same for both methods):** one call
`Algorithms.kruskal(request)` / `Algorithms.prim(request)`, which includes converting the request lists into
`int[][]` (`Input.edges`), the algorithm and building the result map. Excluded: compilation, JVM start, graph
generation, JSON parsing and output.

**Command.** `java -cp .build/tests Bench 2026 5 3`

**Environment.** AMD Ryzen 5 7430U with Radeon Graphics,Windows 11,OpenJDK 25.0.1

**Results** 

| n | m | method | timings (ms) | median (ms) | cost | components |
|--:|--:|--------|--------------|------------:|-----:|-----------:|
| 1000 | 4000 | Kruskal | 2,51, 2,21, 1,56, 1,44, 1,20 | 1,56 | -698021646031 | 1 |
| 1000 | 4000 | Prim | 3,37, 1,78, 3,62, 1,81, 1,61 | 1,81 | -698021646031 | 1 |
| 10000 | 40000 | Kruskal | 14,78, 6,28, 7,22, 6,13, 6,13 | 6,28 | -7000369493780 | 3 |
| 10000 | 40000 | Prim | 26,65, 30,79, 18,34, 21,00, 21,00 | 21,00 | -7000369493780 | 3 |
| 100000 | 250000 | Kruskal | 52,35, 44,73, 40,90, 42,18, 49,86 | 44,73 | -53037068600098 | 698 |
| 100000 | 250000 | Prim | 213,71, 222,37, 213,15, 206,48, 200,67 | 213,15 | -53037068600098 | 698 |
Kruskal was faster than Prim at all three sizes. The medians were 1.56 ms (Kruskal) and 1.81 ms (Prim) for n = 1 000, m = 4 000; 6.28 ms and 21.00 ms for n = 10 000, m = 40 000; and 44.73 ms and 213.15 ms for n = 100 000, m = 250 000. The ratio of the medians (Prim / Kruskal) is therefore about 1.2, 3.3 and 4.8, so the gap grows with the size of the graph. Both methods returned the same cost and the same number of components at every size, as required. The timings of the five runs are fairly stable at the largest size (Kruskal 40.90-52.35 ms, Prim 200.67-222.37 ms), while at the smaller sizes a few runs are noticeably slower than the median (for example 14.78 ms for Kruskal and 26.65 ms for Prim at n = 10 000), which is typical JIT and garbage-collection noise.Typical explanation to adapt to your numbers (it is an argument, not a measurement): both methods are
`O(m log m)`, so asymptotically they are equal; the constants differ. Kruskal sorts one primitive `long[]`
(cache-friendly, no per-edge object) and then performs near-constant-time DSU operations. This Prim version is a lazy
heap: every edge may be pushed twice as a `long[2]` object, so it allocates up to `2m` small arrays and moves them
through a binary heap of size up to `2m`, and walking linked adjacency lists is less cache-friendly. Prim's
advantage appears for dense graphs with an indexed heap, which this benchmark does not test.

**Limitations.** One graph per size and one seed; five runs only; the JIT compiler and garbage collector add noise
(the first runs after warm-up can still be slower); no `-Xint`/`-Xmx` variation; results depend on the machine
and on the sparse random structure (average degree 8 and 5); the boundary includes `Input.edges` conversion and
the result map, which dilutes the pure algorithm difference.

## 6. Sources and AI assistance

* Course lecture notes and the assignment repository README (contracts, limits, examples).
* Standard algorithm descriptions: path compression and union by size (Tarjan's DSU analysis), Kruskal and Prim
  with the cut property, Kosaraju's SCC algorithm, DFS colouring for cycle detection, Kahn's algorithm
  (used here only as the cycle check and topological order in `dag`, and as a reference in tests), Tarjan's SCC
  algorithm (used only as a test reference).
* **AI assistance:** I used Claude to help understand the Java implementation, the test and benchmark
  programs and the first draft of this document. 