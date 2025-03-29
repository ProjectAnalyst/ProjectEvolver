"""
Whitepaper processing module for Project Evolver.

This module handles loading, parsing, and analyzing whitepapers to extract
requirements and features for project evolution.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import re
import uuid
from dataclasses import dataclass
import ast
import json
from ..utils.llm_logger import LLMLogger


@dataclass
class Section:
    """Represents a logical section of the whitepaper."""
    id: str
    title: str
    content: str
    dependencies: List[str]  # IDs of sections that must be processed first
    status: str  # 'pending', 'in_progress', 'completed', 'failed'
    code_blocks: List[str]  # Code blocks found in the section
    file_paths: List[str]  # File paths mentioned in the section


@dataclass
class Feature:
    """Represents a feature extracted from the whitepaper."""
    name: str
    description: str
    section: str


class WhitepaperProcessor:
    """Processes and analyzes project whitepapers."""
    
    def __init__(self):
        """Initialize the whitepaper processor."""
        self.logger = logging.getLogger(__name__)
        self.sections: Dict[str, Section] = {}
        self.current_section: Optional[Section] = None
        self.features: List[Feature] = []
        self.llm_logger = LLMLogger()
    
    def load_and_analyze(self, file_path: str) -> Dict[str, Any]:
        """
        Load and analyze a whitepaper file.
        
        Args:
            file_path: Path to the whitepaper file
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # Start a new LLM logging session
            self.llm_logger.start_session("whitepaper_processing")
            
            # Read the whitepaper content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract features from the entire whitepaper
            features = self._extract_features(content)
            
            # Group features by section
            features_by_section = {}
            for feature in features:
                section = feature.section
                if section not in features_by_section:
                    features_by_section[section] = []
                features_by_section[section].append({
                    "name": feature.name,
                    "description": feature.description
                })
            
            return {
                "content": content,
                "features": [{"name": f.name, "description": f.description, "section": f.section} for f in features],
                "features_by_section": features_by_section
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load and analyze whitepaper: {str(e)}")
            raise
    
    def _extract_features(self, content: str) -> List[Feature]:
        """
        Extract features from the entire whitepaper content.
        
        Args:
            content: Whitepaper content
            
        Returns:
            List of extracted features
        """
        try:
            # Create prompt for LLM
            prompt = f"""Analyze this whitepaper and extract all actionable features and requirements.
Focus on concrete, implementable items. Group them into logical categories.

Whitepaper content:
{content}

Provide your analysis in this format:
FEATURES:
- Feature 1: <description>
- Feature 2: <description>
...

APIs/ENDPOINTS:
- API 1: <description>
- API 2: <description>
...

UI COMPONENTS:
- Component 1: <description>
- Component 2: <description>
...

LOGIC/ALGORITHMS:
- Logic 1: <description>
- Logic 2: <description>
...

Ignore these sections:
- Abstract
- Introduction
- Background
- Related Work
- Future Work
- Conclusion
- References
- Appendix"""
            
            # Get response from LLM
            response = self._get_llm_response(
                "You are a code analysis expert. Extract actionable features and requirements from the whitepaper.",
                prompt
            )
            
            # Parse response into features
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
            
        except Exception as e:
            self.logger.error(f"Failed to extract features: {str(e)}")
            return []
    
    def _process_section(self, section: str, content: List[str]) -> List[Feature]:
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
            features.append(Feature(
                name=f"{section.title()} - {item.split(':')[0].strip()}",
                description=item,
                section=section
            ))
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
    
    def _split_into_sections(self, content: str) -> List[Section]:
        """
        Split whitepaper content into logical sections.
        
        Args:
            content: Whitepaper content
            
        Returns:
            List of sections
        """
        sections = []
        current_title = "Overview"
        current_content = []
        current_code_blocks = []
        current_file_paths = []
        
        for line in content.split('\n'):
            # Check for section headers
            if line.startswith('## '):
                # Save previous section if exists
                if current_content:
                    sections.append(Section(
                        id=str(uuid.uuid4()),
                        title=current_title,
                        content='\n'.join(current_content),
                        dependencies=[],
                        status="pending",
                        code_blocks=current_code_blocks,
                        file_paths=current_file_paths
                    ))
                
                # Start new section
                current_title = line[3:].strip()
                current_content = []
                current_code_blocks = []
                current_file_paths = []
            else:
                # Extract code blocks
                if line.startswith('```'):
                    code_block = []
                    while line and not line.startswith('```'):
                        code_block.append(line)
                        line = next(content.split('\n'))
                    current_code_blocks.append('\n'.join(code_block))
                else:
                    current_content.append(line)
                    
                    # Extract file paths
                    file_paths = re.findall(r'`([^`]+\.py)`', line)
                    current_file_paths.extend(file_paths)
        
        # Add final section
        if current_content:
            sections.append(Section(
                id=str(uuid.uuid4()),
                title=current_title,
                content='\n'.join(current_content),
                dependencies=[],
                status="pending",
                code_blocks=current_code_blocks,
                file_paths=current_file_paths
            ))
        
        return sections
    
    def _analyze_section(self, section: Section) -> None:
        """
        Analyze a section to extract requirements and features.
        
        Args:
            section: Section to analyze
        """
        # Store section
        self.sections[section.id] = section
        
        # Extract features using semantic analysis
        features = []
        
        # Split content into meaningful chunks
        paragraphs = [p.strip() for p in section.content.split('\n\n') if p.strip()]
        
        for paragraph in paragraphs:
            # Process each line in the paragraph
            lines = [line.strip() for line in paragraph.split('\n') if line.strip()]
            for line in lines:
                # Clean up the line
                cleaned_line = re.sub(r'[-*•]', '', line).strip()
                
                # Analyze the line for potential features/requirements
                if any(indicator in cleaned_line.lower() for indicator in [
                    'implement', 'add', 'create', 'support', 'enable', 'provide',
                    'should', 'must', 'needs to', 'requires', 'shall', 'will',
                    'feature', 'functionality', 'capability'
                ]):
                    features.append(cleaned_line)
        
        # Process code blocks for technical requirements
        code_requirements = []
        for code_block in section.code_blocks:
            if code_block.startswith('python'):
                code_block_content = code_block[7:]
                code_requirements.append(code_block_content)
                
                try:
                    tree = ast.parse(code_block_content)
                    
                    # Extract function/class definitions
                    for node in ast.walk(tree):
                        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                            # Get docstring if available
                            docstring = ast.get_docstring(node)
                            if docstring:
                                features.append(f"{node.name}: {docstring.split('.')[0]}")
                            else:
                                features.append(f"{node.name}")
                            
                            # Analyze function parameters and return annotations
                            if isinstance(node, ast.FunctionDef):
                                if node.returns:
                                    features.append(f"{node.name} returns {ast.unparse(node.returns)}")
                                
                                for arg in node.args.args:
                                    if arg.annotation:
                                        features.append(f"{node.name} requires {arg.arg}: {ast.unparse(arg.annotation)}")
                except:
                    pass
        
        # Extract API endpoints or routes
        route_patterns = [
            r'@\w+\.route\([\'"]([^\'"]+)[\'"]\)',  # Flask/FastAPI style
            r'path=[\'"]([^\'"]+)[\'"]',  # Django style
            r'URL:\s*[\'"]([^\'"]+)[\'"]',  # Generic URL documentation
        ]
        
        for pattern in route_patterns:
            routes = re.findall(pattern, section.content)
            for route in routes:
                features.append(f"API endpoint: {route}")
        
        # Clean up and deduplicate features
        cleaned_features = []
        seen = set()
        
        for feature in features:
            # Normalize feature text
            normalized = ' '.join(feature.lower().split())
            if normalized not in seen:
                seen.add(normalized)
                cleaned_features.append(feature)
        
        # Store extracted features and requirements
        section.features = cleaned_features
        section.code_requirements = code_requirements
    
    def _build_dependencies(self) -> None:
        """Build dependencies between sections."""
        for section in self.sections.values():
            # Find references to other sections
            references = re.findall(r'\[(.*?)\]', section.content)
            for ref in references:
                # Look for matching section titles
                for other_section in self.sections.values():
                    if ref.lower() in other_section.title.lower():
                        section.dependencies.append(other_section.id)
    
    def get_section(self, section_id: str) -> Optional[Section]:
        """
        Get a section by its ID.
        
        Args:
            section_id: ID of the section
            
        Returns:
            Section if found, None otherwise
        """
        return self.sections.get(section_id)
    
    def get_pending_sections(self) -> List[Section]:
        """
        Get all pending sections.
        
        Returns:
            List of pending sections
        """
        return [
            section for section in self.sections.values()
            if section.status == "pending"
        ]
    
    def mark_section_complete(self, section_id: str) -> None:
        """
        Mark a section as complete.
        
        Args:
            section_id: ID of the section
        """
        if section_id in self.sections:
            self.sections[section_id].status = "completed"
    
    def mark_section_failed(self, section_id: str, error: str) -> None:
        """
        Mark a section as failed.
        
        Args:
            section_id: ID of the section
            error: Error message
        """
        if section_id in self.sections:
            section = self.sections[section_id]
            section.status = "failed"
            section.error_message = error 