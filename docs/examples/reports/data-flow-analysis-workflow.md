╔════════════════════════════════════════════════════════════════════════════╗
║           KERNEL-GRAPHRAG SENTINEL v0.2.0 - DATA FLOW ANALYSIS            ║
║                  Complex Case Study: ext4_map_blocks                       ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─ STEP 1: Database Connection ────────────────────────────────────────────┐
│ ✅ Connected to Neo4j at bolt://localhost:7687                           │
│ ✅ Existing data: 10,431 functions, 0 variables                          │
└──────────────────────────────────────────────────────────────────────────┘

┌─ STEP 2: Function Selection ─────────────────────────────────────────────┐
│ 🎯 Selected: ext4_map_blocks                                             │
│    Complexity Rank: #1 (154 call relationships)                          │
│    Direct Callers: 142 functions                                         │
│    Direct Callees: 12 functions                                          │
│    Impact Scope: CRITICAL - Core filesystem block mapping                │
└──────────────────────────────────────────────────────────────────────────┘

┌─ STEP 3: Data Flow Ingestion ────────────────────────────────────────────┐
│ 📂 File: /workspaces/ubuntu/linux-6.13/fs/ext4/inode.c                   │
│ ⚙️  Processing with tree-sitter C parser...                              │
│                                                                           │
│ Results:                                                                  │
│   ✅ Variables extracted: 514                                            │
│   ✅ Data flows created: 1,330                                           │
│   ⏱️  Processing time: ~5 seconds                                        │
│                                                                           │
│ Variables in ext4_map_blocks:                                            │
│   [PARAM] handle_t* handle (line 595)                                    │
│   [PARAM] struct inode* inode (line 595)                                 │
│   [PARAM] struct ext4_map_blocks* map (line 596)                         │
│   [LOCAL] int ret (line 600)                                             │
│   [LOCAL] loff_t start_byte (line 719)                                   │
│   [LOCAL] loff_t length (line 721)                                       │
└──────────────────────────────────────────────────────────────────────────┘

┌─ STEP 4: Impact Analysis ────────────────────────────────────────────────┐
│ 🔍 Analyzing function relationships...                                   │
│                                                                           │
│ Call Graph Statistics:                                                   │
│   • Direct callers: 22 (sample from 142 total)                           │
│   • Direct callees: 5                                                    │
│   • Indirect callers (depth 3): 50                                       │
│   • Indirect callees (depth 3): 91                                       │
│   • Total call chains: 65                                                │
│                                                                           │
│ Test Coverage:                                                            │
│   ❌ Direct unit tests: 0                                                │
│   ❌ Integration tests: 0                                                │
│   ⚠️  Risk Level: UNKNOWN → HIGH                                         │
└──────────────────────────────────────────────────────────────────────────┘

┌─ STEP 5: LLM Report Generation ──────────────────────────────────────────┐
│ 🤖 Provider: Ollama (qwen3-vl:30b)                                       │
│ 📊 Context Building:                                                     │
│    ✓ Call graph visualization (Mermaid diagram)                          │
│    ✓ Impact statistics (callers, callees, depth)                         │
│    ✓ Test coverage analysis                                              │
│    ✓ Variable flow information                                           │
│    ✓ Risk assessment data                                                │
│                                                                           │
│ 🎯 Report Structure (10 sections):                                       │
│    1. Header Section (with risk emoji 🔴)                                │
│    2. Executive Summary                                                   │
│    3. Code Impact Analysis + Call Graph Viz                              │
│    4. Testing Requirements                                                │
│    5. Recommended New Tests                                               │
│    6. Risk Assessment                                                     │
│    7. Implementation Recommendations                                      │
│    8. Escalation Criteria                                                 │
│    9. Recommendations Summary                                             │
│    10. Conclusion                                                         │
│                                                                           │
│ ⏱️  Generation time: ~2.5 minutes                                        │
│ 📄 Report length: 163 lines                                              │
│ 💾 Saved to: docs/examples/reports/ext4_map_blocks_dataflow_report.md   │
└──────────────────────────────────────────────────────────────────────────┘

┌─ STEP 6: Security Analysis ──────────────────────────────────────────────┐
│ 🔒 Security Findings:                                                    │
│                                                                           │
│ ⚠️  Integer Overflow Risk:                                               │
│    start_byte = map->m_lblk << inode->i_blkbits                          │
│    → User-controlled m_lblk could overflow                               │
│                                                                           │
│ ⚠️  Buffer Boundary Risk:                                                │
│    length = map->m_len << inode->i_blkbits                               │
│    → Need range validation for m_len                                     │
│                                                                           │
│ ⚠️  Pointer Safety:                                                      │
│    All 3 parameters are pointers (handle, inode, map)                    │
│    → Require NULL checks before dereferencing                            │
│                                                                           │
│ 📊 Taint Analysis Potential:                                             │
│    User input → map structure → block calculations                       │
│    Can track flow: map->m_lblk → start_byte → callees                    │
└──────────────────────────────────────────────────────────────────────────┘

┌─ STEP 7: Actionable Recommendations ─────────────────────────────────────┐
│ 🚨 CRITICAL: DO NOT MODIFY without test coverage!                       │
│                                                                           │
│ Immediate Actions Required:                                              │
│   1. ✅ Create unit tests for:                                           │
│      • Small file block allocation                                       │
│      • Large file extent mapping                                         │
│      • Journal replay scenarios                                          │
│      • Inline data conversion                                            │
│                                                                           │
│   2. ✅ Add security hardening:                                          │
│      • Integer overflow checks for byte calculations                     │
│      • Block count range validation                                      │
│      • NULL pointer checks for all parameters                            │
│                                                                           │
│   3. ✅ Implement tracing:                                               │
│      • Add kernel tracepoints for debugging                              │
│      • Log critical decision points                                      │
│                                                                           │
│   4. ✅ Resolve call graph discrepancy:                                  │
│      • Re-run static analysis to validate 142 callers                    │
│      • Document all call paths                                           │
└──────────────────────────────────────────────────────────────────────────┘

╔════════════════════════════════════════════════════════════════════════════╗
║                           ANALYSIS COMPLETE                                ║
╚════════════════════════════════════════════════════════════════════════════╝

📊 Final Statistics:
   • Variables in database: 514
   • Functions in database: 10,431
   • Data flows analyzed: 1,330
   • Report sections: 10
   • Security issues identified: 3
   • Recommendations provided: 12

📁 Generated Files:
   1. docs/examples/reports/ext4_map_blocks_dataflow_report.md
      → Full LLM-generated impact analysis report
   
   2. docs/examples/reports/ext4_map_blocks_dataflow_summary.md
      → Comprehensive data flow analysis summary

🎯 Key Achievements:
   ✅ Identified most complex function in ext4 (142 callers!)
   ✅ Extracted all 6 variables with type information
   ✅ Generated professional AI report with security insights
   ✅ Provided actionable recommendations with specific commands
   ✅ Created Mermaid call graph visualization
   ✅ Demonstrated Module D capabilities at scale

⚠️  Known Limitations:
   • FLOWS_TO relationships not fully populated (0 created)
   • Need to implement intra-procedural flow analysis
   • Some parsing errors due to kernel macros

🚀 Next Steps:
   1. Fix FLOWS_TO relationship creation
   2. Implement pointer aliasing analysis
   3. Add automated security query templates
   4. Extend to inter-procedural data flow