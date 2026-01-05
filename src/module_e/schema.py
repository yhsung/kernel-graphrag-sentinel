"""
Module E: CVE Schema Definitions
Defines the Neo4j graph schema for CVE impact analysis.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class VulnerabilityType(Enum):
    """Types of vulnerabilities."""
    BUFFER_OVERFLOW = "buffer_overflow"
    NULL_DEREFERENCE = "null_dereference"
    USE_AFTER_FREE = "use_after_free"
    RACE_CONDITION = "race_condition"
    INTEGER_OVERFLOW = "integer_overflow"
    MEMORY_LEAK = "memory_leak"
    DOUBLE_FREE = "double_free"
    CODE_INJECTION = "code_injection"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DENIAL_OF_SERVICE = "denial_of_service"
    INFORMATION_LEAK = "information_leak"
    OTHER = "other"


class Severity(Enum):
    """CVSS severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class CVENode:
    """
    Represents a CVE vulnerability in the graph.

    Attributes:
        id: CVE identifier (e.g., "CVE-2024-1234")
        description: Full CVE description
        affected_function: Name of the vulnerable function
        file_path: Path to the file containing the function
        line_number: Line number where vulnerability occurs
        vulnerability_type: Type of vulnerability
        severity: Severity level
        cvss_score: CVSS score (0-10)
        cwe_id: CWE identifier
        kernel_version_affected: Affected kernel version range
        fixed_commit: Git commit hash that fixes the vulnerability
        discovered_date: Date the CVE was discovered
    """

    def __init__(
        self,
        id: str,
        description: str,
        affected_function: str,
        file_path: str = "",
        line_number: Optional[int] = None,
        vulnerability_type: str = "other",
        severity: str = "MEDIUM",
        cvss_score: float = 0.0,
        cwe_id: str = "",
        kernel_version_affected: str = "",
        fixed_commit: str = "",
        discovered_date: str = ""
    ):
        self.id = id
        self.description = description
        self.affected_function = affected_function
        self.file_path = file_path
        self.line_number = line_number
        self.vulnerability_type = vulnerability_type
        self.severity = severity
        self.cvss_score = cvss_score
        self.cwe_id = cwe_id
        self.kernel_version_affected = kernel_version_affected
        self.fixed_commit = fixed_commit
        self.discovered_date = discovered_date

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j storage."""
        return {
            'id': self.id,
            'description': self.description,
            'affected_function': self.affected_function,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'vulnerability_type': self.vulnerability_type,
            'severity': self.severity,
            'cvss_score': self.cvss_score,
            'cwe_id': self.cwe_id,
            'kernel_version_affected': self.kernel_version_affected,
            'fixed_commit': self.fixed_commit,
            'discovered_date': self.discovered_date
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CVENode':
        """Create CVENode from dictionary."""
        return cls(
            id=data.get('id', ''),
            description=data.get('description', ''),
            affected_function=data.get('affected_function', ''),
            file_path=data.get('file_path', ''),
            line_number=data.get('line_number'),
            vulnerability_type=data.get('vulnerability_type', 'other'),
            severity=data.get('severity', 'MEDIUM'),
            cvss_score=data.get('cvss_score', 0.0),
            cwe_id=data.get('cwe_id', ''),
            kernel_version_affected=data.get('kernel_version_affected', ''),
            fixed_commit=data.get('fixed_commit', ''),
            discovered_date=data.get('discovered_date', '')
        )


@dataclass
class CVEGraphNode:
    """
    Graph node representation for Neo4j.
    """

    def __init__(self, cve: CVENode):
        self.id = cve.id
        self.label = "CVE"
        self.properties = cve.to_dict()


@dataclass
class AffectsFunctionRelationship:
    """
    Relationship between CVE and affected function.
    """

    def __init__(self, cve_id: str, function_id: str,
                 verified: bool = False,
                 note: str = ""):
        self.cve_id = cve_id
        self.function_id = function_id
        self.verified = verified
        self.note = note

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Neo4j storage."""
        return {
            'cve_id': self.cve_id,
            'function_id': self.function_id,
            'verified': self.verified,
            'note': self.note
        }


# Cypher query templates for CVE schema
CVE_SCHEMA_CONSTRAINTS = """
// Create uniqueness constraint for CVE nodes
CREATE CONSTRAINT cve_id IF NOT EXISTS FOR (c:CVE) REQUIRE c.id IS UNIQUE;

// Create indexes for frequently queried properties
CREATE INDEX cve_severity IF NOT EXISTS FOR (c:CVE) ON (c.severity);
CREATE INDEX cve_function IF NOT EXISTS FOR (c:CVE) ON (c.affected_function);
CREATE INDEX cve_cvss IF NOT EXISTS FOR (c:CVE) ON (c.cvss_score);
"""


def get_cve_merge_query(cve: CVENode) -> str:
    """
    Generate a Cypher MERGE query for a CVE node.

    Args:
        cve: CVENode to merge

    Returns:
        Cypher query string
    """
    props = ", ".join([f"{k}: ${k}" for k in cve.to_dict().keys() if k != 'id'])

    return f"""
    MERGE (c:CVE {{id: $id}})
    SET c += {{{props}}}
    RETURN c
    """


def get_affects_function_merge_query(cve_id: str, function_id: str) -> str:
    """
    Generate a Cypher MERGE query for AFFECTS_FUNCTION relationship.

    Args:
        cve_id: CVE identifier
        function_id: Function identifier

    Returns:
        Cypher query string
    """
    return f"""
    MATCH (c:CVE {{id: $cve_id}})
    MATCH (f:Function {{name: $function_name}})
    MERGE (c)-[r:AFFECTS_FUNCTION]->(f)
    SET r.verified = $verified
    RETURN r
    """


def get_cve_by_id_query(cve_id: str) -> str:
    """
    Generate a Cypher query to retrieve CVE by ID.

    Args:
        cve_id: CVE identifier

    Returns:
        Cypher query string
    """
    return f"""
    MATCH (c:CVE {{id: $cve_id}})
    RETURN c
    """


def get_cves_by_severity_query(severity: str) -> str:
    """
    Generate a Cypher query to retrieve CVEs by severity.

    Args:
        severity: Severity level

    Returns:
        Cypher query string
    """
    return f"""
    MATCH (c:CVE {{severity: $severity}})
    RETURN c ORDER BY c.cvss_score DESC
    """


if __name__ == "__main__":
    # Example usage
    cve = CVENode(
        id="CVE-2024-1234",
        description="A buffer overflow vulnerability in ext4_writepages() function",
        affected_function="ext4_writepages",
        file_path="fs/ext4/inode.c",
        line_number=2145,
        vulnerability_type="buffer_overflow",
        severity="CRITICAL",
        cvss_score=9.8,
        cwe_id="CWE-787",
        kernel_version_affected="6.0-6.6",
        fixed_commit="7a8b9c1d2e3f",
        discovered_date="2024-03-15"
    )

    print(f"CVE Node: {cve.id}")
    print(f"Properties: {cve.to_dict()}")
    print(f"\nMerge Query:\n{get_cve_merge_query(cve)}")
