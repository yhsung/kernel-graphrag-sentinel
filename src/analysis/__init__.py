"""
Analysis Module: Impact Analysis and Reporting
Provides impact analysis, call chain queries, and LLM-powered reporting.
"""

from .impact_analyzer import ImpactAnalyzer, ImpactResult
from . import queries

__all__ = ['ImpactAnalyzer', 'ImpactResult', 'queries']
