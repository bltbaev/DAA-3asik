import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Calls Algorithms.dag(...) and the route helper Algorithms.route(...) directly.
 * Build and run from the repository root:
 *   javac --release 17 -d .build/tests src/Java/*.java tests/RouteTest.java tests/Bench.java
 *   java -cp .build/tests RouteTest
 * The program exits with code 1 if any check fails.
 */
public final class RouteTest {
    private static int failures = 0;

    private static Map<String, Object> request(int n, int source, long[][] edges) {
        List<Object> rows = new ArrayList<>();
        for (long[] e : edges) {
            List<Object> row = new ArrayList<>();
            for (long x : e) {
                row.add(x);
            }
            rows.add(row);
        }
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("task", "dag");
        input.put("n", (long) n);
        input.put("source", (long) source);
        input.put("edges", rows);
        return input;
    }

    private static void expect(boolean condition, String message) {
        if (!condition) {
            failures++;
            System.out.println("  FAIL: " + message);
        }
    }

    /** Calls the helper, prints the result and checks direction, edge IDs and total weight. */
    private static void call(String label, int n, int source, long[][] edges, int target,
                             List<Integer> expectedRoute, boolean uniqueRoute) {
        Map<String, Object> result = Algorithms.dag(request(n, source, edges));
        int[] parent = (int[]) result.get("parent_edge");
        Long[] distance = (Long[]) result.get("distance");
        int[][] edgeRows = new int[edges.length][];
        for (int i = 0; i < edges.length; i++) {
            edgeRows[i] = new int[]{(int) edges[i][0], (int) edges[i][1], (int) edges[i][2]};
        }

        List<Integer> route = Algorithms.route(parent, edgeRows, source, target);
        List<Integer> ids = new ArrayList<>();
        long total = 0;
        for (int v = target; route.size() > 0 && v != source; v = edgeRows[parent[v]][0]) {
            ids.add(0, parent[v]);
            total += edgeRows[parent[v]][2];
        }

        System.out.println(label);
        System.out.println("  route(parent_edge=" + java.util.Arrays.toString(parent) + ", source=" + source
                + ", target=" + target + ") = " + route);
        System.out.println("  selected edge IDs = " + ids + ", total weight = " + total
                + ", distance[target] = " + distance[target]);

        if (distance[target] == null) {
            expect(route.isEmpty(), "unreachable target must give an empty list");
            return;
        }
        expect(!route.isEmpty() && route.get(0) == source, "route must start at the source");
        expect(route.get(route.size() - 1) == target, "route must end at the target");
        expect(ids.size() == route.size() - 1, "one edge per step");
        for (int k = 0; k < ids.size(); k++) {      // direction: edge k goes route[k] -> route[k+1]
            int[] e = edgeRows[ids.get(k)];
            expect(e[0] == route.get(k) && e[1] == route.get(k + 1), "edge " + ids.get(k) + " has wrong direction");
        }
        expect(total == distance[target], "total weight of the route equals distance[target]");
        if (uniqueRoute) {
            expect(route.equals(expectedRoute), "expected route " + expectedRoute);
        }
    }

    public static void main(String[] args) {
        long[][] example = {{0, 1, 3}, {0, 2, 8}, {1, 2, -7}, {2, 3, 4}};
        call("1. Reachable target (README example, vertex 3)", 5, 0, example, 3, List.of(0, 1, 2, 3), true);
        call("2. Route to the source itself", 5, 0, example, 0, List.of(0), true);
        call("3. Unreachable target (vertex 4 has no incoming path)", 5, 0, example, 4, List.of(), true);

        // Parallel edges 0 and 1 are tied; 0->2 (5) ties with 0->1->2 (2+3).
        long[][] tied = {{0, 1, 2}, {0, 1, 2}, {0, 2, 5}, {1, 2, 3}, {2, 3, 1}};
        call("4a. Tied and parallel edges (target 3: either of two equal routes is valid)",
                4, 0, tied, 3, List.of(), false);
        call("4b. Tied and parallel edges (target 1: parallel edges 0 and 1 give the same route)",
                4, 0, tied, 1, List.of(0, 1), true);

        // Negative weights and a target that is not the last vertex.
        long[][] negative = {{0, 1, 4}, {0, 2, 1}, {2, 1, -2}, {1, 3, 1}};
        call("5. Negative edge makes the longer route cheaper (0->2->1->3 beats 0->1->3)",
                4, 0, negative, 3, List.of(0, 2, 1, 3), true);

        System.out.println(failures == 0 ? "\nALL ROUTE CHECKS PASSED" : "\n" + failures + " ROUTE CHECK(S) FAILED");
        System.exit(failures == 0 ? 0 : 1);
    }
}
