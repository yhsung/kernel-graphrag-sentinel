"""
Schema definitions for Module G: Git History Integration

This module defines the data structures and graph schemas for git repository
metadata, including commits, branches, tags, and authors.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime


class NodeType(Enum):
    """Node types for git-related graph entities."""
    GIT_COMMIT = "GitCommit"
    GIT_BRANCH = "GitBranch"
    GIT_TAG = "GitTag"
    GIT_AUTHOR = "GitAuthor"


class ChangeType(Enum):
    """Types of file/function changes in commits."""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"
    COPIED = "copied"


@dataclass
class GitCommitNode:
    """
    Represents a git commit in the graph database.

    Attributes:
        id: Full commit hash (SHA-256)
        hash_short: Short commit hash (first 8 characters)
        title: Commit title (first line of message)
        message: Full commit message
        author_name: Author name
        author_email: Author email
        author_date: Author date (ISO format)
        committer_name: Committer name
        committer_email: Committer email
        committer_date: Committer date (ISO format)
        branch: Branch name (default: "master")
        files_changed: Number of files changed
        insertions: Number of lines inserted
        deletions: Number of lines deleted
        is_merge: True if this is a merge commit
        signed_off: True if Signed-off-by line present
    """
    id: str
    hash_short: str
    title: str
    message: str
    author_name: str
    author_email: str
    author_date: str
    committer_name: str
    committer_email: str
    committer_date: str
    branch: str = "master"
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    is_merge: bool = False
    signed_off: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/Neo4j serialization."""
        return {
            'id': self.id,
            'hash_short': self.hash_short,
            'title': self.title,
            'message': self.message,
            'author_name': self.author_name,
            'author_email': self.author_email,
            'author_date': self.author_date,
            'committer_name': self.committer_name,
            'committer_email': self.committer_email,
            'committer_date': self.committer_date,
            'branch': self.branch,
            'files_changed': self.files_changed,
            'insertions': self.insertions,
            'deletions': self.deletions,
            'is_merge': self.is_merge,
            'signed_off': self.signed_off,
        }

    def to_neo4j_properties(self) -> Dict[str, Any]:
        """Convert to Neo4j node properties."""
        return {
            'hash': self.id,
            'hash_short': self.hash_short,
            'title': self.title,
            'message': self.message,
            'author_name': self.author_name,
            'author_email': self.author_email,
            'author_date': datetime.fromisoformat(self.author_date),
            'committer_name': self.committer_name,
            'committer_email': self.committer_email,
            'committer_date': datetime.fromisoformat(self.committer_date),
            'branch': self.branch,
            'files_changed': self.files_changed,
            'insertions': self.insertions,
            'deletions': self.deletions,
            'is_merge': self.is_merge,
            'signed_off': self.signed_off,
        }


@dataclass
class GitBranchNode:
    """
    Represents a git branch in the graph database.

    Attributes:
        id: Branch name (unique identifier)
        name: Branch display name
        is_head: True if this is the current HEAD branch
        commit_count: Number of commits in this branch
        last_commit_hash: Hash of the most recent commit
    """
    id: str
    name: str
    is_head: bool = False
    commit_count: int = 0
    last_commit_hash: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'is_head': self.is_head,
            'commit_count': self.commit_count,
            'last_commit_hash': self.last_commit_hash,
        }


@dataclass
class GitTagNode:
    """
    Represents a git tag in the graph database.

    Attributes:
        id: Tag name (unique identifier)
        name: Tag display name
        commit_hash: Hash of the commit this tag points to
        tag_date: Date the tag was created
        is_release: True if this is a release tag (e.g., v6.6)
        message: Tag message (for annotated tags)
    """
    id: str
    name: str
    commit_hash: str
    tag_date: str
    is_release: bool = False
    message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'commit_hash': self.commit_hash,
            'tag_date': self.tag_date,
            'is_release': self.is_release,
            'message': self.message,
        }


@dataclass
class GitAuthorNode:
    """
    Represents a git author (aggregated across all commits).

    Attributes:
        id: Author email (unique identifier)
        name: Author name
        email: Author email
        commits_count: Total number of commits by this author
        lines_added: Total lines added
        lines_removed: Total lines removed
        first_commit: Date of first commit
        last_commit: Date of most recent commit
        main_subsystems: List of subsystems this author contributes to
    """
    id: str
    name: str
    email: str
    commits_count: int = 0
    lines_added: int = 0
    lines_removed: int = 0
    first_commit: Optional[str] = None
    last_commit: Optional[str] = None
    main_subsystems: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'commits_count': self.commits_count,
            'lines_added': self.lines_added,
            'lines_removed': self.lines_removed,
            'first_commit': self.first_commit,
            'last_commit': self.last_commit,
            'main_subsystems': self.main_subsystems,
        }


@dataclass
class FileChange:
    """
    Represents a file change in a commit.

    Attributes:
        file_path: Path to the file
        change_type: Type of change (added, modified, deleted, etc.)
        lines_added: Number of lines added
        lines_removed: Number of lines removed
    """
    file_path: str
    change_type: ChangeType
    lines_added: int = 0
    lines_removed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'file_path': self.file_path,
            'change_type': self.change_type.value,
            'lines_added': self.lines_added,
            'lines_removed': self.lines_removed,
        }


@dataclass
class FunctionChange:
    """
    Represents a function change in a commit.

    Attributes:
        function_name: Name of the function
        file_path: Path to the file containing the function
        action: Action performed (created, modified, deleted)
        lines_added: Number of lines added
        lines_removed: Number of lines removed
    """
    function_name: str
    file_path: str
    action: str  # created, modified, deleted, renamed
    lines_added: int = 0
    lines_removed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'function_name': self.function_name,
            'file_path': self.file_path,
            'action': self.action,
            'lines_added': self.lines_added,
            'lines_removed': self.lines_removed,
        }


@dataclass
class BlameInfo:
    """
    Represents git blame information for a code segment.

    Attributes:
        commit_hash: Hash of the commit that last modified this line
        author: Author who made the change
        date: Date of the commit
        line_number: Line number in the file
        line_content: Content of the line
    """
    commit_hash: str
    author: str
    date: str
    line_number: int
    line_content: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'commit_hash': self.commit_hash,
            'author': self.author,
            'date': self.date,
            'line_number': self.line_number,
            'line_content': self.line_content,
        }


@dataclass
class FunctionBlameInfo:
    """
    Aggregated blame information for a function.

    Attributes:
        function_name: Name of the function
        file_path: Path to the file
        line_start: Function start line
        line_end: Function end line
        last_modified_commit: Hash of most recent modifying commit
        author: Author of last modification
        date: Date of last modification
        line_count: Total lines in function
        commits_touching: List of commits that modified this function
    """
    function_name: str
    file_path: str
    line_start: int
    line_end: int
    last_modified_commit: str
    author: str
    date: str
    line_count: int
    commits_touching: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'function_name': self.function_name,
            'file_path': self.file_path,
            'line_start': self.line_start,
            'line_end': self.line_end,
            'last_modified_commit': self.last_modified_commit,
            'author': self.author,
            'date': self.date,
            'line_count': self.line_count,
            'commits_touching': self.commits_touching,
        }


@dataclass
class FunctionVersion:
    """
    Represents a function version at a specific commit.

    Attributes:
        commit_hash: Hash of the commit
        commit_date: Date of the commit
        author: Author of the commit
        message: Commit message
        lines_added: Number of lines added in this version
        lines_removed: Number of lines removed in this version
        complexity: Cyclomatic complexity
        line_count: Total line count
        test_count: Number of tests covering this function
    """
    commit_hash: str
    commit_date: str
    author: str
    message: str
    lines_added: int
    lines_removed: int
    complexity: int
    line_count: int
    test_count: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'commit_hash': self.commit_hash,
            'commit_date': self.commit_date,
            'author': self.author,
            'message': self.message,
            'lines_added': self.lines_added,
            'lines_removed': self.lines_removed,
            'complexity': self.complexity,
            'line_count': self.line_count,
            'test_count': self.test_count,
        }


# Neo4j relationship types
class RelationshipType(Enum):
    """Relationship types for git-related graph connections."""
    # Commit relationships
    MODIFIES_FILE = "MODIFIES_FILE"
    DEFINES_FUNCTION = "DEFINES_FUNCTION"
    FIXES_CVE = "FIXES_CVE"
    PARENT_OF = "PARENT_OF"

    # Branch relationships
    CONTAINS_COMMIT = "CONTAINS_COMMIT"

    # Tag relationships
    POINTS_TO_COMMIT = "POINTS_TO_COMMIT"

    # Author relationships
    AUTHORED_COMMIT = "AUTHORED_COMMIT"

    # Evolution tracking
    EVOLVED_INTO = "EVOLVED_INTO"
    CONTAINS_VERSION = "CONTAINS_VERSION"

    # Blame information
    HAS_LINE_COMMIT = "HAS_LINE_COMMIT"
