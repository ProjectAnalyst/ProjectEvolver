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
        
    def analyze_codebase(self, root_dir: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Analyze the entire codebase to identify implemented features.
        
        Args:
            root_dir: Root directory of the codebase (optional)
            
        Returns:
            Dictionary mapping file paths to lists of implemented features
        """
        try:
            # Start a new LLM logging session
            self.llm_logger.start_session("codebase_analysis")
            
            # Use provided root_dir or repo_path
            root_path = Path(root_dir) if root_dir else self.repo_path
            if not root_path:
                raise ValueError("No repository path set. Call set_repo_path first.")
                
            self.features = {}
            
            # Define directories and files to exclude
            exclude_dirs = {'backups', 'docs', '__pycache__', '.git', '.idea', '.vscode', 'venv', 'env'}
            exclude_files = {'requirements.txt', 'README.md', '.gitignore', '.env'}
            
            # Walk through all Python files
            for file_path in root_path.rglob("*.py"):
                # Skip if any part of the path is in exclude_dirs
                if any(part in exclude_dirs for part in file_path.parts):
                    continue
                    
                # Skip if file is in exclude_files
                if file_path.name in exclude_files:
                    continue
                    
                # Skip hidden files and directories
                if any(part.startswith('.') for part in file_path.parts):
                    continue
                    
                self.logger.info(f"Analyzing file: {file_path}")
                self._analyze_file(file_path)
            
            return self.features
            
        except Exception as e:
            self.logger.error(f"Failed to analyze codebase: {str(e)}")
            raise
            
    def _analyze_file(self, file_path: Path) -> None:
        """
        Analyze a single file to identify implemented features.
        
        Args:
            file_path: Path to the file to analyze
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create prompt for LLM
            prompt = f"""You are given source code from a web application.

Below are the features we want to eventually implement (extracted from our whitepaper):
{self._format_whitepaper_features()}

Analyze the given code and identify:
1. Which features from our whitepaper are partially or fully implemented in this file
2. Any other implemented features or functionality that might be related to our goals
3. Concrete actions, APIs, UI components, or logic that are already present

Code:
```
{content}
```

Provide your analysis in this format:
FEATURES:
- Feature 1: <description> [Related to whitepaper feature: <feature name>]
- Feature 2: <description> [Related to whitepaper feature: <feature name>]
...

APIs/ENDPOINTS:
- API 1: <description> [Related to whitepaper feature: <feature name>]
- API 2: <description> [Related to whitepaper feature: <feature name>]
...

UI COMPONENTS:
- Component 1: <description> [Related to whitepaper feature: <feature name>]
- Component 2: <description> [Related to whitepaper feature: <feature name>]
...

LOGIC/ALGORITHMS:
- Logic 1: <description> [Related to whitepaper feature: <feature name>]
- Logic 2: <description> [Related to whitepaper feature: <feature name>]
..."""
            
            # Get response from LLM
            response = self._get_llm_response(
                "You are a code analysis expert. Analyze the code and identify implemented features, particularly those related to our whitepaper requirements.",
                prompt
            )
            
            # Parse response into structured format
            features = self._parse_llm_response(response)
            
            # Store features for this file
            self.features[str(file_path)] = features
            
        except Exception as e:
            self.logger.error(f"Failed to analyze file {file_path}: {str(e)}")
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
        
    def _get_llm_response(self, system_prompt: str, user_prompt: str) -> str:
        """Get response from OpenAI's GPT-4 model."""
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