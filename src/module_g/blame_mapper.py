"""
BlameMapper: Map lines to their modifying commits

This module uses git blame to map each line in a file or function to
the commit that last modified it.
"""

import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

from .git_extractor import GitExtractor
from .schema import BlameInfo, FunctionBlameInfo

logger = logging.getLogger(__name__)


class BlameMapper:
    """
    Map lines and functions to their modifying commits using git blame.

    Provides blame information for individual lines, functions, and file ranges.
    """

    def __init__(self, repo_path: str):
        """
        Initialize the blame mapper.

        Args:
            repo_path: Path to the git repository
        """
        self.extractor = GitExtractor(repo_path)
        self.repo_path = Path(repo_path)

    def blame_function(
        self,
        file_path: str,
        line_start: int,
        line_end: int,
        function_name: Optional[str] = None
    ) -> FunctionBlameInfo:
        """
        Get git blame information for a function.

        Args:
            file_path: Path to the file (relative to repo root)
            line_start: Function start line number
            line_end: Function end line number
            function_name: Optional function name

        Returns:
            FunctionBlameInfo object with aggregated blame data
        """
        logger.debug(f"Blaming function at {file_path}:{line_start}-{line_end}")

        # Get blame for the function range
        blame_data = self.extractor.get_file_blame(file_path, line_start, line_end)

        if not blame_data:
            logger.warning(f"No blame data for {file_path}:{line_start}-{line_end}")
            return FunctionBlameInfo(
                function_name=function_name or 'unknown',
                file_path=file_path,
                line_start=line_start,
                line_end=line_end,
                last_modified_commit='',
                author='',
                date='',
                line_count=line_end - line_start + 1,
                commits_touching=[],
            )

        # Aggregate by commit
        commits_by_hash = {}
        for blame_entry in blame_data:
            commit_hash = blame_entry['commit_hash']

            if commit_hash not in commits_by_hash:
                commits_by_hash[commit_hash] = {
                    'commit_hash': commit_hash,
                    'author': blame_entry.get('author', 'Unknown'),
                    'date': blame_entry.get('date', ''),
                    'summary': blame_entry.get('summary', ''),
                    'line_count': 0,
                }

            commits_by_hash[commit_hash]['line_count'] += 1

        # Find the most recent commit (highest line number typically)
        commits_list = sorted(
            commits_by_hash.values(),
            key=lambda x: x['line_count'],
            reverse=True
        )

        last_modified = commits_list[0] if commits_list else {
            'commit_hash': '',
            'author': 'Unknown',
            'date': '',
            'summary': '',
            'line_count': 0,
        }

        # Build commits_touching list
        commits_touching = []
        for commit in commits_list:
            commits_touching.append({
                'hash': commit['commit_hash'][:8],
                'author': commit['author'],
                'lines': commit['line_count'],
            })

        return FunctionBlameInfo(
            function_name=function_name or 'unknown',
            file_path=file_path,
            line_start=line_start,
            line_end=line_end,
            last_modified_commit=last_modified['commit_hash'][:8],
            author=last_modified['author'],
            date=last_modified['date'],
            line_count=line_end - line_start + 1,
            commits_touching=commits_touching,
        )

    def blame_file_range(
        self,
        file_path: str,
        line_start: int,
        line_end: int
    ) -> List[BlameInfo]:
        """
        Get blame info for each line in a range.

        Args:
            file_path: Path to the file
            line_start: Start line number
            line_end: End line number

        Returns:
            List of BlameInfo objects, one per line
        """
        blame_data = self.extractor.get_file_blame(file_path, line_start, line_end)

        blame_info_list = []
        line_number = line_start

        for blame_entry in blame_data:
            blame = BlameInfo(
                commit_hash=blame_entry['commit_hash'][:8],
                author=blame_entry.get('author', 'Unknown'),
                date=blame_entry.get('date', ''),
                line_number=line_number,
                line_content=blame_entry.get('line_content', ''),
            )

            blame_info_list.append(blame)
            line_number += 1

        return blame_info_list

    def find_function_introduction_commit(
        self,
        file_path: str,
        function_name: str,
        line_start: int
    ) -> Optional[Dict[str, Any]]:
        """
        Find the commit that introduced a function.

        Args:
            file_path: Path to the file
            function_name: Function name
            line_start: Function start line

        Returns:
            Dict with commit info or None
        """
        logger.debug(f"Finding introduction commit for {function_name} in {file_path}")

        # Use git log -S to find commits that added this function
        try:
            import subprocess
            cmd = [
                'git', 'log',
                '--reverse',
                '--diff-filter=A',
                '-S', function_name,
                '--oneline',
                '--',
                file_path
            ]

            result = subprocess.run(
                cmd,
                cwd=str(self.repo_path),
                capture_output=True,
                text=True,
                check=True
            )

            output = result.stdout.strip()
            if not output:
                return None

            # Parse first line: "hash message"
            parts = output.split('\n')[0].split(' ', 1)
            commit_hash = parts[0]
            commit_message = parts[1] if len(parts) > 1 else ''

            # Get commit details
            commits = self.extractor.extract_commits(limit=100)
            for commit in commits:
                if commit.id.startswith(commit_hash):
                    return {
                        'commit_hash': commit.hash_short,
                        'author': commit.author_name,
                        'date': commit.author_date,
                        'message': commit.title,
                    }

            return {
                'commit_hash': commit_hash[:8],
                'author': 'Unknown',
                'date': '',
                'message': commit_message,
            }

        except subprocess.CalledProcessError:
            logger.warning(f"Failed to find introduction commit for {function_name}")
            return None

    def get_commit_for_line(
        self,
        file_path: str,
        line_number: int
    ) -> Optional[Dict[str, str]]:
        """
        Get the commit that last modified a specific line.

        Args:
            file_path: Path to the file
            line_number: Line number

        Returns:
            Dict with commit_hash, author, date or None
        """
        blame_data = self.extractor.get_file_blame(file_path, line_number, line_number)

        if blame_data:
            entry = blame_data[0]
            return {
                'commit_hash': entry['commit_hash'][:8],
                'author': entry.get('author', 'Unknown'),
                'date': entry.get('date', ''),
                'summary': entry.get('summary', ''),
            }

        return None
