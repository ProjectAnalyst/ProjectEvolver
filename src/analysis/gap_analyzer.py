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
        self.gaps = []  # This will store our gaps
        self.codebase_index = {}
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
        """
        Identify gaps between whitepaper requirements and current implementation.
        
        Args:
            whitepaper: Analyzed whitepaper content
            codebase_index: Current codebase analysis
            
        Returns:
            List of identified gaps
        """
        try:
            # Start LLM logging session
            self.llm_logger.start_session("gap_analysis")
            
            # Format features for prompt
            features_text = self._format_features(whitepaper.get("features", []))
            codebase_text = self._format_codebase_analysis(codebase_index)
            
            # Create analysis prompt
            prompt = f"""Analyze the gap between required features and current implementation.
For each feature, determine if it is implemented, partially implemented, or missing.
Also identify relevant existing files and suggest new files needed.

REQUIRED FEATURES:
{features_text}

CURRENT CODEBASE:
{codebase_text}

For each feature, provide analysis in this format:

FEATURE: <feature_name>
STATUS: <implemented/partial/missing>
REASON: <detailed explanation>
FOUND IN: 
- EXISTING RELATED FILES: <list of relevant existing files, with explanation why they're relevant>
- NEW FILES NEEDED: < If feature cannot be implemented in existing files, list of suggested new files with purpose>
MISSING COMPONENTS: <specific components that need to be implemented>
IMPLEMENTATION DETAILS:
- Current State: <description of current implementation if any>
- Required Changes: <specific changes needed>
- Dependencies: <any dependencies or prerequisites>

Analyze each feature thoroughly and provide specific file paths and explanations.
If suggesting new files, explain their purpose and how they fit into the architecture.
"""
            
            # Get LLM response
            response = self._get_llm_response(
                "You are a software architect analyzing implementation gaps. Be specific about file locations and new file needs.",
                prompt
            )
            
            # Parse response into gaps
            gaps = self._parse_multi_feature_analysis(response, whitepaper.get("features", []))
            
            return gaps
            
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
        current_feature = None
        current_analysis = {}
        
        # Split response into lines and clean them
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        for line in lines:
            # Remove markdown formatting if present
            line = line.replace('###', '').replace('**', '').strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Check for feature start
            if line.lower().startswith('feature:'):
                # Save previous feature analysis if it exists
                if current_feature and current_analysis:
                    status = current_analysis.get("status", "").lower()
                    if status not in ["implemented", "fully implemented", "complete", "fully"]:
                        # Create gap with all the information
                        gap = Gap(
                            section=current_feature.get("name", "Unknown"),
                            status=current_analysis.get("status", "not implemented"),
                            reason=current_analysis.get("reason", ""),
                            affected_files=current_analysis.get("existing_files", []),  # From FOUND IN: EXISTING FILES
                            priority=self._determine_priority(current_analysis.get("status", ""), current_feature.get("name", "")),
                            implementation_details={
                                "current_state": current_analysis.get("current_state", "No current implementation"),
                                "required_changes": current_analysis.get("required_changes", "No changes specified"),
                                "dependencies": current_analysis.get("dependencies", "No dependencies"),
                                "new_files": current_analysis.get("new_files", []),  # From FOUND IN: NEW FILES NEEDED
                                "missing_components": current_analysis.get("missing_components", [])
                            },
                            suggested_fixes=[],
                            type=current_feature.get("name", "").split(" - ")[0].lower(),
                            description=current_feature.get("description", ""),
                            requirements=[],
                            missing_components=current_analysis.get("missing_components", []),
                            confidence=current_analysis.get("confidence", "medium")
                        )
                        gaps.append(gap)
                
                # Start new feature analysis
                feature_name = line.split(':', 1)[1].strip()
                current_feature = {"name": feature_name, "description": ""}
                current_analysis = {}
                
            # Process other fields
            elif line.lower().startswith('status:'):
                current_analysis["status"] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('reason:'):
                current_analysis["reason"] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('found in:'):
                current_analysis["existing_files"] = []
                current_analysis["new_files"] = []
            elif line.lower().startswith('- existing related files:'):
                value = line.split(':', 1)[1].strip()
                if value.lower() != "none" and value.lower() != "none.":
                    current_analysis["existing_files"] = [f.strip() for f in value.split(',')]
            elif line.lower().startswith('- new files needed:'):
                value = line.split(':', 1)[1].strip()
                if value.lower() != "none" and value.lower() != "none.":
                    current_analysis["new_files"] = [f.strip() for f in value.split(',')]
            elif line.lower().startswith('missing components:'):
                value = line.split(':', 1)[1].strip()
                if value.lower() != "none" and value.lower() != "none.":
                    current_analysis["missing_components"] = [item.strip() for item in value.split(',')]
            elif line.lower().startswith('- current state:'):
                current_analysis["current_state"] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('- required changes:'):
                current_analysis["required_changes"] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('- dependencies:'):
                current_analysis["dependencies"] = line.split(':', 1)[1].strip()
            elif line.lower().startswith('confidence:'):
                current_analysis["confidence"] = line.split(':', 1)[1].strip()
        
        # Process the last feature
        if current_feature and current_analysis:
            status = current_analysis.get("status", "").lower()
            if status not in ["implemented", "fully implemented", "complete", "fully"]:
                gap = Gap(
                    section=current_feature.get("name", "Unknown"),
                    status=current_analysis.get("status", "not implemented"),
                    reason=current_analysis.get("reason", ""),
                    affected_files=current_analysis.get("existing_files", []),
                    priority=self._determine_priority(current_analysis.get("status", ""), current_feature.get("name", "")),
                    implementation_details={
                        "current_state": current_analysis.get("current_state", "No current implementation"),
                        "required_changes": current_analysis.get("required_changes", "No changes specified"),
                        "dependencies": current_analysis.get("dependencies", "No dependencies"),
                        "new_files": current_analysis.get("new_files", []),
                        "missing_components": current_analysis.get("missing_components", [])
                    },
                    suggested_fixes=[],
                    type=current_feature.get("name", "").split(" - ")[0].lower(),
                    description=current_feature.get("description", ""),
                    requirements=[],
                    missing_components=current_analysis.get("missing_components", []),
                    confidence=current_analysis.get("confidence", "medium")
                )
                gaps.append(gap)
        
        # Store gaps and log
        self.gaps = gaps
        self.logger.info(f"Parsed {len(self.gaps)} gaps from analysis")
        
        return self.gaps

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
