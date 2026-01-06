# Implementation Plan v0.6.0 - Git History Integration

**Status**: Ready for Review
**Timeline**: 5 weeks
**Complexity**: High (integrates with multiple existing modules)

---

## Executive Summary

**Problem**: Kernel developers lose time switching between git commands and code analysis tools. Questions like "When was this function introduced?", "Who introduced this bug?", and "What changed in this commit?" require 5-10 minutes of manual investigation.

**Solution**: Module G - Git History Integration that brings git repository metadata into Neo4j, enabling temporal queries alongside existing code analysis.

**Success Metric**: Reduce "git blame + code review" workflow from 5-10 minutes to <30 seconds

---

## Real-World Problems Solved

### 1. Bug Investigation - "Who introduced this?"
**Before**: Manual git blame, git show, git log - 5-10 minutes
**After**: `kgraph git blame ext4_writepages` - 3-5 seconds with full context

### 2. Code Review - "What does this commit change?"
**Before**: Manual git show + individual kgraph analyze - 10-15 minutes
**After**: `kgraph git commit 7a8b9c1d --analyze` - 5-10 seconds with risk assessment

### 3. Bisect Helper - "Find the bug-introducing commit"
**Before**: 2-4 hours of compile/test cycles
**After**: Accelerated analysis at each bisect step - reduces to 1-2 hours

### 4. Code Evolution - "How did this function change?"
**Before**: Manual git log -p parsing - 30-60 minutes
**After**: `kgraph git timeline ext4_writepages` - 5-10 seconds with visualization

---

## Module G Architecture

### New Components

```
src/module_g/
├── __init__.py
├── schema.py                    # Git-specific graph schema
├── git_extractor.py             # Extract git metadata
├── blame_mapper.py              # Map lines to commits
├── commit_analyzer.py           # Analyze commit changes
├── evolution_tracker.py         # Track function evolution
├── timeline_generator.py        # Generate visual timelines
├── author_analytics.py          # Code ownership metrics
└── bisect_helper.py             # Git bisect assistance
```

### Neo4j Schema Extensions

**New Node Types**:
- `GitCommit` - Commit metadata (hash, author, timestamp, message)
- `GitBranch` - Branch information
- `GitTag` - Release tags
- `GitAuthor` - Aggregated author stats

**New Relationships**:
- `DEFINES_FUNCTION` - Commit → Function (created/modified/deleted)
- `MODIFIES_FILE` - Commit → File (with line counts)
- `AUTHORED_COMMIT` - Author → Commit
- `FIXES_CVE` - Commit → CVE (links to Module E)

---

## 6 New CLI Commands

### 1. `kgraph git log <function>` - Show Function History
```bash
kgraph git log ext4_writepages
# Shows all commits that modified this function
# With author, date, complexity changes
```

### 2. `kgraph git blame <file:line>` - Git Blame with Context
```bash
kgraph git blame fs/ext4/inode.c:2145
# Shows commit info + function context + evolution
```

### 3. `kgraph git commit <hash>` - Show What Changed
```bash
kgraph git commit 7a8b9c1d --analyze
# Shows files changed + functions modified + risk assessment
```

### 4. `kgraph git timeline <function>` - Visual Timeline
```bash
kgraph git timeline ext4_writepages --stats
# ASCII timeline showing function evolution over time
```

### 5. `kgraph git authors <subsystem>` - Code Ownership
```bash
kgraph git authors fs/ext4
# Shows top contributors with ownership percentages
```

### 6. `kgraph git bisect-helper <bug>` - Bisect Assistance
```bash
kgraph git bisect-helper "ext4: writepage hang on ENOMEM"
# Analyzes current state, suggests verdict (good/bad)
```

---

## 5-Week Implementation Plan

### Week 1: Git Extraction & Storage
- Create git schema (GitCommit, GitBranch, GitTag, GitAuthor nodes)
- Implement GitExtractor (git log, git show, git blame)
- CLI: `kgraph git ingest`
- Test: Extract 1000+ commits from fs/ext4

**Files Created**:
- src/module_g/schema.py
- src/module_g/git_extractor.py
- tests/test_module_g_git_extractor.py

### Week 2: Blame & Commit Analysis
- Implement BlameMapper (git blame integration)
- Implement CommitAnalyzer (parse diffs, link to functions)
- CLI: `kgraph git blame`, `kgraph git commit`
- Test: Real commit analysis with impact calculation

**Files Created**:
- src/module_g/blame_mapper.py
- src/module_g/commit_analyzer.py
- tests/test_module_g_blame_mapper.py
- tests/test_module_g_commit_analyzer.py

### Week 3: Evolution Tracking
- Implement EvolutionTracker (git log -S, function history)
- Implement TimelineGenerator (ASCII/markdown/Mermaid)
- CLI: `kgraph git timeline`
- Test: Timeline generation for real functions

**Files Created**:
- src/module_g/evolution_tracker.py
- src/module_g/timeline_generator.py
- tests/test_module_g_evolution_tracker.py

### Week 4: Author Analytics & Bisect Helper
- Implement AuthorAnalytics (code ownership metrics)
- Implement BisectHelper (bisect acceleration)
- CLI: `kgraph git authors`, `kgraph git bisect-helper`
- Test: Real bug investigation scenarios

**Files Created**:
- src/module_g/author_analytics.py
- src/module_g/bisect_helper.py
- tests/test_module_g_author_analytics.py
- tests/test_module_g_bisect_helper.py

### Week 5: Integration & Polish
- Integration with Module E (CVE → fix commits)
- Integration with Module A (add blame to Function nodes)
- Documentation (user guide, 3 examples)
- Performance optimization (caching, incremental extraction)

**Files Modified**:
- src/module_e/impact_analyzer.py (add fix commit info)
- src/module_a/extractor.py (add blame info)
- src/main.py (add all 6 git commands)

**Documentation Created**:
- docs/git_analysis_guide.md
- examples/git_analysis_cve_tracking.md
- examples/git_analysis_bisect_workflow.md
- examples/git_analysis_commit_review.md

---

## Critical Integration Points

### 1. Module A Integration
**File**: `src/module_a/extractor.py`
**Change**: Add `last_modified_commit` property to FunctionNode
```python
if self.git_repo:
    blame_info = self.get_blame_info(func_node, file_path)
    func_node.last_modified_commit = blame_info['commit']
```

### 2. Module B Integration
**File**: `src/module_b/graph_store.py`
**Change**: Add methods for git node upsert
```python
def upsert_git_commit(self, commit_node):
    # MERGE GitCommit node
def link_commit_to_function(self, commit_hash, function_id):
    # CREATE DEFINES_FUNCTION relationship
```

### 3. Module E Integration
**File**: `src/module_e/impact_analyzer.py`
**Change**: Link CVEs to fix commits
```python
def get_cve_fix_commit(self, cve_id):
    # MATCH (cve:CVE)<-[:FIXES_CVE]-(commit:GitCommit)
```

---

## Performance Considerations

### Challenge: Git Operations Are Slow
**Solutions**:
1. **Caching**: Cache blame results (TTL: 1 day)
2. **Incremental Extraction**: Only new commits since last run
3. **Lazy Loading**: Extract on-demand, not all upfront
4. **Parallel Processing**: Extract multiple files in parallel
5. **Query Optimization**: Use Neo4j indexes, paginate results

### Challenge: Database Size (1M+ commits)
**Solutions**:
1. **Selective Extraction**: Only specific subsystems/branches
2. **Date Filtering**: Only last 5 years by default
3. **Aggregation**: Merge old commits (>5 years) by month

---

## Success Metrics

### Functional Metrics
| Metric | Target |
|--------|--------|
| Commit extraction | 1000 commits / 30 sec |
| Blame query | <5 seconds |
| Timeline generation | <3 seconds |
| Test coverage | 80%+ |

### User Feedback
- Reduced git + code review time from 5-10 min to <30 sec ✓
- Bisect helper reduces investigation by 50%+ ✓
- Timeline helps understand evolution ✓

### Adoption
- 10+ kernel teams using git features
- 500+ functions analyzed
- 50+ commits reviewed
- 20+ bugs investigated

---

## Dependencies

### New Python Packages
- `GitPython` >= 3.1.0 (for git operations)

### System Requirements
- Git >= 2.30.0 (existing)
- Neo4j >= 4.4.0 (existing)

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Git operations too slow | HIGH | Caching, incremental extraction, lazy loading |
| Database size explosion | HIGH | Selective extraction, aggregation |
| Integration breaks existing | MEDIUM | Extensive testing, feature flags |
| Performance on large repos | HIGH | Pagination, parallel processing |

---

## Critical Files

**Must Create** (9 new modules):
1. src/module_g/schema.py - Git graph schema
2. src/module_g/git_extractor.py - Core git extraction
3. src/module_g/blame_mapper.py - Git blame integration
4. src/module_g/commit_analyzer.py - Commit analysis
5. src/module_g/evolution_tracker.py - History tracking
6. src/module_g/timeline_generator.py - Visualization
7. src/module_g/author_analytics.py - Ownership metrics
8. src/module_g/bisect_helper.py - Bisect assistance
9. src/main.py - Add 6 new CLI commands

**Must Modify** (3 integration points):
1. src/module_a/extractor.py - Add blame info
2. src/module_b/graph_store.py - Git node upsert
3. src/module_e/impact_analyzer.py - CVE-commit links

**Documentation**:
1. docs/git_analysis_guide.md - User guide
2. examples/git_analysis_*.md - 3 real-world examples

---

## Example Use Case

### CVE Investigation (End-to-End)

```bash
# Step 1: Import CVE (existing)
$ kgraph cve import CVE-2024-1234 -d "Buffer overflow" -s CRITICAL

# Step 2: Check impact (existing)
$ kgraph cve impact CVE-2024-1234
# Shows: ext4_writepages affects 23 callers

# Step 3: Find when bug introduced (NEW)
$ kgraph git blame ext4_writepages
# Introduced: 2019-03-20 (commit a1b2c3d4)
# Fixed: 2024-02-15 (commit 7a8b9c1d)

# Step 4: Analyze fix commit (NEW)
$ kgraph git commit 7a8b9c1d --analyze
# Risk: HIGH (23 callers)
# Recommendation: Backport to 5.15, 6.1

Result: Complete CVE investigation in <2 minutes (vs 30+ min manually)
```

---

## Next Steps

1. ✅ Plan approved by user
2. Start with Week 1: Git extraction & storage
3. Build incrementally, test each module
4. Integrate with existing modules in Week 5
5. Release v0.6.0 with complete documentation

**Ready to proceed with implementation?**
