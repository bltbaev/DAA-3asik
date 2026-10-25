import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * Kruskal vs Prim on the SAME random graphs at three sizes.
 * Build and run from the repository root:
 *   javac --release 17 -d .build/tests src/Java/*.java tests/RouteTest.java tests/Bench.java
 *   java -cp .build/tests Bench            # seed 2026, 5 timed runs, 3 warm-up rounds
 *   java -cp .build/tests Bench 2026 7 3   # seed, timed runs per method, warm-up rounds
 *
 * Timing boundary (identical for both methods): one call Algorithms.kruskal(request) or
 * Algorithms.prim(request). It INCLUDES converting the request lists to int[][] (Input.edges),
 * the algorithm and building the result map. It EXCLUDES compilation, JVM start, graph generation,
 * JSON parsing and JSON output. Timer: System.nanoTime(). Kruskal and Prim runs alternate.
 */
public final class Bench {
    private static final long W = 1_000_000_000L;

    private static List<Object> graph(Random random, int n, int m) {
        List<Object> edges = new ArrayList<>(m);
        for (int i = 0; i < m; i++) {
            List<Object> row = new ArrayList<>(3);
            row.add((long) random.nextInt(n));
            row.add((long) random.nextInt(n));
            row.add((long) (random.nextDouble() * (2 * W + 1)) - W); // weight in [-1e9, 1e9]
            edges.add(row);
        }
        return edges;
    }

    private static Map<String, Object> request(String task, int n, List<Object> edges) {
        Map<String, Object> input = new LinkedHashMap<>();
        input.put("task", task);
        input.put("n", (long) n);
        input.put("edges", edges);
        return input;
    }

    @SuppressWarnings("unchecked")
    private static void verifyForest(int n, List<Object> edges, Map<String, Object> result) {
        int[] parent = new int[n];
        for (int i = 0; i < n; i++) {
            parent[i] = i;
        }
        List<Integer> ids = (List<Integer>) result.get("edge_ids");
        long sum = 0;
        for (int id : ids) {
            List<Object> e = (List<Object>) edges.get(id);
            int u = find(parent, (int) (long) (Long) e.get(0));
            int v = find(parent, (int) (long) (Long) e.get(1));
            if (u == v) {
                throw new IllegalStateException("selected edges contain a cycle or a self-loop");
            }
            parent[u] = v;
            sum += (Long) e.get(2);
        }
        int components = 0;
        for (int i = 0; i < n; i++) {
            if (find(parent, i) == i) {
                components++;
            }
        }
        if (sum != (Long) result.get("cost")) {
            throw new IllegalStateException("cost is not the sum of the selected weights");
        }
        if (components != (Integer) result.get("components")) {
            throw new IllegalStateException("component count does not match the selected forest");
        }
    }

    private static int find(int[] parent, int x) {
        while (parent[x] != x) {
            parent[x] = parent[parent[x]];
            x = parent[x];
        }
        return x;
    }

    private static double median(double[] values) {
        double[] sorted = values.clone();
        Arrays.sort(sorted);
        int k = sorted.length;
        return k % 2 == 1 ? sorted[k / 2] : (sorted[k / 2 - 1] + sorted[k / 2]) / 2.0;
    }

    private static double time(Map<String, Object> request, boolean kruskal) {
        long start = System.nanoTime();
        Map<String, Object> result = kruskal ? Algorithms.kruskal(request) : Algorithms.prim(request);
        long elapsed = System.nanoTime() - start;
        if (result.get("cost") == null) {
            throw new IllegalStateException("no result");
        }
        return elapsed / 1e6;
    }

    public static void main(String[] args) {
        long seed = args.length > 0 ? Long.parseLong(args[0]) : 2026L;
        int runs = args.length > 1 ? Integer.parseInt(args[1]) : 5;
        int warmup = args.length > 2 ? Integer.parseInt(args[2]) : 3;
        int[][] sizes = {{1_000, 4_000}, {10_000, 40_000}, {100_000, 250_000}};

        System.out.println("Environment: java " + System.getProperty("java.version") + ", "
                + System.getProperty("os.name") + " " + System.getProperty("os.arch") + ", "
                + Runtime.getRuntime().availableProcessors() + " logical CPUs, max heap "
                + Runtime.getRuntime().maxMemory() / (1024 * 1024) + " MiB");
        System.out.println("Seed " + seed + ", " + runs + " timed runs per method and size, "
                + warmup + " warm-up rounds per size, timer System.nanoTime(), times in ms");
        System.out.println();
        System.out.println("| n | m | method | timings (ms) | median (ms) | cost | components |");
        System.out.println("|--:|--:|--------|--------------|------------:|-----:|-----------:|");

        Random random = new Random(seed);
        for (int[] size : sizes) {
            int n = size[0];
            int m = size[1];
            List<Object> edges = graph(random, n, m);
            Map<String, Object> kruskalRequest = request("kruskal", n, edges);
            Map<String, Object> primRequest = request("prim", n, edges); // same edge list object

            Map<String, Object> k = Algorithms.kruskal(kruskalRequest);
            Map<String, Object> p = Algorithms.prim(primRequest);
            verifyForest(n, edges, k);
            verifyForest(n, edges, p);
            if (!k.get("cost").equals(p.get("cost")) || !k.get("components").equals(p.get("components"))) {
                throw new IllegalStateException("Kruskal and Prim disagree on n=" + n);
            }

            for (int i = 0; i < warmup; i++) {
                time(kruskalRequest, true);
                time(primRequest, false);
            }
            double[] kt = new double[runs];
            double[] pt = new double[runs];
            for (int i = 0; i < runs; i++) {
                kt[i] = time(kruskalRequest, true);
                pt[i] = time(primRequest, false);
            }
            row(n, m, "Kruskal", kt, k);
            row(n, m, "Prim", pt, p);
        }
    }

    private static void row(int n, int m, String name, double[] timings, Map<String, Object> result) {
        StringBuilder list = new StringBuilder();
        for (int i = 0; i < timings.length; i++) {
            list.append(i == 0 ? "" : ", ").append(String.format("%.2f", timings[i]));
        }
        System.out.println("| " + n + " | " + m + " | " + name + " | " + list + " | "
                + String.format("%.2f", median(timings)) + " | " + result.get("cost") + " | "
                + result.get("components") + " |");
    }
}
