"""
Configuration management module for Project Evolver.

This module handles loading and managing configuration settings for the project.
It supports loading from environment variables, config files, and command-line
arguments, with proper validation and type conversion.
"""

from typing import Any, Dict, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import json
import os
from dotenv import load_dotenv


@dataclass
class ProjectConfig:
    """Represents the complete project configuration."""
    github_token: str = ""
    project_root: Path = Path.cwd()
    memory_file: Path = Path("project_memory.json")
    use_simulated_tests: bool = False
    git_enabled: bool = True
    max_retries: int = 3
    log_level: str = "INFO"
    custom_settings: Dict[str, Any] = None
    development_mode: bool = True  # Added development mode flag

    def __post_init__(self):
        if self.custom_settings is None:
            self.custom_settings = {}


class Config:
    """Manages project configuration."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize configuration.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config = ProjectConfig()
        
        # Load from file if provided
        if config_path:
            self.load_from_file(config_path)
        
        # Update from environment variables
        self.update_from_env()
        
        # Validate configuration
        if not self.validate_config():
            raise ValueError("Invalid configuration")
    
    def load_from_file(self, config_path: Path) -> None:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file
        """
        try:
            with open(config_path, 'r') as f:
                config_dict = json.load(f)
                
            # Convert string paths to Path objects
            if 'project_root' in config_dict:
                config_dict['project_root'] = Path(config_dict['project_root'])
            if 'memory_file' in config_dict:
                config_dict['memory_file'] = Path(config_dict['memory_file'])
            
            # Update configuration
            for key, value in config_dict.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                    
        except Exception as e:
            raise ValueError(f"Failed to load configuration: {str(e)}")
    
    def validate_config(self) -> bool:
        """
        Validate the current configuration.
        
        Returns:
            True if valid, False otherwise
        """
        # Check required values
        if not self.config.github_token and not self.config.development_mode:
            return False
        
        # Check path validity
        if not self.config.project_root.exists():
            return False
        
        # Check value ranges
        if self.config.max_retries < 0:
            return False
        
        # Check log level validity
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.config.log_level.upper() not in valid_log_levels:
            return False
        
        return True
    
    def update_from_env(self) -> None:
        """Update configuration from environment variables."""
        # Update GitHub token if provided in environment
        if os.getenv("GITHUB_TOKEN"):
            self.config.github_token = os.getenv("GITHUB_TOKEN")
        
        # Update project root
        if os.getenv("PROJECT_ROOT"):
            self.config.project_root = Path(os.getenv("PROJECT_ROOT"))
        
        # Update git enabled
        if os.getenv("GIT_ENABLED"):
            self.config.git_enabled = os.getenv("GIT_ENABLED").lower() == "true"
        
        # Update log level
        if os.getenv("LOG_LEVEL"):
            self.config.log_level = os.getenv("LOG_LEVEL")
        
        # Update max retries
        if os.getenv("MAX_RETRIES"):
            try:
                self.config.max_retries = int(os.getenv("MAX_RETRIES"))
            except ValueError:
                pass
        
        # Update development mode
        if os.getenv("DEVELOPMENT_MODE"):
            self.config.development_mode = os.getenv("DEVELOPMENT_MODE").lower() == "true"
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        config_dict = asdict(self.config)
        config_dict.update(self.config.custom_settings)
        return config_dict 