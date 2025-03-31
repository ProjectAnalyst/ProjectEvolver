"""
Gap analysis module for Project Evolver.

This module analyzes the differences between the current codebase state
and the requirements specified in the whitepaper.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
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
    suggested_fixes: List[str]
    type: str = "general"
    description: str = ""
    requirements: List[str] = field(default_factory=list)
    missing_components: List[str] = field(default_factory=list)
    confidence: str = "medium"
    
    def __post_init__(self):
        """Set description based on reason if not provided."""
        if not self.description:
            self.description = self.reason


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

    def identify_gaps(self, whitepaper: Dict[str, Any], codebase_index: Dict[str, Any]) -> List[Gap]:
        """Compare all whitepaper requirements against the codebase index in a single analysis."""
        try:
            # Start a new LLM logging session for gap analysis
            self.llm_logger.start_session("gap_analysis")
            self.logger.info("Starting gap analysis")
            
            # Format the features from whitepaper
            features = whitepaper.get("features", [])
            features_text = "\n".join(
                f"Feature: {feature['name']}\n"
                f"Description: {feature.get('description', '')}\n"
                for feature in features
            )
            
            # Create a single analysis prompt
            prompt = f"""Analyze which features from the whitepaper are implemented in the codebase:

WHITEPAPER FEATURES:
{features_text}

CODEBASE IMPLEMENTATION:
{self._format_codebase_analysis(codebase_index)}

For each feature listed in the whitepaper above, provide your analysis in this format:
FEATURE: <feature name>
STATUS: <fully/partially/not> implemented
REASON: <detailed explanation>
FOUND IN: <list of relevant code elements>
MISSING COMPONENTS: <list of missing pieces>
CONFIDENCE: <high/medium/low>

Analyze each feature separately, but consider relationships between features when relevant.
"""
            
            # Get analysis for all features at once
            response = self._get_llm_response(
                "You are a code analysis expert. Analyze implementation status of multiple features.",
                prompt
            )
            
            # Parse the response into individual gaps
            self.gaps = self._parse_multi_feature_analysis(response, features)
            
            self.logger.info(f"Identified {len(self.gaps)} gaps")
            return self.gaps
            
        except Exception as e:
            self.logger.error(f"Failed to identify gaps: {str(e)}")
            raise

    def _format_features(self, features: List[Dict[str, Any]]) -> str:
        """Format the list of features for the prompt."""
        formatted = []
        for i, feature in enumerate(features, 1):
            formatted.append(f"{i}. {feature['name']}")
            formatted.append(f"   Description: {feature.get('description', '')}\n")
        return "\n".join(formatted)

    def _parse_multi_feature_analysis(self, response: str, features: List[Dict[str, Any]]) -> List[Gap]:
        """Parse the multi-feature analysis response into individual gaps."""
        gaps = []
        total_features = len(features)
        current_feature = None
        current_analysis = {}
        
        self.logger.debug(f"Starting to parse analysis for {total_features} features")
        
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            self.logger.debug(f"Processing line: {line}")
            
            if line.startswith('FEATURE:'):
                # Save previous feature analysis if it exists
                if current_feature and current_analysis:
                    self.logger.debug(f"Current status: {current_analysis.get('status', 'unknown')}")
                    if current_analysis.get("status", "").lower() not in ["fully implemented", "fully"]:
                        self.logger.debug(f"Creating gap for {current_feature['name']}")
                        gap = self._create_gap(
                            feature=current_feature,
                            status=current_analysis.get("status", "not"),
                            confidence=current_analysis.get("confidence", "medium"),
                            reason=current_analysis.get("reason", ""),
                            missing_components=current_analysis.get("missing_components", [])
                        )
                        gaps.append(gap)
                
                # Start new feature analysis
                feature_name = line.replace('FEATURE:', '').strip()
                self.logger.debug(f"Starting analysis of feature: {feature_name}")
                current_feature = next(
                    (f for f in features if f["name"].endswith(feature_name)), 
                    {"name": feature_name, "description": ""}
                )
                current_analysis = {}
                
            elif line.startswith('STATUS:'):
                status = line.split(':', 1)[1].strip().lower()
                current_analysis["status"] = status
                self.logger.debug(f"Found status: {status}")
            elif line.startswith('REASON:'):
                current_analysis["reason"] = line.split(':', 1)[1].strip()
            elif line.startswith('FOUND IN:'):
                found_in = line.split(':', 1)[1].strip()
                if found_in and found_in.lower() != "none":
                    current_analysis["found_in"] = [item.strip() for item in found_in.split(',')]
            elif line.startswith('MISSING COMPONENTS:'):
                missing = line.split(':', 1)[1].strip()
                if missing and missing.lower() != "none":
                    current_analysis["missing_components"] = [item.strip() for item in missing.split('.')]
            elif line.startswith('CONFIDENCE:'):
                current_analysis["confidence"] = line.split(':', 1)[1].strip()
        
        # Process the last feature if needed
        if current_feature and current_analysis:
            self.logger.debug(f"Processing final feature: {current_feature['name']} with status {current_analysis.get('status', 'unknown')}")
            if current_analysis.get("status", "").lower() not in ["fully implemented", "fully"]:
                gap = self._create_gap(
                    feature=current_feature,
                    status=current_analysis.get("status", "not"),
                    confidence=current_analysis.get("confidence", "medium"),
                    reason=current_analysis.get("reason", ""),
                    missing_components=current_analysis.get("missing_components", [])
                )
                gaps.append(gap)
        
        self.logger.debug(f"Found {len(gaps)} gaps")
        self.logger.info(f"Identified {len(gaps)} gaps out of {total_features} total features")
        
        return gaps

    def _format_codebase_analysis(self, codebase_index: Dict[str, Any]) -> str:
        """Format codebase analysis for LLM prompt."""
        # Just return the complete analysis text as-is
        if "analysis_text" in codebase_index:
            return codebase_index["analysis_text"]
        return "No codebase analysis available."

    def _is_feature_match(self, feature: Dict[str, Any], implementation: Dict[str, Any]) -> bool:
        """Check if an implementation matches a feature requirement."""
        feature_name = feature.get("name", "").lower()
        feature_desc = feature.get("description", "").lower()
        
        impl_name = implementation.get("name", "").lower()
        impl_desc = implementation.get("description", "").lower()
        
        # Check for name matches
        if feature_name in impl_name or impl_name in feature_name:
            return True
        
        # Check for description matches
        if any(word in impl_desc for word in feature_desc.split()):
            return True
        
        return False

    def _extract_required_components(self, description: str) -> List[str]:
        """Extract required components from feature description."""
        # Use LLM to identify required components
        prompt = f"""Given this feature description, list the key components required for implementation:

Description: {description}

Format your response as a list of technical components, one per line:
- component1
- component2
etc.
"""
        
        try:
            response = self._get_llm_response(
                "You are a technical analyst. Extract required implementation components.",
                prompt
            )
            
            components = []
            for line in response.split('\n'):
                if line.strip().startswith('- '):
                    components.append(line.strip()[2:])
            return components
            
        except Exception as e:
            self.logger.error(f"Failed to extract components: {str(e)}")
            return []

    def _find_component(self, component: str, codebase_index: Dict[str, Any]) -> bool:
        """Check if a component exists in the codebase."""
        component = component.lower()
        
        # Check all sections of the codebase index
        for section in ["functions", "classes", "apis", "ui_elements", "constants"]:
            for item in codebase_index.get(section, []):
                if component in item.get("name", "").lower() or \
                   component in item.get("description", "").lower():
                    return True
        
        return False

    def _create_gap(self, 
                   feature: Dict[str, Any], 
                   status: str, 
                   confidence: str,
                   reason: str = "",
                   missing_components: List[str] = None) -> Gap:
        """Create a Gap object without implementation suggestions."""
        return Gap(
            section=feature['name'],
            status=status,
            reason=reason or f"Feature {status} with {confidence} confidence",
            affected_files=[],  # This can be populated later if needed
            priority=self._determine_priority(status, feature['name']),
            implementation_details={
                "missing_components": missing_components or []
            },
            suggested_fixes=[],  # This can be populated later if needed
            type=feature['name'].split(" - ")[0].lower(),
            description=feature['description'],
            requirements=[],
            missing_components=missing_components or [],
            confidence=confidence
        )

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
        """Get response from LLM."""
        # Add debug logging
        self.logger.debug(f"Making LLM call from: {system_prompt}")
        import traceback
        self.logger.debug(f"Call stack:\n{traceback.format_stack()}")
        
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