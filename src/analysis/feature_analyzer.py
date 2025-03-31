"""
Feature analysis module for Project Evolver.
Combines gap analysis and task planning into a unified analysis system.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
import logging
from pathlib import Path

@dataclass
class ImplementationPlan:
    """Represents analysis of a feature and its implementation plan."""
    feature_name: str
    status: str  # 'implemented', 'partial', 'missing'
    current_state: Dict[str, Any]
    required_changes: List[Dict[str, Any]]
    implementation_approach: str
    affected_files: List[str]
    dependencies: List[str]
    priority: int

class FeatureAnalyzer:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm_logger = LLMLogger()
        
    def analyze_feature(self, feature: Dict[str, Any], codebase_context: Dict[str, Any]) -> ImplementationPlan:
        """Analyze a feature and create implementation plan."""
        prompt = f"""Analyze this feature and provide a complete implementation plan:

FEATURE:
Name: {feature['name']}
Description: {feature['description']}

CURRENT CODEBASE CONTEXT:
{self._format_codebase_context(codebase_context)}

Provide a complete analysis in this format:
STATUS: <implemented/partial/missing>
CURRENT STATE: <description of existing implementation if any>
REQUIRED CHANGES:
- <specific change needed>
- <impact and scope>
IMPLEMENTATION APPROACH:
<detailed approach including code structure>
AFFECTED FILES:
- <file path>: <what needs to change>
DEPENDENCIES:
- <any dependencies for implementation>
"""
        
        response = self._get_llm_response(
            "You are a technical architect. Analyze feature implementation and create detailed plan.",
            prompt
        )
        
        # Parse response into ImplementationPlan
        analysis = self._parse_analysis(response)
        return analysis 