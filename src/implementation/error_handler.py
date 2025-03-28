"""
Error handling module for Project Evolver.

This module provides centralized error handling and logging for the project.
"""

import logging
from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ErrorInfo:
    """Represents information about an error."""
    error_type: str
    message: str
    task_id: Optional[str] = None
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: Optional[str] = None


class ErrorHandler:
    """Handles errors and provides error reporting functionality."""
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        Initialize the error handler.
        
        Args:
            log_file: Optional path to log file
        """
        self.logger = logging.getLogger(__name__)
        self.log_file = log_file or Path("error.log")
        self.errors: Dict[str, ErrorInfo] = {}
        
        # Set up error logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Set up error logging."""
        handler = logging.FileHandler(self.log_file)
        handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(handler)
    
    def handle_error(self, error: Exception, task: Optional[Any] = None) -> None:
        """
        Handle an error that occurred during task execution.
        
        Args:
            error: The exception that occurred
            task: Optional task that was being executed
        """
        error_info = ErrorInfo(
            error_type=type(error).__name__,
            message=str(error),
            task_id=task.id if task else None,
            stack_trace=self._get_stack_trace(error)
        )
        
        # Log the error
        self.logger.error(
            f"Error in task {task.id if task else 'unknown'}: {str(error)}",
            exc_info=True
        )
        
        # Store error info
        if task and task.id:
            self.errors[task.id] = error_info
    
    def _get_stack_trace(self, error: Exception) -> Optional[str]:
        """
        Get the stack trace for an error.
        
        Args:
            error: The exception to get stack trace for
            
        Returns:
            Stack trace as string if available
        """
        import traceback
        return ''.join(traceback.format_tb(error.__traceback__))
    
    def get_error_info(self, task_id: str) -> Optional[ErrorInfo]:
        """
        Get error information for a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Error information if available
        """
        return self.errors.get(task_id)
    
    def get_all_errors(self) -> Dict[str, ErrorInfo]:
        """
        Get all recorded errors.
        
        Returns:
            Dictionary mapping task IDs to error information
        """
        return self.errors
    
    def clear_errors(self) -> None:
        """Clear all recorded errors."""
        self.errors.clear()
    
    def has_errors(self) -> bool:
        """
        Check if there are any recorded errors.
        
        Returns:
            True if there are errors, False otherwise
        """
        return bool(self.errors) 