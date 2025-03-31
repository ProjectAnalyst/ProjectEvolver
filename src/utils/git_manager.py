import os
from datetime import datetime
from git import Repo
from typing import List

class GitManager:
    """Manages Git operations for the project."""
    
    def __init__(self, repo_path: str):
        """Initialize with path to repository."""
        self.repo_path = repo_path
        self.repo = Repo(repo_path)
        
    def get_timestamp(self) -> str:
        """Get current timestamp for branch naming."""
        return datetime.now().strftime('%Y%m%d-%H%M%S')
        
    def create_branch(self, branch_name: str) -> None:
        """Create and checkout a new branch."""
        current = self.repo.create_head(branch_name)
        current.checkout()
        
    def commit(self, files: List[str], message: str) -> None:
        """Stage and commit changes to specified files."""
        # Add files
        for file_path in files:
            full_path = os.path.join(self.repo_path, file_path)
            self.repo.index.add([full_path])
        
        # Commit
        self.repo.index.commit(message)
        
    def push(self, branch_name: str) -> None:
        """Push changes to remote repository."""
        origin = self.repo.remote('origin')
        origin.push(branch_name) 