"""
Git operations module for Project Evolver.

This module handles all version control operations, including committing
changes, managing branches, and tracking file history. It provides a
clean interface for git operations while handling errors and edge cases.
"""

from typing import List, Optional, Dict
from pathlib import Path
from dataclasses import dataclass
import subprocess
import os
from git import Repo


@dataclass
class CommitInfo:
    """Represents information about a git commit."""
    hash: str
    message: str
    author: str
    timestamp: str
    files_changed: List[str]


class GitOperator:
    """Handles git operations for the project."""
    
    def __init__(self, repo_path: Optional[Path] = None, github_token: Optional[str] = None):
        """
        Initialize the git operator.
        
        Args:
            repo_path: Optional path to the git repository
            github_token: Optional GitHub token for authentication
        """
        self.repo_path = repo_path or Path.cwd()
        self.current_branch: Optional[str] = None
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.has_token = bool(self.github_token)  # Track if we have a token
    
    def _run_git_command(self, command: List[str]) -> bool:
        """
        Run a git command and return success status.
        
        Args:
            command: List of command parts
            
        Returns:
            True if command succeeded, False otherwise
        """
        try:
            result = subprocess.run(
                ["git"] + command,
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"Git command failed: {str(e)}")
            return False
    
    def initialize_repo(self) -> bool:
        """
        Initialize a new git repository if one doesn't exist.
        
        Returns:
            True if successful, False otherwise
        """
        if not self._run_git_command(["init"]):
            return False
        
        # Configure git user if not already configured
        if not self._run_git_command(["config", "--get", "user.name"]):
            self._run_git_command(["config", "user.name", "Project Evolver"])
            self._run_git_command(["config", "user.email", "evolver@example.com"])
        
        return True
    
    def stage_changes(self, files: Optional[List[str]] = None) -> bool:
        """
        Stage changes to specified files or all changes if no files specified.
        
        Args:
            files: Optional list of files to stage
            
        Returns:
            True if successful, False otherwise
        """
        if files:
            return self._run_git_command(["add"] + files)
        else:
            return self._run_git_command(["add", "."])
    
    def commit_changes(self, message: str) -> bool:
        """
        Commit changes to the repository.
        
        Args:
            message: Commit message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add all changes
            if not self._run_git_command(["add", "."]):
                return False
            
            # Commit changes
            if not self._run_git_command(["commit", "-m", message]):
                return False
            
            # Push changes if we have a token
            if self.has_token:
                if not self._run_git_command(["push", "origin", "main"]):
                    return False
            
            return True
        except Exception as e:
            print(f"Failed to commit changes: {str(e)}")
            return False
    
    def push_changes(self, branch: Optional[str] = None) -> bool:
        """
        Push committed changes to the remote repository.
        
        Args:
            branch: Optional branch name to push to
            
        Returns:
            True if successful, False otherwise
        """
        if not branch:
            # Get current branch name
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                branch = result.stdout.strip()
            else:
                branch = "main"  # Default to main if branch detection fails
        
        # Set up the remote URL with token if available
        if self.github_token:
            remote_url = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            if remote_url.returncode == 0:
                url = remote_url.stdout.strip()
                if url.startswith("https://"):
                    new_url = f"https://{self.github_token}@" + url[8:]
                    self._run_git_command(["remote", "set-url", "origin", new_url])
        
        # Push changes
        return self._run_git_command(["push", "origin", branch])
    
    def get_status(self) -> Dict[str, List[str]]:
        """
        Get the current git status.
        
        Returns:
            Dictionary of status categories and their files
        """
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return {}
        
        status_dict = {
            "modified": [],
            "untracked": [],
            "deleted": [],
            "renamed": [],
            "conflicted": []
        }
        
        for line in result.stdout.splitlines():
            status = line[:2]
            file = line[3:]
            
            if status.startswith("M"):
                status_dict["modified"].append(file)
            elif status.startswith("??"):
                status_dict["untracked"].append(file)
            elif status.startswith("D"):
                status_dict["deleted"].append(file)
            elif status.startswith("R"):
                status_dict["renamed"].append(file)
            elif status.startswith("U"):
                status_dict["conflicted"].append(file)
        
        return status_dict
    
    def is_repo_initialized(self) -> bool:
        """
        Check if a git repository exists at the specified path.
        
        Returns:
            True if a git repository exists, False otherwise
        """
        try:
            # Check if .git directory exists
            git_dir = Path(self.repo_path) / ".git"
            if not git_dir.exists() or not git_dir.is_dir():
                return False
            
            # Verify git repo is valid by running git status
            result = subprocess.run(
                ["git", "status"],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
            
        except Exception as e:
            print(f"Failed to check repository status: {str(e)}")
            return False
    
    def get_commit_history(self, limit: int = 10) -> List[CommitInfo]:
        """
        Get recent commit history.
        
        Args:
            limit: Maximum number of commits to return
            
        Returns:
            List of commit information
        """
        result = subprocess.run(
            ["git", "log", f"-n{limit}", "--pretty=format:%H|%s|%an|%at"],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return []
        
        commits = []
        for line in result.stdout.splitlines():
            hash_, message, author, timestamp = line.split("|")
            commits.append(CommitInfo(
                hash=hash_,
                message=message,
                author=author,
                timestamp=timestamp,
                files_changed=[]  # We could add file changes if needed
            ))
        
        return commits
    
    def create_branch(self, branch_name: str) -> bool:
        """
        Create and switch to a new branch.
        
        Args:
            branch_name: Name of the new branch
            
        Returns:
            True if successful, False otherwise
        """
        if not self._run_git_command(["checkout", "-b", branch_name]):
            return False
        
        self.current_branch = branch_name
        return True
    
    def switch_branch(self, branch_name: str) -> bool:
        """
        Switch to an existing branch.
        
        Args:
            branch_name: Name of the branch to switch to
            
        Returns:
            True if successful, False otherwise
        """
        if not self._run_git_command(["checkout", branch_name]):
            return False
        self.current_branch = branch_name
        return True
    
    def merge_branch(self, branch_name: str) -> bool:
        """
        Merge a branch into the current branch.
        
        Args:
            branch_name: Name of the branch to merge
            
        Returns:
            True if successful, False otherwise
        """
        return self._run_git_command(["merge", branch_name])
    
    def clone_repository(self, repo_url: str) -> bool:
        """
        Clone a GitHub repository or update if it exists.
        
        Args:
            repo_url: GitHub repository URL or username/repo format
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert username/repo format to full URL if needed
            if '/' in repo_url and not repo_url.startswith(('http://', 'https://')):
                repo_url = f"https://github.com/{repo_url}.git"
                print(f"Converting to full URL: {repo_url}")
            
            # Add token to URL if available
            if self.github_token and 'github.com' in repo_url:
                if repo_url.startswith('https://'):
                    repo_url = f"https://{self.github_token}@{repo_url[8:]}"
                elif repo_url.startswith('http://'):
                    repo_url = f"http://{self.github_token}@{repo_url[7:]}"
                print("Added GitHub token to URL")
            
            # Extract repository name from URL
            repo_name = repo_url.split('/')[-1].replace('.git', '')
            target_path = self.repo_path / repo_name
            print(f"Attempting to clone repository to: {target_path}")
            
            # Check if repository exists
            if target_path.exists():
                print(f"Repository already exists at {target_path}, updating...")
                # Update existing repository
                self.repo_path = target_path
                if not self._run_git_command(["fetch", "origin"]):
                    print("Failed to fetch updates")
                    return False
                if not self._run_git_command(["reset", "--hard", "origin/main"]):
                    print("Failed to reset to latest changes")
                    return False
                print("Successfully updated repository")
                return True
            
            # Clone the repository
            result = subprocess.run(
                ["git", "clone", repo_url],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                print(f"Git clone failed with error: {result.stderr}")
                return False
            
            # Update repo_path to point to the cloned repository
            self.repo_path = target_path
            print(f"Successfully cloned repository to {self.repo_path}")
            return True
            
        except Exception as e:
            print(f"Failed to clone repository: {str(e)}")
            return False 