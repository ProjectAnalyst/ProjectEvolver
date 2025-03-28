"""
Code validation module for Project Evolver.

This module validates generated code changes to ensure they meet
quality standards and requirements.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import ast
import black
import isort
import pylint.lint
from io import StringIO
import re


class ValidationError(Exception):
    """Exception raised when code validation fails."""
    pass


class Validator:
    """Validates generated code changes."""
    
    def __init__(self):
        """Initialize the validator."""
        self.logger = logging.getLogger(__name__)
        self.validation_rules = self._load_validation_rules()
    
    def validate_changes(self, changes: Dict[str, str]) -> bool:
        """
        Validate generated code changes.
        
        Args:
            changes: Dictionary mapping file paths to new content
            
        Returns:
            True if changes are valid, False otherwise
            
        Raises:
            ValidationError: If validation fails
        """
        try:
            # Validate each file
            for file_path, content in changes.items():
                self._validate_file(file_path, content)
            
            return True
            
        except ValidationError as e:
            self.logger.error(f"Validation failed: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Validation error: {str(e)}")
            return False
    
    def _validate_file(self, file_path: str, content: str) -> None:
        """
        Validate a single file.
        
        Args:
            file_path: Path to the file
            content: Content to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Check syntax
        if not self._validate_syntax(content):
            raise ValidationError(f"Syntax error in {file_path}")
        
        # Check formatting
        if not self._validate_formatting(content):
            raise ValidationError(f"Formatting error in {file_path}")
        
        # Check imports
        if not self._validate_imports(content):
            raise ValidationError(f"Import error in {file_path}")
        
        # Check code style
        if not self._validate_style(file_path, content):
            raise ValidationError(f"Style error in {file_path}")
        
        # Check documentation
        if not self._validate_documentation(content):
            raise ValidationError(f"Documentation error in {file_path}")
    
    def _validate_syntax(self, content: str) -> bool:
        """
        Validate Python syntax.
        
        Args:
            content: Code content to validate
            
        Returns:
            True if syntax is valid, False otherwise
        """
        try:
            ast.parse(content)
            return True
        except SyntaxError:
            return False
    
    def _validate_formatting(self, content: str) -> bool:
        """
        Validate code formatting.
        
        Args:
            content: Code content to validate
            
        Returns:
            True if formatting is valid, False otherwise
        """
        try:
            # Format with black
            formatted = black.format_str(content, mode=black.FileMode())
            
            # Compare with original
            return formatted == content
        except Exception:
            return False
    
    def _validate_imports(self, content: str) -> bool:
        """
        Validate import statements.
        
        Args:
            content: Code content to validate
            
        Returns:
            True if imports are valid, False otherwise
        """
        try:
            # Sort imports
            sorted_content = isort.code(content)
            
            # Compare with original
            return sorted_content == content
        except Exception:
            return False
    
    def _validate_style(self, file_path: str, content: str) -> bool:
        """
        Validate code style using pylint.
        
        Args:
            file_path: Path to the file
            content: Code content to validate
            
        Returns:
            True if style is valid, False otherwise
        """
        try:
            # Create a temporary file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Run pylint
            output = StringIO()
            pylint.lint.Run(
                [file_path],
                do_exit=False,
                reporter=TextReporter(output)
            )
            
            # Check for errors
            return "error" not in output.getvalue().lower()
            
        except Exception:
            return False
    
    def _validate_documentation(self, content: str) -> bool:
        """
        Validate code documentation.
        
        Args:
            content: Code content to validate
            
        Returns:
            True if documentation is valid, False otherwise
        """
        try:
            # Parse the code
            tree = ast.parse(content)
            
            # Check for module docstring
            if not ast.get_docstring(tree):
                return False
            
            # Check for function/class docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        return False
            
            return True
            
        except Exception:
            return False
    
    def _load_validation_rules(self) -> Dict[str, Any]:
        """
        Load validation rules from configuration.
        
        Returns:
            Dictionary of validation rules
        """
        return {
            "max_line_length": 88,  # Black default
            "require_docstrings": True,
            "require_type_hints": True,
            "max_complexity": 10,
            "min_test_coverage": 0.8
        }
    
    def update_rules(self, rules: Dict[str, Any]) -> None:
        """
        Update validation rules.
        
        Args:
            rules: New validation rules
        """
        self.validation_rules.update(rules)
    
    def get_rules(self) -> Dict[str, Any]:
        """
        Get current validation rules.
        
        Returns:
            Current validation rules
        """
        return self.validation_rules.copy()


class TextReporter:
    """Custom reporter for pylint output."""
    
    def __init__(self, output: StringIO):
        """
        Initialize the reporter.
        
        Args:
            output: Output stream
        """
        self.output = output
    
    def handle_message(self, msg):
        """Handle a pylint message."""
        self.output.write(f"{msg}\n")
    
    def on_set_current_module(self, module, filepath):
        """Handle module change."""
        pass
    
    def on_close(self, stats, previous_stats):
        """Handle close event."""
        pass 