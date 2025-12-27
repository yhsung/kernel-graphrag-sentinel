"""
Module A: C Preprocessor for Kernel Code
Handles macro expansion using gcc -E (cpp) with kernel-specific configurations.
"""

import subprocess
import os
import re
from pathlib import Path
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class KernelPreprocessor:
    """Preprocesses Linux kernel C source files to expand macros."""

    def __init__(self, kernel_root: str):
        """
        Initialize the preprocessor.

        Args:
            kernel_root: Path to the Linux kernel source root
        """
        self.kernel_root = Path(kernel_root)
        if not self.kernel_root.exists():
            raise ValueError(f"Kernel root does not exist: {kernel_root}")

        self.include_paths = self._extract_include_paths()
        self.kernel_defines = self._get_kernel_defines()

    def _extract_include_paths(self) -> List[str]:
        """
        Extract include paths from kernel source tree.

        Returns:
            List of include directory paths
        """
        include_paths = [
            self.kernel_root / "include",
            self.kernel_root / "include" / "uapi",
            self.kernel_root / "arch" / "arm64" / "include",
            self.kernel_root / "arch" / "arm64" / "include" / "generated",
            self.kernel_root / "arch" / "arm64" / "include" / "uapi",
            self.kernel_root / "arch" / "arm64" / "include" / "generated" / "uapi",
        ]

        # Add x86 architecture includes as fallback
        arch_include = self.kernel_root / "arch" / "x86" / "include"
        if arch_include.exists():
            include_paths.append(arch_include)
            include_paths.append(arch_include / "generated")
            include_paths.append(arch_include / "uapi")

        # Add asm-generic as fallback
        asm_generic = self.kernel_root / "include" / "asm-generic"
        if asm_generic.exists():
            include_paths.append(asm_generic)

        # Filter to existing paths
        return [str(p) for p in include_paths if p.exists()]

    def _get_kernel_defines(self) -> List[str]:
        """
        Get kernel-specific preprocessor defines.

        Returns:
            List of -D flags for gcc
        """
        return [
            "-D__KERNEL__",
            "-DCONFIG_64BIT",
            "-DCONFIG_SMP",
            "-DKBUILD_MODNAME=ext4",  # Default to ext4, can be customized
            "-D__KERNEL_PRINTK__",
            "-D__linux__",
        ]

    def preprocess_file(self, source_file: str, preserve_lines: bool = True) -> str:
        """
        Preprocess a C source file to expand macros.

        Args:
            source_file: Path to the C source file
            preserve_lines: Whether to preserve #line directives for source mapping

        Returns:
            Preprocessed C code as a string

        Raises:
            RuntimeError: If preprocessing fails
        """
        source_path = Path(source_file)
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")

        # Build gcc -E command
        cmd = ["gcc", "-E"]

        # Add kernel defines
        cmd.extend(self.kernel_defines)

        # Add include paths
        for inc_path in self.include_paths:
            cmd.extend(["-I", inc_path])

        # Suppress standard includes to avoid conflicts
        cmd.append("-nostdinc")

        # Preserve comments for better debugging (optional)
        # cmd.append("-C")

        # Add the source file
        cmd.append(str(source_path))

        logger.debug(f"Running preprocessor: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=60
            )

            preprocessed_code = result.stdout

            if not preserve_lines:
                # Remove #line directives if requested
                preprocessed_code = self._strip_line_directives(preprocessed_code)

            logger.info(f"Successfully preprocessed {source_file}")
            return preprocessed_code

        except subprocess.CalledProcessError as e:
            logger.error(f"Preprocessing failed for {source_file}: {e.stderr}")
            raise RuntimeError(f"Preprocessing failed: {e.stderr}")
        except subprocess.TimeoutExpired:
            logger.error(f"Preprocessing timeout for {source_file}")
            raise RuntimeError("Preprocessing timeout")

    def _strip_line_directives(self, code: str) -> str:
        """
        Remove #line directives from preprocessed code.

        Args:
            code: Preprocessed C code

        Returns:
            Code without #line directives
        """
        return re.sub(r'^#\s+\d+\s+"[^"]*".*$', '', code, flags=re.MULTILINE)

    def get_original_location(self, preprocessed_line: int, line_map: Dict[int, Tuple[str, int]]) -> Tuple[str, int]:
        """
        Map a line number in preprocessed code back to original source.

        Args:
            preprocessed_line: Line number in preprocessed code
            line_map: Mapping from preprocessed line to (file, original_line)

        Returns:
            Tuple of (original_file, original_line)
        """
        return line_map.get(preprocessed_line, ("unknown", 0))

    def build_line_map(self, preprocessed_code: str) -> Dict[int, Tuple[str, int]]:
        """
        Build a mapping from preprocessed line numbers to original source locations.

        Parses #line directives to create the mapping.

        Args:
            preprocessed_code: The preprocessed C code with #line directives

        Returns:
            Dictionary mapping preprocessed line numbers to (file, line) tuples
        """
        line_map = {}
        current_file = None
        current_line = 0

        for i, line in enumerate(preprocessed_code.split('\n'), 1):
            # Match #line directive: # linenum "filename" flags
            match = re.match(r'^#\s+(\d+)\s+"([^"]*)"', line)
            if match:
                current_line = int(match.group(1)) - 1  # -1 because next line is numbered
                current_file = match.group(2)
            else:
                if current_file:
                    current_line += 1
                    line_map[i] = (current_file, current_line)

        return line_map


def preprocess_subsystem(kernel_root: str, subsystem_path: str) -> Dict[str, str]:
    """
    Preprocess all C files in a kernel subsystem.

    Args:
        kernel_root: Path to kernel source root
        subsystem_path: Relative path to subsystem (e.g., "fs/ext4")

    Returns:
        Dictionary mapping source file paths to preprocessed code
    """
    preprocessor = KernelPreprocessor(kernel_root)
    subsystem_dir = Path(kernel_root) / subsystem_path

    if not subsystem_dir.exists():
        raise ValueError(f"Subsystem path does not exist: {subsystem_dir}")

    preprocessed_files = {}

    # Find all .c files (excluding test files for now)
    c_files = [
        f for f in subsystem_dir.glob("*.c")
        if not f.name.endswith("-test.c")  # Skip KUnit tests
    ]

    logger.info(f"Found {len(c_files)} C files in {subsystem_path}")

    for c_file in c_files:
        try:
            preprocessed = preprocessor.preprocess_file(str(c_file))
            preprocessed_files[str(c_file)] = preprocessed
        except Exception as e:
            logger.warning(f"Skipping {c_file.name}: {e}")
            continue

    logger.info(f"Successfully preprocessed {len(preprocessed_files)}/{len(c_files)} files")
    return preprocessed_files


if __name__ == "__main__":
    # Example usage
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("Usage: python preprocessor.py <source_file>")
        sys.exit(1)

    kernel_root = os.getenv("KERNEL_ROOT", "/workspaces/ubuntu/linux-6.13")
    preprocessor = KernelPreprocessor(kernel_root)

    source_file = sys.argv[1]
    result = preprocessor.preprocess_file(source_file)

    print(f"Preprocessed {len(result.splitlines())} lines")
    print("\n=== First 50 lines ===")
    print('\n'.join(result.splitlines()[:50]))
