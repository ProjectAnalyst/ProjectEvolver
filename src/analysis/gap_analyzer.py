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
import re


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
    file_metadata: Dict[str, Any] = field(default_factory=dict)
    file_contents: Dict[str, str] = field(default_factory=dict)  # New field for file contents
    file_changes: Dict[str, str] = field(default_factory=dict)  # New field for required changes per file
    
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
        self.file_metadata = {}  # New dictionary for storing file metadata
        
    def analyze_codebase(self, root_dir: str) -> None:
        """
        Analyze the codebase structure and create an index.
        
        Args:
            root_dir: Root directory of the codebase
        """
        try:
            # Get the CodebaseAnalyzer results
            self.codebase_index = self.codebase_analyzer.analyze_codebase(root_dir)
            
            # Enhanced file analysis
            self.file_contents = {}
            self.file_metadata = {}  # New dictionary for storing file metadata
            
            for file_path in self.codebase_index.keys():
                full_path = os.path.join(root_dir, file_path)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        self.file_contents[file_path] = content
                        
                        # Extract metadata about the file
                        self.file_metadata[file_path] = {
                            'imports': self._extract_imports(content),
                            'classes': self._extract_classes(content),
                            'functions': self._extract_functions(content),
                            'dependencies': self._analyze_dependencies(content),
                            'type': self._determine_file_type(file_path, content)
                        }
                        
                    self.logger.info(f"Successfully analyzed {file_path}")
                except Exception as e:
                    self.logger.error(f"Failed to analyze {file_path}: {str(e)}")
                
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
            self.llm_logger.start_session("gap_analysis")
            
            # Format features for prompt
            features_text = self._format_features(whitepaper.get("features", []))
            codebase_text = self._format_codebase_analysis(codebase_index)
            
            # Add structural information to the prompt
            structure_text = self._format_codebase_structure()
            
            prompt = f"""Analyze the gap between required features and current implementation.
Consider the current codebase structure and suggest the most appropriate locations for changes.

REQUIRED FEATURES:
{features_text}

CURRENT CODEBASE STRUCTURE:
{structure_text}

CURRENT CODEBASE ANALYSIS:
{codebase_text}

For each feature, provide detailed analysis including file locations:

FEATURE: <feature_name>
STATUS: <implemented/partial/missing>
REASON: <detailed explanation>
FILES_TO_MODIFY:
- FILE: <file_path>
  LOCATION: <specific location in file>
  CHANGES: <detailed description of changes needed>
  REASON: <why these changes are needed>
NEW_FILES_NEEDED:
- FILE: <file_path>
  PURPOSE: <what this file will do>
  LOCATION: <where it should be placed>
MISSING_COMPONENTS: <specific components that need to be implemented>
IMPLEMENTATION_DETAILS:
- Current State: <description of current implementation if any>
- Required Changes: <specific changes needed>
- Dependencies: <any dependencies or prerequisites>
- File Structure Impact: <how changes affect project structure>

Consider existing file types and dependencies when suggesting changes.
Be specific about where new code should be placed and how it integrates with existing files.
"""
            
            # Get LLM response
            response = self._get_llm_response(
                "You are a software architect analyzing implementation gaps. Be specific about file locations and new file needs.",
                prompt
            )
            
            # Parse response into feature analyses
            feature_analyses = self._parse_multi_feature_analysis(response, whitepaper.get("features", []))
            
            # Convert feature analyses into gaps
            gaps = []
            for feature_analysis in feature_analyses:
                # Get file contents for the files mentioned in the analysis
                file_contents = {}
                for file_path in feature_analysis["files"]:
                    if file_path in self.file_contents:
                        file_contents[file_path] = self.file_contents[file_path]
                
                # Create a basic gap with the raw analysis
                gap = Gap(
                    section=feature_analysis["name"],
                    status="not implemented",  # Default status
                    reason="Feature analysis available",  # Default reason
                    affected_files=feature_analysis["files"],  # Use the extracted files
                    priority=3,  # Default priority
                    implementation_details={
                        "raw_analysis": feature_analysis["analysis"]
                    },
                    suggested_fixes=[],
                    type=feature_analysis["name"].split(" - ")[0].lower(),
                    description="",  # Will be extracted from analysis if needed
                    requirements=[],
                    missing_components=[],
                    confidence="medium",
                    file_metadata={},
                    file_contents=file_contents,  # Add the file contents
                    file_changes={}
                )
                gaps.append(gap)
            
            # Store gaps and log
            self.gaps = gaps
            self.logger.info(f"Created {len(self.gaps)} gaps from feature analyses")
            
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

    def _parse_multi_feature_analysis(self, response: str, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse the multi-feature analysis response into a list of raw feature analyses."""
        feature_analyses = []
        current_feature = None
        current_analysis = []
        current_files = []
        
        # Split response into lines
        lines = response.split('\n')
        
        for line in lines:
            # Check for feature start - handle both markdown and plain formats
            if line.strip().lower().startswith(('### feature:', 'feature:')):
                # Save previous feature analysis if it exists
                if current_feature and current_analysis:
                    feature_analyses.append({
                        "name": current_feature,
                        "analysis": '\n'.join(current_analysis),
                        "files": current_files
                    })
                
                # Start new feature analysis
                # Remove markdown formatting if present
                feature_line = line.replace('###', '').strip()
                current_feature = feature_line.split(':', 1)[1].strip()
                current_analysis = []
                current_files = []
            else:
                # Add line to current analysis
                current_analysis.append(line)
                
                # Check for file paths in the line
                if line.strip().lower().startswith('- existing files to modify:'):
                    # Extract file paths from the line
                    files_text = line.split(':', 1)[1].strip()
                    if files_text.lower() not in ["none", "none."]:
                        # Split by comma and clean up each file path
                        files = [f.strip().strip('`') for f in files_text.split(',')]
                        # Extract just the file path from each entry
                        current_files = [f.split(':')[0].strip() for f in files]
        
        # Add final feature analysis if exists
        if current_feature and current_analysis:
            feature_analyses.append({
                "name": current_feature,
                "analysis": '\n'.join(current_analysis),
                "files": current_files
            })
        
        # Store analyses and log
        self.logger.info(f"Parsed {len(feature_analyses)} feature analyses")
        
        return feature_analyses

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

    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from file content."""
        imports = []
        for line in content.split('\n'):
            if line.strip().startswith(('import ', 'from ')):
                imports.append(line.strip())
        return imports

    def _extract_classes(self, content: str) -> List[str]:
        """Extract class names from file content."""
        classes = []
        for line in content.split('\n'):
            if line.strip().startswith('class '):
                class_name = line.split('class ')[1].split('(')[0].strip()
                classes.append(class_name)
        return classes

    def _extract_functions(self, content: str) -> List[str]:
        """Extract function names from file content."""
        functions = []
        for line in content.split('\n'):
            if line.strip().startswith('def '):
                func_name = line.split('def ')[1].split('(')[0].strip()
                functions.append(func_name)
        return functions

    def _analyze_dependencies(self, content: str) -> Dict[str, List[str]]:
        """Analyze file dependencies based on imports and usage."""
        dependencies = {
            'direct': [],  # Direct imports
            'internal': [], # Internal project dependencies
            'external': []  # External package dependencies
        }
        
        for line in content.split('\n'):
            if line.strip().startswith(('import ', 'from ')):
                if line.startswith('from .'):
                    dependencies['internal'].append(line.strip())
                elif line.startswith(('import ', 'from ')):
                    dependencies['external'].append(line.strip())
        return dependencies

    def _determine_file_type(self, file_path: str, content: str) -> str:
        """Determine the type/role of the file in the project."""
        filename = file_path.lower()
        if 'test' in filename:
            return 'test'
        elif 'api' in filename:
            return 'api'
        elif 'model' in filename or 'entity' in filename:
            return 'model'
        elif 'view' in filename or 'template' in filename:
            return 'view'
        elif 'controller' in filename:
            return 'controller'
        elif 'util' in filename:
            return 'utility'
        return 'other'

    def _format_codebase_structure(self) -> str:
        """Format codebase structural information for the prompt."""
        structure = []
        
        # Group files by type
        files_by_type = {}
        for file_path, metadata in self.file_metadata.items():
            file_type = metadata['type']
            if file_type not in files_by_type:
                files_by_type[file_type] = []
            files_by_type[file_type].append((file_path, metadata))
        
        # Format the structure
        for file_type, files in files_by_type.items():
            structure.append(f"\n{file_type.upper()} FILES:")
            for file_path, metadata in files:
                structure.append(f"\n{file_path}")
                structure.append(f"  Classes: {', '.join(metadata['classes'])}")
                structure.append(f"  Functions: {', '.join(metadata['functions'])}")
                structure.append(f"  Dependencies: {len(metadata['dependencies']['direct'])} direct, "
                               f"{len(metadata['dependencies']['internal'])} internal, "
                               f"{len(metadata['dependencies']['external'])} external")
        
        return '\n'.join(structure)
