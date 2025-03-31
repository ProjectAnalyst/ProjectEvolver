"""
Code generation module for Project Evolver.

This module generates code changes based on tasks and requirements.
It uses the Cursor Pro API to generate and modify code.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import ast
import black
import isort
import difflib
from dataclasses import dataclass
import re
from ..analysis.feature_analyzer import ImplementationPlan
from .context_manager import ContextManager


@dataclass
class CodeChange:
    """Represents a specific code change."""
    file_path: str
    start_line: int
    end_line: int
    new_content: str
    change_type: str  # 'insert', 'replace', 'delete'
    context: Dict[str, Any]


class CodeGenerator:
    """Generates code changes based on tasks."""
    
    def __init__(self):
        """Initialize the code generator."""
        self.context_manager = ContextManager()
        self.logger = logging.getLogger(__name__)
        self.context: Dict[str, Any] = {}
        self.codebase_structure: Dict[str, Any] = {}
        self.import_graph: Dict[str, List[str]] = {}
    
    def analyze_codebase(self, root_dir: str) -> None:
        """
        Analyze the codebase structure.
        
        Args:
            root_dir: Root directory of the codebase
        """
        try:
            root_path = Path(root_dir)
            self._analyze_directory(root_path)
            self._build_import_graph()
            self.logger.info("Codebase analysis completed")
        except Exception as e:
            self.logger.error(f"Failed to analyze codebase: {str(e)}")
            raise
    
    def _analyze_directory(self, directory: Path) -> None:
        """Analyze a directory and its contents."""
        for item in directory.iterdir():
            if item.is_file() and item.suffix == '.py':
                self._analyze_file(item)
            elif item.is_dir() and not item.name.startswith('.'):
                self._analyze_directory(item)
    
    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a Python file's structure."""
        try:
            with open(file_path, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            file_info = {
                'classes': [],
                'functions': [],
                'imports': [],
                'dependencies': set()
            }
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    file_info['classes'].append({
                        'name': node.name,
                        'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)],
                        'line_number': node.lineno
                    })
                elif isinstance(node, ast.FunctionDef):
                    file_info['functions'].append({
                        'name': node.name,
                        'line_number': node.lineno
                    })
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    file_info['imports'].append(ast.unparse(node))
                    if isinstance(node, ast.ImportFrom):
                        file_info['dependencies'].add(node.module)
            
            self.codebase_structure[str(file_path)] = file_info
            
        except Exception as e:
            self.logger.error(f"Failed to analyze {file_path}: {str(e)}")
    
    def _build_import_graph(self) -> None:
        """Build a graph of module dependencies."""
        for file_path, info in self.codebase_structure.items():
            self.import_graph[file_path] = list(info['dependencies'])
    
    def generate_changes(self, plan: ImplementationPlan, codebase_root: Path) -> Dict[str, Any]:
        """Generate code changes based on implementation plan."""
        # Get relevant context
        context = self.context_manager.get_relevant_context(plan, codebase_root)
        
        prompt = f"""Generate implementation code based on this plan and context:

IMPLEMENTATION PLAN:
{self._format_plan(plan)}

PRIMARY FILES:
{self._format_primary_context(context['primary_files'])}

RELATED CONTEXT:
{self._format_related_context(context['related_files'])}

PROJECT PATTERNS:
{self._format_patterns(context['project_patterns'])}

Generate complete, implementation-ready code that:
1. Follows existing project patterns
2. Maintains compatibility with related code
3. Includes proper error handling and tests
4. Documents changes clearly

Format your response as:
---FILE: <filename>---
```python
<complete file content>
```
"""
        
        response = self._get_llm_response(
            "You are an expert code implementer. Generate production-ready code that integrates seamlessly with the existing codebase.",
            prompt
        )
        
        return self._parse_changes(response)
    
    def _get_current_content(self, file_paths: List[str]) -> Dict[str, str]:
        """
        Get current content of files.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Dictionary mapping file paths to their content
        """
        content = {}
        for file_path in file_paths:
            try:
                with open(file_path, 'r') as f:
                    content[file_path] = f.read()
            except Exception as e:
                self.logger.error(f"Failed to read {file_path}: {str(e)}")
        return content
    
    def _generate_file_changes(self, file_path: str, current_content: str, task: Any) -> List[CodeChange]:
        """
        Generate changes for a specific file.
        
        Args:
            file_path: Path to the file
            current_content: Current content of the file
            task: Task to generate changes for
            
        Returns:
            List of code changes
        """
        try:
            changes = []
            tree = ast.parse(current_content)
            
            # Analyze existing code structure
            file_info = self.codebase_structure.get(file_path, {})
            existing_classes = {c['name']: c for c in file_info.get('classes', [])}
            existing_functions = {f['name']: f for f in file_info.get('functions', [])}
            
            # Generate changes based on requirements
            for req in task.requirements:
                if "add method" in req.lower():
                    # Find the appropriate class to add the method to
                    target_class = self._find_target_class(req, existing_classes)
                    if target_class:
                        new_method = self._generate_method(req, existing_classes[target_class])
                        changes.append(CodeChange(
                            file_path=file_path,
                            start_line=existing_classes[target_class]['line_number'],
                            end_line=existing_classes[target_class]['line_number'],
                            new_content=new_method,
                            change_type='insert',
                            context={'class': target_class}
                        ))
                elif "modify method" in req.lower():
                    # Find and modify existing method
                    target_method = self._find_target_method(req, existing_functions)
                    if target_method:
                        modified_method = self._modify_method(req, existing_functions[target_method])
                        changes.append(CodeChange(
                            file_path=file_path,
                            start_line=existing_functions[target_method]['line_number'],
                            end_line=existing_functions[target_method]['line_number'],
                            new_content=modified_method,
                            change_type='replace',
                            context={'method': target_method}
                        ))
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Failed to generate changes for {file_path}: {str(e)}")
            return []
    
    def _find_target_class(self, requirement: str, existing_classes: Dict[str, Any]) -> Optional[str]:
        """Find the most appropriate class to add a method to."""
        # Use context and requirement analysis to find the best class
        # This is a simplified version - you might want to make it more sophisticated
        for class_name, class_info in existing_classes.items():
            if any(method in requirement.lower() for method in class_info['methods']):
                return class_name
        return list(existing_classes.keys())[0] if existing_classes else None
    
    def _find_target_method(self, requirement: str, existing_functions: Dict[str, Any]) -> Optional[str]:
        """Find the method to modify based on the requirement."""
        # Use context and requirement analysis to find the best method
        for func_name, func_info in existing_functions.items():
            if func_name.lower() in requirement.lower():
                return func_name
        return None
    
    def _generate_method(self, requirement: str, class_info: Dict[str, Any]) -> str:
        """Generate a new method based on the requirement."""
        # This is where you'd use your AI model to generate the method
        # For now, we'll use a simple template
        method_name = self._extract_method_name(requirement)
        return f"""
    def {method_name}(self):
        \"\"\"Generated method based on requirement: {requirement}\"\"\"
        # TODO: Implement method
        pass
"""
    
    def _modify_method(self, requirement: str, method_info: Dict[str, Any]) -> str:
        """Modify an existing method based on the requirement."""
        # This is where you'd use your AI model to modify the method
        # For now, we'll use a simple template
        return f"""
    def {method_info['name']}(self):
        \"\"\"Modified method based on requirement: {requirement}\"\"\"
        # TODO: Implement modifications
        pass
"""
    
    def _extract_method_name(self, requirement: str) -> str:
        """Extract a method name from a requirement."""
        # Convert requirement to snake_case method name
        words = requirement.lower().split()
        return '_'.join(words)
    
    def apply_changes(self, changes: Dict[str, List[CodeChange]]) -> None:
        """
        Apply the generated changes to the files.
        
        Args:
            changes: Dictionary mapping file paths to lists of code changes
        """
        for file_path, file_changes in changes.items():
            try:
                with open(file_path, 'r') as f:
                    content = f.read().splitlines()
                
                # Sort changes by line number in reverse order to avoid offset issues
                file_changes.sort(key=lambda x: x.start_line, reverse=True)
                
                for change in file_changes:
                    new_lines = change.new_content.strip().splitlines()
                    if change.change_type == 'insert':
                        content.insert(change.start_line - 1, *new_lines)
                    elif change.change_type == 'replace':
                        content[change.start_line - 1:change.end_line] = new_lines
                    elif change.change_type == 'delete':
                        del content[change.start_line - 1:change.end_line]
                
                # Write the modified content back to the file
                with open(file_path, 'w') as f:
                    f.write('\n'.join(content))
                
                # Re-analyze the file
                self._analyze_file(Path(file_path))
                
            except Exception as e:
                self.logger.error(f"Failed to apply changes to {file_path}: {str(e)}")
    
    def validate_code(self, code: str) -> bool:
        """
        Validate generated code.
        
        Args:
            code: Code to validate
            
        Returns:
            True if code is valid, False otherwise
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
    
    def update_context(self, context: Dict[str, Any]) -> None:
        """
        Update the generation context.
        
        Args:
            context: New context information
        """
        self.context.update(context)
    
    def get_context(self) -> Dict[str, Any]:
        """
        Get the current generation context.
        
        Returns:
            Current context dictionary
        """
        return self.context.copy()
    
    def _format_plan(self, plan: ImplementationPlan) -> str:
        """Format implementation plan for LLM prompt."""
        return f"""
Feature: {plan.feature_name}
Status: {plan.status}
Current State: {plan.current_state}
Required Changes:
{chr(10).join(f"- {change}" for change in plan.required_changes)}
Implementation Approach: {plan.implementation_approach}
Affected Files: {', '.join(plan.affected_files)}
Dependencies: {', '.join(plan.dependencies)}
Priority: {plan.priority}
"""
        
    def _format_primary_context(self, primary_files: Dict[str, Any]) -> str:
        """Format primary files context for LLM prompt."""
        formatted = []
        for file_path, context in primary_files.items():
            formatted.append(f"\nFile: {file_path}")
            formatted.append("Classes:")
            for cls in context['classes']:
                formatted.append(f"- {cls['name']} (line {cls['line_number']})")
                formatted.append(f"  Methods: {', '.join(cls['methods'])}")
            formatted.append("Functions:")
            for func in context['functions']:
                formatted.append(f"- {func['name']} (line {func['line_number']})")
            formatted.append("Imports:")
            for imp in context['imports']:
                formatted.append(f"- {imp}")
        return "\n".join(formatted)
        
    def _format_related_context(self, related_files: Dict[str, Any]) -> str:
        """Format related files context for LLM prompt."""
        formatted = []
        for file_path, context in related_files.items():
            formatted.append(f"\nRelated File: {file_path}")
            formatted.append("Classes:")
            for cls in context['classes']:
                formatted.append(f"- {cls['name']}")
            formatted.append("Functions:")
            for func in context['functions']:
                formatted.append(f"- {func['name']}")
        return "\n".join(formatted)
        
    def _format_patterns(self, patterns: Dict[str, Any]) -> str:
        """Format project patterns for LLM prompt."""
        formatted = []
        formatted.append("\nProject Patterns:")
        formatted.append("Import Style:")
        for key, value in patterns['import_style'].items():
            formatted.append(f"- {key}: {value}")
        formatted.append("\nNaming Conventions:")
        for key, value in patterns['naming_conventions'].items():
            formatted.append(f"- {key}: {value}")
        formatted.append("\nError Handling:")
        for key, value in patterns['error_handling'].items():
            formatted.append(f"- {key}: {value}")
        return "\n".join(formatted)
        
    def _parse_changes(self, response: str) -> Dict[str, List[CodeChange]]:
        """Parse LLM response into code changes."""
        changes = {}
        current_file = None
        current_content = []
        
        for line in response.split('\n'):
            if line.startswith('---FILE:'):
                if current_file and current_content:
                    changes[current_file] = self._create_code_changes(current_file, '\n'.join(current_content))
                    current_content = []
                current_file = line.replace('---FILE:', '').strip()
            elif line.startswith('CHANGES EXPLAINED:'):
                if current_file and current_content:
                    changes[current_file] = self._create_code_changes(current_file, '\n'.join(current_content))
                break
            elif current_file:
                current_content.append(line)
                
        return changes
        
    def _create_code_changes(self, file_path: str, content: str) -> List[CodeChange]:
        """Create CodeChange objects from file content."""
        try:
            tree = ast.parse(content)
            changes = []
            
            # Analyze the AST to determine change types and line numbers
            for node in ast.walk(tree):
                if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    changes.append(CodeChange(
                        file_path=file_path,
                        start_line=node.lineno,
                        end_line=node.end_lineno or node.lineno,
                        new_content=ast.unparse(node),
                        change_type='replace',
                        context={'type': type(node).__name__}
                    ))
                    
            return changes
            
        except Exception as e:
            self.logger.error(f"Failed to create code changes for {file_path}: {str(e)}")
            return [] 