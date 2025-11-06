"""
Progress Indicators Module

Provides progress indicators for long-running operations.
"""

from typing import Optional
import sys


class ProgressIndicator:
    """Simple progress indicator for operations."""
    
    def __init__(self, total: int, description: str = "Processing"):
        """
        Initialize progress indicator.
        
        Parameters
        ----------
        total : int
            Total number of items to process
        description : str, optional
            Description of the operation (default: "Processing")
        """
        self.total = total
        self.current = 0
        self.description = description
    
    def update(self, increment: int = 1):
        """
        Update progress.
        
        Parameters
        ----------
        increment : int, optional
            Number of items completed (default: 1)
        """
        self.current += increment
        percentage = (self.current / self.total) * 100 if self.total > 0 else 0
        print(f"\r{self.description}: {self.current}/{self.total} ({percentage:.1f}%)", end='', flush=True)
    
    def finish(self):
        """Finish progress indicator."""
        print(f"\r{self.description}: {self.current}/{self.total} (100.0%) - Complete!")
        sys.stdout.flush()


def print_progress(current: int, total: int, description: str = "Processing"):
    """
    Print simple progress message.
    
    Parameters
    ----------
    current : int
        Current item number
    total : int
        Total number of items
    description : str, optional
        Description of the operation (default: "Processing")
    """
    percentage = (current / total) * 100 if total > 0 else 0
    print(f"{description}: {current}/{total} ({percentage:.1f}%)")

