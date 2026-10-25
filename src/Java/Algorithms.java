import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.PriorityQueue;
import java.util.Set;

/**
 * Implement the six methods and add your route-reconstruction helper.
 * Input extraction is provided; all algorithm state belongs to the current request.
 * See ../../README.md for contracts and Java guidance.
 */
public final class Algorithms {
    static final class DSU {
        final int[] parent;
        final int[] size;
        int components;
        int largest;

        DSU(int n) {
            parent = new int[n];
            size = new int[n];
            for (int i = 0; i < n; i++) {
                parent[i] = i;
                size[i] = 1;
            }
            components = n;
            largest = n > 0 ? 1 : 0;
        }

        int find(int x) {
            int root = x;
            while (parent[root] != root) {
                root = parent[root];
            }
            while (parent[x] != root) {
                int next = parent[x];
                parent[x] = root;
                x = next;
            }
            return root;
        }

        boolean union(int a, int b) {
            a = find(a);
            b = find(b);
            if (a == b) {
                return false;
            }
            if (size[a] < size[b]) {
                int t = a;
                a = b;
                b = t;
            }
            parent[b] = a;
            size[a] += size[b];
            components--;
            if (size[a] > largest) {
                largest = size[a];
            }
            return true;
        }
    }
    /** DSU with path compression and union by size/rank; return states. */
    static Map<String, Object> dsu(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] operations = Input.operations(input);

        DSU d = new DSU(n);
        int[][] states = new int[operations.length][];
        for (int i = 0; i < operations.length; i++) {
            d.union(operations[i][0], operations[i][1]);
            states[i] = new int[]{d.components, d.largest};
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("states", states);
        return result;
    }

    /** Separate Kruskal implementation; return cost, edge_ids, components. */
    static Map<String, Object> kruskal(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);

        int m = edges.length;
        long[] keys = new long[m];
        for (int i = 0; i < m; i++) {
            keys[i] = ((edges[i][2] + 1_000_000_000L) << 18) | i;
        }
        Arrays.sort(keys);

        DSU d = new DSU(n);
        long cost = 0;
        List<Integer> ids = new ArrayList<>();
        for (long key : keys) {
            int id = (int) (key & ((1 << 18) - 1));
            if (d.union(edges[id][0], edges[id][1])) {
                cost += edges[id][2];
                ids.add(id);
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("cost", cost);
        result.put("edge_ids", ids);
        result.put("components", d.components);
        return result;
    }

    /** Separate Prim implementation; restart for every unvisited component. */
    static Map<String, Object> prim(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);

        int m = edges.length;
        int[] head = new int[n];
        Arrays.fill(head, -1);
        int[] next = new int[2 * m];
        int[] to = new int[2 * m];
        for (int i = 0; i < m; i++) {
            int u = edges[i][0];
            int v = edges[i][1];
            to[2 * i] = v;
            next[2 * i] = head[u];
            head[u] = 2 * i;
            to[2 * i + 1] = u;
            next[2 * i + 1] = head[v];
            head[v] = 2 * i + 1;
        }

        boolean[] visited = new boolean[n];
        PriorityQueue<long[]> heap = new PriorityQueue<>((a, b) -> Long.compare(a[0], b[0]));
        long cost = 0;
        int components = 0;
        List<Integer> ids = new ArrayList<>();

        for (int start = 0; start < n; start++) {
            if (visited[start]) {
                continue;
            }
            components++;
            visited[start] = true;
            for (int a = head[start]; a != -1; a = next[a]) {
                if (!visited[to[a]]) {
                    heap.add(new long[]{edges[a >> 1][2], a});
                }
            }
            while (!heap.isEmpty()) {
                long[] top = heap.poll();
                int arc = (int) top[1];
                int v = to[arc];
                if (visited[v]) {
                    continue;
                }
                visited[v] = true;
                cost += top[0];
                ids.add(arc >> 1);
                for (int a = head[v]; a != -1; a = next[a]) {
                    if (!visited[to[a]]) {
                        heap.add(new long[]{edges[a >> 1][2], a});
                    }
                }
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("cost", cost);
        result.put("edge_ids", ids);
        result.put("components", components);
        return result;
    }

    /** Kosaraju's two DFS passes; return component and exact condensation. */
    static Map<String, Object> scc(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);

        int m = edges.length;
        int[] head = new int[n];
        int[] thead = new int[n];
        Arrays.fill(head, -1);
        Arrays.fill(thead, -1);
        int[] next = new int[m];
        int[] tnext = new int[m];
        for (int i = 0; i < m; i++) {
            int u = edges[i][0];
            int v = edges[i][1];
            next[i] = head[u];
            head[u] = i;
            tnext[i] = thead[v];
            thead[v] = i;
        }

        boolean[] seen = new boolean[n];
        int[] cursor = head.clone();
        int[] stack = new int[n];
        int[] finish = new int[n];
        int finished = 0;
        for (int s = 0; s < n; s++) {
            if (seen[s]) {
                continue;
            }
            int sp = 0;
            stack[sp++] = s;
            seen[s] = true;
            while (sp > 0) {
                int v = stack[sp - 1];
                int a = cursor[v];
                if (a != -1) {
                    cursor[v] = next[a];
                    int u = edges[a][1];
                    if (!seen[u]) {
                        seen[u] = true;
                        stack[sp++] = u;
                    }
                } else {
                    finish[finished++] = v;
                    sp--;
                }
            }
        }

        int[] component = new int[n];
        Arrays.fill(component, -1);
        int label = 0;
        for (int k = n - 1; k >= 0; k--) {
            int s = finish[k];
            if (component[s] != -1) {
                continue;
            }
            int sp = 0;
            stack[sp++] = s;
            component[s] = label;
            while (sp > 0) {
                int v = stack[--sp];
                for (int a = thead[v]; a != -1; a = tnext[a]) {
                    int u = edges[a][0];
                    if (component[u] == -1) {
                        component[u] = label;
                        stack[sp++] = u;
                    }
                }
            }
            label++;
        }

        Set<Long> pairs = new HashSet<>();
        List<int[]> condensation = new ArrayList<>();
        for (int i = 0; i < m; i++) {
            int from = component[edges[i][0]];
            int target = component[edges[i][1]];
            if (from != target && pairs.add((long) from * n + target)) {
                condensation.add(new int[]{from, target});
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("component", component);
        result.put("condensation", condensation);
        return result;
    }

    /** Three-state DFS and reverse finish order; return acyclic and order. */
    static Map<String, Object> topo(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int[][] edges = Input.edges(input);

        int m = edges.length;
        int[] head = new int[n];
        Arrays.fill(head, -1);
        int[] next = new int[m];
        for (int i = 0; i < m; i++) {
            next[i] = head[edges[i][0]];
            head[edges[i][0]] = i;
        }

        int[] state = new int[n];
        int[] cursor = head.clone();
        int[] stack = new int[n];
        int[] finish = new int[n];
        int finished = 0;
        boolean acyclic = true;

        search:
        for (int s = 0; s < n; s++) {
            if (state[s] != 0) {
                continue;
            }
            int sp = 0;
            stack[sp++] = s;
            state[s] = 1;
            while (sp > 0) {
                int v = stack[sp - 1];
                int a = cursor[v];
                if (a != -1) {
                    cursor[v] = next[a];
                    int u = edges[a][1];
                    if (state[u] == 1) {
                        acyclic = false;
                        break search;
                    }
                    if (state[u] == 0) {
                        state[u] = 1;
                        stack[sp++] = u;
                    }
                } else {
                    state[v] = 2;
                    finish[finished++] = v;
                    sp--;
                }
            }
        }

        int[] order = new int[0];
        if (acyclic) {
            order = new int[n];
            for (int i = 0; i < n; i++) {
                order[i] = finish[n - 1 - i];
            }
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("acyclic", acyclic);
        result.put("order", order);
        return result;
    }

    /** Whole-graph cycle check and DAG relaxation; return acyclic, distance, parent_edge. */
    static Map<String, Object> dag(Map<String, Object> input) {
        int n = Input.vertexCount(input);
        int source = Input.source(input);
        int[][] edges = Input.edges(input);

        // Add and test your own route-reconstruction helper.
        int m = edges.length;
        int[] head = new int[n];
        Arrays.fill(head, -1);
        int[] next = new int[m];
        int[] indegree = new int[n];
        for (int i = 0; i < m; i++) {
            next[i] = head[edges[i][0]];
            head[edges[i][0]] = i;
            indegree[edges[i][1]]++;
        }

        int[] queue = new int[n];
        int qh = 0;
        int qt = 0;
        for (int v = 0; v < n; v++) {
            if (indegree[v] == 0) {
                queue[qt++] = v;
            }
        }
        while (qh < qt) {
            int v = queue[qh++];
            for (int a = head[v]; a != -1; a = next[a]) {
                int u = edges[a][1];
                if (--indegree[u] == 0) {
                    queue[qt++] = u;
                }
            }
        }

        Map<String, Object> result = new LinkedHashMap<>();
        if (qt < n) {   // не все вершины обработаны = есть цикл
            result.put("acyclic", false);
            result.put("distance", new Long[0]);
            result.put("parent_edge", new int[0]);
            return result;
        }

        long[] dist = new long[n];
        boolean[] reached = new boolean[n];
        int[] parentEdge = new int[n];
        Arrays.fill(parentEdge, -1);
        reached[source] = true;

        for (int k = 0; k < n; k++) {
            int v = queue[k];
            if (!reached[v]) {
                continue;
            }
            for (int a = head[v]; a != -1; a = next[a]) {
                int u = edges[a][1];
                long candidate = dist[v] + edges[a][2];
                if (!reached[u] || candidate < dist[u]) {
                    reached[u] = true;
                    dist[u] = candidate;
                    parentEdge[u] = a;
                }
            }
        }

        Long[] distance = new Long[n];
        for (int v = 0; v < n; v++) {
            distance[v] = reached[v] ? Long.valueOf(dist[v]) : null;
        }
        result.put("acyclic", true);
        result.put("distance", distance);
        result.put("parent_edge", parentEdge);
        return result;    }
    static List<Integer> route(int[] parentEdge, int[][] edges, int source, int target) {
        List<Integer> path = new ArrayList<>();
        int current = target;
        while (current != source) {
            int edgeId = parentEdge[current];
            if (edgeId == -1) {
                return new ArrayList<>();
            }
            path.add(current);
            current = edges[edgeId][0];
        }
        path.add(source);
        Collections.reverse(path);
        return path;
    }
}
