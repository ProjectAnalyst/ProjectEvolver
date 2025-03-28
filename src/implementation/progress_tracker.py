"""
Progress tracking module for Project Evolver.

This module tracks the progress of task implementation and maintains
metrics about the evolution process.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path


@dataclass
class TaskProgress:
    """Represents progress information for a task."""
    task_id: str
    status: str  # pending, in_progress, completed, failed
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    changes_made: List[str] = None
    metrics: Dict[str, Any] = None


class ProgressTracker:
    """Tracks implementation progress and metrics."""
    
    def __init__(self, progress_file: Optional[Path] = None):
        """
        Initialize the progress tracker.
        
        Args:
            progress_file: Optional path to progress file
        """
        self.logger = logging.getLogger(__name__)
        self.progress_file = progress_file or Path("progress.json")
        self.tasks: Dict[str, TaskProgress] = {}
        self.metrics: Dict[str, Any] = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "in_progress_tasks": 0,
            "start_time": None,
            "end_time": None,
            "total_changes": 0,
            "files_modified": set()
        }
        
        # Load existing progress if file exists
        if self.progress_file.exists():
            self._load_progress()
    
    def update(self, task: Any, status: str = "completed", error: Optional[str] = None) -> None:
        """
        Update progress for a task.
        
        Args:
            task: Task to update
            status: New status for the task
            error: Optional error message
        """
        try:
            # Get or create task progress
            if task.id not in self.tasks:
                self.tasks[task.id] = TaskProgress(
                    task_id=task.id,
                    status="pending",
                    changes_made=[],
                    metrics={}
                )
            
            progress = self.tasks[task.id]
            
            # Update status
            progress.status = status
            
            # Update timestamps
            if status == "in_progress" and not progress.start_time:
                progress.start_time = datetime.now()
            elif status in ["completed", "failed"] and not progress.end_time:
                progress.end_time = datetime.now()
            
            # Update error message if any
            if error:
                progress.error_message = error
            
            # Update metrics
            self._update_metrics()
            
            # Save progress
            self._save_progress()
            
        except Exception as e:
            self.logger.error(f"Failed to update progress: {str(e)}")
    
    def record_changes(self, task_id: str, changes: List[str]) -> None:
        """
        Record changes made for a task.
        
        Args:
            task_id: ID of the task
            changes: List of changes made
        """
        try:
            if task_id in self.tasks:
                self.tasks[task_id].changes_made.extend(changes)
                self.metrics["total_changes"] += len(changes)
                self.metrics["files_modified"].update(changes)
                self._save_progress()
        except Exception as e:
            self.logger.error(f"Failed to record changes: {str(e)}")
    
    def get_task_progress(self, task_id: str) -> Optional[TaskProgress]:
        """
        Get progress information for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            TaskProgress object if found, None otherwise
        """
        return self.tasks.get(task_id)
    
    def get_overall_progress(self) -> Dict[str, Any]:
        """
        Get overall progress information.
        
        Returns:
            Dictionary containing overall progress metrics
        """
        return {
            "total_tasks": self.metrics["total_tasks"],
            "completed_tasks": self.metrics["completed_tasks"],
            "failed_tasks": self.metrics["failed_tasks"],
            "in_progress_tasks": self.metrics["in_progress_tasks"],
            "completion_percentage": self._calculate_completion_percentage(),
            "total_changes": self.metrics["total_changes"],
            "files_modified": len(self.metrics["files_modified"]),
            "start_time": self.metrics["start_time"],
            "end_time": self.metrics["end_time"]
        }
    
    def get_failed_tasks(self) -> List[TaskProgress]:
        """
        Get all failed tasks.
        
        Returns:
            List of failed task progress objects
        """
        return [
            progress for progress in self.tasks.values()
            if progress.status == "failed"
        ]
    
    def get_completed_tasks(self) -> List[TaskProgress]:
        """
        Get all completed tasks.
        
        Returns:
            List of completed task progress objects
        """
        return [
            progress for progress in self.tasks.values()
            if progress.status == "completed"
        ]
    
    def get_in_progress_tasks(self) -> List[TaskProgress]:
        """
        Get all in-progress tasks.
        
        Returns:
            List of in-progress task progress objects
        """
        return [
            progress for progress in self.tasks.values()
            if progress.status == "in_progress"
        ]
    
    def _update_metrics(self) -> None:
        """Update overall metrics."""
        self.metrics.update({
            "total_tasks": len(self.tasks),
            "completed_tasks": len(self.get_completed_tasks()),
            "failed_tasks": len(self.get_failed_tasks()),
            "in_progress_tasks": len(self.get_in_progress_tasks())
        })
        
        # Update start time if not set
        if not self.metrics["start_time"]:
            self.metrics["start_time"] = datetime.now()
    
    def _calculate_completion_percentage(self) -> float:
        """Calculate completion percentage."""
        total = self.metrics["total_tasks"]
        if total == 0:
            return 0.0
        completed = self.metrics["completed_tasks"]
        return (completed / total) * 100
    
    def _save_progress(self) -> None:
        """Save progress to file."""
        try:
            # Convert progress to serializable format
            progress_data = {
                "tasks": {
                    task_id: {
                        "status": progress.status,
                        "start_time": progress.start_time.isoformat() if progress.start_time else None,
                        "end_time": progress.end_time.isoformat() if progress.end_time else None,
                        "error_message": progress.error_message,
                        "changes_made": progress.changes_made,
                        "metrics": progress.metrics
                    }
                    for task_id, progress in self.tasks.items()
                },
                "metrics": {
                    key: list(value) if isinstance(value, set) else value
                    for key, value in self.metrics.items()
                }
            }
            
            # Save to file
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
                
        except Exception as e:
            self.logger.error(f"Failed to save progress: {str(e)}")
    
    def _load_progress(self) -> None:
        """Load progress from file."""
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            # Restore tasks
            self.tasks = {
                task_id: TaskProgress(
                    task_id=task_id,
                    status=data["status"],
                    start_time=datetime.fromisoformat(data["start_time"]) if data["start_time"] else None,
                    end_time=datetime.fromisoformat(data["end_time"]) if data["end_time"] else None,
                    error_message=data["error_message"],
                    changes_made=data["changes_made"],
                    metrics=data["metrics"]
                )
                for task_id, data in progress_data["tasks"].items()
            }
            
            # Restore metrics
            self.metrics = {
                key: set(value) if isinstance(value, list) and key == "files_modified" else value
                for key, value in progress_data["metrics"].items()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load progress: {str(e)}")
            # Reset to initial state
            self.tasks = {}
            self.metrics = {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "in_progress_tasks": 0,
                "start_time": None,
                "end_time": None,
                "total_changes": 0,
                "files_modified": set()
            } 