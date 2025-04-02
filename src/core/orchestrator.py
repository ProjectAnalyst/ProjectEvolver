"""
Main orchestrator for Project Evolver.

This module coordinates the interaction between all components to implement
the project evolution workflow.
"""

import logging
import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

from ..analysis.codebase_analyzer import CodebaseAnalyzer
from ..analysis.gap_analyzer import GapAnalyzer
from ..implementation.code_generator import CodeGenerator
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


class ProjectEvolver:
    """Main orchestrator class that coordinates the project evolution process."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize the Project Evolver with configuration."""
        # Configure logging
        self._setup_logging()
        
        # Load environment variables from .env file
        load_dotenv()
        
        # Load configuration
        self.config = Config(config_path)
        
        # Initialize components
        self._initialize_components()
        
        # Initialize git operator with token from environment
        self.git_operator = GitOperator(
            repo_path=self.config.config.project_root,
            github_token=os.getenv("GITHUB_TOKEN")
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
        self.codebase_analyzer = CodebaseAnalyzer()
        self.gap_analyzer = GapAnalyzer()
        self.code_generator = CodeGenerator()
        self.file_manager = FileManager(project_root=self.config.config.project_root, enable_backups=True)
    
    def evolve_project(self, repo_url: str, whitepaper_path: str, max_features: int = 1) -> None:
        """
        Evolve a project based on its whitepaper.
        
        Args:
            repo_url: URL of the GitHub repository
            whitepaper_path: Path to the whitepaper file
            max_features: Maximum number of features to implement
        """
        self.logger.info(f"Starting evolution process for repository: {repo_url}")
        
        try:
            # Analyze project and get gaps
            gaps = self.analyze_project(repo_url, whitepaper_path)
            
            # Sort gaps by priority
            prioritized_gaps = sorted(gaps, key=lambda g: g.priority, reverse=True)
            
            # Take only the specified number of gaps
            gaps_to_implement = prioritized_gaps[:max_features]
            
            # Get repository path
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            repo_path = Path(repo_name)
            
            self.logger.info(f"Implementing {len(gaps_to_implement)} feature(s)...")
            
            # Implement each gap
            for gap in gaps_to_implement:
                try:
                    self.logger.info(f"Implementing: {gap.section}")
                    
                    # Generate changes - now passing repo_path as codebase_root
                    result = self.code_generator.generate_changes(gap, repo_path)
                    if not result or not result['modified_files']:
                        self.logger.warning(f"No changes generated for gap: {gap.section}")
                        continue
                    
                    # Apply changes
                    self.file_manager.apply_changes({"file_updates": result['modified_files']})
                    
                    # Get relative paths for git staging
                    relative_paths = [str(Path(path).relative_to(repo_path)) for path in result['modified_files'].keys()]
                    self.logger.info(f"Staging files: {relative_paths}")
                    
                    # Stage changes
                    if not self.git_operator.stage_changes(relative_paths):
                        self.logger.error("Failed to stage changes")
                        continue
                    
                    # Commit changes
                    if not self.git_operator.commit_changes(result['commit_message']):
                        self.logger.error("Failed to commit changes")
                        continue
                    
                    # Push changes
                    if not self.git_operator.push_changes():
                        self.logger.error("Failed to push changes")
                        continue
                    
                    self.logger.info(f"Successfully implemented gap: {gap.section}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to implement gap: {str(e)}")
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