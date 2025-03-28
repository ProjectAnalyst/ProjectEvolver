"""
File management module for Project Evolver.

This module handles all file system operations, including creating,
modifying, and deleting files. It ensures proper file handling and
maintains file state consistency.
"""

from typing import Optional, List, Dict
from pathlib import Path
from dataclasses import dataclass
import os
import shutil
import logging


@dataclass
class FileOperation:
    """Represents a file system operation."""
    operation_type: str  # 'create', 'modify', 'delete'
    file_path: str
    content: Optional[str] = None
    backup_path: Optional[str] = None


class FileManager:
    """Manages file system operations for the project."""
    
    def __init__(self, project_root: Optional[Path] = None, enable_backups: bool = False):
        """
        Initialize the file manager.
        
        Args:
            project_root: Optional root directory for the project
            enable_backups: Whether to enable backup functionality
        """
        self.project_root = project_root or Path.cwd()
        self.backup_dir = None
        
        # Ensure project root exists
        self.project_root.mkdir(parents=True, exist_ok=True)
        
        # Create backup directory only if backups are enabled
        if enable_backups:
            self.backup_dir = self.project_root / ".backups"
            try:
                self.backup_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                logging.error(f"Failed to create backup directory: {str(e)}")
                self.backup_dir = None
            
        self.changes: Dict[str, str] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_file(self, file_path: str, content: str) -> bool:
        """
        Create a new file with the given content.
        
        Args:
            file_path: Path to create the file at
            content: Content to write to the file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(file_path)
            if path.exists():
                self.logger.warning(f"File already exists: {file_path}")
                return False
                
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            path.write_text(content)
            
            # Track change
            self.changes[file_path] = content
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to create file {file_path}: {str(e)}")
            return False
    
    def modify_file(self, file_path: str, content: str) -> bool:
        """
        Modify an existing file with new content.
        
        Args:
            file_path: Path to the file to modify
            content: New content to write
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.warning(f"File does not exist: {file_path}")
                return False
                
            # Create backup before modifying if backup directory exists
            backup_path = None
            if self.backup_dir:
                backup_path = self.backup_file(file_path)
                if not backup_path:
                    self.logger.warning(f"Failed to create backup for {file_path}")
                    return False
                
            # Write new content
            path.write_text(content)
            
            # Track change
            self.changes[file_path] = content
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to modify file {file_path}: {str(e)}")
            # Try to restore from backup
            if backup_path:
                self.restore_file(file_path, backup_path)
            return False
    
    def delete_file(self, file_path: str) -> bool:
        """
        Delete a file.
        
        Args:
            file_path: Path to the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.warning(f"File does not exist: {file_path}")
                return False
                
            # Create backup before deleting if backup directory exists
            backup_path = None
            if self.backup_dir:
                backup_path = self.backup_file(file_path)
                if not backup_path:
                    self.logger.warning(f"Failed to create backup for {file_path}")
                    return False
                
            # Delete file
            path.unlink()
            
            # Track change
            self.changes[file_path] = None
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete file {file_path}: {str(e)}")
            return False
    
    def read_file(self, file_path: str) -> Optional[str]:
        """
        Read the contents of a file.
        
        Args:
            file_path: Path to the file to read
            
        Returns:
            File contents as string, or None if file doesn't exist
        """
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.warning(f"File does not exist: {file_path}")
                return None
                
            return path.read_text()
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {str(e)}")
            return None
    
    def backup_file(self, file_path: str) -> Optional[str]:
        """
        Create a backup of a file.
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file, or None if backup failed
        """
        try:
            path = Path(file_path)
            if not path.exists():
                self.logger.warning(f"File does not exist: {file_path}")
                return None
                
            # Create backup filename with timestamp
            backup_name = f"{path.stem}_{os.urandom(4).hex()}{path.suffix}"
            backup_path = self.backup_dir / backup_name
            
            # Copy file to backup location
            shutil.copy2(path, backup_path)
            
            return str(backup_path)
        except Exception as e:
            self.logger.error(f"Failed to backup file {file_path}: {str(e)}")
            return None
    
    def restore_file(self, file_path: str, backup_path: str) -> bool:
        """
        Restore a file from a backup.
        
        Args:
            file_path: Path to restore the file to
            backup_path: Path to the backup file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backup = Path(backup_path)
            if not backup.exists():
                self.logger.warning(f"Backup file does not exist: {backup_path}")
                return False
                
            # Copy backup back to original location
            shutil.copy2(backup, file_path)
            
            # Remove the backup
            backup.unlink()
            
            return True
        except Exception as e:
            self.logger.error(f"Failed to restore file {file_path}: {str(e)}")
            return False
    
    def list_files(self, directory: Optional[str] = None) -> List[str]:
        """
        List all files in a directory.
        
        Args:
            directory: Optional directory to list files from
            
        Returns:
            List of file paths
        """
        try:
            base_dir = Path(directory) if directory else self.project_root
            if not base_dir.exists():
                self.logger.warning(f"Directory does not exist: {base_dir}")
                return []
                
            return [str(p) for p in base_dir.rglob('*') if p.is_file()]
        except Exception as e:
            self.logger.error(f"Failed to list files in {directory}: {str(e)}")
            return []
    
    def apply_changes(self, changes: Dict) -> bool:
        """Apply changes to files with backup support."""
        try:
            # Create backups first if backup directory exists
            if self.backup_dir:
                for file_path in changes["file_updates"].keys():
                    self._backup_file(file_path)

            # Apply changes
            for file_path, new_content in changes["file_updates"].items():
                # Create directory if it doesn't exist
                path = Path(file_path)
                path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write content to file
                path.write_text(new_content)
                
                # Track change
                self.changes[file_path] = new_content

            return True
        except Exception as e:
            if self.backup_dir:
                self._restore_backups()
            raise Exception(f"Failed to apply changes: {str(e)}")

    def _backup_file(self, file_path: str) -> None:
        """Create a backup of the file if it exists and backup directory is enabled."""
        if not self.backup_dir:
            return
            
        path = Path(file_path)
        if path.exists():
            backup_path = self.backup_dir / path.name
            shutil.copy2(path, backup_path)

    def _restore_backups(self) -> None:
        """Restore files from backups if something goes wrong."""
        if not self.backup_dir:
            return
            
        for backup_file in self.backup_dir.glob("*"):
            shutil.copy2(backup_file, backup_file.name)
            backup_file.unlink()

    def _write_file(self, file_path: str, content: str) -> None:
        """Write content to file, creating directories if needed."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    
    def write_file(self, file_path: str, content: str) -> None:
        """
        Write content to a file.
        
        Args:
            file_path: Path to the file to write
            content: Content to write to the file
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        self.changes[file_path] = content
    
    def copy_file(self, source: str, destination: str) -> None:
        """
        Copy a file from source to destination.
        
        Args:
            source: Path to the source file
            destination: Path to the destination file
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        
        shutil.copy2(source, destination)
        
        # Read the copied file's content
        with open(destination, 'r', encoding='utf-8') as f:
            self.changes[destination] = f.read()
    
    def get_changes(self) -> Dict[str, str]:
        """
        Get all pending changes.
        
        Returns:
            Dictionary mapping file paths to their new content
        """
        return self.changes
    
    def clear_changes(self) -> None:
        """Clear all pending changes."""
        self.changes.clear() 