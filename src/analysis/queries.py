"""
Analysis Module: Cypher Query Templates
Defines Neo4j Cypher queries for impact analysis and call chain traversal.
"""

# ==============================================================================
# FUNCTION QUERIES
# ==============================================================================

GET_FUNCTION_BY_NAME = """
MATCH (f:Function {name: $func_name})
RETURN f.id as id, f.name as name, f.file_path as file_path,
       f.line_start as line_start, f.line_end as line_end,
       f.subsystem as subsystem, f.is_static as is_static
"""

GET_FUNCTION_BY_ID = """
MATCH (f:Function {id: $func_id})
RETURN f.id as id, f.name as name, f.file_path as file_path,
       f.line_start as line_start, f.line_end as line_end,
       f.subsystem as subsystem, f.is_static as is_static
"""

# ==============================================================================
# CALL CHAIN QUERIES (IMPACT ANALYSIS)
# ==============================================================================

GET_DIRECT_CALLERS = """
MATCH (caller:Function)-[r:CALLS]->(target:Function {name: $func_name})
RETURN caller.id as id, caller.name as name, caller.file_path as file_path,
       caller.subsystem as subsystem, r.call_site_line as call_line,
       1 as distance
ORDER BY caller.name
"""

GET_DIRECT_CALLEES = """
MATCH (source:Function {name: $func_name})-[r:CALLS]->(callee:Function)
RETURN callee.id as id, callee.name as name, callee.file_path as file_path,
       callee.subsystem as subsystem, r.call_site_line as call_line,
       1 as distance
ORDER BY callee.name
"""

GET_CALLERS_MULTI_HOP = """
MATCH (target:Function {name: $func_name})
MATCH path = (caller:Function)-[:CALLS*1..$max_depth]->(target)
WHERE caller <> target
RETURN caller.id as id, caller.name as name, caller.file_path as file_path,
       caller.subsystem as subsystem,
       length(path) as distance,
       [node in nodes(path) | node.name] as call_chain
ORDER BY distance, caller.name
LIMIT $limit
"""

GET_CALLEES_MULTI_HOP = """
MATCH (source:Function {name: $func_name})
MATCH path = (source)-[:CALLS*1..$max_depth]->(callee:Function)
WHERE source <> callee
RETURN callee.id as id, callee.name as name, callee.file_path as file_path,
       callee.subsystem as subsystem,
       length(path) as distance,
       [node in nodes(path) | node.name] as call_chain
ORDER BY distance, callee.name
LIMIT $limit
"""

# ==============================================================================
# TEST COVERAGE QUERIES
# ==============================================================================

GET_COVERING_TESTS = """
MATCH (test:TestCase)-[r:COVERS]->(func:Function {name: $func_name})
RETURN test.id as id, test.name as name, test.file_path as file_path,
       test.test_suite as test_suite, r.coverage_type as coverage_type
ORDER BY test.name
"""

GET_INDIRECT_TEST_COVERAGE = """
MATCH (target:Function {name: $func_name})
MATCH (caller:Function)-[:CALLS*1..$max_depth]->(target)
MATCH (test:TestCase)-[:COVERS]->(caller)
WHERE caller <> target
RETURN test.id as test_id, test.name as test_name,
       test.file_path as test_file,
       caller.name as via_function,
       length((caller)-[:CALLS*]->(target)) as indirection_level
ORDER BY indirection_level, test_name
LIMIT $limit
"""

GET_FUNCTIONS_COVERED_BY_TEST = """
MATCH (test:TestCase {name: $test_name})-[r:COVERS]->(func:Function)
RETURN func.id as id, func.name as name, func.file_path as file_path,
       func.subsystem as subsystem, r.coverage_type as coverage_type
ORDER BY func.name
"""

# ==============================================================================
# IMPACT ANALYSIS (COMBINED)
# ==============================================================================

ANALYZE_FUNCTION_IMPACT = """
MATCH (target:Function {name: $func_name})

// Get direct callers
OPTIONAL MATCH (direct_caller:Function)-[:CALLS]->(target)

// Get indirect callers (up to max_depth hops)
OPTIONAL MATCH path = (indirect_caller:Function)-[:CALLS*2..$max_depth]->(target)
WHERE indirect_caller <> target AND NOT (direct_caller)-[:CALLS]->(target)

// Get direct test coverage
OPTIONAL MATCH (direct_test:TestCase)-[:COVERS]->(target)

// Get indirect test coverage (tests covering callers)
OPTIONAL MATCH (caller:Function)-[:CALLS*1..$max_depth]->(target)
OPTIONAL MATCH (indirect_test:TestCase)-[:COVERS]->(caller)
WHERE caller <> target

RETURN
    target.name as target_function,
    target.file_path as target_file,
    collect(DISTINCT direct_caller.name) as direct_callers,
    collect(DISTINCT indirect_caller.name) as indirect_callers,
    collect(DISTINCT direct_test.name) as direct_tests,
    collect(DISTINCT indirect_test.name) as indirect_tests,
    count(DISTINCT direct_caller) as direct_caller_count,
    count(DISTINCT indirect_caller) as indirect_caller_count,
    count(DISTINCT direct_test) as direct_test_count,
    count(DISTINCT indirect_test) as indirect_test_count
"""

GET_IMPACT_CALL_CHAINS = """
MATCH (target:Function {name: $func_name})
MATCH path = (caller:Function)-[:CALLS*1..$max_depth]->(target)
WHERE caller <> target

// Get test coverage for each caller
OPTIONAL MATCH (test:TestCase)-[:COVERS]->(caller)

RETURN
    [node in nodes(path) | node.name] as call_chain,
    length(path) as depth,
    caller.name as caller_name,
    caller.file_path as caller_file,
    caller.subsystem as caller_subsystem,
    collect(DISTINCT test.name) as covering_tests,
    count(DISTINCT test) as test_count
ORDER BY depth, caller_name
LIMIT $limit
"""

# ==============================================================================
# SUBSYSTEM ANALYSIS
# ==============================================================================

GET_SUBSYSTEM_FUNCTIONS = """
MATCH (f:Function {subsystem: $subsystem_name})
RETURN f.id as id, f.name as name, f.file_path as file_path,
       f.is_static as is_static
ORDER BY f.name
"""

GET_CROSS_SUBSYSTEM_CALLS = """
MATCH (caller:Function)-[r:CALLS]->(callee:Function)
WHERE caller.subsystem = $subsystem_name
  AND callee.subsystem <> $subsystem_name
RETURN caller.name as caller, caller.file_path as caller_file,
       callee.name as callee, callee.file_path as callee_file,
       callee.subsystem as target_subsystem,
       r.call_site_line as call_line
ORDER BY target_subsystem, callee
"""

GET_SUBSYSTEM_ENTRY_POINTS = """
MATCH (external:Function)-[r:CALLS]->(entry:Function {subsystem: $subsystem_name})
WHERE external.subsystem <> $subsystem_name
WITH entry, count(DISTINCT external) as external_caller_count
WHERE external_caller_count > 0
RETURN entry.name as entry_point, entry.file_path as file_path,
       entry.is_static as is_static, external_caller_count
ORDER BY external_caller_count DESC, entry.name
LIMIT $limit
"""

# ==============================================================================
# STATISTICS QUERIES
# ==============================================================================

GET_FUNCTION_CALL_STATS = """
MATCH (f:Function {name: $func_name})
OPTIONAL MATCH (f)-[calls_out:CALLS]->()
OPTIONAL MATCH ()-[calls_in:CALLS]->(f)
RETURN
    f.name as function_name,
    count(DISTINCT calls_out) as functions_called,
    count(DISTINCT calls_in) as called_by_count
"""

GET_TOP_CALLED_FUNCTIONS = """
MATCH (f:Function)<-[r:CALLS]-()
WITH f, count(r) as call_count
WHERE call_count >= $min_callers
RETURN f.name as function_name, f.file_path as file_path,
       f.subsystem as subsystem, call_count
ORDER BY call_count DESC
LIMIT $limit
"""

GET_TEST_COVERAGE_STATS = """
MATCH (f:Function)
OPTIONAL MATCH (t:TestCase)-[:COVERS]->(f)
WITH f, count(DISTINCT t) as test_count
RETURN
    CASE
        WHEN test_count = 0 THEN 'uncovered'
        WHEN test_count = 1 THEN 'single_test'
        ELSE 'multiple_tests'
    END as coverage_category,
    count(f) as function_count
ORDER BY coverage_category
"""

# ==============================================================================
# RISK ASSESSMENT QUERIES
# ==============================================================================

GET_CRITICAL_UNCOVERED_FUNCTIONS = """
MATCH (f:Function)
WHERE NOT (f)<-[:COVERS]-(:TestCase)
WITH f
MATCH (caller:Function)-[:CALLS]->(f)
WITH f, count(DISTINCT caller) as caller_count
WHERE caller_count >= $min_callers
RETURN f.name as function_name, f.file_path as file_path,
       f.subsystem as subsystem, caller_count,
       'critical_uncovered' as risk_level
ORDER BY caller_count DESC
LIMIT $limit
"""

GET_HIGH_IMPACT_FUNCTIONS = """
MATCH (f:Function)
MATCH path = (caller:Function)-[:CALLS*1..2]->(f)
WITH f, count(DISTINCT caller) as impact_score
WHERE impact_score >= $min_impact_score
OPTIONAL MATCH (test:TestCase)-[:COVERS]->(f)
RETURN f.name as function_name, f.file_path as file_path,
       f.subsystem as subsystem, impact_score,
       count(DISTINCT test) as test_coverage_count,
       CASE
           WHEN count(DISTINCT test) = 0 THEN 'high_risk'
           WHEN count(DISTINCT test) < 3 THEN 'medium_risk'
           ELSE 'low_risk'
       END as risk_level
ORDER BY impact_score DESC, test_coverage_count ASC
LIMIT $limit
"""

# ==============================================================================
# QUERY PARAMETER DEFAULTS
# ==============================================================================

DEFAULT_PARAMS = {
    'max_depth': 3,
    'limit': 100,
    'min_callers': 5,
    'min_impact_score': 10,
}


def build_query(template: str, **params) -> tuple[str, dict]:
    """
    Build a Cypher query with parameters.

    Args:
        template: Query template string
        **params: Query parameters

    Returns:
        Tuple of (query, parameters)
    """
    # Merge with defaults
    query_params = DEFAULT_PARAMS.copy()
    query_params.update(params)

    return template, query_params
