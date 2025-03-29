"""
Gap analysis module for Project Evolver.

This module analyzes the differences between the current codebase state
and the requirements specified in the whitepaper using Cursor's LLM capabilities.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import re
import ast
from pathlib import Path
import json
from collections import defaultdict
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Gap:
    """Represents a gap between current state and requirements."""
    section: str  # Section from whitepaper
    status: str  # missing, partial, outdated
    reason: str  # Detailed explanation
    affected_files: List[str]  # Files that need changes
    priority: int  # 1-5 priority level
    implementation_details: Dict[str, Any]  # Detailed analysis
    suggested_fixes: List[str]  # Suggested fixes


class GapAnalyzer:
    """Analyzes gaps between current codebase and whitepaper requirements."""
    
    def __init__(self):
        """Initialize the gap analyzer."""
        self.logger = logging.getLogger(__name__)
        self.gaps: List[Gap] = []
        self.codebase_index: Dict[str, Any] = {}
        
    def analyze_codebase(self, root_dir: str) -> None:
        """
        Analyze the codebase structure and create an index.
        
        Args:
            root_dir: Root directory of the codebase
        """
        try:
            root_path = Path(root_dir)
            self._build_codebase_index(root_path)
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
            all_features = []
            
            # First, collect all features from all sections
            for section_id, section in whitepaper["sections"].items():
                self.logger.info(f"Processing section: {section['title']}")
                features = self._extract_features(section["content"])
                self.logger.info(f"Extracted features from section '{section['title']}': {features}")
                all_features.extend([(feature, section["title"]) for feature in features])
            
            if not all_features:
                self.logger.warning("No features were extracted from the whitepaper")
                return []
            
            self.logger.info(f"Total features to analyze: {len(all_features)}")
            
            # Batch analyze all features at once
            codebase_context = self._get_codebase_context()
            self.logger.info("Codebase context for analysis:")
            self.logger.info(codebase_context)
            
            batch_results = self._batch_analyze_features(all_features, codebase_context)
            self.logger.info("Batch analysis results:")
            for (feature, section), (status, reason, files, details, suggestions) in batch_results.items():
                self.logger.info(f"\nFeature: {feature}")
                self.logger.info(f"Section: {section}")
                self.logger.info(f"Status: {status}")
                self.logger.info(f"Reason: {reason}")
                self.logger.info(f"Affected files: {files}")
                self.logger.info(f"Details: {details}")
                self.logger.info(f"Suggestions: {suggestions}")
            
            # Create gap objects from batch results
            for (feature, section_title), (status, reason, affected_files, details, suggestions) in batch_results.items():
                # Normalize status
                status_lower = status.lower().strip()
                
                # Consider any status that isn't explicitly complete as a gap
                if status_lower not in ["complete", "completed", "implemented", "done", "finished", "ready"]:
                    self.logger.info(f"Creating gap for feature: {feature}")
                    self.logger.info(f"Status: {status_lower}")
                    self.logger.info(f"Reason: {reason}")
                    
                    self.gaps.append(Gap(
                        section=section_title,
                        status=status_lower,
                        reason=reason,
                        affected_files=affected_files,
                        priority=self._determine_priority(status_lower, section_title),
                        implementation_details=details,
                        suggested_fixes=suggestions
                    ))
            
            self.logger.info(f"Total gaps identified: {len(self.gaps)}")
            return self.gaps
            
        except Exception as e:
            self.logger.error(f"Failed to identify gaps: {str(e)}")
            raise

    def _extract_features(self, content: str) -> List[str]:
        """Extract features from section content using LLM."""
        try:
            # Use LLM to extract features from the content
            prompt = f"""Analyze this section and extract all features and requirements that need to be implemented.
            Focus on concrete, actionable items. Format each feature as a clear, concise statement.
            
            Section content:
            {content}
            
            Extract features in this format:
            FEATURE: <feature description>
            """
            
            self.logger.info("Sending feature extraction prompt to LLM:")
            self.logger.info(prompt)
            
            response = self._get_llm_response(
                "You are a code analysis expert. Extract features and requirements from the given content.",
                prompt
            )
            
            self.logger.info("LLM response for feature extraction:")
            self.logger.info(response)
            
            # Parse features from response
            features = []
            for line in response.split('\n'):
                if line.startswith('FEATURE:'):
                    feature = line[8:].strip()
                    if feature:
                        features.append(feature)
            
            return features
            
        except Exception as e:
            self.logger.error(f"Failed to extract features: {str(e)}")
            return []

    def _check_implementation_status(self, feature: str) -> tuple[str, str, List[str]]:
        """
        Check implementation status of a feature using LLM.
        
        Returns:
            Tuple of (status, reason, affected_files)
        """
        try:
            # Create a prompt that includes both the feature and codebase context
            codebase_context = self._get_codebase_context()
            
            prompt = f"""Analyze if this feature is implemented in the codebase.
            
            Feature to check: {feature}
            
            Codebase context:
            {codebase_context}
            
            Provide your analysis in this format:
            STATUS: <complete/partial/missing>
            REASON: <explanation>
            FILES: <affected files, one per line>
            """
            
            response = self._get_llm_response(
                "You are a code analysis expert. Analyze if the feature is implemented in the codebase.",
                prompt
            )
            
            # Parse response
            status = "missing"
            reason = "No implementation found"
            affected_files = []
            
            for line in response.split('\n'):
                if line.startswith('STATUS:'):
                    status = line[7:].strip().lower()
                elif line.startswith('REASON:'):
                    reason = line[7:].strip()
                elif line.startswith('FILES:'):
                    affected_files = [f.strip() for f in line[6:].split('\n') if f.strip()]
            
            return status, reason, affected_files
            
        except Exception as e:
            self.logger.error(f"Failed to check implementation status: {str(e)}")
            return "missing", "Failed to analyze implementation", []

    def _get_implementation_analysis(self, feature: str, status: str, reason: str) -> tuple[Dict[str, Any], List[str]]:
        """Get implementation details and suggestions using LLM."""
        try:
            codebase_context = self._get_codebase_context()
            
            prompt = f"""Analyze this feature and provide implementation details and suggestions.
            
            Feature: {feature}
            Current Status: {status}
            Reason: {reason}
            
            Codebase context:
            {codebase_context}
            
            Provide your analysis in this format:
            CURRENT_STATE: <current implementation analysis>
            MISSING_COMPONENTS:
            - <component 1>
            - <component 2>
            SUGGESTED_APPROACH: <implementation approach>
            SUGGESTIONS:
            - <suggestion 1>
            - <suggestion 2>
            """
            
            response = self._get_llm_response(
                "You are a code analysis expert. Provide detailed implementation analysis and suggestions.",
                prompt
            )
            
            # Parse response
            details = {
                "current_implementation": None,
                "missing_components": [],
                "suggested_approach": None
            }
            suggestions = []
            
            current_section = None
            current_content = []
            
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('CURRENT_STATE:'):
                    current_section = 'current_implementation'
                    current_content = []
                elif line.startswith('MISSING_COMPONENTS:'):
                    if current_section == 'current_implementation':
                        details['current_implementation'] = '\n'.join(current_content).strip()
                    current_section = 'missing_components'
                    current_content = []
                elif line.startswith('SUGGESTED_APPROACH:'):
                    if current_section == 'missing_components':
                        details['missing_components'] = [c[2:] for c in current_content if c.startswith('- ')]
                    current_section = 'suggested_approach'
                    current_content = []
                elif line.startswith('SUGGESTIONS:'):
                    if current_section == 'suggested_approach':
                        details['suggested_approach'] = '\n'.join(current_content).strip()
                    current_section = 'suggestions'
                    current_content = []
                elif line and current_section == 'suggestions':
                    if line.startswith('- '):
                        suggestions.append(line[2:])
                elif line and current_section:
                    current_content.append(line)
            
            return details, suggestions
            
        except Exception as e:
            self.logger.error(f"Failed to get implementation analysis: {str(e)}")
            return {
                "current_implementation": None,
                "missing_components": [],
                "suggested_approach": None
            }, []

    def _get_codebase_context(self) -> str:
        """Get a summary of the codebase context for LLM analysis."""
        context = []
        
        # Add file summaries
        for file_path, summary in self.codebase_index.get("file_summaries", {}).items():
            context.append(f"File: {file_path}\nSummary: {summary}\n")
        
        # Add function information
        for func_name, func_info in self.codebase_index.get("functions", {}).items():
            context.append(f"Function: {func_name}")
            if func_name in self.codebase_index.get("docstrings", {}):
                context.append(f"Docstring: {self.codebase_index['docstrings'][func_name]}\n")
        
        return "\n".join(context)

    def _determine_priority(self, status: str, section: str) -> int:
        """Determine priority level for a gap."""
        # Priority 1: Missing core features
        if status == "missing" and any(word in section.lower() for word in ["core", "essential", "required"]):
            return 1
        
        # Priority 2: Missing non-core features
        if status == "missing":
            return 2
        
        # Priority 3: Partial implementations
        if status == "partial":
            return 3
        
        # Priority 4: Outdated implementations
        if status == "outdated":
            return 4
        
        # Priority 5: Improvements
        return 5
    
    def _get_llm_response(self, system_prompt: str, user_prompt: str) -> str:
        """Get response from OpenAI's GPT-4o-mini model."""
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
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(f"Failed to get LLM response: {str(e)}")
            # Fallback to a simple response if LLM is not available
            return f"LLM Response for: {user_prompt}"

    def _batch_analyze_features(self, features: List[tuple[str, str]], codebase_context: str) -> Dict[tuple[str, str], tuple[str, str, List[str], Dict[str, Any], List[str]]]:
        """Batch analyze multiple features in a single API call."""
        try:
            # Prepare batch prompt
            prompt = "Analyze multiple features and their implementation status in the codebase.\n\n"
            
            for i, (feature, section) in enumerate(features):
                prompt += f"""Feature {i}:
                Name: {feature}
                Section: {section}
                
                """
            
            prompt += f"""
            Codebase context:
            {codebase_context}
            
            For each feature, provide analysis in this format:
            Feature <number>:
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
            
            self.logger.info("Sending batch analysis prompt to LLM:")
            self.logger.info(prompt)
            
            response = self._get_llm_response(
                "You are a code analysis expert. Analyze multiple features and their implementation status.",
                prompt
            )
            
            self.logger.info("LLM response for batch analysis:")
            self.logger.info(response)
            
            # Parse batch response
            results = {}
            current_feature = None
            current_section = None
            current_status = "missing"
            current_reason = "No implementation found"
            current_files = []
            current_details = {
                "current_implementation": None,
                "missing_components": [],
                "suggested_approach": None
            }
            current_suggestions = []
            
            for line in response.split('\n'):
                line = line.strip()
                if line.startswith('Feature '):
                    # Store previous feature's results if exists
                    if current_feature is not None:
                        results[(current_feature, current_section)] = (
                            current_status,
                            current_reason,
                            current_files,
                            current_details,
                            current_suggestions
                        )
                    
                    # Start new feature
                    try:
                        feature_num = int(line[8:].strip(':'))
                        if 0 <= feature_num < len(features):
                            current_feature = features[feature_num][0]
                            current_section = features[feature_num][1]
                            current_status = "missing"
                            current_reason = "No implementation found"
                            current_files = []
                            current_details = {
                                "current_implementation": None,
                                "missing_components": [],
                                "suggested_approach": None
                            }
                            current_suggestions = []
                    except ValueError:
                        self.logger.warning(f"Could not parse feature number from line: {line}")
                        continue
                elif line.startswith('STATUS:'):
                    current_status = line[7:].strip()
                elif line.startswith('REASON:'):
                    current_reason = line[7:].strip()
                elif line.startswith('FILES:'):
                    current_files = [f.strip() for f in line[6:].split('\n') if f.strip()]
                elif line.startswith('CURRENT_STATE:'):
                    current_section = 'current_implementation'
                    current_content = []
                elif line.startswith('MISSING_COMPONENTS:'):
                    if current_section == 'current_implementation':
                        current_details['current_implementation'] = '\n'.join(current_content).strip()
                    current_section = 'missing_components'
                    current_content = []
                elif line.startswith('SUGGESTED_APPROACH:'):
                    if current_section == 'missing_components':
                        current_details['missing_components'] = [c[2:] for c in current_content if c.startswith('- ')]
                    current_section = 'suggested_approach'
                    current_content = []
                elif line.startswith('SUGGESTIONS:'):
                    if current_section == 'suggested_approach':
                        current_details['suggested_approach'] = '\n'.join(current_content).strip()
                    current_section = 'suggestions'
                    current_content = []
                elif line and current_section == 'suggestions':
                    if line.startswith('- '):
                        current_suggestions.append(line[2:])
                elif line and current_section:
                    current_content.append(line)
            
            # Store last feature's results
            if current_feature is not None:
                results[(current_feature, current_section)] = (
                    current_status,
                    current_reason,
                    current_files,
                    current_details,
                    current_suggestions
                )
            
            # Log the parsed results for debugging
            self.logger.info("Parsed results:")
            for (feature, section), (status, reason, files, details, suggestions) in results.items():
                self.logger.info(f"\nFeature: {feature}")
                self.logger.info(f"Section: {section}")
                self.logger.info(f"Status: {status}")
                self.logger.info(f"Reason: {reason}")
                self.logger.info(f"Files: {files}")
                self.logger.info(f"Details: {details}")
                self.logger.info(f"Suggestions: {suggestions}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to batch analyze features: {str(e)}")
            # Return empty results as fallback
            return {
                (feature, section): (
                    "missing",
                    "Failed to analyze implementation",
                    [],
                    {
                        "current_implementation": None,
                        "missing_components": [],
                        "suggested_approach": None
                    },
                    []
                )
                for feature, section in features
            }

    def _build_codebase_index(self, root_path: Path) -> None:
        """Build an index of the codebase structure and content."""
        try:
            self.codebase_index = {
                "file_summaries": {},
                "functions": {},
                "docstrings": {}
            }
            
            # Walk through all Python files
            for file_path in root_path.rglob("*.py"):
                if not any(part.startswith(".") for part in file_path.parts):
                    self.logger.info(f"Analyzing file: {file_path}")
                    self._analyze_file(file_path)
            
            self.logger.info("Codebase index built successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to build codebase index: {str(e)}")
            raise

    def _analyze_file(self, file_path: Path) -> None:
        """Analyze a Python file and extract relevant information."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the file content
            tree = ast.parse(content)
            
            # Extract functions and their docstrings
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_name = node.name
                    self.codebase_index["functions"][func_name] = {
                        "file": str(file_path),
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args]
                    }
                    
                    # Extract docstring if present
                    if ast.get_docstring(node):
                        self.codebase_index["docstrings"][func_name] = ast.get_docstring(node)
            
            # Create a summary of the file
            self.codebase_index["file_summaries"][str(file_path)] = self._generate_file_summary(content)
            
        except Exception as e:
            self.logger.error(f"Failed to analyze file {file_path}: {str(e)}")
            raise

    def _generate_file_summary(self, content: str) -> str:
        """Generate a summary of a file's content."""
        try:
            # Use LLM to generate a summary
            prompt = f"""Analyze this Python file and provide a concise summary of its purpose and main functionality.
            
            File content:
            {content}
            
            Provide a brief summary that captures the main purpose and functionality of this file.
            """
            
            response = self._get_llm_response(
                "You are a code analysis expert. Provide a concise summary of the file's purpose and functionality.",
                prompt
            )
            
            return response.strip()
            
        except Exception as e:
            self.logger.error(f"Failed to generate file summary: {str(e)}")
            return "Failed to generate summary" 