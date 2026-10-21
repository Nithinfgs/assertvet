"""Base analyzer contract for test integrity verification."""

from abc import ABC, abstractmethod
from typing import List

from assertvet.models import FileDiff, Violation


class BaseAnalyzer(ABC):
    """Abstract base class for language/format-specific diff analyzers."""

    @abstractmethod
    def can_handle(self, file_diff: FileDiff) -> bool:
        """Return True if this analyzer should process the given file diff."""
        pass

    @abstractmethod
    def analyze(self, file_diff: FileDiff) -> List[Violation]:
        """Inspect the file diff hunks and return any detected integrity violations."""
        pass
