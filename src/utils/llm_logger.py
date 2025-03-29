"""
LLM logging utility for Project Evolver.

This module provides functionality to log LLM interactions for debugging and analysis.
"""

import logging
from datetime import datetime
from pathlib import Path
import os
import glob
from typing import Dict, Any, Optional, List
import json

class LLMLogger:
    """Logs LLM interactions for debugging and analysis."""
    
    def __init__(self):
        """Initialize the LLM logger."""
        self.logger = logging.getLogger(__name__)
        self.log_dir = Path("logs/llm")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_session = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_purpose = None
        self.current_file = None
        
    def start_session(self, purpose: str) -> None:
        """
        Start a new logging session for a specific purpose.
        
        Args:
            purpose: Purpose of the LLM calls (e.g., "whitepaper_processing", "codebase_analysis")
        """
        self.current_purpose = purpose
        self.current_session = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create purpose-specific directory
        purpose_dir = self.log_dir / purpose
        purpose_dir.mkdir(parents=True, exist_ok=True)
        
        # Create log file for this session
        self.current_file = purpose_dir / f"session_{self.current_session}.md"
        
        # Write header
        with open(self.current_file, 'w', encoding='utf-8') as f:
            f.write(f"# LLM Interactions: {purpose}\n")
            f.write(f"Session started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
        # Clean up old logs
        self._cleanup_old_logs(purpose)
        
    def log_interaction(self, 
                       system_prompt: str,
                       user_prompt: str,
                       response: str,
                       metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an LLM interaction.
        
        Args:
            system_prompt: System prompt sent to LLM
            user_prompt: User prompt sent to LLM
            response: Response received from LLM
            metadata: Optional metadata about the interaction
        """
        if not self.current_purpose:
            self.logger.warning("No active session. Call start_session first.")
            return
            
        try:
            # Write to markdown file
            with open(self.current_file, 'a', encoding='utf-8') as f:
                f.write(f"## Interaction {datetime.now().strftime('%H:%M:%S')}\n\n")
                f.write("### System Prompt\n")
                f.write(f"```\n{system_prompt}\n```\n\n")
                f.write("### User Prompt\n")
                f.write(f"```\n{user_prompt}\n```\n\n")
                f.write("### Response\n")
                f.write(f"```\n{response}\n```\n\n")
                if metadata:
                    f.write("### Metadata\n")
                    f.write("```json\n")
                    f.write(json.dumps(metadata, indent=2))
                    f.write("\n```\n\n")
                f.write("---\n\n")
                
        except Exception as e:
            self.logger.error(f"Failed to log LLM interaction: {str(e)}")
            
    def _cleanup_old_logs(self, purpose: str) -> None:
        """
        Clean up old log files, keeping only the last 3 runs.
        
        Args:
            purpose: Purpose of the logs to clean up
        """
        try:
            # Find all log files in the purpose directory
            purpose_dir = self.log_dir / purpose
            pattern = purpose_dir / "session_*.md"
            log_files = sorted(glob.glob(str(pattern)))
            
            # Remove oldest files if we have more than 3
            while len(log_files) > 3:
                oldest_file = log_files.pop(0)
                try:
                    os.remove(oldest_file)
                except Exception as e:
                    self.logger.warning(f"Failed to remove old log file {oldest_file}: {str(e)}")
                    
        except Exception as e:
            self.logger.error(f"Failed to clean up old logs: {str(e)}")
            
    def get_recent_interactions(self, purpose: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent LLM interactions for a specific purpose.
        
        Args:
            purpose: Purpose of the interactions to retrieve
            limit: Maximum number of interactions to return
            
        Returns:
            List of recent interactions
        """
        try:
            # Find the most recent log file in the purpose directory
            purpose_dir = self.log_dir / purpose
            pattern = purpose_dir / "session_*.md"
            log_files = sorted(glob.glob(str(pattern)), reverse=True)
            
            if not log_files:
                return []
                
            # Read the most recent file
            with open(log_files[0], 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse interactions from markdown
            interactions = []
            current_interaction = {}
            
            for line in content.split('\n'):
                line = line.strip()
                if line.startswith('## Interaction'):
                    if current_interaction:
                        interactions.append(current_interaction)
                    current_interaction = {'timestamp': line[3:].strip()}
                elif line.startswith('### System Prompt'):
                    current_interaction['system_prompt'] = ''
                elif line.startswith('### User Prompt'):
                    current_interaction['user_prompt'] = ''
                elif line.startswith('### Response'):
                    current_interaction['response'] = ''
                elif line.startswith('### Metadata'):
                    current_interaction['metadata'] = {}
                elif line.startswith('```'):
                    continue
                elif line and current_interaction:
                    if 'system_prompt' in current_interaction and isinstance(current_interaction['system_prompt'], str):
                        current_interaction['system_prompt'] += line + '\n'
                    elif 'user_prompt' in current_interaction and isinstance(current_interaction['user_prompt'], str):
                        current_interaction['user_prompt'] += line + '\n'
                    elif 'response' in current_interaction and isinstance(current_interaction['response'], str):
                        current_interaction['response'] += line + '\n'
                    elif 'metadata' in current_interaction and isinstance(current_interaction['metadata'], dict):
                        try:
                            current_interaction['metadata'] = json.loads(line)
                        except:
                            pass
            
            if current_interaction:
                interactions.append(current_interaction)
                
            return interactions[-limit:]
            
        except Exception as e:
            self.logger.error(f"Failed to get recent interactions: {str(e)}")
            return []