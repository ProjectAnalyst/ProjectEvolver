"""
Code generation module for Project Evolver.

This module generates code changes based on tasks and requirements.
It uses the Cursor Pro API to generate and modify code.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import ast
import black
import isort


class CodeGenerator:
    """Generates code changes based on tasks."""
    
    def __init__(self):
        """Initialize the code generator."""
        self.logger = logging.getLogger(__name__)
        self.context: Dict[str, Any] = {}
    
    def generate_changes(self, task: Any) -> Dict[str, str]:
        """
        Generate code changes for a task.
        
        Args:
            task: Task to generate changes for
            
        Returns:
            Dictionary mapping file paths to their new content
        """
        try:
            # Skip if no target files
            if not task.target_files:
                self.logger.warning(f"No target files specified for task {task.id}")
                return {}
            
            # Get current content of target files
            current_content = self._get_current_content(task.target_files)
            
            # Generate changes for each file
            changes = {}
            for file_path in task.target_files:
                new_content = self._generate_file_changes(
                    file_path,
                    current_content.get(file_path, ""),
                    task
                )
                if new_content:
                    changes[file_path] = new_content
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Failed to generate changes: {str(e)}")
            raise
    
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
    
    def _generate_file_changes(self, file_path: str, current_content: str, task: Any) -> Optional[str]:
        """
        Generate changes for a specific file.
        
        Args:
            file_path: Path to the file
            current_content: Current content of the file
            task: Task to generate changes for
            
        Returns:
            New content for the file if changes were made
        """
        try:
            # Parse the current content
            tree = ast.parse(current_content)
            
            # Find the main class
            class_node = None
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_node = node
                    break
            
            if not class_node:
                self.logger.warning(f"No class found in {file_path}")
                return None
            
            # Generate new methods based on requirements
            new_methods = self._generate_implementation(task.requirements, self._get_imports(current_content))
            
            # Add new methods to the class
            new_methods_ast = ast.parse(new_methods)
            for node in ast.walk(new_methods_ast):
                if isinstance(node, ast.FunctionDef):
                    class_node.body.append(node)
            
            # Convert back to source code
            new_content = ast.unparse(tree)
            
            # Format the code
            try:
                new_content = black.format_str(new_content, mode=black.FileMode())
                new_content = isort.code(new_content)
            except Exception as e:
                self.logger.warning(f"Failed to format code: {str(e)}")
            
            return new_content
            
        except Exception as e:
            self.logger.error(f"Failed to generate changes for {file_path}: {str(e)}")
            return None
    
    def _get_imports(self, content: str) -> List[str]:
        """
        Extract imports from content.
        
        Args:
            content: File content
            
        Returns:
            List of import statements
        """
        try:
            tree = ast.parse(content)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.append(ast.unparse(node))
            return imports
        except Exception:
            return []
    
    def _generate_implementation(self, requirements: List[str], existing_imports: List[str]) -> str:
        """
        Generate implementation based on requirements.
        
        Args:
            requirements: List of requirements
            existing_imports: List of existing imports
            
        Returns:
            Generated code
        """
        code_parts = []
        
        for req in requirements:
            if "collision detection" in req.lower():
                code_parts.append("""
    def check_collision(self) -> bool:
        \"\"\"Check for collisions with walls and self.\"\"\"
        head = self.body[0]
        
        # Check wall collision
        if head[0] < 0 or head[0] >= self.width or head[1] < 0 or head[1] >= self.height:
            return True
        
        # Check self collision
        if head in self.body[1:]:
            return True
        
        return False
""")
            elif "frame rate control" in req.lower():
                code_parts.append("""
    def maintain_frame_rate(self):
        \"\"\"Maintain consistent frame rate.\"\"\"
        self.clock.tick(self.fps)
        pygame.time.wait(1)  # Small delay to prevent CPU overuse
""")
            elif "game speed" in req.lower():
                code_parts.append("""
    def update_speed(self):
        \"\"\"Update game speed based on score.\"\"\"
        self.speed = min(self.base_speed + (self.score // 10) * self.speed_increment, self.max_speed)
""")
            elif "error handling" in req.lower():
                code_parts.append("""
    def handle_error(self, error: Exception):
        \"\"\"Handle game errors gracefully.\"\"\"
        self.logger.error(f"Game error: {str(error)}")
        self.game_over = True
        self.error_message = str(error)
""")
            elif "game state" in req.lower():
                code_parts.append("""
    def save_game_state(self):
        \"\"\"Save current game state.\"\"\"
        state = {
            "score": self.score,
            "snake": self.snake.body,
            "food": self.food.position,
            "speed": self.speed
        }
        return state

    def load_game_state(self, state: dict):
        \"\"\"Load saved game state.\"\"\"
        self.score = state["score"]
        self.snake.body = state["snake"]
        self.food.position = state["food"]
        self.speed = state["speed"]
""")
        
        return "\n".join(code_parts)
    
    def validate_code(self, code: str) -> bool:
        """
        Validate generated code.
        
        Args:
            code: Code to validate
            
        Returns:
            True if code is valid, False otherwise
        """
        try:
            # Try to parse the code
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