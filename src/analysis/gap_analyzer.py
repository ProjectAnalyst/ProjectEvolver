"""
Gap analysis module for Project Evolver.

This module analyzes the differences between the current codebase state
and the requirements specified in the whitepaper.
"""

import logging
from typing import Dict, List, Any
from dataclasses import dataclass
import re


@dataclass
class Gap:
    """Represents a gap between current state and requirements."""
    id: str
    type: str  # missing_feature, incorrect_implementation, improvement_needed
    description: str
    priority: int
    affected_files: List[str]
    requirements: List[str]
    current_state: str
    desired_state: str


class GapAnalyzer:
    """Analyzes gaps between current codebase and whitepaper requirements."""
    
    def __init__(self):
        """Initialize the gap analyzer."""
        self.logger = logging.getLogger(__name__)
        self.gaps: List[Gap] = []
    
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
            # Clear previous gaps
            self.gaps = []
            
            # Analyze feature gaps
            self._analyze_feature_gaps(whitepaper, current_state)
            
            # Analyze implementation gaps
            self._analyze_implementation_gaps(whitepaper, current_state)
            
            # Analyze improvement gaps
            self._analyze_improvement_gaps(whitepaper, current_state)
            
            return self.gaps
            
        except Exception as e:
            self.logger.error(f"Failed to identify gaps: {str(e)}")
            raise
    
    def _analyze_feature_gaps(self, whitepaper: Dict[str, Any], current_state: Dict[str, Any]) -> None:
        """Analyze gaps in required features."""
        required_features = self._extract_required_features(whitepaper)
        implemented_features = self._extract_implemented_features(current_state)
        
        for feature in required_features:
            if feature not in implemented_features:
                self.gaps.append(Gap(
                    id=f"feature_{len(self.gaps)}",
                    type="missing_feature",
                    description=f"Missing required feature: {feature}",
                    priority=1,
                    affected_files=self._find_affected_files(feature, current_state),
                    requirements=[feature],
                    current_state="Not implemented",
                    desired_state=feature
                ))
    
    def _analyze_implementation_gaps(self, whitepaper: Dict[str, Any], current_state: Dict[str, Any]) -> None:
        """Analyze gaps in implementation correctness."""
        # Compare function implementations with requirements
        for file_path, functions in current_state["functions"].items():
            for func in functions:
                # Check if function matches requirements
                if not self._function_matches_requirements(func, whitepaper):
                    self.gaps.append(Gap(
                        id=f"impl_{len(self.gaps)}",
                        type="incorrect_implementation",
                        description=f"Incorrect implementation of function: {func}",
                        priority=2,
                        affected_files=[file_path],
                        requirements=self._get_function_requirements(func, whitepaper),
                        current_state=f"Current implementation in {file_path}",
                        desired_state="Implementation matching requirements"
                    ))
    
    def _analyze_improvement_gaps(self, whitepaper: Dict[str, Any], current_state: Dict[str, Any]) -> None:
        """Analyze gaps in code quality and improvements."""
        # Check for code quality issues
        for file_path in current_state["functions"].keys():
            if self._needs_improvement(file_path, current_state):
                self.gaps.append(Gap(
                    id=f"improve_{len(self.gaps)}",
                    type="improvement_needed",
                    description=f"Code quality improvements needed in: {file_path}",
                    priority=3,
                    affected_files=[file_path],
                    requirements=["Code quality standards"],
                    current_state="Current implementation",
                    desired_state="Improved implementation"
                ))
    
    def _extract_required_features(self, whitepaper: Dict[str, Any]) -> List[str]:
        """Extract required features from whitepaper."""
        features = []
        
        # Get all sections from whitepaper
        sections = whitepaper.get("sections", {})
        
        # Look for sections containing features
        for section in sections.values():
            # Check section title for feature indicators
            title = section.get("title", "").lower()
            if any(word in title for word in ["feature", "improvement", "enhancement", "requirement"]):
                # Extract bullet points from content
                content = section.get("content", "")
                bullets = re.findall(r"[-*]\s+(.*)", content)
                features.extend(bullets)
        
        # Also look for features in the main content
        content = whitepaper.get("content", "")
        feature_sections = re.findall(r"##\s+Features?\s*(.*?)(?=##|$)", content, re.DOTALL)
        
        for section in feature_sections:
            # Extract bullet points
            bullets = re.findall(r"[-*]\s+(.*)", section)
            features.extend(bullets)
        
        # Remove duplicates and clean up
        features = list(set(features))
        features = [f.strip() for f in features if f.strip()]
        
        self.logger.info(f"Extracted {len(features)} required features from whitepaper")
        for feature in features:
            self.logger.info(f"  - {feature}")
        
        return features
    
    def _extract_implemented_features(self, current_state: Dict[str, Any]) -> List[str]:
        """Extract implemented features from current state."""
        features = []
        
        # Analyze function names and docstrings to identify features
        for file_path, functions in current_state["functions"].items():
            for func in functions:
                if self._is_feature_function(func):
                    features.append(func)
        
        # Also look for features in class names
        for file_path, classes in current_state["classes"].items():
            for cls in classes:
                if self._is_feature_class(cls):
                    features.append(cls)
        
        self.logger.info(f"Found {len(features)} implemented features in codebase")
        for feature in features:
            self.logger.info(f"  - {feature}")
        
        return features
    
    def _is_feature_function(self, func_name: str) -> bool:
        """Determine if a function represents a feature."""
        feature_indicators = [
            "implement", "provide", "support", "enable", "allow",
            "handle", "process", "manage", "create", "update",
            "delete", "add", "remove", "get", "set"
        ]
        return any(indicator in func_name.lower() for indicator in feature_indicators)
    
    def _is_feature_class(self, class_name: str) -> bool:
        """Determine if a class represents a feature."""
        feature_indicators = [
            "manager", "handler", "processor", "controller",
            "service", "provider", "factory", "builder"
        ]
        return any(indicator in class_name.lower() for indicator in feature_indicators)
    
    def _find_affected_files(self, feature: str, current_state: Dict[str, Any]) -> List[str]:
        """Find files that would be affected by implementing a feature."""
        affected_files = []
        # Look for files that might need to be modified
        for file_path, functions in current_state["functions"].items():
            if self._is_related_to_feature(feature, functions):
                affected_files.append(file_path)
        return affected_files
    
    def _is_related_to_feature(self, feature: str, functions: List[str]) -> bool:
        """Determine if functions are related to a feature."""
        feature_keywords = feature.lower().split()
        return any(
            any(keyword in func.lower() for keyword in feature_keywords)
            for func in functions
        )
    
    def _function_matches_requirements(self, func: str, whitepaper: Dict[str, Any]) -> bool:
        """Check if a function implementation matches requirements."""
        # This would need more sophisticated analysis
        return True
    
    def _get_function_requirements(self, func: str, whitepaper: Dict[str, Any]) -> List[str]:
        """Get requirements for a specific function."""
        # This would need more sophisticated analysis
        return []
    
    def _needs_improvement(self, file_path: str, current_state: Dict[str, Any]) -> bool:
        """Determine if a file needs improvement."""
        # This would need more sophisticated analysis
        return False 