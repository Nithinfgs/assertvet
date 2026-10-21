"""Analyzer registry for AssertVet."""

from typing import List

from assertvet.analyzers.base import BaseAnalyzer
from assertvet.analyzers.config_analyzer import ConfigAnalyzer
from assertvet.analyzers.javascript_analyzer import JavaScriptAnalyzer
from assertvet.analyzers.python_analyzer import PythonAnalyzer


def get_default_analyzers() -> List[BaseAnalyzer]:
    """Return an instantiated list of all standard analyzers."""
    return [
        PythonAnalyzer(),
        JavaScriptAnalyzer(),
        ConfigAnalyzer(),
    ]
