"""Unit tests for Module G: Blame Mapper (blame_mapper.py)."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.module_g.blame_mapper import BlameMapper
from src.module_g.schema import FunctionBlameInfo, BlameInfo


class TestBlameMapper:
    """Test cases for BlameMapper class."""

    @pytest.fixture
    def repo_path(self, tmp_path):
        """Create a temporary git repository for testing."""
        import subprocess

        subprocess.run(['git', 'init'], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.email', 'test@example.com'],
                      cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(['git', 'config', 'user.name', 'Test User'],
                      cwd=tmp_path, check=True, capture_output=True)

        # Create a test file with multiple lines
        test_file = tmp_path / 'test.c'
        test_file.write_text('''
int main() {
    printf("Hello\\n");
    return 0;
}
''')

        subprocess.run(['git', 'add', 'test.c'], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Add test function'],
                      cwd=tmp_path, check=True, capture_output=True)

        return str(tmp_path)

    @pytest.fixture
    def mapper(self, repo_path):
        """Create a BlameMapper instance for testing."""
        return BlameMapper(repo_path)

    def test_blame_mapper_initialization(self, mapper):
        """Test that BlameMapper initializes correctly."""
        assert mapper.extractor is not None
        assert mapper.repo_path.exists()

    def test_blame_function(self, mapper):
        """Test blaming a function."""
        blame_info = mapper.blame_function(
            file_path='test.c',
            line_start=2,
            line_end=4,
            function_name='main'
        )

        assert isinstance(blame_info, FunctionBlameInfo)
        assert blame_info.function_name == 'main'
        assert blame_info.file_path == 'test.c'
        assert blame_info.line_start == 2
        assert blame_info.line_end == 4
        assert blame_info.last_modified_commit
        assert blame_info.author
        assert blame_info.line_count == 3

    def test_blame_function_multiple_commits(self, repo_path):
        """Test blaming a function modified by multiple commits."""
        import subprocess

        # Modify the file and create another commit
        test_file = Path(repo_path) / 'test.c'
        test_file.write_text('''
int main() {
    printf("Hello, World!\\n");
    return 0;
}
''')

        subprocess.run(['git', 'add', 'test.c'], cwd=repo_path, check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'Modify function'],
                      cwd=repo_path, check=True, capture_output=True)

        mapper = BlameMapper(repo_path)
        blame_info = mapper.blame_function(
            file_path='test.c',
            line_start=2,
            line_end=4,
            function_name='main'
        )

        # Should track commits touching the function
        assert len(blame_info.commits_touching) >= 1

    def test_blame_file_range(self, mapper):
        """Test blaming a file range."""
        blame_info = mapper.blame_file_range(
            file_path='test.c',
            line_start=2,
            line_end=3
        )

        assert len(blame_info) == 2
        assert all(isinstance(b, BlameInfo) for b in blame_info)
        assert blame_info[0].line_number == 2
        assert blame_info[1].line_number == 3

    def test_get_commit_for_line(self, mapper):
        """Test getting commit for a specific line."""
        commit_info = mapper.get_commit_for_line('test.c', 2)

        assert commit_info is not None
        assert 'commit_hash' in commit_info
        assert 'author' in commit_info
        assert 'date' in commit_info


class TestBlameInfo:
    """Test cases for BlameInfo dataclass."""

    def test_create_blame_info(self):
        """Test creating a BlameInfo."""
        blame = BlameInfo(
            commit_hash='a1b2c3d4',
            author='Test User',
            date='2024-01-01',
            line_number=10,
            line_content='printf("Hello");'
        )

        assert blame.commit_hash == 'a1b2c3d4'
        assert blame.author == 'Test User'
        assert blame.line_number == 10
        assert blame.line_content == 'printf("Hello");'

    def test_blame_info_to_dict(self):
        """Test converting blame info to dictionary."""
        blame = BlameInfo(
            commit_hash='a1b2c3d4',
            author='Test',
            date='2024-01-01',
            line_number=10,
            line_content='test'
        )

        blame_dict = blame.to_dict()

        assert blame_dict['commit_hash'] == 'a1b2c3d4'
        assert blame_dict['author'] == 'Test'
        assert blame_dict['line_number'] == 10


class TestFunctionBlameInfo:
    """Test cases for FunctionBlameInfo dataclass."""

    def test_create_function_blame_info(self):
        """Test creating a FunctionBlameInfo."""
        blame = FunctionBlameInfo(
            function_name='test_func',
            file_path='test.c',
            line_start=10,
            line_end=20,
            last_modified_commit='a1b2c3d4',
            author='Test User',
            date='2024-01-01',
            line_count=10,
            commits_touching=[
                {'hash': 'a1b2c3d4', 'author': 'Test', 'lines': 8},
                {'hash': 'e5f6g7h8', 'author': 'Other', 'lines': 2},
            ]
        )

        assert blame.function_name == 'test_func'
        assert blame.file_path == 'test.c'
        assert blame.line_start == 10
        assert blame.line_end == 20
        assert blame.line_count == 10
        assert len(blame.commits_touching) == 2

    def test_function_blame_info_to_dict(self):
        """Test converting function blame info to dictionary."""
        blame = FunctionBlameInfo(
            function_name='test_func',
            file_path='test.c',
            line_start=1,
            line_end=10,
            last_modified_commit='abc123',
            author='Test',
            date='2024-01-01',
            line_count=10
        )

        blame_dict = blame.to_dict()

        assert blame_dict['function_name'] == 'test_func'
        assert blame_dict['file_path'] == 'test.c'
        assert blame_dict['line_start'] == 1
        assert blame_dict['line_end'] == 10
