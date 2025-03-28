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


class WhitepaperProcessor:
    """Processes and analyzes project whitepapers."""
    
    def __init__(self):
        """Initialize the whitepaper processor."""
        self.logger = logging.getLogger(__name__)
        self.sections: Dict[str, Section] = {}
        self.current_section: Optional[Section] = None
    
    def load_and_analyze(self, whitepaper_path: str) -> Dict[str, Any]:
        """
        Load and analyze a whitepaper file.
        
        Args:
            whitepaper_path: Path to the whitepaper file
            
        Returns:
            Dictionary containing whitepaper analysis
        """
        try:
            # Read whitepaper content
            with open(whitepaper_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Split content into sections
            sections = self._split_into_sections(content)
            
            # Analyze each section
            for section in sections:
                self._analyze_section(section)
            
            # Build section dependencies
            self._build_dependencies()
            
            return {
                "content": content,
                "sections": {
                    section.id: {
                        "title": section.title,
                        "content": section.content,
                        "dependencies": section.dependencies,
                        "status": section.status,
                        "code_blocks": section.code_blocks,
                        "file_paths": section.file_paths
                    }
                    for section in self.sections.values()
                }
            }
            
        except Exception as e:
            self.logger.error(f"Failed to load whitepaper: {str(e)}")
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
        
        # Extract features from bullet points
        features = re.findall(r'[-*]\s+(.*)', section.content)
        section.features = features
        
        # Extract code requirements
        code_requirements = []
        for code_block in section.code_blocks:
            if code_block.startswith('python'):
                code_requirements.append(code_block[7:])
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