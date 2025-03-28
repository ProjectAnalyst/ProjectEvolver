"""
Task planning module for Project Evolver.

This module handles the creation and management of tasks based on identified gaps
between the current codebase and the whitepaper requirements.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import uuid

from ..analysis.gap_analyzer import Gap

@dataclass
class Task:
    """Represents an actionable task for improving the codebase."""
    id: str
    type: str
    description: str
    priority: int
    target_files: List[str]
    requirements: List[str]
    current_state: str
    desired_state: str
    dependencies: List[str] = None
    status: str = "pending"

class TaskPlanner:
    """Plans and manages tasks for improving the codebase."""
    
    def __init__(self):
        """Initialize the TaskPlanner."""
        self.logger = logging.getLogger(__name__)
    
    def create_tasks(self, gaps: List[Gap]) -> List[Task]:
        """
        Create tasks from identified gaps.
        
        Args:
            gaps: List of identified gaps
            
        Returns:
            List of created tasks
        """
        tasks = []
        
        for gap in gaps:
            try:
                task = self._create_task_from_gap(gap)
                tasks.append(task)
                self.logger.info(f"Created task: {task.description}")
            except Exception as e:
                self.logger.error(f"Failed to create task from gap: {str(e)}")
                continue
        
        return tasks
    
    def _create_task_from_gap(self, gap: Gap) -> Task:
        """
        Create a task from a gap.
        
        Args:
            gap: The gap to create a task from
            
        Returns:
            Created task
        """
        # Map affected_files to target_files
        target_files = gap.affected_files if hasattr(gap, 'affected_files') else []
        
        return Task(
            id=str(uuid.uuid4()),
            type=gap.type,
            description=gap.description,
            priority=gap.priority,
            target_files=target_files,  # Use the mapped target_files
            requirements=gap.requirements,
            current_state=gap.current_state,
            desired_state=gap.desired_state,
            dependencies=[]
        )
    
    def _analyze_task_dependencies(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """
        Analyze dependencies between tasks.
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            Dictionary mapping task IDs to their dependencies
        """
        dependencies = {}
        
        for task in tasks:
            task_deps = []
            
            # Check for dependencies based on affected files
            for other_task in tasks:
                if other_task.id != task.id:
                    # If a task affects files that another task depends on
                    if any(file in other_task.target_files for file in task.target_files):
                        task_deps.append(other_task.id)
            
            dependencies[task.id] = task_deps
        
        return dependencies
    
    def _has_dependency(self, task1: Task, task2: Task) -> bool:
        """
        Check if task1 depends on task2.
        
        Args:
            task1: First task
            task2: Second task
            
        Returns:
            True if task1 depends on task2
        """
        # Check if task2 affects files that task1 depends on
        return any(file in task2.target_files for file in task1.target_files)

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Get a task by its ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            Task if found, None otherwise
        """
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_tasks_by_type(self, task_type: str) -> List[Task]:
        """
        Get all tasks of a specific type.
        
        Args:
            task_type: Type of tasks to get
            
        Returns:
            List of matching tasks
        """
        return [task for task in self.tasks if task.type == task_type]
    
    def get_tasks_by_priority(self, priority: int) -> List[Task]:
        """
        Get all tasks with a specific priority.
        
        Args:
            priority: Priority level to get
            
        Returns:
            List of matching tasks
        """
        return [task for task in self.tasks if task.priority == priority]

    def build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build a graph of task dependencies."""
        graph = {}
        for task in self.tasks:
            graph[task.description] = []
            for other_task in self.tasks:
                if task != other_task:
                    if any(req in other_task.requirements for req in task.requirements):
                        graph[task.description].append(other_task.description)
        return graph

    def prioritize_tasks(self) -> List[Task]:
        """Prioritize tasks based on dependencies and complexity."""
        graph = self.build_dependency_graph()
        visited = set()
        priority = 1
        prioritized_tasks = []

        def visit(task_desc: str):
            nonlocal priority
            if task_desc in visited:
                return
            visited.add(task_desc)
            for dep in graph[task_desc]:
                visit(dep)
            task = next(t for t in self.tasks if t.description == task_desc)
            task.priority = priority
            prioritized_tasks.append(task)
            priority += 1

        for task in self.tasks:
            if task.description not in visited:
                visit(task.description)

        return prioritized_tasks 