"""
Task planning module for Project Evolver.

This module handles the creation and management of tasks based on identified gaps
between the current codebase and the whitepaper requirements.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import uuid

from ..analysis.gap_analyzer import Gap
from ..utils.llm_logger import LLMLogger

@dataclass
class Task:
    """Represents an actionable task for improving the codebase."""
    id: str
    type: str
    description: str
    priority: int
    target_files: List[str]
    requirements: List[str]
    current_state: str
    desired_state: str
    dependencies: List[str] = None
    status: str = "pending"

class TaskPlanner:
    """Plans and manages tasks for improving the codebase."""
    
    def __init__(self):
        """Initialize the TaskPlanner."""
        self.logger = logging.getLogger(__name__)
        self.llm_logger = LLMLogger()
    
    def _get_llm_response(self, system_prompt: str, user_prompt: str) -> str:
        """
        Get response from OpenAI's GPT-4 model.
        
        Args:
            system_prompt: The system prompt for the LLM
            user_prompt: The user prompt for the LLM
            
        Returns:
            str: The LLM's response
        """
        try:
            # Start a new session for task planning
            self.llm_logger.start_session("task_planning")
            
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
            
            # Format messages
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            
            # Get response
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
    
    def create_tasks(self, gaps: List[Gap]) -> List[Task]:
        """Create tasks from identified gaps."""
        tasks = []
        
        for gap in gaps:
            try:
                # Create implementation prompt
                prompt = f"""Create a detailed implementation task for this gap:

FEATURE GAP:
Name: {gap.section}
Description: {gap.description}
Status: {gap.status}
Missing Components: {', '.join(gap.missing_components)}

Requirements:
{chr(10).join(f'- {req}' for req in gap.requirements)}

Current Implementation Details:
{gap.implementation_details.get('suggested_code', 'No code suggestion available')}

Create a specific, actionable task that includes:
1. Clear acceptance criteria
2. Technical approach
3. Testing requirements
4. Estimated complexity (1-5)
5. Dependencies (if any)
"""
                
                response = self._get_llm_response(
                    "You are a technical project manager. Create detailed implementation tasks.",
                    prompt
                )
                
                # Parse response and create task
                task = self._parse_task_response(response, gap)
                tasks.append(task)
                self.logger.info(f"Created task for gap: {gap.section}")
                
            except Exception as e:
                self.logger.error(f"Failed to create task from gap: {str(e)}")
                continue
        
        return tasks
    
    def _parse_task_response(self, response: str, gap: Gap) -> Task:
        """Parse LLM response into a Task object."""
        # Default values
        task_data = {
            "id": str(uuid.uuid4())[:8],
            "title": f"Implement {gap.section}",
            "description": gap.description,
            "acceptance_criteria": [],
            "technical_approach": "",
            "testing_requirements": [],
            "complexity": 3,
            "dependencies": [],
            "status": "pending"
        }
        
        current_section = None
        for line in response.split('\n'):
            line = line.strip()
            if not line:
                continue
            
            if line.startswith('ACCEPTANCE CRITERIA:'):
                current_section = 'acceptance'
            elif line.startswith('TECHNICAL APPROACH:'):
                current_section = 'approach'
            elif line.startswith('TESTING REQUIREMENTS:'):
                current_section = 'testing'
            elif line.startswith('COMPLEXITY:'):
                task_data['complexity'] = int(line.split(':')[1].strip()[0])
            elif line.startswith('DEPENDENCIES:'):
                current_section = 'dependencies'
            elif line.startswith('- '):
                if current_section == 'acceptance':
                    task_data['acceptance_criteria'].append(line[2:])
                elif current_section == 'testing':
                    task_data['testing_requirements'].append(line[2:])
                elif current_section == 'dependencies':
                    task_data['dependencies'].append(line[2:])
            elif current_section == 'approach':
                task_data['technical_approach'] += line + '\n'
        
        return Task(
            id=task_data['id'],
            title=task_data['title'],
            description=task_data['description'],
            acceptance_criteria=task_data['acceptance_criteria'],
            technical_approach=task_data['technical_approach'],
            testing_requirements=task_data['testing_requirements'],
            complexity=task_data['complexity'],
            dependencies=task_data['dependencies'],
            status=task_data['status']
        )
    
    def _analyze_task_dependencies(self, tasks: List[Task]) -> Dict[str, List[str]]:
        """
        Analyze dependencies between tasks.
        
        Args:
            tasks: List of tasks to analyze
            
        Returns:
            Dictionary mapping task IDs to their dependencies
        """
        dependencies = {}
        
        for task in tasks:
            task_deps = []
            
            # Check for dependencies based on affected files
            for other_task in tasks:
                if other_task.id != task.id:
                    # If a task affects files that another task depends on
                    if any(file in other_task.target_files for file in task.target_files):
                        task_deps.append(other_task.id)
            
            dependencies[task.id] = task_deps
        
        return dependencies
    
    def _has_dependency(self, task1: Task, task2: Task) -> bool:
        """
        Check if task1 depends on task2.
        
        Args:
            task1: First task
            task2: Second task
            
        Returns:
            True if task1 depends on task2
        """
        # Check if task2 affects files that task1 depends on
        return any(file in task2.target_files for file in task1.target_files)

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Get a task by its ID.
        
        Args:
            task_id: ID of the task to get
            
        Returns:
            Task if found, None otherwise
        """
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_tasks_by_type(self, task_type: str) -> List[Task]:
        """
        Get all tasks of a specific type.
        
        Args:
            task_type: Type of tasks to get
            
        Returns:
            List of matching tasks
        """
        return [task for task in self.tasks if task.type == task_type]
    
    def get_tasks_by_priority(self, priority: int) -> List[Task]:
        """
        Get all tasks with a specific priority.
        
        Args:
            priority: Priority level to get
            
        Returns:
            List of matching tasks
        """
        return [task for task in self.tasks if task.priority == priority]

    def build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build a graph of task dependencies."""
        graph = {}
        for task in self.tasks:
            graph[task.description] = []
            for other_task in self.tasks:
                if task != other_task:
                    if any(req in other_task.requirements for req in task.requirements):
                        graph[task.description].append(other_task.description)
        return graph

    def prioritize_tasks(self) -> List[Task]:
        """Prioritize tasks based on dependencies and complexity."""
        graph = self.build_dependency_graph()
        visited = set()
        priority = 1
        prioritized_tasks = []

        def visit(task_desc: str):
            nonlocal priority
            if task_desc in visited:
                return
            visited.add(task_desc)
            for dep in graph[task_desc]:
                visit(dep)
            task = next(t for t in self.tasks if t.description == task_desc)
            task.priority = priority
            prioritized_tasks.append(task)
            priority += 1

        for task in self.tasks:
            if task.description not in visited:
                visit(task.description)

        return prioritized_tasks 