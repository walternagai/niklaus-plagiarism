"""
Clustering Module

Detect clusters of similar files using hierarchical and graph-based methods.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import pdist, squareform
import networkx as nx


class ClusterDetector:
    """Detect clusters of similar files using various algorithms."""
    
    def hierarchical_clustering(self, 
                              similarity_matrix: np.ndarray, 
                              files: List[str],
                              threshold: float = 0.3) -> Dict[int, List[str]]:
        """
        Perform hierarchical clustering on similarity matrix.
        
        Args:
            similarity_matrix: NxN matrix of similarities (0-1)
            files: List of file names
            threshold: Distance threshold for clustering (0-1, lower = more similar)
        
        Returns:
            Dictionary mapping cluster_id to list of files
        """
        # Convert similarity to distance
        distance_matrix = 1 - similarity_matrix
        
        # Convert to condensed form for linkage
        if distance_matrix.shape[0] > 1:
            condensed = squareform(distance_matrix)
            
            # Perform hierarchical clustering
            Z = linkage(condensed, method='ward')
            
            # Form flat clusters
            labels = fcluster(Z, t=threshold, criterion='distance')
        else:
            labels = np.array([1])
        
        # Group files by cluster
        clusters = {}
        for i, label in enumerate(labels):
            if label not in clusters:
                clusters[label] = []
            clusters[label].append(files[i])
        
        return clusters
    
    def build_similarity_graph(self, 
                               similarity_matrix: np.ndarray, 
                               files: List[str],
                               min_similarity: float = 0.5) -> nx.Graph:
        """
        Build a graph where nodes are files and edges represent similarity above threshold.
        
        Args:
            similarity_matrix: NxN matrix of similarities
            files: List of file names
            min_similarity: Minimum similarity to create an edge
        
        Returns:
            NetworkX graph
        """
        G = nx.Graph()
        
        # Add nodes
        for i, file in enumerate(files):
            G.add_node(i, label=file, filename=file)
        
        # Add edges
        n = len(files)
        for i in range(n):
            for j in range(i+1, n):
                if similarity_matrix[i, j] >= min_similarity:
                    G.add_edge(i, j, 
                              weight=similarity_matrix[i, j],
                              similarity=similarity_matrix[i, j])
        
        return G
    
    def detect_communities(self, G: nx.Graph) -> List[set]:
        """
        Detect communities in similarity graph using modularity optimization.
        
        Args:
            G: NetworkX graph
        
        Returns:
            List of sets, each set contains node IDs in a community
        """
        try:
            communities = list(nx.community.greedy_modularity_communities(G))
            return communities
        except Exception:
            return [set(G.nodes())]
    
    def get_cluster_stats(self, 
                         cluster: List[str], 
                         similarity_matrix: np.ndarray,
                         files: List[str]) -> Dict[str, float]:
        """
        Calculate statistics for a cluster.
        
        Args:
            cluster: List of files in the cluster
            similarity_matrix: Full similarity matrix
            files: All files
        
        Returns:
            Dictionary with cluster statistics
        """
        if len(cluster) < 2:
            return {
                'avg_similarity': 1.0,
                'min_similarity': 1.0,
                'max_similarity': 1.0,
                'std_similarity': 0.0
            }
        
        # Get indices of cluster files
        indices = [files.index(f) for f in cluster]
        
        # Extract similarities within cluster
        similarities = []
        for i in range(len(indices)):
            for j in range(i+1, len(indices)):
                similarities.append(similarity_matrix[indices[i], indices[j]])
        
        return {
            'avg_similarity': float(np.mean(similarities)),
            'min_similarity': float(np.min(similarities)),
            'max_similarity': float(np.max(similarities)),
            'std_similarity': float(np.std(similarities))
        }
    
    def identify_central_files(self, 
                             cluster: List[str], 
                             similarity_matrix: np.ndarray,
                             files: List[str]) -> List[Tuple[str, float]]:
        """
        Identify central files in a cluster (files most similar to others).
        
        Args:
            cluster: Files in cluster
            similarity_matrix: Full similarity matrix
            files: All files
        
        Returns:
            List of (filename, centrality_score) tuples
        """
        if len(cluster) < 2:
            return [(cluster[0], 1.0)]
        
        # Get indices
        indices = [files.index(f) for f in cluster]
        
        # Calculate centrality (average similarity to other files in cluster)
        centralities = []
        for i, idx in enumerate(indices):
            avg_sim = np.mean([similarity_matrix[idx, jdx] for j, jdx in enumerate(indices) if i != j])
            centralities.append((cluster[i], float(avg_sim)))
        
        # Sort by centrality
        centralities.sort(key=lambda x: x[1], reverse=True)
        
        return centralities
    
    def analyze_clusters(self, 
                       similarity_matrix: np.ndarray,
                       files: List[str],
                       min_similarity: float = 0.5) -> Dict[str, any]:
        """
        Perform complete cluster analysis.
        
        Args:
            similarity_matrix: NxN matrix of similarities
            files: List of file names
            min_similarity: Minimum similarity for graph edges
        
        Returns:
            Complete cluster analysis results
        """
        # Hierarchical clustering
        clusters = self.hierarchical_clustering(similarity_matrix, files)
        
        # Graph-based analysis
        G = self.build_similarity_graph(similarity_matrix, files, min_similarity)
        communities = self.detect_communities(G)
        
        # Calculate cluster statistics
        cluster_stats = {}
        for cluster_id, cluster_files in clusters.items():
            stats = self.get_cluster_stats(cluster_files, similarity_matrix, files)
            central_files = self.identify_central_files(cluster_files, similarity_matrix, files)
            
            cluster_stats[cluster_id] = {
                'files': cluster_files,
                'size': len(cluster_files),
                'stats': stats,
                'central_files': central_files[:3]  # Top 3 most central
            }
        
        return {
            'clusters': cluster_stats,
            'num_clusters': len(clusters),
            'largest_cluster': max(len(c) for c in clusters.values()),
            'graph_nodes': G.number_of_nodes(),
            'graph_edges': G.number_of_edges(),
            'graph_density': float(nx.density(G)) if G.number_of_nodes() > 1 else 0.0,
            'communities': [list(comm) for comm in communities]
        }
