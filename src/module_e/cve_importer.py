"""
Module E: CVE Importer
Imports CVEs from NVD JSON feed and parses descriptions using LLM.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import re
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from src.module_e.schema import CVENode
from src.module_b.graph_store import Neo4jGraphStore
from src.config import LLMConfig

logger = logging.getLogger(__name__)


class CVEImporter:
    """
    Import CVEs from NVD JSON feed and parse with LLM.
    """

    def __init__(self, graph_store: Neo4jGraphStore, llm_config: Optional[LLMConfig] = None):
        """
        Initialize the CVE importer.

        Args:
            graph_store: Neo4jGraphStore instance
            llm_config: Optional LLM configuration for parsing CVE descriptions
        """
        self.graph_store = graph_store
        self.llm_config = llm_config

        # Initialize schema
        self._init_schema()

    def _init_schema(self):
        """Initialize CVE schema in Neo4j."""
        from src.module_e.schema import CVE_SCHEMA_CONSTRAINTS
        try:
            self.graph_store.execute_query(CVE_SCHEMA_CONSTRAINTS, {})
            logger.info("CVE schema initialized successfully")
        except Exception as e:
            logger.warning(f"Schema initialization failed (may already exist): {e}")

    def import_from_nvd_json(self, json_path: str) -> List[CVENode]:
        """
        Import CVEs from NVD JSON file.

        Args:
            json_path: Path to NVD JSON file

        Returns:
            List of imported CVENode objects
        """
        logger.info(f"Importing CVEs from {json_path}")

        with open(json_path, 'r') as f:
            data = json.load(f)

        cves = []
        cve_items = data.get('CVE_Items', [])

        for item in cve_items:
            try:
                cve = self._parse_nvd_item(item)
                if cve:
                    cves.append(cve)
            except Exception as e:
                logger.error(f"Failed to parse CVE item: {e}")
                continue

        logger.info(f"Parsed {len(cves)} CVEs from NVD feed")

        # Store in Neo4j
        for cve in cves:
            self._store_cve(cve)

        return cves

    def import_cve_from_text(self, cve_id: str, description: str,
                            metadata: Optional[Dict[str, Any]] = None) -> Optional[CVENode]:
        """
        Import a single CVE from text description.

        Args:
            cve_id: CVE identifier (e.g., "CVE-2024-1234")
            description: CVE description text
            metadata: Optional additional metadata

        Returns:
            CVENode or None if parsing failed
        """
        logger.info(f"Importing CVE {cve_id} from text")

        # Parse description with LLM if available
        if self.llm_config:
            parsed = self._parse_description_with_llm(cve_id, description)
        else:
            parsed = self._parse_description_regex(cve_id, description)

        if not parsed:
            logger.error(f"Failed to parse CVE {cve_id}")
            return None

        # Merge with provided metadata
        if metadata:
            parsed.update(metadata)

        # Create CVE node
        cve = CVENode.from_dict(parsed)

        # Store in Neo4j
        self._store_cve(cve)

        return cve

    def _parse_nvd_item(self, item: Dict[str, Any]) -> Optional[CVENode]:
        """
        Parse CVE from NVD JSON item.

        Args:
            item: NVD JSON item

        Returns:
            CVENode or None
        """
        try:
            cve_id = item['cve']['CVE_data_meta']['ID']
            description = item['cve']['description']['description_data'][0]['value']

            # Extract CVSS score
            cvss_score = 0.0
            severity = "MEDIUM"

            if 'metrics' in item.get('impact', {}):
                cvss_data = item['impact']['metrics']
                if 'CVSS_V3' in cvss_data:
                    cvss_v3 = cvss_data['CVSS_V3'][0]
                    cvss_score = cvss_v3['cvssV3']['baseScore']
                    severity = self._cvss_to_severity(cvss_score)

            # Parse description
            if self.llm_config:
                parsed = self._parse_description_with_llm(cve_id, description)
            else:
                parsed = self._parse_description_regex(cve_id, description)

            if not parsed:
                return None

            # Add NVD metadata
            parsed['cvss_score'] = cvss_score
            parsed['severity'] = severity

            # Extract CWE ID if available
            if 'problemtype' in item['cve']:
                problem_data = item['cve']['problemtype']['problemtype_data']
                if problem_data and len(problem_data) > 0:
                    cwe_entries = problem_data[0].get('description', [])
                    for entry in cwe_entries:
                        if entry.get('lang') == 'en':
                            cwe_id = entry.get('value', '')
                            if cwe_id.startswith('CWE-'):
                                parsed['cwe_id'] = cwe_id
                                break

            return CVENode.from_dict(parsed)

        except Exception as e:
            logger.error(f"Failed to parse NVD item: {e}")
            return None

    def _parse_description_regex(self, cve_id: str, description: str) -> Optional[Dict[str, Any]]:
        """
        Parse CVE description using regex patterns.

        Args:
            cve_id: CVE identifier
            description: CVE description

        Returns:
            Parsed data dictionary or None
        """
        # Try to extract function name from description
        # Pattern: "vulnerability in <function_name>()" or "in <function_name> function"
        function_patterns = [
            r'in\s+(\w+)\(\)\s+function',
            r'in\s+(\w+)\s+function',
            r'vulnerability\s+in\s+(\w+)\(',
            r'flaw\s+in\s+(\w+)\(',
        ]

        function_name = None
        for pattern in function_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                function_name = match.group(1)
                break

        # Try to extract file path
        # Pattern: "fs/ext4/inode.c" or similar
        file_pattern = r'([a-z/]+/[a-z_]+\.[ch])'
        file_match = re.search(file_pattern, description)
        file_path = file_match.group(1) if file_match else ""

        # Detect vulnerability type
        vuln_type = "other"
        description_lower = description.lower()
        if "buffer overflow" in description_lower or "overflow" in description_lower:
            vuln_type = "buffer_overflow"
        elif "null pointer" in description_lower or "null dereference" in description_lower:
            vuln_type = "null_dereference"
        elif "use after free" in description_lower:
            vuln_type = "use_after_free"
        elif "race" in description_lower:
            vuln_type = "race_condition"
        elif "memory leak" in description_lower:
            vuln_type = "memory_leak"

        if not function_name:
            logger.warning(f"Could not extract function name from CVE {cve_id}")
            return None

        return {
            'id': cve_id,
            'description': description,
            'affected_function': function_name,
            'file_path': file_path,
            'vulnerability_type': vuln_type,
            'severity': 'MEDIUM',
            'cvss_score': 0.0,
            'cwe_id': '',
            'kernel_version_affected': '',
            'fixed_commit': '',
            'discovered_date': datetime.now().strftime('%Y-%m-%d')
        }

    def _parse_description_with_llm(self, cve_id: str, description: str) -> Optional[Dict[str, Any]]:
        """
        Parse CVE description using LLM.

        Args:
            cve_id: CVE identifier
            description: CVE description

        Returns:
            Parsed data dictionary or None
        """
        if not self.llm_config:
            logger.warning("LLM config not provided, falling back to regex parsing")
            return self._parse_description_regex(cve_id, description)

        try:
            # Import LLM reporter
            from src.analysis.llm_reporter import LLMReporter

            prompt = f"""You are a Linux kernel security expert. Extract the following from this CVE description:

CVE: {cve_id}
Description: {description}

Extract:
1. Function name (exact): The vulnerable kernel function name
2. File path: Source file path if mentioned
3. Vulnerability type: One of: buffer_overflow, null_dereference, use_after_free, race_condition, integer_overflow, memory_leak, double_free, code_injection, privilege_escalation, denial_of_service, information_leak, other

Return JSON format only:
{{
    "affected_function": "function_name",
    "file_path": "path/to/file.c",
    "vulnerability_type": "vulnerability_type"
}}
"""

            reporter = LLMReporter(self.llm_config)
            response = reporter.client.chat.completions.create(
                model=self.llm_config.model,
                messages=[
                    {"role": "system", "content": "You are a Linux kernel security expert. Always return valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            result_text = response.choices[0].message.content.strip()

            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group(0)

            parsed = json.loads(result_text)

            return {
                'id': cve_id,
                'description': description,
                'affected_function': parsed.get('affected_function', ''),
                'file_path': parsed.get('file_path', ''),
                'vulnerability_type': parsed.get('vulnerability_type', 'other'),
                'severity': 'MEDIUM',
                'cvss_score': 0.0,
                'cwe_id': '',
                'kernel_version_affected': '',
                'fixed_commit': '',
                'discovered_date': datetime.now().strftime('%Y-%m-%d')
            }

        except Exception as e:
            logger.error(f"LLM parsing failed for CVE {cve_id}: {e}")
            return self._parse_description_regex(cve_id, description)

    def _store_cve(self, cve: CVENode):
        """
        Store CVE in Neo4j.

        Args:
            cve: CVENode to store
        """
        from src.module_e.schema import get_cve_merge_query

        try:
            query = get_cve_merge_query(cve)
            params = cve.to_dict()

            self.graph_store.execute_query(query, params)

            # Create AFFECTS_FUNCTION relationship if function exists
            if cve.affected_function:
                self._create_affects_relationship(cve)

            logger.info(f"Stored CVE {cve.id} in Neo4j")

        except Exception as e:
            logger.error(f"Failed to store CVE {cve.id}: {e}")

    def _create_affects_relationship(self, cve: CVENode):
        """
        Create AFFECTS_FUNCTION relationship.

        Args:
            cve: CVENode
        """
        try:
            query = """
            MATCH (c:CVE {id: $cve_id})
            MATCH (f:Function {name: $function_name})
            MERGE (c)-[r:AFFECTS_FUNCTION]->(f)
            SET r.verified = false
            RETURN r
            """

            self.graph_store.execute_query(query, {
                'cve_id': cve.id,
                'function_name': cve.affected_function
            })

            logger.info(f"Created AFFECTS_FUNCTION relationship for {cve.id}")

        except Exception as e:
            logger.warning(f"Failed to create AFFECTS_FUNCTION relationship: {e}")

    def _cvss_to_severity(self, cvss_score: float) -> str:
        """
        Convert CVSS score to severity level.

        Args:
            cvss_score: CVSS score (0-10)

        Returns:
            Severity level string
        """
        if cvss_score >= 9.0:
            return "CRITICAL"
        elif cvss_score >= 7.0:
            return "HIGH"
        elif cvss_score >= 4.0:
            return "MEDIUM"
        else:
            return "LOW"

    def import_batch_from_nvd(self, start_date: str, end_date: str) -> List[CVENode]:
        """
        Import CVEs from NVD API for a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            List of imported CVENode objects
        """
        if not REQUESTS_AVAILABLE:
            logger.error("requests library not available, cannot fetch from NVD API")
            return []

        logger.info(f"Fetching CVEs from NVD API: {start_date} to {end_date}")

        # NVD API endpoint (v2.0)
        base_url = "https://services.nvd.nist.gov/rest/json/cves/2.0"

        params = {
            'pubStartDate': f"{start_date}T00:00:00.000",
            'pubEndDate': f"{end_date}T23:59:59.999",
            'resultsPerPage': 2000
        }

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()

            data = response.json()

            cves = []
            vulns = data.get('vulnerabilities', [])

            for vuln in vulns:
                try:
                    cve = self._parse_nvd_v2_item(vuln)
                    if cve:
                        cves.append(cve)
                        self._store_cve(cve)
                except Exception as e:
                    logger.error(f"Failed to parse CVE: {e}")
                    continue

            logger.info(f"Imported {len(cves)} CVEs from NVD API")
            return cves

        except Exception as e:
            logger.error(f"Failed to fetch CVEs from NVD API: {e}")
            return []

    def _parse_nvd_v2_item(self, vuln: Dict[str, Any]) -> Optional[CVENode]:
        """
        Parse CVE from NVD API v2.0 format.

        Args:
            vuln: NVD v2.0 vulnerability item

        Returns:
            CVENode or None
        """
        try:
            cve_id = vuln['cve']['id']
            descriptions = vuln['cve']['descriptions']

            # Get English description
            description = ""
            for desc in descriptions:
                if desc['lang'] == 'en':
                    description = desc['value']
                    break

            # Extract CVSS score
            cvss_score = 0.0
            severity = "MEDIUM"

            metrics = vuln['cve'].get('metrics', {})
            if 'cvssMetricV31' in metrics:
                cvss_data = metrics['cvssMetricV31'][0]['cvssData']
                cvss_score = cvss_data['baseScore']
                severity = self._cvss_to_severity(cvss_score)
            elif 'cvssMetricV2' in metrics:
                cvss_data = metrics['cvssMetricV2'][0]['cvssData']
                cvss_score = cvss_data['baseScore']
                severity = self._cvss_to_severity(cvss_score)

            # Parse description
            if self.llm_config:
                parsed = self._parse_description_with_llm(cve_id, description)
            else:
                parsed = self._parse_description_regex(cve_id, description)

            if not parsed:
                return None

            # Add metadata
            parsed['cvss_score'] = cvss_score
            parsed['severity'] = severity

            # Extract CWE ID
            if 'problemTypes' in vuln['cve']:
                problem_types = vuln['cve']['problemTypes']
                if problem_types and len(problem_types) > 0:
                    descriptions = problem_types[0].get('descriptions', [])
                    for desc in descriptions:
                        if desc.get('lang') == 'en':
                            cwe_id = desc.get('description', '')
                            if cwe_id.startswith('CWE-'):
                                parsed['cwe_id'] = cwe_id
                                break

            return CVENode.from_dict(parsed)

        except Exception as e:
            logger.error(f"Failed to parse NVD v2.0 item: {e}")
            return None


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) < 3:
        print("Usage: python cve_importer.py <json_file> <kernel_root>")
        print("Example: python cve_importer.py nvd-2024.json /path/to/linux")
        sys.exit(1)

    json_file = sys.argv[1]
    kernel_root = sys.argv[2]

    from src.config import Config

    config = Config.from_defaults(kernel_root=kernel_root)

    with Neo4jGraphStore(
        config.neo4j.url,
        config.neo4j.user,
        config.neo4j.password
    ) as store:
        importer = CVEImporter(store, config.llm)

        # Import CVEs
        cves = importer.import_from_nvd_json(json_file)

        print(f"\nImported {len(cves)} CVEs")
        for cve in cves[:5]:
            print(f"  - {cve.id}: {cve.affected_function} ({cve.severity})")
