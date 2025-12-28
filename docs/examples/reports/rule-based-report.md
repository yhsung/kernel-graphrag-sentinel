================================================================================
IMPACT ANALYSIS: show_val_kb
================================================================================
File: /workspaces/ubuntu/linux-6.13/fs/proc/meminfo.c

SUMMARY
--------------------------------------------------------------------------------
  Direct callers:       49
  Indirect callers:     0
  Direct callees:       0
  Indirect callees:     0
  Direct test coverage: 0
  Indirect test coverage: 0
  Total call chains:    1

DIRECT CALLERS (functions that call this function)
--------------------------------------------------------------------------------
  1. meminfo_proc_show (meminfo.c:157)
  2. meminfo_proc_show (meminfo.c:119)
  3. meminfo_proc_show (meminfo.c:73)
  4. meminfo_proc_show (meminfo.c:64)
  5. meminfo_proc_show (meminfo.c:108)
  6. meminfo_proc_show (meminfo.c:128)
  7. meminfo_proc_show (meminfo.c:103)
  8. meminfo_proc_show (meminfo.c:127)
  9. meminfo_proc_show (meminfo.c:92)
  10. meminfo_proc_show (meminfo.c:151)
  11. meminfo_proc_show (meminfo.c:90)
  12. meminfo_proc_show (meminfo.c:131)
  13. meminfo_proc_show (meminfo.c:122)
  14. meminfo_proc_show (meminfo.c:66)
  15. meminfo_proc_show (meminfo.c:68)
  ... and 34 more

RISK ASSESSMENT
--------------------------------------------------------------------------------
  Risk Level: CRITICAL (widely used, no test coverage)

================================================================================