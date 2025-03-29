"""
Main orchestrator for Project Evolver.

This module coordinates the interaction between all components to implement
the project evolution workflow. It manages the main loop of analyzing the project,
planning improvements, and implementing changes.
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass

from ..analysis.codebase_analyzer import CodebaseAnalyzer
from ..analysis.gap_analyzer import GapAnalyzer
from ..planning.task_planner import TaskPlanner
from ..planning.dependency_analyzer import DependencyAnalyzer
from ..planning.task_prioritizer import TaskPrioritizer
from ..implementation.code_generator import CodeGenerator
from ..implementation.validator import Validator
from ..implementation.progress_tracker import ProgressTracker
from ..implementation.error_handler import ErrorHandler
from ..implementation.file_manager import FileManager
from .git_operator import GitOperator
from .whitepaper_processor import WhitepaperProcessor
from .config import Config


class ValidationError(Exception):
    """Raised when code changes fail validation."""
    pass


class TestError(Exception):
    """Raised when tests fail after applying changes."""
    pass


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
    status: str = "pending"  # pending, in_progress, completed, failed


class ProjectEvolver:
    """Main orchestrator class that coordinates the project evolution process."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the Project Evolver with configuration.
        
        Args:
            config_path: Optional path to configuration file
        """
        # Configure logging
        self._setup_logging()
        
        # Load configuration
        self.config = Config(config_path)
        
        # Initialize components
        self._initialize_components()
        
        # Initialize git operator
        self.git_operator = GitOperator(
            repo_path=self.config.config.project_root,
            github_token=self.config.config.github_token
        )
        
        # Initialize whitepaper processor
        self.whitepaper_processor = WhitepaperProcessor()
    
    def _setup_logging(self):
        """Configure logging for the project."""
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('project_evolver.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _initialize_components(self):
        """Initialize all component classes."""
        # Analysis components
        self.codebase_analyzer = CodebaseAnalyzer()
        self.gap_analyzer = GapAnalyzer()
        
        # Planning components
        self.task_planner = TaskPlanner()
        self.dependency_analyzer = DependencyAnalyzer()
        self.task_prioritizer = TaskPrioritizer()
        
        # Implementation components
        self.code_generator = CodeGenerator()
        self.validator = Validator()
        self.progress_tracker = ProgressTracker()
        self.error_handler = ErrorHandler()
        self.file_manager = FileManager(project_root=self.config.config.project_root, enable_backups=True)
    
    def evolve_project(self, repo_url: str, whitepaper_path: str) -> None:
        """
        Evolve a project based on its whitepaper.
        
        Args:
            repo_url: URL of the GitHub repository
            whitepaper_path: Path to the whitepaper file
        """
        self.logger.info(f"Starting evolution process for repository: {repo_url}")
        
        try:
            # 1. Initial Analysis Phase
            self.logger.info("Starting analysis phase...")
            gaps = self.analyze_project(repo_url, whitepaper_path)
            
            # 2. Planning Phase
            self.logger.info("Starting planning phase...")
            tasks = self.plan_improvements(gaps)
            
            # 3. Implementation Phase
            self.logger.info(f"Starting project evolution with {len(tasks)} tasks")
            
            for task in tasks:
                try:
                    self.logger.info(f"Implementing task: {task.description}")
                    
                    # Generate changes
                    changes = self.code_generator.generate_changes(task)
                    if not changes:
                        self.logger.warning(f"No changes generated for task: {task.description}")
                        continue
                    
                    # Wrap changes in expected format
                    wrapped_changes = {"file_updates": changes}
                    
                    # Apply changes
                    self.file_manager.apply_changes(wrapped_changes)
                    
                    # Validate changes
                    if not self.validator.validate_changes(changes):
                        raise ValidationError(f"Changes failed validation for task: {task.description}")
                    
                    self.logger.info(f"Successfully implemented task: {task.description}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to implement task: {str(e)}")
                    continue
                
            self.logger.info("Project evolution completed")
            
        except Exception as e:
            self.logger.error(f"Project evolution failed: {str(e)}")
            raise
    
    def analyze_project(self, repo_url: str, whitepaper_path: str) -> List[dict]:
        """
        Analyze the project and identify gaps with whitepaper requirements.
        
        Args:
            repo_url: URL of the GitHub repository
            whitepaper_path: Path to the whitepaper file (optional)
            
        Returns:
            List of identified gaps
        """
        self.logger.info("Starting project analysis...")
        
        # Extract repository name from URL
        repo_name = repo_url.split('/')[-1].replace('.git', '')
        repo_path = Path(repo_name)
        
        # Always try to clone/update the repository
        self.logger.info(f"Cloning/updating repository: {repo_url}")
        if not self.git_operator.clone_repository(repo_url):
            raise Exception(f"Failed to clone/update repository: {repo_url}")
        
        # Find whitepaper automatically if not provided
        if not whitepaper_path:
            whitepaper_path = repo_path / "docs" / "whitepaper.md"
            if not whitepaper_path.exists():
                raise FileNotFoundError(f"Could not find whitepaper at {whitepaper_path}")
            self.logger.info(f"Found whitepaper at: {whitepaper_path}")
        
        # Load and analyze whitepaper
        self.logger.info("Loading and analyzing whitepaper...")
        whitepaper = self.whitepaper_processor.load_and_analyze(str(whitepaper_path))
        self.logger.info("Whitepaper analysis complete")
        
        # Set repository path for codebase analyzer
        self.codebase_analyzer.set_repo_path(repo_path)
        
        # Pass whitepaper features to codebase analyzer
        self.codebase_analyzer.set_whitepaper_features(whitepaper.get("features", []))
        
        # Scan current codebase
        self.logger.info("Scanning current codebase...")
        current_state = self.codebase_analyzer.scan_codebase()
        self.logger.info(f"Found {len(current_state)} files in codebase")
        
        # Identify gaps
        self.logger.info("Identifying gaps between current state and whitepaper requirements...")
        gaps = self.gap_analyzer.identify_gaps(whitepaper, current_state)
        self.logger.info(f"Identified {len(gaps)} gaps")
        
        return gaps
    
    def plan_improvements(self, gaps: List[dict]) -> List[Task]:
        """
        Plan improvements based on identified gaps.
        
        Args:
            gaps: List of identified gaps
            
        Returns:
            List of tasks to implement
        """
        self.logger.info("Starting improvement planning phase...")
        
        # Create tasks from gaps
        self.logger.info("Creating tasks from identified gaps...")
        tasks = self.task_planner.create_tasks(gaps)
        self.logger.info(f"Created {len(tasks)} tasks")
        
        # Build dependency graph
        self.logger.info("Building task dependency graph...")
        dependencies = self.dependency_analyzer.build_graph(tasks)
        self.logger.info(f"Graph contains {len(dependencies)} nodes")
        
        # Prioritize tasks
        self.logger.info("Prioritizing tasks...")
        prioritized_tasks = self.task_prioritizer.order_tasks(dependencies)
        self.logger.info("Task prioritization complete")
        
        # Log task details
        for task in tasks:
            self.logger.info(f"Task {task.id}: {task.description}")
            self.logger.info(f"  Priority: {task.priority}")
            self.logger.info(f"  Target files: {task.target_files}")
            self.logger.info(f"  Dependencies: {task.dependencies}")
        
        return tasks 