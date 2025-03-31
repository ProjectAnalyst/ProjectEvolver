"""
Codebase analysis module for Project Evolver.

This module analyzes the codebase to identify implemented features and functionality.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import ast
from ..utils.llm_logger import LLMLogger

class CodebaseAnalyzer:
    """Analyzes codebase to identify implemented features."""
    
    def __init__(self):
        """Initialize the codebase analyzer."""
        self.logger = logging.getLogger(__name__)
        self.llm_logger = LLMLogger()
        self.features: Dict[str, List[Dict[str, Any]]] = {}
        self.repo_path: Optional[Path] = None
        self.whitepaper_features: List[Dict[str, Any]] = []
        
    def set_repo_path(self, repo_path: str) -> None:
        """
        Set the repository path for analysis.
        
        Args:
            repo_path: Path to the repository root
        """
        self.repo_path = Path(repo_path)
        
    def set_whitepaper_features(self, features: List[Dict[str, Any]]) -> None:
        """
        Set the features extracted from the whitepaper for reference.
        
        Args:
            features: List of features from the whitepaper
        """
        self.whitepaper_features = features
        
    def scan_codebase(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Alias for analyze_codebase to maintain compatibility.
        
        Returns:
            Dictionary mapping file paths to lists of implemented features
        """
        return self.analyze_codebase("")
        
    def analyze_codebase(self, root_dir: str) -> Dict[str, Any]:
        """Create a detailed index of the codebase."""
        try:
            self.llm_logger.start_session("codebase_analysis")
            
            root_path = Path(root_dir) if root_dir else self.repo_path
            if not root_path:
                raise ValueError("No repository path set")
                
            codebase_index = {}
            
            # Analyze each Python file
            for file_path in root_path.rglob("*.py"):
                if self._should_skip_file(file_path):
                    continue
                    
                self.logger.info(f"Analyzing file: {file_path}")
                analysis = self._analyze_file(file_path)
                
                if analysis:
                    # Store the complete analysis text
                    codebase_index["analysis_text"] = analysis
            
            return codebase_index
            
        except Exception as e:
            self.logger.error(f"Failed to analyze codebase: {str(e)}")
            raise

    def _analyze_file(self, file_path: Path) -> str:
        """Analyze a single file and return the complete analysis text."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            response = self._get_llm_response(
                "You are a detailed code analysis expert. Extract ALL concrete functionalities with high granularity.",
                f"""Analyze this Python file and extract ALL concrete functionalities.
Be extremely detailed and specific. Do not generalize.

File: {file_path}

Code:
```python
{content}
```
"""
            )
            
            return response
            
        except Exception as e:
            self.logger.error(f"Failed to analyze file {file_path}: {str(e)}")
            return ""

    def _should_skip_file(self, file_path: Path) -> bool:
        """
        Determine if a file should be skipped during analysis.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file should be skipped, False otherwise
        """
        # Define directories and files to exclude
        exclude_dirs = {'backups', 'docs', '__pycache__', '.git', '.idea', '.vscode', 'venv', 'env'}
        exclude_files = {'requirements.txt', 'README.md', '.gitignore', '.env'}
        
        # Skip if any part of the path is in exclude_dirs
        if any(part in exclude_dirs for part in file_path.parts):
            return True
            
        # Skip if file is in exclude_files
        if file_path.name in exclude_files:
            return True
            
        # Skip hidden files and directories
        if any(part.startswith('.') for part in file_path.parts):
            return True
            
        return False

    def _categorize_features(self, file_analysis: Dict[str, Any], codebase_index: Dict[str, Any]) -> None:
        """
        Categorize and add features from file analysis to the codebase index.
        
        Args:
            file_analysis: Analysis results for a single file
            codebase_index: The overall codebase index to update
        """
        try:
            # Add functions
            for func in file_analysis.get("functions", []):
                codebase_index["features"].append({
                    "type": "function",
                    "name": func["name"],
                    "description": func.get("description", ""),
                    "confidence": func.get("confidence", "medium")
                })
            
            # Add classes
            for cls in file_analysis.get("classes", []):
                codebase_index["features"].append({
                    "type": "class",
                    "name": cls["name"],
                    "description": cls.get("description", ""),
                    "confidence": cls.get("confidence", "medium")
                })
            
            # Add APIs
            for api in file_analysis.get("apis", []):
                codebase_index["apis"].append({
                    "name": api["name"],
                    "description": api.get("description", ""),
                    "confidence": api.get("confidence", "medium")
                })
            
            # Add UI elements
            for ui in file_analysis.get("ui_elements", []):
                codebase_index["ui_elements"].append({
                    "name": ui["name"],
                    "description": ui.get("description", ""),
                    "confidence": ui.get("confidence", "medium")
                })
            
            # Add constants
            for const in file_analysis.get("constants", []):
                codebase_index["constants"].append({
                    "name": const["name"],
                    "value": const.get("value", ""),
                    "purpose": const.get("purpose", ""),
                    "confidence": const.get("confidence", "medium")
                })
            
            # Add strings
            for string in file_analysis.get("strings", []):
                codebase_index["strings"].append({
                    "context": string.get("context", ""),
                    "text": string.get("text", ""),
                    "purpose": string.get("purpose", ""),
                    "confidence": string.get("confidence", "medium")
                })
                
        except Exception as e:
            self.logger.error(f"Failed to categorize features: {str(e)}")
            raise

    def _get_llm_response(self, system_prompt: str, user_prompt: str) -> str:
        """
        Get response from OpenAI's GPT-4 model.
        
        Args:
            system_prompt: The system prompt for the LLM
            user_prompt: The user prompt for the LLM
            
        Returns:
            str: The LLM's response
        """
        try:
            import os
            from openai import OpenAI
            from dotenv import load_dotenv
            import httpx
            
            # Load environment variables from .env file
            load_dotenv()
            
            # Get API key
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            
            # Create a custom transport without proxies
            transport = httpx.HTTPTransport(retries=3)
            
            # Initialize OpenAI client with custom transport
            client = OpenAI(
                api_key=api_key,
                http_client=httpx.Client(transport=transport)
            )
            
            # Format the prompt with system and user messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Get response from OpenAI's API
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                temperature=0.7,
                max_tokens=4000
            )
            
            response_content = response.choices[0].message.content
            
            # Log the interaction
            metadata = {
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 4000,
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            self.llm_logger.log_interaction(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response=response_content,
                metadata=metadata
            )
            
            return response_content
            
        except Exception as e:
            self.logger.error(f"Failed to get LLM response: {str(e)}")
            raise

    def _format_whitepaper_features(self) -> str:
        """
        Format whitepaper features for inclusion in the prompt.
        
        Returns:
            Formatted string of whitepaper features
        """
        if not self.whitepaper_features:
            return "No whitepaper features available for reference."
            
        formatted = []
        for feature in self.whitepaper_features:
            formatted.append(f"- {feature['name']}: {feature['description']}")
        return "\n".join(formatted)
        
    def _parse_llm_response(self, response: str) -> List[Dict[str, Any]]:
        """
        Parse LLM response into structured format.
        
        Args:
            response: Response from LLM
            
        Returns:
            List of parsed features
        """
        features = []
        current_section = None
        current_content = []
        
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('FEATURES:'):
                if current_section and current_content:
                    features.extend(self._process_section(current_section, current_content))
                current_section = 'features'
                current_content = []
            elif line.startswith('APIs/ENDPOINTS:'):
                if current_section and current_content:
                    features.extend(self._process_section(current_section, current_content))
                current_section = 'apis'
                current_content = []
            elif line.startswith('UI COMPONENTS:'):
                if current_section and current_content:
                    features.extend(self._process_section(current_section, current_content))
                current_section = 'ui'
                current_content = []
            elif line.startswith('LOGIC/ALGORITHMS:'):
                if current_section and current_content:
                    features.extend(self._process_section(current_section, current_content))
                current_section = 'logic'
                current_content = []
            elif line.startswith('- '):
                current_content.append(line[2:])
        
        # Process final section
        if current_section and current_content:
            features.extend(self._process_section(current_section, current_content))
            
        return features
        
    def _process_section(self, section: str, content: List[str]) -> List[Dict[str, Any]]:
        """
        Process a section of the LLM response.
        
        Args:
            section: Section type (features, apis, ui, logic)
            content: List of items in the section
            
        Returns:
            List of processed features
        """
        features = []
        for item in content:
            features.append({
                "type": section,
                "description": item
            })
        return features 