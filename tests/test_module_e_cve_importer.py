"""
Tests for Module E: CVE Importer
"""

import pytest
from pathlib import Path
import tempfile
import json

from src.module_e.schema import CVENode, VulnerabilityType, Severity
from src.module_e.cve_importer import CVEImporter


@pytest.fixture
def mock_graph_store():
    """Create a mock graph store."""
    class MockGraphStore:
        def __init__(self):
            self.data = {}

        def execute_query(self, query, params):
            # Mock query execution
            return []

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    return MockGraphStore()


@pytest.fixture
def sample_cve_data():
    """Sample CVE data for testing."""
    return {
        'id': 'CVE-2024-1234',
        'description': 'A buffer overflow vulnerability in ext4_writepages() function in fs/ext4/inode.c allows local users to cause a denial of service.',
        'affected_function': 'ext4_writepages',
        'file_path': 'fs/ext4/inode.c',
        'line_number': 2145,
        'vulnerability_type': 'buffer_overflow',
        'severity': 'CRITICAL',
        'cvss_score': 9.8,
        'cwe_id': 'CWE-787',
        'kernel_version_affected': '6.0-6.6',
        'fixed_commit': '7a8b9c1d2e3f',
        'discovered_date': '2024-03-15'
    }


class TestCVENode:
    """Tests for CVENode class."""

    def test_create_cve_node(self, sample_cve_data):
        """Test creating a CVE node."""
        cve = CVENode.from_dict(sample_cve_data)

        assert cve.id == 'CVE-2024-1234'
        assert cve.affected_function == 'ext4_writepages'
        assert cve.file_path == 'fs/ext4/inode.c'
        assert cve.vulnerability_type == 'buffer_overflow'
        assert cve.severity == 'CRITICAL'
        assert cve.cvss_score == 9.8

    def test_cve_node_to_dict(self, sample_cve_data):
        """Test converting CVE node to dictionary."""
        cve = CVENode.from_dict(sample_cve_data)
        data = cve.to_dict()

        assert data['id'] == 'CVE-2024-1234'
        assert data['affected_function'] == 'ext4_writepages'
        assert 'description' in data

    def test_cve_node_with_minimal_data(self):
        """Test creating CVE node with minimal required data."""
        cve = CVENode(
            id='CVE-2024-5678',
            description='Test vulnerability',
            affected_function='test_function'
        )

        assert cve.id == 'CVE-2024-5678'
        assert cve.affected_function == 'test_function'
        assert cve.severity == 'MEDIUM'  # default


class TestCVEImporter:
    """Tests for CVEImporter class."""

    def test_importer_initialization(self, mock_graph_store):
        """Test importer initialization."""
        importer = CVEImporter(mock_graph_store)

        assert importer.graph_store == mock_graph_store
        assert importer.llm_config is None

    def test_parse_description_regex(self, mock_graph_store):
        """Test parsing CVE description using regex."""
        importer = CVEImporter(mock_graph_store)

        description = "Buffer overflow in ext4_writepages() function in fs/ext4/inode.c"
        parsed = importer._parse_description_regex('CVE-2024-1234', description)

        assert parsed is not None
        assert parsed['affected_function'] == 'ext4_writepages'
        assert parsed['vulnerability_type'] == 'buffer_overflow'
        assert 'fs/ext4/inode.c' in parsed['file_path']

    def test_parse_description_with_null_deref(self, mock_graph_store):
        """Test parsing NULL pointer dereference vulnerability."""
        importer = CVEImporter(mock_graph_store)

        description = "NULL pointer dereference in tcp_v6_rcv() allows local users to crash the system"
        parsed = importer._parse_description_regex('CVE-2024-5678', description)

        assert parsed is not None
        assert parsed['affected_function'] == 'tcp_v6_rcv'
        assert parsed['vulnerability_type'] == 'null_dereference'

    def test_parse_description_with_race_condition(self, mock_graph_store):
        """Test parsing race condition vulnerability."""
        importer = CVEImporter(mock_graph_store)

        description = "Race condition in fcntl_setlk() allows local users to cause a denial of service"
        parsed = importer._parse_description_regex('CVE-2024-9999', description)

        assert parsed is not None
        assert parsed['affected_function'] == 'fcntl_setlk'
        assert parsed['vulnerability_type'] == 'race_condition'

    def test_cvss_to_severity_conversion(self, mock_graph_store):
        """Test CVSS score to severity conversion."""
        importer = CVEImporter(mock_graph_store)

        assert importer._cvss_to_severity(9.8) == 'CRITICAL'
        assert importer._cvss_to_severity(7.5) == 'HIGH'
        assert importer._cvss_to_severity(5.0) == 'MEDIUM'
        assert importer._cvss_to_severity(3.5) == 'LOW'

    def test_import_cve_from_text(self, mock_graph_store):
        """Test importing CVE from text description."""
        importer = CVEImporter(mock_graph_store)

        # Mock the _store_cve method to avoid actual database operations
        def mock_store(cve):
            pass

        importer._store_cve = mock_store

        cve = importer.import_cve_from_text(
            'CVE-2024-1234',
            'Buffer overflow in ext4_writepages() function',
            metadata={'severity': 'CRITICAL', 'cvss_score': 9.8}
        )

        assert cve is not None
        assert cve.id == 'CVE-2024-1234'
        assert cve.affected_function == 'ext4_writepages'
        assert cve.severity == 'CRITICAL'
        assert cve.cvss_score == 9.8


@pytest.fixture
def sample_nvd_json():
    """Create a sample NVD JSON file for testing."""
    data = {
        'CVE_Items': [
            {
                'cve': {
                    'CVE_data_meta': {'ID': 'CVE-2024-1234'},
                    'description': {
                        'description_data': [
                            {
                                'lang': 'en',
                                'value': 'Buffer overflow in ext4_writepages() in fs/ext4/inode.c'
                            }
                        ]
                    }
                },
                'impact': {
                    'metrics': [
                        {
                            'CVSS_V3': [
                                {
                                    'cvssV3': {
                                        'baseScore': 9.8
                                    }
                                }
                            ]
                        }
                    ]
                }
            }
        ]
    }

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink()


class TestCVEImporterNVD:
    """Tests for NVD JSON import."""

    def test_import_from_nvd_json(self, mock_graph_store, sample_nvd_json):
        """Test importing CVEs from NVD JSON file."""
        importer = CVEImporter(mock_graph_store)

        # Mock the _store_cve method
        stored_cves = []
        def mock_store(cve):
            stored_cves.append(cve)

        importer._store_cve = mock_store

        cves = importer.import_from_nvd_json(sample_nvd_json)

        assert len(cves) > 0
        assert cves[0].id == 'CVE-2024-1234'
        assert cves[0].cvss_score == 9.8


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
