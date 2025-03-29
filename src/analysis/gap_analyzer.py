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


class GapAnalyzer:
    """Analyzes gaps between current codebase and whitepaper requirements."""
    
    def __init__(self):
        """Initialize the gap analyzer."""
        self.logger = logging.getLogger(__name__)
        self.gaps: List[Gap] = []
        self.codebase_index: Dict[str, Any] = {}
        self.codebase_analyzer = CodebaseAnalyzer()
        self.llm_logger = LLMLogger()
        
    def analyze_codebase(self, root_dir: str) -> None:
        """
        Analyze the codebase structure and create an index.
        
        Args:
            root_dir: Root directory of the codebase
        """
        try:
            # Use CodebaseAnalyzer to analyze implemented features
            self.codebase_index = self.codebase_analyzer.analyze_codebase(root_dir)
            self.logger.info("Codebase analysis completed")
        except Exception as e:
            self.logger.error(f"Failed to analyze codebase: {str(e)}")
            raise

    def identify_gaps(self, whitepaper: Dict[str, Any], current_state: Dict[str, Any]) -> List[Gap]:
        """
        Identify gaps between current state and whitepaper requirements.
        
        Args:
            whitepaper: Dictionary containing whitepaper analysis
            current_state: Dictionary containing current codebase state
            
        Returns:
            List of identified gaps
        """
        try:
            self.gaps = []
            
            # Get features from whitepaper
            features = whitepaper.get("features", [])
            if not features:
                self.logger.warning("No features found in whitepaper analysis")
                return []
            
            self.logger.info(f"Total features to analyze: {len(features)}")
            
            # Get implemented features from codebase analysis
            implemented_features = self._get_implemented_features()
            
            # Analyze each feature from whitepaper
            for feature in features:
                feature_name = feature["name"]
                feature_desc = feature["description"]
                feature_section = feature["section"]
                
                # Check if feature is implemented
                status, reason, files, details, suggestions = self._analyze_feature(
                    feature_name,
                    feature_desc,
                    implemented_features
                )
                
                # Create gap if feature is not fully implemented
                if status.lower() not in ["complete", "completed", "implemented", "done", "finished", "ready"]:
                    self.gaps.append(Gap(
                        section=feature_section,
                        status=status.lower(),
                        reason=reason,
                        affected_files=files,
                        priority=self._determine_priority(status.lower(), feature_section),
                        implementation_details=details,
                        suggested_fixes=suggestions
                    ))
            
            self.logger.info(f"Total gaps identified: {len(self.gaps)}")
            return self.gaps
            
        except Exception as e:
            self.logger.error(f"Failed to identify gaps: {str(e)}")
            raise
            
    def _get_implemented_features(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all implemented features from codebase analysis."""
        return self.codebase_index
        
    def _analyze_feature(self, 
                        feature_name: str,
                        feature_desc: str,
                        implemented_features: Dict[str, List[Dict[str, Any]]]) -> tuple[str, str, List[str], Dict[str, Any], List[str]]:
        """
        Analyze a feature to determine its implementation status.
        
        Args:
            feature_name: Name of the feature to analyze
            feature_desc: Description of the feature
            implemented_features: Dictionary of implemented features
            
        Returns:
            Tuple of (status, reason, affected_files, details, suggestions)
        """
        try:
            # Create prompt for LLM
            prompt = f"""Analyze if this feature is implemented in the codebase.

Feature to analyze:
Name: {feature_name}
Description: {feature_desc}

Implemented features:
"""
            for file_path, features in implemented_features.items():
                prompt += f"\nFile: {file_path}\n"
                for feature in features:
                    prompt += f"- {feature['type']}: {feature['description']}\n"
            
            prompt += """
Provide your analysis in this format:
STATUS: <complete/partial/missing/planned>
REASON: <explanation>
FILES: <affected files, one per line>
CURRENT_STATE: <current implementation analysis>
MISSING_COMPONENTS:
- <component 1>
- <component 2>
SUGGESTED_APPROACH: <implementation approach>
SUGGESTIONS:
- <suggestion 1>
- <suggestion 2>
"""
            
            # Get response from LLM
            response = self._get_llm_response(
                "You are a code analysis expert. Analyze if the feature is implemented and provide detailed feedback.",
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
            
            details = {
                "current_state": current_state,
                "missing_components": missing_components,
                "suggested_approach": suggested_approach
            }
            
            return status, reason, files, details, suggestions
            
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