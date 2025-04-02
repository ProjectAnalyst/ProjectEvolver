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
            
            # Parse file information from implementation details
            files_to_modify = []
            if 'raw_analysis' in gap.implementation_details:
                analysis = gap.implementation_details['raw_analysis']
                # Parse files to modify from the structured format
                current_file = None
                current_info = {}
                for line in analysis.split('\n'):
                    line = line.strip()
                    if line.startswith('- FILE:'):
                        if current_file:
                            files_to_modify.append((current_file, current_info))
                        current_file = line[7:].strip()
                        current_info = {}
                    elif line.startswith('  LOCATION:'):
                        current_info['location'] = line[11:].strip()
                    elif line.startswith('  CHANGES:'):
                        current_info['changes'] = line[10:].strip()
                    elif line.startswith('  REASON:'):
                        current_info['reason'] = line[9:].strip()
                if current_file:
                    files_to_modify.append((current_file, current_info))
            
            # Initialize gap info with basic information
            gap_info = f"""# Feature Gap Analysis

## Feature Details
- **Name**: {gap.section}
- **Status**: {gap.status}
- **Type**: {gap.type}
- **Priority**: {gap.priority}
- **Confidence**: {gap.confidence}

## Description
{gap.description}

## Implementation Details
{gap.implementation_details.get('raw_analysis', 'No current implementation')}

## Missing Components
{', '.join(gap.missing_components)}

## Files to Modify"""
            
            # Add information about existing files to modify
            if files_to_modify:
                for file_path, file_info in files_to_modify:
                    gap_info += f"\n### {file_path}\n"
                    if 'location' in file_info:
                        gap_info += f"- Location: {file_info['location']}\n"
                    if 'changes' in file_info:
                        gap_info += f"- Changes: {file_info['changes']}\n"
                    if 'reason' in file_info:
                        gap_info += f"- Reason: {file_info['reason']}\n"
                    
                    # Get the file content if available
                    file_content = gap.file_contents.get(file_path, '')
                    if file_content:
                        gap_info += f"\nCurrent file content:\n```python\n{file_content}\n```\n"
            
            # Create implementation prompt
            prompt = f"""Generate code to implement this feature gap:

{gap_info}

Generate complete, implementation-ready code for each affected file.
Format your response as:

FILE: <file_path>
```python
<complete file content>
```

Repeat for each affected file.

Consider the following when generating code:
1. Maintain consistent code style with existing files
2. Include all necessary imports
3. Handle dependencies properly
4. Follow the project's architectural patterns
5. Include appropriate error handling
6. Implement all required changes specified for each file
7. Ensure all missing components are implemented
8. Follow the file structure impact guidelines
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