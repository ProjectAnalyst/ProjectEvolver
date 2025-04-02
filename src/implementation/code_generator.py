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

    def _apply_diff(self, file_path: Path, diff_content: str) -> str:
        """
        Apply a git-style diff to a file.
        
        Args:
            file_path: Path to the file to modify
            diff_content: Git-style diff content
            
        Returns:
            The new content of the file after applying the diff
        """
        try:
            # Read current file content
            with open(file_path, 'r', encoding='utf-8') as f:
                current_lines = f.readlines()
            
            # Parse diff content
            diff_lines = diff_content.split('\n')
            new_lines = []
            i = 0
            
            while i < len(diff_lines):
                line = diff_lines[i]
                
                # Skip empty lines and diff headers
                if not line or line.startswith('@@'):
                    i += 1
                    continue
                
                # Handle removed lines
                if line.startswith('- '):
                    i += 1
                    continue
                
                # Handle added lines
                if line.startswith('+ '):
                    new_lines.append(line[2:])
                    i += 1
                    continue
                
                # Handle context lines (lines without + or -)
                if line.startswith(' '):
                    new_lines.append(line[1:])
                    i += 1
                    continue
                
                i += 1
            
            return ''.join(new_lines)
            
        except Exception as e:
            self.logger.error(f"Failed to apply diff to {file_path}: {str(e)}")
            raise

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
            
            # Log the codebase root for debugging
            self.logger.info(f"Codebase root: {codebase_root}")
            
            # Parse file information from implementation details
            files_to_modify = []
            if 'raw_analysis' in gap.implementation_details:
                analysis = gap.implementation_details['raw_analysis']
                # Parse files to modify from the structured format
                current_file = None
                current_info = {}
                for line in analysis.split('\n'):
                    line = line.strip()
                    # Handle both markdown and plain formats
                    if line.startswith(('- FILE:', '- **FILE:**', '**FILE:**')):
                        if current_file:
                            files_to_modify.append((current_file, current_info))
                        # Clean up file path - remove backticks, markdown, and get relative path
                        current_file = line.replace('-', '').replace('**', '').replace('FILE:', '').strip().strip('`')
                        current_info = {}
                    elif line.startswith(('  LOCATION:', '  - **LOCATION:**', '**LOCATION:**')):
                        current_info['location'] = line.replace('-', '').replace('**', '').replace('LOCATION:', '').strip()
                    elif line.startswith(('  CHANGES:', '  - **CHANGES:**', '**CHANGES:**')):
                        current_info['changes'] = line.replace('-', '').replace('**', '').replace('CHANGES:', '').strip()
                    elif line.startswith(('  REASON:', '  - **REASON:**', '**REASON:**')):
                        current_info['reason'] = line.replace('-', '').replace('**', '').replace('REASON:', '').strip()
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
                    
                    # Get the file content from the repository
                    try:
                        # Try different path variations
                        possible_paths = [
                            file_path,  # Try exact path
                            file_path.split('/')[-1],  # Try just the filename
                            '/'.join(file_path.split('/')[1:])  # Try without project name prefix
                        ]
                        
                        file_content = None
                        target_path = None
                        for path in possible_paths:
                            full_path = codebase_root / path
                            self.logger.info(f"Trying path: {full_path}")
                            
                            if full_path.exists() and full_path.is_file():
                                with open(full_path, 'r', encoding='utf-8') as f:
                                    file_content = f.read()
                                    target_path = full_path
                                    self.logger.info(f"Successfully read file from: {full_path}")
                                    break
                        
                        if file_content:
                            gap_info += f"\nCurrent file content:\n```python\n{file_content}\n```\n"
                        else:
                            self.logger.warning(f"File not found in any of the attempted paths: {possible_paths}")
                            gap_info += "\nFile not found in repository.\n"
                    except Exception as e:
                        self.logger.warning(f"Failed to read file {file_path}: {str(e)}")
                        gap_info += "\nFailed to read file content.\n"
            
            # Create implementation prompt
            prompt = f"""Generate code changes to implement this feature gap:

{gap_info}

Generate specific code changes for each affected file.
Format your response as:

FILE: <file_path>
```diff
- <lines to remove>
+ <lines to add>
```

Repeat for each affected file.

Consider the following when generating changes:
1. Only include the specific lines that need to be changed
2. Use git-style diff format with - for lines to remove and + for lines to add
3. Include enough context around the changes (2-3 lines before and after)
4. Maintain consistent code style with existing files
5. Include all necessary imports if adding new ones
6. Handle dependencies properly
7. Follow the project's architectural patterns
8. Include appropriate error handling
9. Implement all required changes specified for each file
10. Ensure all missing components are implemented
11. Follow the file structure impact guidelines
"""
            
            # Get response from LLM
            response = self._get_llm_response(
                "You are an expert Python developer. Generate specific code changes in git-style diff format.",
                prompt
            )
            
            # Parse response into file changes
            changes = self._parse_changes(response)
            
            # Apply changes to files
            modified_files = {}
            for file_path, diff_content in changes.items():
                try:
                    # Construct the full path for the file
                    full_path = codebase_root / file_path
                    self.logger.info(f"Processing file: {full_path}")
                    
                    # For new files, just write the content directly
                    if not full_path.exists():
                        self.logger.info(f"Creating new file: {full_path}")
                        full_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(full_path, 'w', encoding='utf-8') as f:
                            f.write(diff_content)
                        modified_files[str(full_path)] = diff_content
                        continue
                    
                    # For existing files, apply the diff
                    new_content = self._apply_diff(full_path, diff_content)
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    modified_files[str(full_path)] = new_content
                    self.logger.info(f"Successfully applied changes to {full_path}")
                    
                except Exception as e:
                    self.logger.error(f"Failed to apply changes to {file_path}: {str(e)}")
            
            if not modified_files:
                self.logger.warning("No changes were applied to any files")
                return {}
            
            # Create a commit message
            commit_message = f"""
Implement {gap.section}

Description: {gap.description}
Status: {gap.status}
Files modified: {', '.join(modified_files.keys())}

Missing components addressed:
{chr(10).join('- ' + comp for comp in gap.missing_components)}

Implementation approach:
{gap.implementation_details.get('suggested_approach', 'No specific approach provided')}
"""
            
            # Return both the modified files and commit message
            return {
                'modified_files': modified_files,
                'commit_message': commit_message
            }
            
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
                model="gpt-4o-mini",
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
        in_diff_block = False
        
        for line in response.split('\n'):
            if line.startswith('FILE: '):
                # Save previous file if exists
                if current_file and current_content:
                    changes[current_file] = '\n'.join(current_content)
                    current_content = []
                
                # Start new file - clean up the path by removing backticks and extra spaces
                current_file = line[6:].strip().strip('`')
                
            elif line.startswith('```diff'):
                # Start of diff block
                in_diff_block = True
                continue
            elif line.startswith('```'):
                # End of diff block
                in_diff_block = False
                if current_file and current_content:
                    changes[current_file] = '\n'.join(current_content)
                    current_content = []
            elif in_diff_block:
                # Add line to current content
                current_content.append(line)
        
        # Add final file if exists
        if current_file and current_content:
            changes[current_file] = '\n'.join(current_content)
        
        return changes 