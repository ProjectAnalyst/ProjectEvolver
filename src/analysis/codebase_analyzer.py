"""
Codebase analysis module for Project Evolver.

This module handles scanning and analyzing the current codebase to understand
its structure, dependencies, and functionality.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import ast
import re


class CodebaseAnalyzer:
    """Analyzes the current codebase structure and functionality."""
    
    def __init__(self):
        """Initialize the codebase analyzer."""
        self.logger = logging.getLogger(__name__)
        self.imports: Dict[str, List[str]] = {}
        self.functions: Dict[str, List[str]] = {}
        self.classes: Dict[str, List[str]] = {}
        self.file_dependencies: Dict[str, List[str]] = {}
        self.repo_path: Optional[Path] = None
    
    def set_repo_path(self, repo_path: Path) -> None:
        """
        Set the repository path to analyze.
        
        Args:
            repo_path: Path to the repository
        """
        self.repo_path = repo_path
        self.logger.info(f"Set repository path to: {repo_path}")
    
    def scan_codebase(self) -> Dict[str, Any]:
        """
        Scan and analyze the current codebase.
        
        Returns:
            Dictionary containing codebase analysis results
        """
        try:
            if not self.repo_path:
                raise ValueError("Repository path not set. Call set_repo_path first.")
            
            self.logger.info(f"Scanning codebase at: {self.repo_path}")
            
            # Get all Python files
            python_files = self._get_python_files()
            self.logger.info(f"Found {len(python_files)} Python files")
            
            # Analyze each file
            for file_path in python_files:
                self.logger.info(f"Analyzing file: {file_path}")
                self._analyze_file(file_path)
            
            # Build dependency graph
            self.logger.info("Building dependency graph...")
            self._build_dependency_graph()
            
            return {
                "imports": self.imports,
                "functions": self.functions,
                "classes": self.classes,
                "dependencies": self.file_dependencies,
                "file_count": len(python_files)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to scan codebase: {str(e)}")
            raise
    
    def _get_python_files(self) -> List[Path]:
        """Get all Python files in the codebase."""
        python_files = []
        for path in self.repo_path.rglob("*.py"):
            if not any(part.startswith(".") for part in path.parts):
                python_files.append(path)
        return python_files
    
    def _analyze_file(self, file_path: Path) -> None:
        """
        Analyze a single Python file.
        
        Args:
            file_path: Path to the file to analyze
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the file
            tree = ast.parse(content)
            
            # Extract imports
            imports = self._extract_imports(tree)
            self.imports[str(file_path)] = imports
            
            # Extract functions
            functions = self._extract_functions(tree)
            self.functions[str(file_path)] = functions
            
            # Extract classes
            classes = self._extract_classes(tree)
            self.classes[str(file_path)] = classes
            
        except Exception as e:
            self.logger.error(f"Failed to analyze file {file_path}: {str(e)}")
    
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements from the AST."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.unparse(node))
        return imports
    
    def _extract_functions(self, tree: ast.AST) -> List[str]:
        """Extract function definitions from the AST."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        return functions
    
    def _extract_classes(self, tree: ast.AST) -> List[str]:
        """Extract class definitions from the AST."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
        return classes
    
    def _build_dependency_graph(self) -> None:
        """Build the dependency graph between files."""
        for file_path, imports in self.imports.items():
            dependencies = []
            for imp in imports:
                # Try to resolve the import to a file
                module_name = imp.split('.')[0]
                for other_file in self.imports.keys():
                    if module_name in other_file:
                        dependencies.append(other_file)
            self.file_dependencies[file_path] = dependencies
    
    def get_file_dependencies(self, file_path: str) -> List[str]:
        """
        Get dependencies for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of dependent file paths
        """
        return self.file_dependencies.get(file_path, [])
    
    def get_file_functions(self, file_path: str) -> List[str]:
        """
        Get functions defined in a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of function names
        """
        return self.functions.get(file_path, [])
    
    def get_file_classes(self, file_path: str) -> List[str]:
        """
        Get classes defined in a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of class names
        """
        return self.classes.get(file_path, []) 