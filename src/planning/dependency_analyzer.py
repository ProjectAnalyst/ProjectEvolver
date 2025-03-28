"""
Dependency analysis module for Project Evolver.

This module analyzes and manages dependencies between tasks to ensure
they are executed in the correct order.
"""

import logging
from typing import Dict, List, Any, Set
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TaskNode:
    """Represents a task node in the dependency graph."""
    task_id: str
    dependencies: Set[str]
    dependents: Set[str]
    visited: bool = False
    temp_visited: bool = False


class DependencyAnalyzer:
    """Analyzes and manages task dependencies."""
    
    def __init__(self):
        """Initialize the dependency analyzer."""
        self.logger = logging.getLogger(__name__)
        self.graph: Dict[str, TaskNode] = {}
        self.cycles: List[List[str]] = []
    
    def build_graph(self, tasks: List[Any]) -> Dict[str, TaskNode]:
        """
        Build a dependency graph from tasks.
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            Dictionary mapping task IDs to their nodes
        """
        try:
            # Clear previous graph
            self.graph.clear()
            self.cycles.clear()
            
            # Create nodes for each task
            for task in tasks:
                self.graph[task.id] = TaskNode(
                    task_id=task.id,
                    dependencies=set(task.dependencies),
                    dependents=set()
                )
            
            # Build dependency relationships
            self._build_dependencies()
            
            # Check for cycles
            self._detect_cycles()
            
            return self.graph
            
        except Exception as e:
            self.logger.error(f"Failed to build dependency graph: {str(e)}")
            raise
    
    def _build_dependencies(self) -> None:
        """Build bidirectional dependency relationships."""
        # Add dependents for each task
        for task_id, node in self.graph.items():
            for dep_id in node.dependencies:
                if dep_id in self.graph:
                    self.graph[dep_id].dependents.add(task_id)
    
    def _detect_cycles(self) -> None:
        """Detect cycles in the dependency graph."""
        # Reset visited flags
        for node in self.graph.values():
            node.visited = False
            node.temp_visited = False
        
        # Check each node for cycles
        for task_id in self.graph:
            if not self.graph[task_id].visited:
                self._dfs_cycle_detection(task_id, [])
    
    def _dfs_cycle_detection(self, task_id: str, path: List[str]) -> None:
        """
        Perform depth-first search for cycle detection.
        
        Args:
            task_id: Current task ID
            path: Current path in the search
        """
        node = self.graph[task_id]
        
        # Mark as temporarily visited
        node.temp_visited = True
        path.append(task_id)
        
        # Check each dependency
        for dep_id in node.dependencies:
            if dep_id not in self.graph:
                continue
                
            dep_node = self.graph[dep_id]
            
            # If dependency is temporarily visited, we found a cycle
            if dep_node.temp_visited:
                cycle_start = path.index(dep_id)
                cycle = path[cycle_start:]
                if cycle not in self.cycles:
                    self.cycles.append(cycle)
                continue
            
            # If dependency is not visited, continue DFS
            if not dep_node.visited:
                self._dfs_cycle_detection(dep_id, path)
        
        # Mark as permanently visited
        node.temp_visited = False
        node.visited = True
        path.pop()
    
    def get_task_order(self) -> List[str]:
        """
        Get a valid order for executing tasks.
        
        Returns:
            List of task IDs in execution order
        """
        if self.cycles:
            self.logger.warning("Cannot determine task order: cycles detected")
            return []
        
        # Reset visited flags
        for node in self.graph.values():
            node.visited = False
        
        # Perform topological sort
        order = []
        for task_id in self.graph:
            if not self.graph[task_id].visited:
                self._topological_sort(task_id, order)
        
        return list(reversed(order))
    
    def _topological_sort(self, task_id: str, order: List[str]) -> None:
        """
        Perform topological sort starting from a task.
        
        Args:
            task_id: Current task ID
            order: List to store the order
        """
        node = self.graph[task_id]
        
        # Skip if already visited
        if node.visited:
            return
        
        # Mark as visited
        node.visited = True
        
        # Process dependencies first
        for dep_id in node.dependencies:
            if dep_id in self.graph:
                self._topological_sort(dep_id, order)
        
        # Add to order
        order.append(task_id)
    
    def get_dependent_tasks(self, task_id: str) -> List[str]:
        """
        Get all tasks that depend on a specific task.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            List of dependent task IDs
        """
        if task_id not in self.graph:
            return []
        return list(self.graph[task_id].dependents)
    
    def get_dependency_tasks(self, task_id: str) -> List[str]:
        """
        Get all tasks that a specific task depends on.
        
        Args:
            task_id: ID of the task to check
            
        Returns:
            List of dependency task IDs
        """
        if task_id not in self.graph:
            return []
        return list(self.graph[task_id].dependencies)
    
    def has_cycles(self) -> bool:
        """
        Check if the dependency graph has cycles.
        
        Returns:
            True if cycles exist, False otherwise
        """
        return bool(self.cycles)
    
    def get_cycles(self) -> List[List[str]]:
        """
        Get all cycles in the dependency graph.
        
        Returns:
            List of cycles, where each cycle is a list of task IDs
        """
        return self.cycles.copy() 