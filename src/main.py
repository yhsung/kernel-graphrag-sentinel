#!/usr/bin/env python3
"""
Kernel-GraphRAG Sentinel CLI
Main command-line interface for kernel code analysis.
"""

import sys
import os
from pathlib import Path
import click
import json
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import load_config, Config
from src.module_a.extractor import FunctionExtractor
from src.module_b.graph_store import Neo4jGraphStore
from src.module_b.ingestion import ingest_from_extractor
from src.module_c.test_mapper import TestMapper
from src.analysis.impact_analyzer import ImpactAnalyzer
from src.module_d.flow_ingestion import DataFlowIngestion

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
@click.option('--config', '-c', type=click.Path(exists=True),
              help='Path to configuration YAML file')
@click.option('--kernel-root', '-k', type=click.Path(exists=True),
              help='Path to Linux kernel source root')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.pass_context
def cli(ctx, config, kernel_root, verbose):
    """
    Kernel-GraphRAG Sentinel - AI-powered Linux kernel code analysis tool.

    Analyzes kernel code structure, builds call graphs, maps test coverage,
    and provides impact analysis for code changes.
    """
    # Set logging level
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    ctx.ensure_object(dict)
    ctx.obj['config'] = load_config(config, kernel_root=kernel_root)
    ctx.obj['verbose'] = verbose


@cli.command()
@click.argument('subsystem')
@click.option('--skip-preprocessing', is_flag=True,
              help='Skip macro preprocessing (faster but less accurate)')
@click.option('--clear-db', is_flag=True,
              help='Clear database before ingestion')
@click.pass_context
def ingest(ctx, subsystem, skip_preprocessing, clear_db):
    """
    Extract and ingest kernel subsystem into Neo4j.

    SUBSYSTEM: Relative path to subsystem (e.g., fs/ext4)

    Examples:

        kgraph ingest fs/ext4

        kgraph ingest fs/ext4 --clear-db

        kgraph ingest net/ipv4 --skip-preprocessing
    """
    config = ctx.obj['config']
    config.kernel.subsystem = subsystem

    click.echo(f"Ingesting {subsystem}...")
    click.echo(f"Kernel root: {config.kernel.root}")
    click.echo(f"Skip preprocessing: {skip_preprocessing}")

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        # Clear database if requested
        if clear_db:
            click.confirm('⚠️  This will delete all data in Neo4j. Continue?',
                          abort=True)
            store.clear_database()
            click.echo("Database cleared.")

        # Initialize schema
        store.initialize_schema()

        # Extract and ingest
        stats = ingest_from_extractor(
            config.kernel.root,
            subsystem,
            store,
            skip_preprocessing=skip_preprocessing
        )

        click.echo("\n" + "=" * 60)
        click.echo("INGESTION COMPLETE")
        click.echo("=" * 60)
        click.echo(json.dumps(stats, indent=2))

        # Show database statistics
        db_stats = store.get_statistics()
        click.echo("\nDatabase Statistics:")
        click.echo(json.dumps(db_stats, indent=2))


@cli.command()
@click.argument('subsystem')
@click.pass_context
def map_tests(ctx, subsystem):
    """
    Map KUnit tests to functions for a subsystem.

    SUBSYSTEM: Relative path to subsystem (e.g., fs/ext4)

    Examples:

        kgraph map-tests fs/ext4

        kgraph map-tests fs/btrfs
    """
    config = ctx.obj['config']
    config.kernel.subsystem = subsystem

    click.echo(f"Mapping tests for {subsystem}...")

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        mapper = TestMapper(store)

        stats = mapper.map_subsystem_tests(config.kernel.root, subsystem)

        click.echo("\n" + "=" * 60)
        click.echo("TEST MAPPING COMPLETE")
        click.echo("=" * 60)
        click.echo(json.dumps(stats, indent=2))


@cli.command()
@click.argument('function_name')
@click.option('--max-depth', '-d', default=3, type=int,
              help='Maximum call chain depth to analyze')
@click.option('--output', '-o', type=click.File('w'),
              help='Output file for report (default: stdout)')
@click.option('--llm', is_flag=True,
              help='Generate AI-powered natural language report using LLM')
@click.pass_context
def analyze(ctx, function_name, max_depth, output, llm):
    """
    Analyze the impact of modifying a function.

    FUNCTION_NAME: Name of the function to analyze

    Examples:

        kgraph analyze ext4_map_blocks

        kgraph analyze ext4_mb_new_blocks_simple --max-depth 5

        kgraph analyze ext4_inode_bitmap --output report.txt

        kgraph analyze ext4_map_blocks --llm  # AI-powered report
    """
    config = ctx.obj['config']

    click.echo(f"Analyzing impact for: {function_name}")
    click.echo(f"Max call depth: {max_depth}")
    if llm:
        click.echo(f"LLM provider: {config.llm.provider} ({config.llm.model})")

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        analyzer = ImpactAnalyzer(store)

        impact = analyzer.analyze_function_impact(
            function_name,
            max_depth=max_depth,
            limit=config.analysis.max_results
        )

        if impact:
            # Generate LLM report if requested
            if llm:
                try:
                    from src.analysis.llm_reporter import LLMReporter, LLMConfig

                    click.echo("\n🤖 Generating AI-powered report...")

                    llm_config = LLMConfig(
                        provider=config.llm.provider,
                        model=config.llm.model,
                        api_key=config.llm.api_key,
                        temperature=config.llm.temperature
                    )

                    # Pass graph_store for Mermaid diagram generation
                    reporter = LLMReporter(llm_config, graph_store=store)

                    # Convert ImpactResult to dict
                    impact_data = {
                        "file_path": impact.target_file,
                        "stats": impact.stats,
                        "direct_callers": impact.direct_callers,
                        "indirect_callers": impact.indirect_callers,
                        "direct_callees": impact.direct_callees,
                        "indirect_callees": impact.indirect_callees,
                        "direct_tests": impact.direct_tests,
                        "indirect_tests": impact.indirect_tests,
                        "risk_level": impact.stats.get('risk_level', 'UNKNOWN')
                    }

                    report = reporter.generate_impact_report(impact_data, function_name)

                except Exception as e:
                    click.echo(f"\n❌ LLM report generation failed: {e}")
                    click.echo("\nFalling back to standard report...\n")
                    report = analyzer.format_impact_report(impact, max_items=15)
            else:
                report = analyzer.format_impact_report(impact, max_items=15)

            if output:
                output.write(report)
                click.echo(f"\nReport written to {output.name}")
            else:
                click.echo("\n" + report)
        else:
            click.echo(f"❌ Function '{function_name}' not found in database")
            sys.exit(1)


@cli.command()
@click.argument('subsystem')
@click.option('--skip-preprocessing', is_flag=True,
              help='Skip macro preprocessing')
@click.option('--clear-db', is_flag=True,
              help='Clear database before ingestion')
@click.pass_context
def pipeline(ctx, subsystem, skip_preprocessing, clear_db):
    """
    Run complete analysis pipeline: ingest + map tests.

    SUBSYSTEM: Relative path to subsystem (e.g., fs/ext4)

    Examples:

        kgraph pipeline fs/ext4

        kgraph pipeline fs/ext4 --clear-db
    """
    config = ctx.obj['config']
    config.kernel.subsystem = subsystem

    click.echo("=" * 60)
    click.echo(f"RUNNING PIPELINE FOR {subsystem}")
    click.echo("=" * 60)

    # Step 1: Ingest
    click.echo("\n[1/2] Ingesting subsystem...")
    ctx.invoke(ingest, subsystem=subsystem,
               skip_preprocessing=skip_preprocessing,
               clear_db=clear_db)

    # Step 2: Map tests
    click.echo("\n[2/2] Mapping tests...")
    ctx.invoke(map_tests, subsystem=subsystem)

    click.echo("\n" + "=" * 60)
    click.echo("PIPELINE COMPLETE")
    click.echo("=" * 60)
    click.echo(f"\n✅ {subsystem} is now ready for analysis!")
    click.echo(f"\nTry: kgraph analyze <function_name>")


@cli.command()
@click.pass_context
def stats(ctx):
    """
    Show database statistics.

    Examples:

        kgraph stats
    """
    config = ctx.obj['config']

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        db_stats = store.get_statistics()

        click.echo("\n" + "=" * 60)
        click.echo("DATABASE STATISTICS")
        click.echo("=" * 60)
        click.echo(json.dumps(db_stats, indent=2))

        # Calculate totals
        total_nodes = sum(v for k, v in db_stats.items() if k.endswith('_count') and 'Function' in k or 'TestCase' in k or 'File' in k or 'Subsystem' in k)
        total_rels = sum(v for k, v in db_stats.items() if k.endswith('_count') and 'CALLS' in k or 'COVERS' in k or 'BELONGS_TO' in k or 'CONTAINS' in k)

        click.echo(f"\nTotal nodes: {total_nodes}")
        click.echo(f"Total relationships: {total_rels}")


@cli.command()
@click.option('--output', '-o', default='kgraph-config.yaml',
              help='Output configuration file path')
@click.pass_context
def init_config(ctx, output):
    """
    Generate example configuration file.

    Examples:

        kgraph init-config

        kgraph init-config --output my-config.yaml
    """
    config = ctx.obj.get('config') or Config.from_defaults()

    config.save_yaml(output)
    click.echo(f"✅ Configuration file created: {output}")
    click.echo(f"\nEdit the file and run:")
    click.echo(f"  kgraph --config {output} pipeline fs/ext4")


@cli.command()
@click.option('--subsystem', '-s', help='Filter by subsystem')
@click.option('--min-callers', '-m', default=5, type=int,
              help='Minimum number of callers to show')
@click.option('--limit', '-l', default=20, type=int,
              help='Maximum number of results')
@click.pass_context
def top_functions(ctx, subsystem, min_callers, limit):
    """
    Show most frequently called functions.

    Examples:

        kgraph top-functions

        kgraph top-functions --subsystem ext4

        kgraph top-functions --min-callers 10 --limit 50
    """
    config = ctx.obj['config']

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        # Query top functions
        query = """
        MATCH (f:Function)<-[r:CALLS]-()
        """ + (f"WHERE f.subsystem = '{subsystem}'" if subsystem else "") + """
        WITH f, count(r) as call_count
        WHERE call_count >= $min_callers
        RETURN f.name as function_name, f.file_path as file_path,
               f.subsystem as subsystem, call_count
        ORDER BY call_count DESC
        LIMIT $limit
        """

        results = store.execute_query(query, {
            'min_callers': min_callers,
            'limit': limit
        })

        click.echo("\n" + "=" * 60)
        click.echo(f"TOP CALLED FUNCTIONS (min {min_callers} callers)")
        if subsystem:
            click.echo(f"Subsystem: {subsystem}")
        click.echo("=" * 60)

        for i, record in enumerate(results, 1):
            file_short = Path(record['file_path']).name if record['file_path'] else 'unknown'
            click.echo(f"{i:2}. {record['function_name']:40} "
                      f"({record['call_count']:3} calls) - {file_short}")


@cli.command('export-graph')
@click.argument('function_name')
@click.option('--format', type=click.Choice(['mermaid', 'dot', 'json']),
              default='mermaid', help='Export format')
@click.option('--output', '-o', help='Output file (stdout if not specified)')
@click.option('--max-depth', default=2, help='Maximum call graph depth')
@click.option('--direction', type=click.Choice(['callers', 'callees', 'both']),
              default='both', help='Graph direction')
@click.pass_context
def export_graph(ctx, function_name, format, output, max_depth, direction):
    """Export call graph visualization for a function.

    Exports call graph in various formats:
    - mermaid: Mermaid diagram (for GitHub/VS Code)
    - dot: Graphviz DOT format
    - json: JSON format for custom processing

    Examples:
        python3 src/main.py export-graph show_val_kb --format mermaid
        python3 src/main.py export-graph show_val_kb --format dot -o graph.dot
        python3 src/main.py export-graph show_val_kb --format json --direction callers
    """
    config = ctx.obj['config']

    from src.module_b.graph_store import Neo4jGraphStore
    from src.analysis.graph_exporter import GraphExporter

    try:
        # Initialize graph store
        store = Neo4jGraphStore(
            uri=config.neo4j.url,
            user=config.neo4j.user,
            password=config.neo4j.password
        )

        # Create exporter
        exporter = GraphExporter(store)

        # Export graph
        graph_output = exporter.export_callgraph(
            function_name=function_name,
            max_depth=max_depth,
            format=format,
            direction=direction
        )

        # Output result
        if output:
            with open(output, 'w') as f:
                f.write(graph_output)
            click.echo(f"✅ Graph exported to {output} ({format} format)")

            if format == 'dot':
                click.echo(f"\nTo render: dot -Tpng {output} -o graph.png")
            elif format == 'mermaid':
                click.echo(f"\nView in GitHub, VS Code, or https://mermaid.live/")
        else:
            click.echo(graph_output)

    except Exception as e:
        click.echo(f"❌ Error exporting graph: {e}", err=True)
        raise click.Abort()


@cli.command('ingest-dataflow')
@click.argument('subsystem')
@click.option('--skip-preprocessing', is_flag=True,
              help='Skip macro preprocessing')
@click.pass_context
def ingest_dataflow(ctx, subsystem, skip_preprocessing):
    """
    Extract and ingest data flow information into Neo4j.

    SUBSYSTEM: Relative path to subsystem (e.g., fs/ext4)

    This command extracts variable definitions, uses, and data flow edges
    from C code and stores them in Neo4j for advanced analysis.

    Examples:

        kgraph ingest-dataflow fs/ext4

        kgraph ingest-dataflow fs/ext4 --skip-preprocessing
    """
    config = ctx.obj['config']
    config.kernel.subsystem = subsystem

    click.echo(f"Ingesting data flow for {subsystem}...")
    click.echo(f"Kernel root: {config.kernel.root}")

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        # Create data flow ingestion pipeline
        ingestion = DataFlowIngestion(store)

        # Setup schema
        click.echo("Setting up data flow schema...")
        ingestion.setup_schema()

        # Ingest subsystem directory
        subsystem_path = Path(config.kernel.root) / subsystem
        stats = ingestion.ingest_directory(str(subsystem_path), subsystem)

        click.echo("\n" + "=" * 60)
        click.echo("DATA FLOW INGESTION COMPLETE")
        click.echo("=" * 60)
        click.echo(json.dumps(stats, indent=2))

        # Get statistics
        click.echo("\nData Flow Statistics:")
        df_stats = ingestion.get_variable_statistics()
        click.echo(json.dumps(df_stats, indent=2))


@cli.command('dataflow')
@click.argument('variable_name')
@click.option('--function', '-f', help='Limit to specific function')
@click.option('--max-depth', '-d', default=3, type=int,
              help='Maximum flow chain depth')
@click.option('--direction', type=click.Choice(['forward', 'backward', 'both']),
              default='both', help='Flow direction to analyze')
@click.pass_context
def dataflow(ctx, variable_name, function, max_depth, direction):
    """
    Analyze data flow for a variable.

    VARIABLE_NAME: Name of the variable to trace

    This command shows how data flows through a variable, tracking
    assignments, function parameters, and return values.

    Examples:

        kgraph dataflow inode

        kgraph dataflow buffer --function ext4_read_block

        kgraph dataflow result --max-depth 5 --direction forward
    """
    config = ctx.obj['config']

    click.echo(f"Analyzing data flow for variable: {variable_name}")
    if function:
        click.echo(f"Function scope: {function}")
    click.echo(f"Max depth: {max_depth}")
    click.echo(f"Direction: {direction}")

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        # Build query based on direction
        if direction == 'forward':
            # Variables that this variable flows TO
            query = """
            MATCH path = (v1:Variable {name: $var_name})-[:FLOWS_TO*1..$max_depth]->(v2:Variable)
            """ + (f"WHERE v1.scope = '{function}'" if function else "") + """
            RETURN v1.name as from_var, v1.scope as from_scope,
                   v2.name as to_var, v2.scope as to_scope,
                   length(path) as depth
            ORDER BY depth, to_var
            LIMIT 50
            """
        elif direction == 'backward':
            # Variables that flow TO this variable
            query = """
            MATCH path = (v1:Variable)-[:FLOWS_TO*1..$max_depth]->(v2:Variable {name: $var_name})
            """ + (f"WHERE v2.scope = '{function}'" if function else "") + """
            RETURN v1.name as from_var, v1.scope as from_scope,
                   v2.name as to_var, v2.scope as to_scope,
                   length(path) as depth
            ORDER BY depth, from_var
            LIMIT 50
            """
        else:  # both
            query = """
            MATCH path = (v1:Variable)-[:FLOWS_TO*1..$max_depth]-(v2:Variable)
            WHERE v1.name = $var_name OR v2.name = $var_name
            """ + (f"AND (v1.scope = '{function}' OR v2.scope = '{function}')" if function else "") + """
            RETURN v1.name as from_var, v1.scope as from_scope,
                   v2.name as to_var, v2.scope as to_scope,
                   length(path) as depth
            ORDER BY depth, from_var, to_var
            LIMIT 50
            """

        results = store.execute_query(query, {
            'var_name': variable_name,
            'max_depth': max_depth
        })

        if not results:
            click.echo(f"\n❌ No data flows found for variable '{variable_name}'")
            click.echo("\nTip: Make sure you've run 'kgraph ingest-dataflow <subsystem>' first")
            sys.exit(1)

        click.echo("\n" + "=" * 60)
        click.echo(f"DATA FLOW ANALYSIS: {variable_name}")
        click.echo("=" * 60)

        for record in results:
            depth_indicator = "  " * record['depth']
            click.echo(f"{depth_indicator}{record['from_var']} ({record['from_scope']}) "
                      f"→ {record['to_var']} ({record['to_scope']}) "
                      f"[depth: {record['depth']}]")

        click.echo(f"\nTotal flows: {len(results)}")

        # Show additional variable info
        var_query = """
        MATCH (v:Variable {name: $var_name})
        RETURN v.name as name, v.type as type, v.scope as scope,
               v.is_parameter as is_param, v.is_pointer as is_ptr,
               v.file_path as file
        LIMIT 10
        """
        var_results = store.execute_query(var_query, {'var_name': variable_name})

        if var_results:
            click.echo("\n" + "=" * 60)
            click.echo(f"VARIABLE DEFINITIONS: {variable_name}")
            click.echo("=" * 60)

            for var in var_results:
                file_short = Path(var['file']).name if var['file'] else 'unknown'
                param_marker = " [param]" if var['is_param'] else ""
                ptr_marker = " [ptr]" if var['is_ptr'] else ""
                click.echo(f"  {var['type']} {var['name']} in {var['scope']}{param_marker}{ptr_marker}")
                click.echo(f"    File: {file_short}")


# ==================== CVE Commands ====================

@cli.group()
@click.pass_context
def cve(ctx):
    """CVE impact analysis commands."""
    pass


@cve.command('import')
@click.argument('source')
@click.option('--description', '-d', type=str,
              help='CVE description text (if SOURCE is a CVE ID)')
@click.option('--severity', '-s', type=click.Choice(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']),
              default='MEDIUM', help='CVE severity level')
@click.option('--cvss', type=float, default=0.0, help='CVSS score (0-10)')
@click.pass_context
def cve_import(ctx, source, description, severity, cvss):
    """
    Import CVE from NVD JSON file or CVE ID with description.

    SOURCE: NVD JSON file path or CVE ID (e.g., CVE-2024-1234)

    Examples:

        # Import from NVD JSON file
        kgraph cve import nvd-2024.json

        # Import from CVE ID with description
        kgraph cve import CVE-2024-1234 -d "Buffer overflow in ext4_writepages" -s CRITICAL --cvss 9.8
    """
    config = ctx.obj['config']

    from src.module_e.cve_importer import CVEImporter

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        importer = CVEImporter(store, config.llm)

        # Check if source is a file or CVE ID
        if Path(source).exists():
            # Import from JSON file
            click.echo(f"Importing CVEs from {source}...")
            cves = importer.import_from_nvd_json(source)
            click.echo(f"✅ Imported {len(cves)} CVEs")
        else:
            # Import from CVE ID
            if not description:
                click.echo("❌ Error: --description is required when importing by CVE ID", err=True)
                raise click.Abort()

            click.echo(f"Importing CVE {source}...")
            cve = importer.import_cve_from_text(
                source,
                description,
                metadata={'severity': severity, 'cvss_score': cvss}
            )

            if cve:
                click.echo(f"✅ Imported CVE {source}")
                click.echo(f"   Function: {cve.affected_function}")
                click.echo(f"   Type: {cve.vulnerability_type}")
            else:
                click.echo(f"❌ Failed to import CVE {source}")
                raise click.Abort()


@cve.command('impact')
@click.argument('cve_id')
@click.option('--max-depth', type=int, default=5, help='Max depth for call chain traversal')
@click.pass_context
def cve_impact(ctx, cve_id, max_depth):
    """
    Analyze the impact of a CVE.

    CVE_ID: CVE identifier (e.g., CVE-2024-1234)

    Examples:

        kgraph cve impact CVE-2024-1234

        kgraph cve impact CVE-2024-1234 --max-depth 10
    """
    config = ctx.obj['config']

    from src.module_e.impact_analyzer import CVEImpactAnalyzer

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        analyzer = CVEImpactAnalyzer(store)

        click.echo(f"Analyzing impact for {cve_id}...")
        impact = analyzer.analyze_cve_impact(cve_id, max_depth=max_depth)

        if impact:
            report = analyzer.format_impact_report(impact)
            click.echo(report)
        else:
            click.echo(f"❌ CVE {cve_id} not found", err=True)
            raise click.Abort()


@cve.command('check')
@click.argument('cve_id')
@click.option('--kernel-version', '-k', required=True, type=str,
              help='Kernel version to check (e.g., 5.15, 6.1)')
@click.pass_context
def cve_check(ctx, cve_id, kernel_version):
    """
    Check if CVE affects a specific kernel version.

    CVE_ID: CVE identifier (e.g., CVE-2024-1234)

    Examples:

        kgraph cve check CVE-2024-1234 -k 5.15

        kgraph cve check CVE-2024-1234 --kernel-version 6.1
    """
    config = ctx.obj['config']

    from src.module_e.version_checker import VersionChecker

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        checker = VersionChecker(store, config.kernel.root)

        click.echo(f"Checking {cve_id} for kernel {kernel_version}...")
        result = checker.check_cve_version(cve_id, kernel_version)

        if result:
            report = checker.format_version_report(result)
            click.echo(report)
        else:
            click.echo(f"❌ Failed to check CVE {cve_id}", err=True)
            raise click.Abort()


@cve.command('test-gaps')
@click.argument('cve_id')
@click.pass_context
def cve_test_gaps(ctx, cve_id):
    """
    Analyze test coverage gaps for a CVE.

    CVE_ID: CVE identifier (e.g., CVE-2024-1234)

    Examples:

        kgraph cve test-gaps CVE-2024-1234
    """
    config = ctx.obj['config']

    from src.module_e.test_coverage import CVETestCoverage

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        analyzer = CVETestCoverage(store)

        click.echo(f"Analyzing test coverage for {cve_id}...")
        analysis = analyzer.analyze_cve_test_coverage(cve_id)

        if analysis:
            report = analyzer.format_coverage_report(analysis)
            click.echo(report)
        else:
            click.echo(f"❌ Failed to analyze test coverage for {cve_id}", err=True)
            raise click.Abort()


@cve.command('report')
@click.argument('cve_id')
@click.option('--kernel-version', '-k', type=str, help='Kernel version to check')
@click.option('--output', '-o', type=click.Path(), help='Output file (markdown)')
@click.pass_context
def cve_report(ctx, cve_id, kernel_version, output):
    """
    Generate a comprehensive CVE impact report.

    CVE_ID: CVE identifier (e.g., CVE-2024-1234)

    Examples:

        kgraph cve report CVE-2024-1234

        kgraph cve report CVE-2024-1234 -k 5.15

        kgraph cve report CVE-2024-1234 -k 5.15 -o report.md
    """
    config = ctx.obj['config']

    from src.module_e.cve_reporter import CVEReporter

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        reporter = CVEReporter(store, config.kernel.root)

        click.echo(f"Generating report for {cve_id}...")
        report = reporter.generate_cve_report(cve_id, kernel_version)

        if report:
            if output:
                with open(output, 'w') as f:
                    f.write(report)
                click.echo(f"✅ Report saved to {output}")
            else:
                click.echo(report)
        else:
            click.echo(f"❌ Failed to generate report for {cve_id}", err=True)
            raise click.Abort()


@cve.command('backport-checklist')
@click.option('--kernel-version', '-k', required=True, type=str,
              help='Target kernel version')
@click.option('--severity', '-s', type=click.Choice(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']),
              multiple=True, help='Filter by severity (can be specified multiple times)')
@click.option('--subsystem', type=str, help='Filter by subsystem (e.g., fs/ext4)')
@click.option('--output', '-o', type=click.Path(), help='Output file (markdown)')
@click.pass_context
def cve_backport_checklist(ctx, kernel_version, severity, subsystem, output):
    """
    Generate a backport checklist for CVEs.

    Examples:

        kgraph cve backport-checklist -k 5.15

        kgraph cve backport-checklist -k 5.15 -s CRITICAL -s HIGH

        kgraph cve backport-checklist -k 5.15 --subsystem fs/ext4 -o checklist.md
    """
    config = ctx.obj['config']

    from src.module_e.impact_analyzer import CVEImpactAnalyzer
    from src.module_e.cve_reporter import CVEReporter

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        # Get all CVEs
        impact_analyzer = CVEImpactAnalyzer(store)
        cves = impact_analyzer.get_all_cves()

        # Filter by severity
        if severity:
            cves = [c for c in cves if c.get('severity') in severity]

        # Filter by subsystem
        if subsystem:
            cves = [c for c in cves if subsystem in c.get('file_path', '')]

        if not cves:
            click.echo("No CVEs found matching criteria")
            return

        cve_ids = [c['id'] for c in cves]

        # Generate checklist
        reporter = CVEReporter(store, config.kernel.root)
        checklist = reporter.generate_backport_checklist(cve_ids, kernel_version, output)

        if not output:
            click.echo(checklist)


@cve.command('list')
@click.option('--severity', '-s', type=click.Choice(['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']),
              help='Filter by severity')
@click.option('--limit', '-l', type=int, default=20, help='Maximum number of CVEs to show')
@click.pass_context
def cve_list(ctx, severity, limit):
    """
    List all CVEs in the database.

    Examples:

        kgraph cve list

        kgraph cve list --severity CRITICAL

        kgraph cve list -s HIGH -s CRITICAL -l 50
    """
    config = ctx.obj['config']

    from src.module_e.impact_analyzer import CVEImpactAnalyzer

    with Neo4jGraphStore(config.neo4j.url, config.neo4j.user,
                          config.neo4j.password) as store:
        analyzer = CVEImpactAnalyzer(store)

        # Get CVEs
        if severity:
            cves = analyzer.get_cves_by_severity(severity)
        else:
            cves = analyzer.get_all_cves()

        # Display
        if cves:
            click.echo(f"\nFound {len(cves)} CVE(s)")
            click.echo("=" * 80)

            for cve in cves[:limit]:
                click.echo(f"\n{cve['id']}: {cve.get('affected_function', 'Unknown')}")
                click.echo(f"  Severity: {cve.get('severity', 'UNKNOWN')} (CVSS {cve.get('cvss_score', 0)})")
                click.echo(f"  Type: {cve.get('vulnerability_type', 'unknown')}")
                click.echo(f"  File: {cve.get('file_path', 'Unknown')}")

            if len(cves) > limit:
                click.echo(f"\n... and {len(cves) - limit} more")
        else:
            click.echo("No CVEs found")


# ==================== Version Command ====================

@cli.command()
@click.pass_context
def version(ctx):
    """Show version information."""
    click.echo("Kernel-GraphRAG Sentinel v0.4.0")
    click.echo("AI-powered Linux kernel code analysis")
    click.echo("\nv0.1.0 - Core functionality complete")
    click.echo("  ✅ Phase 1: Environment Setup")
    click.echo("  ✅ Phase 2: C Code Parser")
    click.echo("  ✅ Phase 3: Neo4j Graph Store")
    click.echo("  ✅ Phase 4: KUnit Test Mapper")
    click.echo("  ✅ Phase 5: Impact Analysis")
    click.echo("  ✅ Phase 6: CLI Interface")
    click.echo("  ✅ Phase 7: Visualization & Documentation")
    click.echo("\nv0.2.0 - Data Flow Analysis")
    click.echo("  ✅ Module D: Variable tracking & flow analysis")
    click.echo("  ✅ Neo4j data flow ingestion")
    click.echo("  ✅ CLI commands: ingest-dataflow, dataflow")
    click.echo("\nv0.4.0 - CVE Impact Analysis")
    click.echo("  ✅ Module E: CVE importer & parser")
    click.echo("  ✅ CVE impact analysis engine")
    click.echo("  ✅ Version checking & backport detection")
    click.echo("  ✅ Test coverage analysis for CVEs")
    click.echo("  ✅ CVE reporting & backport checklists")
    click.echo("  ✅ CLI commands: cve import, impact, check, report, ...")


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == '__main__':
    main()
