"""
Manages intelligent context selection for code generation.
"""

from typing import Dict, List, Any
from pathlib import Path
import ast
import networkx as nx
import logging
from ..analysis.feature_analyzer import ImplementationPlan

class ContextManager:
    def __init__(self):
        self.import_graph = nx.DiGraph()
        self.call_graph = nx.DiGraph()
        self.logger = logging.getLogger(__name__)
        
    def get_relevant_context(self, plan: ImplementationPlan, codebase_root: Path) -> Dict[str, Any]:
        """Get relevant context for implementing a feature."""
        context = {
            'primary_files': {},
            'related_files': {},
            'project_patterns': {}
        }
        
        # 1. Load directly affected files
        for file_path in plan.affected_files:
            context['primary_files'][file_path] = self._extract_file_context(file_path)
            
        # 2. Find related files through dependencies
        related_files = self._find_related_files(plan.affected_files)
        for file_path in related_files:
            context['related_files'][file_path] = self._extract_relevant_sections(file_path, plan)
            
        # 3. Extract project patterns
        context['project_patterns'] = self._extract_project_patterns(codebase_root)
        
        return context
        
    def _extract_file_context(self, file_path: str) -> Dict[str, Any]:
        """Extract relevant context from a file."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            tree = ast.parse(content)
            return {
                'content': content,
                'classes': self._extract_classes(tree),
                'functions': self._extract_functions(tree),
                'imports': self._extract_imports(tree)
            }
        except Exception as e:
            self.logger.error(f"Failed to extract context from {file_path}: {str(e)}")
            return {}
            
    def _find_related_files(self, primary_files: List[str]) -> List[str]:
        """Find related files through import and call graphs."""
        related = set()
        for file in primary_files:
            # Add direct imports
            related.update(self.import_graph.neighbors(file))
            # Add files that call or are called by this file
            related.update(self.call_graph.neighbors(file))
        return list(related - set(primary_files))
        
    def _extract_classes(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract class information from AST."""
        classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append({
                    'name': node.name,
                    'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                    'line_number': node.lineno
                })
        return classes
        
    def _extract_functions(self, tree: ast.AST) -> List[Dict[str, Any]]:
        """Extract function information from AST."""
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    'name': node.name,
                    'line_number': node.lineno
                })
        return functions
        
    def _extract_imports(self, tree: ast.AST) -> List[str]:
        """Extract import statements from AST."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.unparse(node))
        return imports
        
    def _extract_relevant_sections(self, file_path: str, plan: ImplementationPlan) -> Dict[str, Any]:
        """Extract relevant sections from a file based on the implementation plan."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                
            tree = ast.parse(content)
            return {
                'content': content,
                'classes': self._extract_classes(tree),
                'functions': self._extract_functions(tree),
                'imports': self._extract_imports(tree)
            }
        except Exception as e:
            self.logger.error(f"Failed to extract relevant sections from {file_path}: {str(e)}")
            return {}
            
    def _extract_project_patterns(self, codebase_root: Path) -> Dict[str, Any]:
        """Extract common patterns from the project."""
        patterns = {
            'import_style': self._analyze_import_style(codebase_root),
            'naming_conventions': self._analyze_naming_conventions(codebase_root),
            'error_handling': self._analyze_error_handling(codebase_root)
        }
        return patterns
        
    def _analyze_import_style(self, codebase_root: Path) -> Dict[str, Any]:
        """Analyze import style patterns in the project."""
        return {
            'absolute_imports': True,  # Default to True, should be analyzed
            'group_imports': True,     # Default to True, should be analyzed
            'sort_imports': True       # Default to True, should be analyzed
        }
        
    def _analyze_naming_conventions(self, codebase_root: Path) -> Dict[str, Any]:
        """Analyze naming conventions in the project."""
        return {
            'class_case': 'PascalCase',  # Default to PascalCase, should be analyzed
            'function_case': 'snake_case',  # Default to snake_case, should be analyzed
            'variable_case': 'snake_case'   # Default to snake_case, should be analyzed
        }
        
    def _analyze_error_handling(self, codebase_root: Path) -> Dict[str, Any]:
        """Analyze error handling patterns in the project."""
        return {
            'exception_types': ['Exception'],  # Default to generic Exception, should be analyzed
            'logging_style': 'info',          # Default to info level, should be analyzed
            'error_recovery': 'fail_fast'     # Default to fail fast, should be analyzed
        } 