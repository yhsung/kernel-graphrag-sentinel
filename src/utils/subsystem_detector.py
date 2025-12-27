"""
Subsystem Boundary Detector
Automatically detects file boundaries and metadata for kernel subsystems.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class SubsystemInfo:
    """Information about a detected subsystem."""

    def __init__(
        self,
        name: str,
        path: str,
        source_files: List[str],
        header_files: List[str],
        test_files: List[str],
        kconfig_files: List[str],
        makefile_files: List[str],
    ):
        self.name = name
        self.path = path
        self.source_files = source_files
        self.header_files = header_files
        self.test_files = test_files
        self.kconfig_files = kconfig_files
        self.makefile_files = makefile_files

    @property
    def total_files(self) -> int:
        """Total number of files in the subsystem."""
        return (
            len(self.source_files)
            + len(self.header_files)
            + len(self.test_files)
            + len(self.kconfig_files)
            + len(self.makefile_files)
        )

    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "path": self.path,
            "source_files": self.source_files,
            "header_files": self.header_files,
            "test_files": self.test_files,
            "kconfig_files": self.kconfig_files,
            "makefile_files": self.makefile_files,
            "statistics": {
                "total_files": self.total_files,
                "source_count": len(self.source_files),
                "header_count": len(self.header_files),
                "test_count": len(self.test_files),
                "kconfig_count": len(self.kconfig_files),
                "makefile_count": len(self.makefile_files),
            },
        }

    def __repr__(self) -> str:
        return (
            f"SubsystemInfo(name={self.name}, "
            f"files={self.total_files}, "
            f"sources={len(self.source_files)}, "
            f"headers={len(self.header_files)}, "
            f"tests={len(self.test_files)})"
        )


class SubsystemDetector:
    """Detects kernel subsystem boundaries and file structure."""

    def __init__(self, kernel_root: str):
        """
        Initialize the subsystem detector.

        Args:
            kernel_root: Path to the Linux kernel source root
        """
        self.kernel_root = Path(kernel_root)
        if not self.kernel_root.exists():
            raise ValueError(f"Kernel root does not exist: {kernel_root}")

    def detect_subsystem(
        self,
        subsystem_path: str,
        recursive: bool = False,
        include_subdirs: bool = False,
    ) -> SubsystemInfo:
        """
        Detect subsystem boundaries and collect file information.

        Args:
            subsystem_path: Relative path to subsystem (e.g., "fs/ext4")
            recursive: Include files from subdirectories
            include_subdirs: Include separate subdirectory analysis

        Returns:
            SubsystemInfo object with detected files
        """
        subsystem_dir = self.kernel_root / subsystem_path
        if not subsystem_dir.exists():
            raise ValueError(f"Subsystem path does not exist: {subsystem_dir}")

        # Extract subsystem name from path
        subsystem_name = Path(subsystem_path).name

        logger.info(f"Detecting subsystem boundaries for: {subsystem_path}")

        # Collect files
        source_files = self._find_source_files(subsystem_dir, recursive)
        header_files = self._find_header_files(subsystem_dir, recursive)
        test_files = self._find_test_files(subsystem_dir, recursive)
        kconfig_files = self._find_kconfig_files(subsystem_dir, recursive)
        makefile_files = self._find_makefile_files(subsystem_dir, recursive)

        logger.info(
            f"Detected: {len(source_files)} source, "
            f"{len(header_files)} headers, "
            f"{len(test_files)} tests"
        )

        return SubsystemInfo(
            name=subsystem_name,
            path=str(subsystem_path),
            source_files=sorted(source_files),
            header_files=sorted(header_files),
            test_files=sorted(test_files),
            kconfig_files=sorted(kconfig_files),
            makefile_files=sorted(makefile_files),
        )

    def _find_source_files(
        self, directory: Path, recursive: bool = False
    ) -> List[str]:
        """
        Find all C source files (.c) excluding test files.

        Args:
            directory: Directory to search
            recursive: Search subdirectories

        Returns:
            List of absolute paths to source files
        """
        pattern = "**/*.c" if recursive else "*.c"
        c_files = []

        for file_path in directory.glob(pattern):
            # Exclude test files (they're handled separately)
            if self._is_test_file(file_path):
                continue

            # Exclude build artifacts
            if "built-in" in file_path.name or "generated" in str(file_path):
                continue

            c_files.append(str(file_path))

        return c_files

    def _find_header_files(
        self, directory: Path, recursive: bool = False
    ) -> List[str]:
        """
        Find all header files (.h).

        Args:
            directory: Directory to search
            recursive: Search subdirectories

        Returns:
            List of absolute paths to header files
        """
        pattern = "**/*.h" if recursive else "*.h"
        h_files = []

        for file_path in directory.glob(pattern):
            # Exclude build artifacts
            if "generated" in str(file_path):
                continue

            h_files.append(str(file_path))

        return h_files

    def _find_test_files(
        self, directory: Path, recursive: bool = False
    ) -> List[str]:
        """
        Find all KUnit test files (*-test.c, *_test.c).

        Args:
            directory: Directory to search
            recursive: Search subdirectories

        Returns:
            List of absolute paths to test files
        """
        pattern = "**/*.c" if recursive else "*.c"
        test_files = []

        for file_path in directory.glob(pattern):
            if self._is_test_file(file_path):
                test_files.append(str(file_path))

        return test_files

    def _find_kconfig_files(
        self, directory: Path, recursive: bool = False
    ) -> List[str]:
        """
        Find Kconfig and .kunitconfig files.

        Args:
            directory: Directory to search
            recursive: Search subdirectories

        Returns:
            List of absolute paths to Kconfig files
        """
        kconfig_files = []

        # Find Kconfig
        kconfig_patterns = ["Kconfig*", ".kunitconfig", "kunitconfig"]

        for pattern in kconfig_patterns:
            if recursive:
                pattern = f"**/{pattern}"

            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    kconfig_files.append(str(file_path))

        return kconfig_files

    def _find_makefile_files(
        self, directory: Path, recursive: bool = False
    ) -> List[str]:
        """
        Find Makefile and Kbuild files.

        Args:
            directory: Directory to search
            recursive: Search subdirectories

        Returns:
            List of absolute paths to Makefile files
        """
        makefile_files = []

        makefile_patterns = ["Makefile*", "Kbuild"]

        for pattern in makefile_patterns:
            if recursive:
                pattern = f"**/{pattern}"

            for file_path in directory.glob(pattern):
                if file_path.is_file():
                    makefile_files.append(str(file_path))

        return makefile_files

    def _is_test_file(self, file_path: Path) -> bool:
        """
        Determine if a file is a test file.

        Args:
            file_path: Path to check

        Returns:
            True if file is a test file
        """
        name = file_path.name

        # Common KUnit test patterns
        test_patterns = [
            "-test.c",
            "_test.c",
            "test-",
            "test_",
        ]

        return any(pattern in name for pattern in test_patterns)

    def list_subsystems(
        self, top_level_dir: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        List all potential subsystems in the kernel tree.

        Args:
            top_level_dir: Limit search to specific top-level directory (e.g., "fs", "net")

        Returns:
            List of dictionaries with subsystem paths and names
        """
        search_root = self.kernel_root

        if top_level_dir:
            search_root = self.kernel_root / top_level_dir
            if not search_root.exists():
                raise ValueError(f"Top-level directory not found: {top_level_dir}")

        subsystems = []

        # Look for directories with Kconfig or Makefile (indicates subsystem)
        for kconfig_path in search_root.glob("**/Kconfig"):
            subsystem_dir = kconfig_path.parent

            # Skip include directories (just headers)
            if "include" in str(subsystem_dir):
                continue

            # Get relative path from kernel root
            rel_path = subsystem_dir.relative_to(self.kernel_root)

            # Check if it has .c files (actual code, not just config)
            if list(subsystem_dir.glob("*.c")):
                subsystems.append(
                    {
                        "path": str(rel_path),
                        "name": subsystem_dir.name,
                        "full_path": str(subsystem_dir),
                    }
                )

        return sorted(subsystems, key=lambda x: x["path"])

    def get_subsystem_statistics(self, subsystem_path: str) -> Dict:
        """
        Get comprehensive statistics for a subsystem.

        Args:
            subsystem_path: Relative path to subsystem

        Returns:
            Dictionary with detailed statistics
        """
        info = self.detect_subsystem(subsystem_path, recursive=False)

        # Count lines of code
        total_lines = 0
        source_lines = {}

        for source_file in info.source_files:
            try:
                with open(source_file, "r", errors="ignore") as f:
                    lines = len(f.readlines())
                    source_lines[source_file] = lines
                    total_lines += lines
            except Exception as e:
                logger.warning(f"Could not read {source_file}: {e}")

        return {
            "name": info.name,
            "path": info.path,
            "file_counts": {
                "source_files": len(info.source_files),
                "header_files": len(info.header_files),
                "test_files": len(info.test_files),
                "kconfig_files": len(info.kconfig_files),
                "makefile_files": len(info.makefile_files),
                "total_files": info.total_files,
            },
            "lines_of_code": {
                "total": total_lines,
                "average_per_file": total_lines // max(len(info.source_files), 1),
                "largest_file": max(source_lines.items(), key=lambda x: x[1])
                if source_lines
                else None,
            },
            "has_tests": len(info.test_files) > 0,
            "has_kconfig": len(info.kconfig_files) > 0,
        }


def detect_subsystem_boundaries(
    kernel_root: str,
    subsystem_path: str,
    recursive: bool = False,
) -> Dict:
    """
    Convenience function to detect subsystem boundaries.

    Args:
        kernel_root: Path to kernel source root
        subsystem_path: Relative path to subsystem (e.g., "fs/ext4")
        recursive: Include subdirectories

    Returns:
        Dictionary with subsystem information
    """
    detector = SubsystemDetector(kernel_root)
    info = detector.detect_subsystem(subsystem_path, recursive=recursive)
    return info.to_dict()


if __name__ == "__main__":
    import sys
    import json

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python subsystem_detector.py <subsystem_path>")
        print("  python subsystem_detector.py --list [top_level_dir]")
        print()
        print("Examples:")
        print("  python subsystem_detector.py fs/ext4")
        print("  python subsystem_detector.py fs/btrfs")
        print("  python subsystem_detector.py --list fs")
        sys.exit(1)

    kernel_root = os.getenv("KERNEL_ROOT", "/workspaces/ubuntu/linux-6.13")
    detector = SubsystemDetector(kernel_root)

    if sys.argv[1] == "--list":
        # List all subsystems
        top_level = sys.argv[2] if len(sys.argv) > 2 else None
        subsystems = detector.list_subsystems(top_level)

        print(f"Found {len(subsystems)} subsystems:")
        for sub in subsystems:
            print(f"  {sub['path']}")

    elif sys.argv[1] == "--stats":
        # Show statistics
        subsystem_path = sys.argv[2] if len(sys.argv) > 2 else "fs/ext4"
        stats = detector.get_subsystem_statistics(subsystem_path)
        print(json.dumps(stats, indent=2))

    else:
        # Detect specific subsystem
        subsystem_path = sys.argv[1]
        info = detector.detect_subsystem(subsystem_path, recursive=False)

        print(f"\n{info}")
        print(f"\nSource files ({len(info.source_files)}):")
        for f in info.source_files:
            print(f"  {Path(f).name}")

        if info.test_files:
            print(f"\nTest files ({len(info.test_files)}):")
            for f in info.test_files:
                print(f"  {Path(f).name}")

        if info.kconfig_files:
            print(f"\nKconfig files ({len(info.kconfig_files)}):")
            for f in info.kconfig_files:
                print(f"  {Path(f).name}")

        # Convert to dict and print JSON
        print(f"\nDetailed information:")
        print(json.dumps(info.to_dict(), indent=2))
