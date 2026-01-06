"""
Module G: Git History Integration

This module provides functionality to:
- Extract git repository metadata (commits, branches, tags, authors)
- Map git blame information to functions and lines
- Analyze commit changes and their impact
- Track function evolution across commits
- Generate visual timelines of code changes
- Calculate code ownership metrics
- Assist with git bisect workflows

Core Components:
- GitExtractor: Extract git metadata using git commands
- BlameMapper: Map lines to their modifying commits
- CommitAnalyzer: Analyze what changed in commits
- EvolutionTracker: Track function history
- TimelineGenerator: Generate visual timelines
- AuthorAnalytics: Calculate ownership metrics
- BisectHelper: Accelerate git bisect workflows
"""

from .schema import (
    GitCommitNode,
    GitBranchNode,
    GitTagNode,
    GitAuthorNode,
    FileChange,
    FunctionChange,
    BlameInfo,
    FunctionBlameInfo,
    FunctionVersion,
    NodeType,
    ChangeType,
    RelationshipType,
)

__version__ = "0.1.0"

__all__ = [
    "GitCommitNode",
    "GitBranchNode",
    "GitTagNode",
    "GitAuthorNode",
    "FileChange",
    "FunctionChange",
    "BlameInfo",
    "FunctionBlameInfo",
    "FunctionVersion",
    "NodeType",
    "ChangeType",
    "RelationshipType",
]
