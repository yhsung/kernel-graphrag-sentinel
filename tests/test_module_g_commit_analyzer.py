"""Unit tests for Module G: Commit Analyzer (commit_analyzer.py)."""

import pytest
from unittest.mock import MagicMock, Mock

from src.module_g.commit_analyzer import CommitAnalyzer
from src.module_g.git_extractor import GitExtractor


class TestCommitAnalyzer:
    """Test cases for CommitAnalyzer class."""

    @pytest.fixture
    def mock_store(self):
        """Create a mock graph store."""
        store = MagicMock()
        store.execute_query.return_value = []
        return store

    @pytest.fixture
    def mock_extractor(self):
        """Create a mock git extractor."""
        extractor = MagicMock(spec=GitExtractor)

        # Mock extract_commits
        mock_commit = MagicMock()
        mock_commit.id = 'a' * 40
        mock_commit.hash_short = 'a' * 8
        mock_commit.title = 'Test commit'
        mock_commit.message = 'Test commit message'
        mock_commit.author_name = 'Test User'
        mock_commit.author_email = 'test@example.com'
        mock_commit.author_date = '2024-01-01'
        mock_commit.committer_name = 'Test User'
        mock_commit.committer_email = 'test@example.com'
        mock_commit.committer_date = '2024-01-01'
        mock_commit.branch = 'master'
        mock_commit.files_changed = 1
        mock_commit.insertions = 10
        mock_commit.deletions = 0
        mock_commit.is_merge = False
        mock_commit.signed_off = False

        extractor.extract_commits.return_value = [mock_commit]

        # Mock extract_commit_files
        mock_file_change = MagicMock()
        mock_file_change.file_path = 'test.c'
        mock_file_change.change_type.value = 'modified'
        mock_file_change.to_dict.return_value = {
            'file_path': 'test.c',
            'change_type': 'modified',
            'lines_added': 0,
            'lines_removed': 0,
        }

        extractor.extract_commit_files.return_value = [mock_file_change]
        extractor.repo_path = '/tmp/test'

        return extractor

    @pytest.fixture
    def analyzer(self, mock_store, mock_extractor):
        """Create a CommitAnalyzer instance for testing."""
        return CommitAnalyzer(mock_store, mock_extractor)

    def test_analyzer_initialization(self, analyzer):
        """Test that CommitAnalyzer initializes correctly."""
        assert analyzer.store is not None
        assert analyzer.extractor is not None

    def test_analyze_commit(self, analyzer):
        """Test analyzing a commit."""
        analysis = analyzer.analyze_commit('a' * 8)

        assert 'commit_info' in analysis
        assert 'files_changed' in analysis
        assert 'functions_modified' in analysis
        assert 'risk_summary' in analysis

        commit_info = analysis['commit_info']
        assert commit_info['hash'] == 'a' * 8
        assert commit_info['title'] == 'Test commit'
        assert commit_info['author'] == 'Test User'

    def test_analyze_commit_structure(self, analyzer):
        """Test that analysis has correct structure."""
        analysis = analyzer.analyze_commit('test')

        # Check commit_info structure
        commit_info = analysis['commit_info']
        expected_keys = ['hash', 'title', 'message', 'author', 'date', 'branch',
                        'files_changed', 'insertions', 'deletions']
        for key in expected_keys:
            assert key in commit_info

        # Check files_changed structure
        files_changed = analysis['files_changed']
        assert isinstance(files_changed, list)

        # Check functions_modified structure
        functions_modified = analysis['functions_modified']
        assert isinstance(functions_modified, list)

        # Check risk_summary structure
        risk_summary = analysis['risk_summary']
        expected_risk_keys = ['high_risk_count', 'medium_risk_count', 'low_risk_count', 'recommendations']
        for key in expected_risk_keys:
            assert key in risk_summary

    def test_calculate_risk_summary(self, analyzer):
        """Test risk summary calculation."""
        functions_modified = [
            {
                'function_name': 'high_risk_func',
                'impact': {'callers': 15, 'callees': 5, 'syscall_paths': []},
                'test_coverage': {'total_tests': 0, 'unique_tests': 0},
            },
            {
                'function_name': 'medium_risk_func',
                'impact': {'callers': 7, 'callees': 3, 'syscall_paths': []},
                'test_coverage': {'total_tests': 1, 'unique_tests': 1},
            },
            {
                'function_name': 'low_risk_func',
                'impact': {'callers': 2, 'callees': 1, 'syscall_paths': []},
                'test_coverage': {'total_tests': 5, 'unique_tests': 2},
            },
        ]

        risk_summary = analyzer._calculate_risk_summary(functions_modified)

        assert risk_summary['high_risk_count'] == 1
        assert risk_summary['medium_risk_count'] == 1
        assert risk_summary['low_risk_count'] == 1
        assert len(risk_summary['recommendations']) == 3

    def test_is_valid_function_name(self, analyzer):
        """Test function name validation."""
        # Valid names
        assert analyzer._is_valid_function_name('main')
        assert analyzer._is_valid_function_name('test_function')
        assert analyzer._is_valid_function_name('ext4_writepages')

        # Invalid names
        assert not analyzer._is_valid_function_name('if')
        assert not analyzer._is_valid_function_name('for')
        assert not analyzer._is_valid_function_name('return')
        assert not analyzer._is_valid_function_name('123func')
        assert not analyzer._is_valid_function_name('')

    def test_parse_commit_diff(self, analyzer):
        """Test parsing commit diff."""
        file_changes = [
            MagicMock(file_path='test.c', change_type=MagicMock(value='modified'))
        ]

        # Mock _get_file_diff
        analyzer._get_file_diff = MagicMock(return_value='''
@@ -1,3 +1,3 @@
 int main() {
-    printf("Hello\\n");
+    printf("Hello, World!\\n");
     return 0;
 }
''')

        functions = analyzer._parse_commit_diff('test', file_changes)

        assert isinstance(functions, list)

    def test_get_function_impact_with_store_results(self, analyzer):
        """Test getting function impact from graph store."""
        # Mock graph store response
        analyzer.store.execute_query.return_value = [{
            'function': 'test_func',
            'callers': 10,
            'callees': 5,
            'syscalls': ['sys_write'],
        }]

        impact = analyzer._get_function_impact('test_func')

        assert impact['callers'] == 10
        assert impact['callees'] == 5
        assert impact['syscall_paths'] == ['sys_write']

    def test_get_function_test_coverage_with_store_results(self, analyzer):
        """Test getting function test coverage from graph store."""
        # Mock graph store response
        analyzer.store.execute_query.return_value = [{
            'function': 'test_func',
            'test_count': 5,
            'unique_tests': 3,
        }]

        coverage = analyzer._get_function_test_coverage('test_func')

        assert coverage['total_tests'] == 5
        assert coverage['unique_tests'] == 3

    def test_risk_level_assignment(self, analyzer):
        """Test risk level assignment for functions."""
        functions = [
            {
                'function_name': 'high',
                'impact': {'callers': 15},
                'test_coverage': {'total_tests': 0},
            },
            {
                'function_name': 'medium',
                'impact': {'callers': 6},
                'test_coverage': {'total_tests': 1},
            },
            {
                'function_name': 'low',
                'impact': {'callers': 2},
                'test_coverage': {'total_tests': 5},
            },
        ]

        risk_summary = analyzer._calculate_risk_summary(functions)

        # Check that risk levels were assigned
        assert functions[0]['risk_level'] == 'HIGH'
        assert functions[1]['risk_level'] == 'MEDIUM'
        assert functions[2]['risk_level'] == 'LOW'
