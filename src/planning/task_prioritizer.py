"""
Task prioritization module for Project Evolver.

This module orders tasks based on their dependencies, priority, and complexity
to determine the optimal execution order.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class TaskPriority:
    """Represents task priority information."""
    task_id: str
    priority: int
    complexity: int
    dependency_count: int
    dependent_count: int


class TaskPrioritizer:
    """Orders tasks based on dependencies and priority."""
    
    def __init__(self):
        """Initialize the task prioritizer."""
        self.logger = logging.getLogger(__name__)
        self.priorities: Dict[str, TaskPriority] = {}
    
    def order_tasks(self, task_graph: Dict[str, Any]) -> List[str]:
        """
        Order tasks based on dependencies and priority.
        
        Args:
            task_graph: Dictionary mapping task IDs to their nodes
            
        Returns:
            List of task IDs in execution order
        """
        try:
            # Clear previous priorities
            self.priorities.clear()
            
            # Calculate priorities for each task
            for task_id, node in task_graph.items():
                self._calculate_task_priority(task_id, node)
            
            # Sort tasks by priority
            ordered_tasks = self._sort_tasks()
            
            return ordered_tasks
            
        except Exception as e:
            self.logger.error(f"Failed to order tasks: {str(e)}")
            raise
    
    def _calculate_task_priority(self, task_id: str, node: Any) -> None:
        """
        Calculate priority for a task.
        
        Args:
            task_id: ID of the task
            node: Task node from the graph
        """
        # Get task details from the graph
        priority = node.priority if hasattr(node, 'priority') else 1
        complexity = node.complexity if hasattr(node, 'complexity') else 1
        
        # Count dependencies and dependents
        dependency_count = len(node.dependencies)
        dependent_count = len(node.dependents)
        
        # Create priority object
        self.priorities[task_id] = TaskPriority(
            task_id=task_id,
            priority=priority,
            complexity=complexity,
            dependency_count=dependency_count,
            dependent_count=dependent_count
        )
    
    def _sort_tasks(self) -> List[str]:
        """
        Sort tasks based on priority information.
        
        Returns:
            List of task IDs in sorted order
        """
        # Convert to list for sorting
        task_list = list(self.priorities.values())
        
        # Sort tasks using multiple criteria
        task_list.sort(key=lambda x: (
            -x.priority,  # Higher priority first
            x.complexity,  # Lower complexity first
            -x.dependent_count,  # More dependents first
            x.dependency_count  # Fewer dependencies first
        ))
        
        # Return task IDs in order
        return [task.task_id for task in task_list]
    
    def get_task_priority(self, task_id: str) -> Optional[TaskPriority]:
        """
        Get priority information for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            TaskPriority object if found, None otherwise
        """
        return self.priorities.get(task_id)
    
    def get_high_priority_tasks(self, threshold: int = 3) -> List[str]:
        """
        Get tasks with priority above a threshold.
        
        Args:
            threshold: Priority threshold
            
        Returns:
            List of high priority task IDs
        """
        return [
            task_id for task_id, priority in self.priorities.items()
            if priority.priority >= threshold
        ]
    
    def get_complex_tasks(self, threshold: int = 3) -> List[str]:
        """
        Get tasks with complexity above a threshold.
        
        Args:
            threshold: Complexity threshold
            
        Returns:
            List of complex task IDs
        """
        return [
            task_id for task_id, priority in self.priorities.items()
            if priority.complexity >= threshold
        ]
    
    def get_critical_tasks(self) -> List[str]:
        """
        Get tasks that are critical to the project.
        
        Returns:
            List of critical task IDs
        """
        return [
            task_id for task_id, priority in self.priorities.items()
            if priority.dependent_count > 0 and priority.priority >= 3
        ]
    
    def get_independent_tasks(self) -> List[str]:
        """
        Get tasks that have no dependencies.
        
        Returns:
            List of independent task IDs
        """
        return [
            task_id for task_id, priority in self.priorities.items()
            if priority.dependency_count == 0
        ]
    
    def get_blocked_tasks(self) -> List[str]:
        """
        Get tasks that are blocked by dependencies.
        
        Returns:
            List of blocked task IDs
        """
        return [
            task_id for task_id, priority in self.priorities.items()
            if priority.dependency_count > 0
        ] 