"""
Module E: CVE Impact Analyzer
Automates CVE impact analysis by mapping CVE descriptions to kernel code using
the existing callgraph infrastructure, showing developers exactly what code paths
to review and test.

Components:
- schema: CVE node and relationship definitions
- cve_importer: Import CVEs from NVD, parse with LLM
- impact_analyzer: Reachability analysis using existing callgraph
- version_checker: Check if function exists in kernel version
- test_coverage: Check test coverage using existing Module C
- cve_reporter: Generate markdown reports
"""

from src.module_e.schema import CVEGraphNode, CVENode, AffectsFunctionRelationship
from src.module_e.cve_importer import CVEImporter
from src.module_e.impact_analyzer import CVEImpactAnalyzer
from src.module_e.version_checker import VersionChecker
from src.module_e.test_coverage import CVETestCoverage
from src.module_e.cve_reporter import CVEReporter

__all__ = [
    'CVEGraphNode',
    'CVENode',
    'AffectsFunctionRelationship',
    'CVEImporter',
    'CVEImpactAnalyzer',
    'VersionChecker',
    'CVETestCoverage',
    'CVEReporter',
]
