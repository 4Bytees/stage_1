import time
import sys
import tracemalloc
import random
import matplotlib.pyplot as plt
import numpy as np

# --- 1. GRAPH REPRESENTATIONS ---

class AdjacencyMatrixGraph:
    def __init__(self, num_nodes):
        self.num_nodes = num_nodes
        self.matrix = [[0] * num_nodes for _ in range(num_nodes)]

    def add_edge(self, u, v):
        self.matrix[u][v] = 1
        self.matrix[v][u] = 1

    def is_connected(self, u, v):
        return self.matrix[u][v] == 1

    def get_neighbors(self, u):
        return [v for v in range(self.num_nodes) if self.matrix[u][v] == 1]


class AdjacencyListGraph:
    def __init__(self, num_nodes):
        self.num_nodes = num_nodes
        self.adj_list = {i: set() for i in range(num_nodes)}

    def add_edge(self, u, v):
        self.adj_list[u].add(v)
        self.adj_list[v].add(u)

    def is_connected(self, u, v):
        return v in self.adj_list[u]

    def get_neighbors(self, u):
        return list(self.adj_list[u])

# --- 2. SYNTHETIC GRAPH GENERATORS ---

def generate_random_edges(num_nodes, density):
    edges = []
    max_edges = (num_nodes * (num_nodes - 1)) // 2
    num_edges = int(max_edges * density)
    
    # Fast sampling for sparse / dense
    sampled_pairs = set()
    while len(sampled_pairs) < num_edges:
        u = random.randint(0, num_nodes - 1)
        v = random.randint(0, num_nodes - 1)
        if u != v:
            pair = (min(u, v), max(u, v))
            sampled_pairs.add(pair)
            
    return list(sampled_pairs)

# --- 3. BENCHMARKING SUITE ---

def measure_memory_and_queries(node_counts, densities):
    results = {
        'nodes': node_counts,
        'sparse': {'mat_mem': [], 'list_mem': [], 'mat_conn': [], 'list_conn': [], 'mat_neigh': [], 'list_neigh': []},
        'dense':  {'mat_mem': [], 'list_mem': [], 'mat_conn': [], 'list_conn': [], 'mat_neigh': [], 'list_neigh': []}
    }

    num_trials = 500  # Number of query repetitions for statistically sound timing

    for p_name, density in [('sparse', densities['sparse']), ('dense', densities['dense'])]:
        print(f"\n--- Benchmarking {p_name.upper()} Graphs (Density p = {density}) ---")
        
        for n in node_counts:
            print(f"Processing Graph with N = {n} nodes...")
            edges = generate_random_edges(n, density)

            # --- Adjacency Matrix Measurement ---
            tracemalloc.start()
            mat_graph = AdjacencyMatrixGraph(n)
            for u, v in edges:
                mat_graph.add_edge(u, v)
            _, peak_mat_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Query: Is Connected
            start = time.perf_counter()
            for _ in range(num_trials):
                u, v = random.randint(0, n-1), random.randint(0, n-1)
                _ = mat_graph.is_connected(u, v)
            time_mat_conn = (time.perf_counter() - start) / num_trials

            # Query: Get Neighbors
            start = time.perf_counter()
            for _ in range(num_trials):
                u = random.randint(0, n-1)
                _ = mat_graph.get_neighbors(u)
            time_mat_neigh = (time.perf_counter() - start) / num_trials


            # --- Adjacency List Measurement ---
            tracemalloc.start()
            list_graph = AdjacencyListGraph(n)
            for u, v in edges:
                list_graph.add_edge(u, v)
            _, peak_list_mem = tracemalloc.get_traced_memory()
            tracemalloc.stop()

            # Query: Is Connected
            start = time.perf_counter()
            for _ in range(num_trials):
                u, v = random.randint(0, n-1), random.randint(0, n-1)
                _ = list_graph.is_connected(u, v)
            time_list_conn = (time.perf_counter() - start) / num_trials

            # Query: Get Neighbors
            start = time.perf_counter()
            for _ in range(num_trials):
                u = random.randint(0, n-1)
                _ = list_graph.get_neighbors(u)
            time_list_neigh = (time.perf_counter() - start) / num_trials

            # Append Metrics (Memory in MB, Time in microseconds)
            results[p_name]['mat_mem'].append(peak_mat_mem / (1024 * 1024))
            results[p_name]['list_mem'].append(peak_list_mem / (1024 * 1024))
            results[p_name]['mat_conn'].append(time_mat_conn * 1e6)
            results[p_name]['list_conn'].append(time_list_conn * 1e6)
            results[p_name]['mat_neigh'].append(time_mat_neigh * 1e6)
            results[p_name]['list_neigh'].append(time_list_neigh * 1e6)

    return results

# --- 4. PLOTTING FUNCTION ---

def plot_benchmark_results(results):
    nodes = results['nodes']

    # Figure 1: Memory Footprint (Sparse vs Dense)
    plt.figure(figsize=(10, 5))
    plt.plot(nodes, results['sparse']['mat_mem'], 'r-o', label='Adj Matrix (Sparse)')
    plt.plot(nodes, results['sparse']['list_mem'], 'b-o', label='Adj List (Sparse)')
    plt.plot(nodes, results['dense']['mat_mem'], 'r--s', label='Adj Matrix (Dense)')
    plt.plot(nodes, results['dense']['list_mem'], 'b--s', label='Adj List (Dense)')
    plt.title('Memory Footprint vs Graph Size (N)', fontsize=13)
    plt.xlabel('Number of Nodes (N)', fontsize=11)
    plt.ylabel('Peak RAM Usage (MB)', fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig('fig_memory_usage.png', dpi=300)
    plt.close() 

    # Figure 2: Query Execution Time - Is Connected
    plt.figure(figsize=(10, 5))
    plt.plot(nodes, results['sparse']['mat_conn'], 'r-o', label='Adj Matrix (Sparse)')
    plt.plot(nodes, results['sparse']['list_conn'], 'b-o', label='Adj List (Sparse)')
    plt.plot(nodes, results['dense']['mat_conn'], 'r--s', label='Adj Matrix (Dense)')
    plt.plot(nodes, results['dense']['list_conn'], 'b--s', label='Adj List (Dense)')
    plt.title('Edge Connection Check Latency (is_connected)', fontsize=13)
    plt.xlabel('Number of Nodes (N)', fontsize=11)
    plt.ylabel('Execution Time (microseconds)', fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig('fig_is_connected_time.png', dpi=300)
    plt.close()  

    # Figure 3: Query Execution Time - Get Neighbors
    plt.figure(figsize=(10, 5))
    plt.plot(nodes, results['sparse']['mat_neigh'], 'r-o', label='Adj Matrix (Sparse)')
    plt.plot(nodes, results['sparse']['list_neigh'], 'b-o', label='Adj List (Sparse)')
    plt.plot(nodes, results['dense']['mat_neigh'], 'r--s', label='Adj Matrix (Dense)')
    plt.plot(nodes, results['dense']['list_neigh'], 'b--s', label='Adj List (Dense)')
    plt.title('Neighbor Discovery Latency (get_neighbors)', fontsize=13)
    plt.xlabel('Number of Nodes (N)', fontsize=11)
    plt.ylabel('Execution Time (microseconds)', fontsize=11)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig('fig_get_neighbors_time.png', dpi=300)
    plt.close()  

    print("\nBenchmark completed. Figures saved successfully:")
    print(" - fig_memory_usage.png")
    print(" - fig_is_connected_time.png")
    print(" - fig_get_neighbors_time.png")

    print("\nBenchmark completed. Figures saved as:")
    print(" - fig_memory_usage.png")
    print(" - fig_is_connected_time.png")
    print(" - fig_get_neighbors_time.png")

if __name__ == '__main__':
    # Configuration
    node_sizes = [200, 500, 1000, 1500, 2000, 2500, 3000]
    graph_densities = {'sparse': 0.01, 'dense': 0.25}
    
    metrics = measure_memory_and_queries(node_sizes, graph_densities)
    plot_benchmark_results(metrics)