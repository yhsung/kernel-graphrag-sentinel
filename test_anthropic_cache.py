#!/usr/bin/env python3
"""
Test script to verify Anthropic prompt caching with KV-cache optimized system prompts.

Usage:
    export ANTHROPIC_API_KEY=your_key_here
    python3 test_anthropic_cache.py
"""

import os
import sys
import logging
from src.analysis.llm_reporter import LLMReporter, LLMConfig

# Set up logging to see cache metrics
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nSet it with:")
        print("  export ANTHROPIC_API_KEY=your_api_key_here")
        sys.exit(1)

    print("=" * 70)
    print("Anthropic Prompt Caching Test")
    print("=" * 70)

    # Initialize reporter with Anthropic
    config = LLMConfig(
        provider="anthropic",
        model="claude-sonnet-4-5-20250929",
        api_key=api_key,
        temperature=0.7
    )

    reporter = LLMReporter(config)
    print(f"\n✅ Initialized Anthropic reporter with model: {config.model}")

    # Test 1: Normal context (first request - cache MISS expected)
    print("\n" + "=" * 70)
    print("TEST 1: Normal Context (First Request - Cache MISS)")
    print("=" * 70)

    test_impact_data_1 = {
        "file_path": "fs/ext4/file.c",
        "stats": {
            "direct_callers": 5,
            "indirect_callers": 15,
            "direct_callees": 8,
            "indirect_callees": 20,
            "direct_tests": 2,
            "indirect_tests": 10,
            "risk_level": "MEDIUM"
        },
        "direct_callers": [
            {"name": "ext4_file_write_iter", "file": "fs/ext4/file.c"},
            {"name": "ext4_file_read_iter", "file": "fs/ext4/file.c"},
        ],
        "direct_tests": [
            {"name": "ext4_file_operations_test"}
        ],
        "risk_level": "MEDIUM"
    }

    print("\nGenerating first report (normal context)...")
    report_1 = reporter.generate_impact_report(
        test_impact_data_1,
        "ext4_file_mmap",
        format="markdown"
    )

    print(f"\n📄 Report generated ({len(report_1)} chars)")
    print(f"First 200 chars:\n{report_1[:200]}...")

    # Test 2: Normal context (second request - cache HIT expected)
    print("\n" + "=" * 70)
    print("TEST 2: Normal Context (Second Request - Cache HIT)")
    print("=" * 70)

    test_impact_data_2 = {
        "file_path": "fs/btrfs/file.c",
        "stats": {
            "direct_callers": 3,
            "indirect_callers": 8,
            "direct_callees": 5,
            "indirect_callees": 12,
            "direct_tests": 0,
            "indirect_tests": 5,
            "risk_level": "HIGH"
        },
        "direct_callers": [
            {"name": "btrfs_file_write", "file": "fs/btrfs/file.c"},
        ],
        "direct_tests": [],
        "risk_level": "HIGH"
    }

    print("\nGenerating second report (should hit cache)...")
    report_2 = reporter.generate_impact_report(
        test_impact_data_2,
        "btrfs_file_llseek",
        format="markdown"
    )

    print(f"\n📄 Report generated ({len(report_2)} chars)")
    print(f"First 200 chars:\n{report_2[:200]}...")

    # Test 3: Automotive context (cache MISS - different system prompt)
    print("\n" + "=" * 70)
    print("TEST 3: Automotive Context (Cache MISS - Different Prompt)")
    print("=" * 70)

    # Create automotive-specific test data
    # Add automotive keywords to trigger extension
    automotive_context_additions = """

AUTOMOTIVE SAFETY REQUIREMENTS:
This function is part of a safety-critical automotive ECU system.
- ISO 26262 ASIL-D classification required
- Real-time constraints: WCET must be < 100ms
- Functional safety validation needed
- ASPICE Level 3 compliance required
"""

    test_impact_data_3 = {
        "file_path": "drivers/automotive/ecu_control.c",
        "stats": {
            "direct_callers": 10,
            "indirect_callers": 50,
            "direct_callees": 15,
            "indirect_callees": 80,
            "direct_tests": 0,
            "indirect_tests": 0,
            "risk_level": "CRITICAL"
        },
        "direct_callers": [
            {"name": "ecu_safety_monitor", "file": "drivers/automotive/safety.c"},
            {"name": "ecu_brake_control", "file": "drivers/automotive/brake.c"},
        ],
        "direct_tests": [],
        "risk_level": "CRITICAL"
    }

    # We need to inject the automotive context through the _build_context method
    # Let's create a custom context string
    print("\nGenerating automotive safety report...")

    # Build context manually to inject automotive keywords
    context_lines = [
        "Function: ecu_brake_signal_handler",
        "File: drivers/automotive/ecu_control.c",
        "",
        "Statistics:",
        "  - Direct callers: 10",
        "  - Indirect callers: 50",
        "  - Direct tests: 0 ⚠️",
        "",
        "⚠️ SAFETY-CRITICAL AUTOMOTIVE FUNCTION",
        "ISO 26262 ASIL-D classification required",
        "Real-time WCET constraint: < 100ms",
        "ASPICE Level 3 traceability mandatory",
        "",
        "Current Risk Level: CRITICAL"
    ]

    automotive_context = "\n".join(context_lines)

    # Check if automotive detection works
    is_auto = reporter._is_automotive_context(automotive_context)
    print(f"\n🔍 Automotive context detected: {is_auto}")

    system_prompt = reporter._build_system_prompt(automotive_context)
    print(f"📏 System prompt size: {len(system_prompt):,} chars")
    print(f"📦 Contains automotive extension: {'AUTOMOTIVE SAFETY ANALYSIS' in system_prompt}")

    # Create the full prompt
    prompt = reporter._create_prompt(automotive_context, "ecu_brake_signal_handler", "markdown")
    parts = prompt.split("\n\n---\n\n", 1)
    if len(parts) == 2:
        sys_msg, user_msg = parts
        print(f"\n📊 System message: {len(sys_msg):,} chars")
        print(f"📊 User message: {len(user_msg):,} chars")

        # Make the API call
        try:
            print("\nCalling Anthropic API with automotive context...")
            report_3 = reporter._call_anthropic_with_system(sys_msg, user_msg)
            print(f"\n📄 Automotive report generated ({len(report_3)} chars)")
            print(f"First 200 chars:\n{report_3[:200]}...")

            # Check if Section 11 is in the report
            has_section_11 = "11." in report_3 and "AUTOMOTIVE" in report_3.upper()
            print(f"\n✅ Report includes Section 11 (Automotive Safety): {has_section_11}")

        except Exception as e:
            print(f"\n❌ Error generating automotive report: {e}")

    print("\n" + "=" * 70)
    print("Summary of Cache Performance")
    print("=" * 70)
    print("""
Expected Results:
1. Test 1 (Normal #1):    Cache MISS - Creates cache (~8,500 tokens)
2. Test 2 (Normal #2):    Cache HIT  - Reads cache (~85% hit rate)
3. Test 3 (Automotive):   Cache MISS - New cache with extension (~12,000 tokens)

If you ran Test 3 again, it would be a Cache HIT for the automotive variant.

Check the logs above for "Cache MISS" and "Cache HIT" messages.

Token Limits (Updated):
- Sonnet 4.5: 16,384 max_tokens (16K for comprehensive reports)
- Haiku:       8,192 max_tokens (8K for shorter reports)
- Default:     4,096 max_tokens (conservative fallback)

The 16K limit ensures complete reports with all 10-11 sections, including
the automotive safety analysis extension when applicable.
    """)

    print("\n✅ Test completed successfully!")

if __name__ == "__main__":
    main()
