"""
Gap analysis module for Project Evolver.

This module analyzes the differences between the current codebase state
and the requirements specified in the whitepaper.
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass
from ..utils.llm_logger import LLMLogger
from .codebase_analyzer import CodebaseAnalyzer
import os


@dataclass
class Gap:
    """Represents a gap between current state and desired state."""
    section: str
    status: str
    reason: str
    affected_files: List[str]
    priority: int
    implementation_details: Dict[str, Any]
    suggested_fixes: List[str]  # Suggested fixes
    type: str = "general"  # More generic default type


class GapAnalyzer:
    """Analyzes gaps between current codebase and whitepaper requirements."""
    
    def __init__(self):
        """Initialize the gap analyzer."""
        self.logger = logging.getLogger(__name__)
        self.gaps: List[Gap] = []
        self.codebase_index: Dict[str, Any] = {}
        self.codebase_analyzer = CodebaseAnalyzer()
        self.llm_logger = LLMLogger()
        self.file_contents = {}
        
    def analyze_codebase(self, root_dir: str) -> None:
        """
        Analyze the codebase structure and create an index.
        
        Args:
            root_dir: Root directory of the codebase
        """
        try:
            # First get the CodebaseAnalyzer results
            self.codebase_index = self.codebase_analyzer.analyze_codebase(root_dir)
            
            # Now also read the actual file contents
            self.file_contents = {}
            for file_path in self.codebase_index.keys():
                full_path = os.path.join(root_dir, file_path)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        self.file_contents[file_path] = f.read()
                    self.logger.info(f"Successfully read contents of {file_path}")
                except Exception as e:
                    self.logger.error(f"Failed to read {file_path}: {str(e)}")
                
            self.logger.info("Codebase analysis completed")
        except Exception as e:
            self.logger.error(f"Failed to analyze codebase: {str(e)}")
            raise

    def identify_gaps(self, whitepaper: Dict[str, Any], current_state: Dict[str, Any]) -> List[Gap]:
        """
        Compare whitepaper requirements against current codebase implementation.
        
        Args:
            whitepaper: Dictionary containing whitepaper analysis results
            current_state: Dictionary containing current codebase state
            
        Returns:
            List of Gap objects representing identified gaps
        """
        try:
            self.gaps = []
            
            # Start a new LLM logging session for gap analysis
            self.llm_logger.start_session("gap_analysis")
            
            # Get features from whitepaper
            features = whitepaper.get("features", [])
            if not features:
                self.logger.warning("No features found in whitepaper analysis")
                return []
            
            self.logger.info(f"Total features to analyze: {len(features)}")
            
            # Get actual files and their contents from current_state
            actual_files = list(current_state.keys())
            self.logger.info(f"Found {len(actual_files)} files in codebase")
            
            # Analyze each feature from whitepaper
            for feature in features:
                feature_name = feature["name"]
                feature_desc = feature["description"]
                feature_section = feature.get("section", "general")
                
                self.logger.info(f"Analyzing feature: {feature_name}")
                
                # Check if feature is implemented
                status, reason, files, details, suggestions = self._analyze_feature(
                    feature_name,
                    feature_desc,
                    current_state,
                    actual_files
                )
                
                self.logger.info(f"Analysis result for {feature_name}: {status}")
                
                # Create gap if feature is not fully implemented
                if status.lower() not in ["complete", "completed", "implemented", "done", "finished", "ready"]:
                    gap = Gap(
                        section=feature_section,
                        status=status.lower(),
                        reason=reason,
                        affected_files=files,
                        priority=self._determine_priority(status.lower(), feature_section),
                        implementation_details=details,
                        suggested_fixes=suggestions,
                        type=feature_section.split(" - ")[0].lower()
                    )
                    self.gaps.append(gap)
                    self.logger.info(f"Gap identified for {feature_name}: {reason}")
            
            self.logger.info(f"Total gaps identified: {len(self.gaps)}")
            return self.gaps
            
        except Exception as e:
            self.logger.error(f"Failed to identify gaps: {str(e)}")
            raise
            
    def _analyze_feature(self, 
                        feature_name: str,
                        feature_desc: str,
                        current_state: Dict[str, Any],
                        actual_files: List[str]) -> tuple[str, str, List[str], Dict[str, Any], List[str]]:
        """
        Analyze a feature to determine its implementation status.
        
        Args:
            feature_name: Name of the feature to analyze
            feature_desc: Description of the feature
            current_state: Dictionary containing current codebase state
            actual_files: List of existing files in the codebase
            
        Returns:
            Tuple of (status, reason, affected_files, details, suggestions)
        """
        try:
            # Create prompt for LLM
            prompt = f"""Analyze if this feature is implemented in the codebase.

Feature to analyze:
Name: {feature_name}
Description: {feature_desc}

Current codebase structure:
Files that exist: {', '.join(actual_files)}

Actual code from relevant files:
"""
            # Add the actual file contents
            for file_path in actual_files:
                prompt += f"\n=== {file_path} ===\n"
                if file_path in self.file_contents:
                    prompt += f"```python\n{self.file_contents[file_path]}\n```\n"
                else:
                    prompt += "(File not accessible)\n"

            prompt += """
IMPORTANT: 
1. Analyze the actual code shown above.
2. Be specific about what exists and what's missing.
3. Reference specific parts of the code in your analysis.
4. If suggesting changes, consider the existing code structure.

Provide your analysis in this format:
STATUS: <complete/partial/missing/planned>
REASON: <explanation with specific references to the code>
FILES: <affected files>
CURRENT_STATE: <detailed analysis of current implementation>
MISSING_COMPONENTS:
- <component 1>
- <component 2>
IMPLEMENTATION_STRATEGY: <explain whether to modify existing files or create new ones, and why>
SUGGESTED_APPROACH: <detailed implementation approach>
SUGGESTIONS:
- <suggestion 1>
- <suggestion 2>
"""
            
            # Get response from LLM
            response = self._get_llm_response(
                "You are a code analysis expert. Analyze if the feature is implemented and provide detailed feedback. Focus on the actual codebase structure and suggest improvements within existing files.",
                prompt
            )
            
            # Parse response
            status = self._extract_section(response, "STATUS:")
            reason = self._extract_section(response, "REASON:")
            files = [f.strip() for f in self._extract_section(response, "FILES:").split('\n') if f.strip()]
            current_state = self._extract_section(response, "CURRENT_STATE:")
            missing_components = [c.strip()[2:] for c in self._extract_section(response, "MISSING_COMPONENTS:").split('\n') if c.strip().startswith('- ')]
            suggested_approach = self._extract_section(response, "SUGGESTED_APPROACH:")
            suggestions = [s.strip()[2:] for s in self._extract_section(response, "SUGGESTIONS:").split('\n') if s.strip().startswith('- ')]
            
            # Validate files mentioned in response
            valid_files = [f for f in files if f in actual_files]
            if len(valid_files) != len(files):
                self.logger.warning(f"Some files mentioned in analysis do not exist: {set(files) - set(valid_files)}")
            
            details = {
                "current_state": current_state,
                "missing_components": missing_components,
                "suggested_approach": suggested_approach
            }
            
            return status, reason, valid_files, details, suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to analyze feature: {str(e)}")
            return "error", str(e), [], {}, []
            
    def _extract_section(self, response: str, section: str) -> str:
        """Extract content from a section in the LLM response."""
        try:
            start = response.find(section)
            if start == -1:
                return ""
            start += len(section)
            end = response.find('\n\n', start)
            if end == -1:
                end = len(response)
            return response[start:end].strip()
        except Exception:
            return ""
            
    def _determine_priority(self, status: str, section: str) -> int:
        """Determine priority level for a gap."""
        # Base priority on status
        if status == "missing":
            base_priority = 3
        elif status == "partial":
            base_priority = 2
        else:
            base_priority = 1
            
        # Adjust based on section
        if "core" in section.lower() or "essential" in section.lower():
            base_priority += 2
        elif "feature" in section.lower() or "enhancement" in section.lower():
            base_priority += 1
            
        return min(base_priority, 5)  # Cap at 5
        
    def _get_llm_response(self, system_prompt: str, user_prompt: str) -> str:
        """Get response from OpenAI's GPT-4 model."""
        try:
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

    def implement_gap(self, gap: Gap, current_state: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate implementation code for a given gap.
        
        Args:
            gap: Gap object containing analysis details
            current_state: Current state of the codebase
            
        Returns:
            Dict mapping file paths to their updated content
        """
        try:
            # Start implementation session
            self.llm_logger.start_session("gap_implementation")
            
            # Create implementation prompt
            prompt = f"""Generate the implementation code for the following gap:

FEATURE GAP:
Name: {gap.section}
Status: {gap.status}
Reason: {gap.reason}

CURRENT STATE:
{gap.implementation_details['current_state']}

MISSING COMPONENTS:
{chr(10).join(f"- {component}" for component in gap.implementation_details['missing_components'])}

IMPLEMENTATION APPROACH:
{gap.implementation_details['suggested_approach']}

FILES TO MODIFY:
{chr(10).join(gap.affected_files)}

Current code in affected files:
"""
            # Add current file contents
            for file_path in gap.affected_files:
                if file_path in current_state:
                    prompt += f"\n--- {file_path} ---\n"
                    if isinstance(current_state[file_path], dict):
                        # Handle structured content
                        prompt += str(current_state[file_path])
                    else:
                        # Handle raw file content
                        prompt += str(current_state[file_path])

            prompt += """
IMPORTANT:
1. Provide complete, implementation-ready code for each file that needs to be modified
2. Maintain the existing code style and structure
3. Include clear comments explaining the changes
4. Only modify the specified files
5. Ensure the implementation addresses all missing components

Format your response as follows for each file:

---FILE: <filename>---
```python
<complete file content with your changes>
```
CHANGES EXPLAINED:
- <explanation of major changes>
- <explanation of how this addresses the gap>
"""

            # Get implementation from LLM
            response = self._get_llm_response(
                "You are an expert code implementer. Generate complete, working code that implements the missing functionality while maintaining the existing codebase structure and style.",
                prompt
            )

            # Parse the response into a map of file changes
            file_changes = {}
            current_file = None
            current_content = []
            
            for line in response.split('\n'):
                if line.startswith('---FILE:'):
                    if current_file and current_content:
                        file_changes[current_file] = '\n'.join(current_content)
                        current_content = []
                    current_file = line.replace('---FILE:', '').strip()
                elif line.startswith('CHANGES EXPLAINED:'):
                    if current_file and current_content:
                        file_changes[current_file] = '\n'.join(current_content)
                    break
                elif current_file:
                    current_content.append(line)

            return file_changes

        except Exception as e:
            self.logger.error(f"Failed to implement gap: {str(e)}")
            raise 