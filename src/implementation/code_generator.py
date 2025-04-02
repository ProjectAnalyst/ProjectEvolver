"""
Code generation module for Project Evolver.

This module handles generating code changes based on identified gaps.
"""

import logging
from typing import Dict, List, Any
from pathlib import Path
from ..utils.llm_logger import LLMLogger

class CodeGenerator:
    """Generates code changes based on identified gaps."""
    
    def __init__(self):
        """Initialize the code generator."""
        self.logger = logging.getLogger(__name__)
        self.llm_logger = LLMLogger()

    def generate_changes(self, gap: Any, codebase_root: Path) -> Dict[str, str]:
        """
        Generate code changes to implement a gap.
        
        Args:
            gap: The gap to implement
            codebase_root: Root directory of the codebase
            
        Returns:
            Dictionary mapping file paths to their new content
        """
        try:
            # Start LLM logging session
            self.llm_logger.start_session("code_generation")
            
            # Create implementation prompt
            prompt = f"""Generate code to implement this feature gap:

FEATURE:
Name: {gap.section}
Description: {gap.description}
Status: {gap.status}
Missing Components: {', '.join(gap.missing_components)}

Current Implementation Details:
{gap.implementation_details.get('current_state', 'No current implementation')}

Required Changes:
{gap.implementation_details.get('required_changes', 'No specific changes required')}

Affected Files: {', '.join(gap.affected_files)}

Generate complete, implementation-ready code for each affected file.
Format your response as:

FILE: <file_path>
```python
<complete file content>
```

Repeat for each affected file.
"""
            
            # Get response from LLM
            response = self._get_llm_response(
                "You are an expert Python developer. Generate complete, implementation-ready code.",
                prompt
            )
            
            # Parse response into file changes
            changes = self._parse_changes(response)
            
            return changes
            
        except Exception as e:
            self.logger.error(f"Failed to generate changes: {str(e)}")
            raise

    def _get_llm_response(self, system_prompt: str, user_prompt: str) -> str:
        """Get response from LLM."""
        try:
            import os
            from openai import OpenAI
            from dotenv import load_dotenv
            import httpx
            
            # Load environment variables
            load_dotenv()
            
            # Get API key
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            
            # Create transport
            transport = httpx.HTTPTransport(retries=3)
            
            # Initialize OpenAI client
            client = OpenAI(
                api_key=api_key,
                http_client=httpx.Client(transport=transport)
            )
            
            # Get response
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            response_content = response.choices[0].message.content
            
            # Log the interaction
            metadata = {
                "model": "gpt-4",
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

    def _parse_changes(self, response: str) -> Dict[str, str]:
        """
        Parse LLM response into file changes.
        
        Args:
            response: LLM response text
            
        Returns:
            Dictionary mapping file paths to their new content
        """
        changes = {}
        current_file = None
        current_content = []
        
        for line in response.split('\n'):
            if line.startswith('FILE: '):
                # Save previous file if exists
                if current_file and current_content:
                    changes[current_file] = '\n'.join(current_content)
                    current_content = []
                
                # Start new file
                current_file = line[6:].strip()
                
            elif line.startswith('```python'):
                # Start of code block
                continue
            elif line.startswith('```'):
                # End of code block
                if current_file and current_content:
                    changes[current_file] = '\n'.join(current_content)
                    current_content = []
            else:
                # Add line to current content
                current_content.append(line)
        
        # Add final file if exists
        if current_file and current_content:
            changes[current_file] = '\n'.join(current_content)
        
        return changes 