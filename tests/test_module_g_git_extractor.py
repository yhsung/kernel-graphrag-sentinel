"""Unit tests for Module G: Git Extractor (git_extractor.py)."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from datetime import datetime

from src.module_g.git_extractor import GitExtractor
from src.module_g.schema import (
    GitCommitNode,
    GitBranchNode,
    GitTagNode,
    GitAuthorNode,
    FileChange,
    ChangeType,
)


class TestGitExtractor:
    """Test cases for GitExtractor class."""

    @pytest.fixture
    def repo_path(self, tmp_path):
        """Create a temporary git repository for testing."""
        import subprocess

        # Initialize a git repo
        subprocess.run(['git', 'init'], cwd=tmp_path, check=True,
                      capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'],
                      cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'],
                      cwd=tmp_path, check=True, capture_output=True)

        # Create a test file and commit
        test_file = tmp_path / 'test.c'
        test_file.write_text('int main() { return 0; }')
        subprocess.run(['git', 'add', 'test.c'], cwd=tmp_path, check=True,
                      capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Initial commit'],
                      cwd=tmp_path, check=True, capture_output=True)

        return str(tmp_path)

    @pytest.fixture
    def extractor(self, repo_path):
        """Create a GitExtractor instance for testing."""
        return GitExtractor(repo_path)

    def test_extractor_initialization(self, extractor):
        """Test that GitExtractor initializes correctly."""
        assert extractor.repo_path.exists()
        assert (extractor.repo_path / '.git').exists()

    def test_extractor_invalid_path(self):
        """Test initialization with invalid path."""
        with pytest.raises(ValueError):
            GitExtractor('/nonexistent/path')

    def test_extractor_not_git_repo(self, tmp_path):
        """Test initialization with non-git directory."""
        with pytest.raises(ValueError):
            GitExtractor(str(tmp_path))

    def test_extract_commits(self, extractor):
        """Test extracting commits from repository."""
        commits = extractor.extract_commits(limit=10)

        assert len(commits) > 0
        assert isinstance(commits[0], GitCommitNode)
        assert commits[0].id
        assert commits[0].author_name
        assert commits[0].author_email
        assert commits[0].title

    def test_extract_commits_with_date_filter(self, extractor):
        """Test extracting commits with date filter."""
        commits = extractor.extract_commits(
            since='2020-01-01',
            until='2030-01-01'
        )

        # Should return commits (or empty list if repo has no commits in range)
        assert isinstance(commits, list)

    def test_extract_commits_with_limit(self, extractor):
        """Test extracting commits with limit."""
        commits = extractor.extract_commits(limit=1)

        assert len(commits) <= 1

    def test_extract_commit_properties(self, extractor):
        """Test that extracted commits have all required properties."""
        commits = extractor.extract_commits(limit=1)

        if commits:
            commit = commits[0]
            assert hasattr(commit, 'id')
            assert hasattr(commit, 'hash_short')
            assert hasattr(commit, 'title')
            assert hasattr(commit, 'message')
            assert hasattr(commit, 'author_name')
            assert hasattr(commit, 'author_email')
            assert hasattr(commit, 'author_date')
            assert hasattr(commit, 'committer_name')
            assert hasattr(commit, 'committer_email')
            assert hasattr(commit, 'committer_date')
            assert hasattr(commit, 'files_changed')
            assert hasattr(commit, 'insertions')
            assert hasattr(commit, 'deletions')
            assert hasattr(commit, 'is_merge')
            assert hasattr(commit, 'signed_off')

    def test_extract_commit_files(self, extractor):
        """Test extracting files changed in a commit."""
        commits = extractor.extract_commits(limit=1)

        if commits:
            commit_hash = commits[0].id
            files = extractor.extract_commit_files(commit_hash)

            assert isinstance(files, list)
            # At least one file should be changed (test.c)
            assert len(files) > 0
            assert isinstance(files[0], FileChange)

    def test_extract_branches(self, extractor):
        """Test extracting branches."""
        branches = extractor.extract_branches()

        assert len(branches) > 0
        assert isinstance(branches[0], GitBranchNode)
        assert branches[0].name
        # One branch should be marked as HEAD
        assert any(b.is_head for b in branches)

    def test_extract_branches_properties(self, extractor):
        """Test that extracted branches have all required properties."""
        branches = extractor.extract_branches()

        if branches:
            branch = branches[0]
            assert hasattr(branch, 'id')
            assert hasattr(branch, 'name')
            assert hasattr(branch, 'is_head')
            assert hasattr(branch, 'commit_count')
            assert hasattr(branch, 'last_commit_hash')

    def test_extract_tags(self, extractor):
        """Test extracting tags."""
        # Create a tag
        import subprocess
        subprocess.run(['git', 'tag', 'v1.0.0'],
                      cwd=extractor.repo_path, check=True, capture_output=True)

        tags = extractor.extract_tags()

        assert len(tags) > 0
        assert isinstance(tags[0], GitTagNode)
        assert tags[0].name == 'v1.0.0'
        assert tags[0].is_release is True

    def test_extract_tags_properties(self, extractor):
        """Test that extracted tags have all required properties."""
        # Create a tag
        import subprocess
        subprocess.run(['git', 'tag', 'v1.0.0'],
                      cwd=extractor.repo_path, check=True, capture_output=True)

        tags = extractor.extract_tags()

        if tags:
            tag = tags[0]
            assert hasattr(tag, 'id')
            assert hasattr(tag, 'name')
            assert hasattr(tag, 'commit_hash')
            assert hasattr(tag, 'tag_date')
            assert hasattr(tag, 'is_release')
            assert hasattr(tag, 'message')

    def test_extract_authors(self, extractor):
        """Test extracting authors."""
        authors = extractor.extract_authors()

        assert len(authors) > 0
        assert isinstance(authors[0], GitAuthorNode)
        assert authors[0].name == 'Test User'
        assert authors[0].email == 'test@example.com'
        assert authors[0].commits_count > 0

    def test_extract_authors_properties(self, extractor):
        """Test that extracted authors have all required properties."""
        authors = extractor.extract_authors()

        if authors:
            author = authors[0]
            assert hasattr(author, 'id')
            assert hasattr(author, 'name')
            assert hasattr(author, 'email')
            assert hasattr(author, 'commits_count')
            assert hasattr(author, 'lines_added')
            assert hasattr(author, 'lines_removed')
            assert hasattr(author, 'first_commit')
            assert hasattr(author, 'last_commit')
            assert hasattr(author, 'main_subsystems')

    def test_get_file_blame(self, extractor):
        """Test getting git blame information."""
        blame_info = extractor.get_file_blame('test.c', 1, 1)

        assert len(blame_info) > 0
        assert 'commit_hash' in blame_info[0]
        assert 'author' in blame_info[0]
        assert 'date' in blame_info[0]
        assert 'line_content' in blame_info[0]


class TestGitCommitNode:
    """Test cases for GitCommitNode dataclass."""

    def test_create_commit_node(self):
        """Test creating a GitCommitNode."""
        commit = GitCommitNode(
            id='a' * 40,
            hash_short='a' * 8,
            title='Test commit',
            message='Test commit message',
            author_name='Test User',
            author_email='test@example.com',
            author_date='2024-01-01 12:00:00 +0000',
            committer_name='Test User',
            committer_email='test@example.com',
            committer_date='2024-01-01 12:00:00 +0000',
        )

        assert commit.id == 'a' * 40
        assert commit.hash_short == 'a' * 8
        assert commit.title == 'Test commit'
        assert commit.author_name == 'Test User'

    def test_commit_to_dict(self):
        """Test converting commit to dictionary."""
        commit = GitCommitNode(
            id='a' * 40,
            hash_short='a' * 8,
            title='Test',
            message='Test message',
            author_name='Test',
            author_email='test@example.com',
            author_date='2024-01-01',
            committer_name='Test',
            committer_email='test@example.com',
            committer_date='2024-01-01',
        )

        commit_dict = commit.to_dict()

        assert commit_dict['id'] == 'a' * 40
        assert commit_dict['hash_short'] == 'a' * 8
        assert commit_dict['title'] == 'Test'


class TestChangeType:
    """Test cases for ChangeType enum."""

    def test_change_type_values(self):
        """Test that change type values are correct."""
        assert ChangeType.ADDED.value == 'added'
        assert ChangeType.MODIFIED.value == 'modified'
        assert ChangeType.DELETED.value == 'deleted'
        assert ChangeType.RENAMED.value == 'renamed'
        assert ChangeType.COPIED.value == 'copied'


class TestFileChange:
    """Test cases for FileChange dataclass."""

    def test_create_file_change(self):
        """Test creating a FileChange."""
        change = FileChange(
            file_path='fs/ext4/inode.c',
            change_type=ChangeType.MODIFIED,
            lines_added=10,
            lines_removed=5,
        )

        assert change.file_path == 'fs/ext4/inode.c'
        assert change.change_type == ChangeType.MODIFIED
        assert change.lines_added == 10
        assert change.lines_removed == 5

    def test_file_change_to_dict(self):
        """Test converting file change to dictionary."""
        change = FileChange(
            file_path='test.c',
            change_type=ChangeType.ADDED,
            lines_added=100,
            lines_removed=0,
        )

        change_dict = change.to_dict()

        assert change_dict['file_path'] == 'test.c'
        assert change_dict['change_type'] == 'added'
        assert change_dict['lines_added'] == 100
        assert change_dict['lines_removed'] == 0
