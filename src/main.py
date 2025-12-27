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

                    reporter = LLMReporter(llm_config)

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


@cli.command()
@click.pass_context
def version(ctx):
    """Show version information."""
    click.echo("Kernel-GraphRAG Sentinel v0.1.0")
    click.echo("AI-powered Linux kernel code analysis")
    click.echo("\nPhases completed: 6/7 (86%)")
    click.echo("  ✅ Phase 1: Environment Setup")
    click.echo("  ✅ Phase 2: C Code Parser")
    click.echo("  ✅ Phase 3: Neo4j Graph Store")
    click.echo("  ✅ Phase 4: KUnit Test Mapper")
    click.echo("  ✅ Phase 5: Impact Analysis")
    click.echo("  ✅ Phase 6: CLI Interface")


def main():
    """Entry point for the CLI."""
    cli(obj={})


if __name__ == '__main__':
    main()
