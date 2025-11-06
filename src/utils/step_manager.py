"""
Step Manager Module

Manages step execution with resume and skip functionality.
"""

from pathlib import Path
from typing import Set, Optional
import json


class StepManager:
    """Manages step execution with resume and skip functionality."""
    
    def __init__(self, progress_file: Path, skip_steps: Set[int] = None, resume: bool = False):
        """
        Initialize step manager.
        
        Parameters
        ----------
        progress_file : Path
            Path to progress state file
        skip_steps : Set[int], optional
            Set of step numbers to skip (default: None)
        resume : bool, optional
            Enable resume mode (default: False)
        """
        self.progress_file = progress_file
        self.skip_steps = skip_steps or set()
        self.resume = resume
        self.completed_steps = self._load_progress()
    
    def _load_progress(self) -> Set[int]:
        """Load completed steps from progress file."""
        if self.resume and self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    progress_data = json.load(f)
                    return set(progress_data.get("completed_steps", []))
            except Exception:
                return set()
        return set()
    
    def should_skip(self, step_num: int) -> bool:
        """
        Check if a step should be skipped.
        
        Parameters
        ----------
        step_num : int
            Step number to check
        
        Returns
        -------
        bool
            True if step should be skipped, False otherwise
        """
        if step_num in self.skip_steps:
            return True
        if self.resume and step_num in self.completed_steps:
            return True
        return False
    
    def mark_completed(self, step_num: int):
        """
        Mark a step as completed.
        
        Parameters
        ----------
        step_num : int
            Step number to mark as completed
        """
        self.completed_steps.add(step_num)
        self._save_progress()
    
    def _save_progress(self):
        """Save progress state to file."""
        try:
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.progress_file, 'w') as f:
                json.dump({"completed_steps": sorted(self.completed_steps)}, f)
        except Exception:
            pass  # Don't fail if we can't save progress
    
    def get_skip_reason(self, step_num: int) -> str:
        """
        Get reason why a step is being skipped.
        
        Parameters
        ----------
        step_num : int
            Step number
        
        Returns
        -------
        str
            Reason for skipping
        """
        if step_num in self.skip_steps:
            return "user requested"
        if self.resume and step_num in self.completed_steps:
            return "already completed"
        return "unknown"

