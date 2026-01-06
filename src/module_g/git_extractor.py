"""
GitExtractor: Extract git repository metadata

This module uses git commands to extract commits, branches, tags, and authors
from a git repository.
"""

import re
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import subprocess
from datetime import datetime

from .schema import (
    GitCommitNode,
    GitBranchNode,
    GitTagNode,
    GitAuthorNode,
    FileChange,
    ChangeType,
)

logger = logging.getLogger(__name__)


class GitExtractor:
    """
    Extract git metadata from a repository.

    Uses git commands (git log, git show, git branch, etc.) to extract
    commits, branches, tags, and author information.
    """

    def __init__(self, repo_path: str):
        """
        Initialize the git extractor.

        Args:
            repo_path: Path to the git repository

        Raises:
            ValueError: If repo_path is not a valid git repository
        """
        self.repo_path = Path(repo_path)

        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repo_path}")

        # Check if this is a git repository
        git_dir = self.repo_path / '.git'
        if not git_dir.exists():
            raise ValueError(f"Not a git repository: {repo_path}")

        logger.info(f"Initialized GitExtractor for {repo_path}")

    def _run_git_command(self, args: List[str], cwd: Optional[str] = None) -> str:
        """
        Run a git command and return its output.

        Args:
            args: Git command arguments (e.g., ['log', '--oneline'])
            cwd: Working directory (default: self.repo_path)

        Returns:
            Command output as string

        Raises:
            subprocess.CalledProcessError: If command fails
        """
        if cwd is None:
            cwd = str(self.repo_path)

        cmd = ['git'] + args
        logger.debug(f"Running: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True
        )

        return result.stdout

    def extract_commits(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        branch: str = 'HEAD',
        limit: Optional[int] = None,
        subsystem: Optional[str] = None
    ) -> List[GitCommitNode]:
        """
        Extract commits from git history.

        Args:
            since: Start date (e.g., "2020-01-01")
            until: End date (e.g., "2024-12-31")
            branch: Branch to analyze (default: HEAD)
            limit: Maximum number of commits to extract
            subsystem: Filter by subsystem path (e.g., "fs/ext4")

        Returns:
            List of GitCommitNode objects
        """
        logger.info(f"Extracting commits from {branch}")

        # Build git log command
        args = [
            'log',
            branch,
            '--pretty=format:%H|%an|%ae|%ad|%cn|%ce|%cd|%s',
            '--date=iso',
        ]

        # Add date filters
        if since:
            args.append(f'--since={since}')
        if until:
            args.append(f'--until={until}')

        # Add limit
        if limit:
            args.append(f'-n {limit}')

        # Add path filter
        if subsystem:
            args.append('--')
            args.append(subsystem)

        try:
            output = self._run_git_command(args)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract commits: {e}")
            return []

        commits = []
        for line in output.strip().split('\n'):
            if not line:
                continue

            parts = line.split('|')
            if len(parts) != 8:
                logger.warning(f"Invalid commit line: {line}")
                continue

            commit_hash, author_name, author_email, author_date, \
                committer_name, committer_email, committer_date, title = parts

            # Get full commit message and stats
            try:
                message_output = self._run_git_command([
                    'log', commit_hash, '-1', '--format:%B%n%cd'
                ])
                message = message_output.strip()
            except:
                message = title

            # Get file change stats
            try:
                stats = self._extract_commit_stats(commit_hash, subsystem)
            except Exception as e:
                logger.warning(f"Failed to get stats for {commit_hash}: {e}")
                stats = {
                    'files_changed': 0,
                    'insertions': 0,
                    'deletions': 0,
                }

            # Check if merge commit
            try:
                parents = self._run_git_command(['rev-parse', commit_hash+'^@']).strip().split('\n')
                is_merge = len(parents) > 1
            except:
                is_merge = False

            # Check for Signed-off-by
            signed_off = 'Signed-off-by:' in message

            # Create commit node
            commit = GitCommitNode(
                id=commit_hash,
                hash_short=commit_hash[:8],
                title=title,
                message=message,
                author_name=author_name,
                author_email=author_email,
                author_date=author_date,
                committer_name=committer_name,
                committer_email=committer_email,
                committer_date=committer_date,
                branch=branch,
                files_changed=stats['files_changed'],
                insertions=stats['insertions'],
                deletions=stats['deletions'],
                is_merge=is_merge,
                signed_off=signed_off,
            )

            commits.append(commit)

        logger.info(f"Extracted {len(commits)} commits")
        return commits

    def _extract_commit_stats(self, commit_hash: str, subsystem: Optional[str] = None) -> Dict[str, int]:
        """
        Extract file change statistics for a commit.

        Args:
            commit_hash: Commit hash
            subsystem: Optional subsystem path filter

        Returns:
            Dict with files_changed, insertions, deletions
        """
        args = ['show', commit_hash, '--shortstat', '--format=%h']

        if subsystem:
            args.append('--')
            args.append(subsystem)

        try:
            output = self._run_git_command(args)

            # Parse shortstat output
            # Example: " 3 files changed, 12 insertions(+), 3 deletions(-)"
            files_changed = 0
            insertions = 0
            deletions = 0

            for line in output.strip().split('\n'):
                if 'file' in line:
                    match = re.search(r'(\d+) files?', line)
                    if match:
                        files_changed = int(match.group(1))

                if 'insertion' in line:
                    match = re.search(r'(\d+) insertion', line)
                    if match:
                        insertions = int(match.group(1))

                if 'deletion' in line:
                    match = re.search(r'(\d+) deletion', line)
                    if match:
                        deletions = int(match.group(1))

            return {
                'files_changed': files_changed,
                'insertions': insertions,
                'deletions': deletions,
            }

        except Exception as e:
            logger.warning(f"Failed to parse commit stats: {e}")
            return {
                'files_changed': 0,
                'insertions': 0,
                'deletions': 0,
            }

    def extract_commit_files(self, commit_hash: str) -> List[FileChange]:
        """
        Extract files changed in a commit.

        Args:
            commit_hash: Commit hash

        Returns:
            List of FileChange objects
        """
        args = [
            'show', commit_hash, '--name-status', '--format=%H'
        ]

        try:
            output = self._run_git_command(args)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract commit files: {e}")
            return []

        changes = []
        for line in output.strip().split('\n'):
            if not line or line == commit_hash:
                continue

            # Parse status line
            # Format: STATUS    filename
            # Example: M       fs/ext4/inode.c
            parts = line.split('\t')
            if len(parts) < 2:
                continue

            status_code = parts[0]
            file_path = parts[1]

            # Map status codes to ChangeType
            status_map = {
                'A': ChangeType.ADDED,
                'M': ChangeType.MODIFIED,
                'D': ChangeType.DELETED,
                'R': ChangeType.RENAMED,
                'C': ChangeType.COPIED,
            }

            change_type = status_map.get(status_code[0], ChangeType.MODIFIED)

            change = FileChange(
                file_path=file_path,
                change_type=change_type,
            )

            changes.append(change)

        logger.debug(f"Extracted {len(changes)} file changes for {commit_hash}")
        return changes

    def extract_branches(self) -> List[GitBranchNode]:
        """
        Extract all branches from the repository.

        Returns:
            List of GitBranchNode objects
        """
        logger.info("Extracting branches")

        try:
            # Get current HEAD
            head_output = self._run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'])
            current_branch = head_output.strip()

            # Get all branches
            branches_output = self._run_git_command(['branch', '-a'])

            branches = []
            for line in branches_output.strip().split('\n'):
                if not line:
                    continue

                # Remove leading whitespace and *
                branch_name = line.strip().lstrip('* ').strip()

                # Skip HEAD reference
                if branch_name == 'HEAD' or '->' in branch_name:
                    continue

                # Remove remote prefix for local branches
                if branch_name.startswith('remotes/origin/'):
                    branch_name = branch_name.replace('remotes/origin/', '')

                # Get commit count for this branch
                try:
                    count_output = self._run_git_command([
                        'rev-list', '--count', branch_name
                    ])
                    commit_count = int(count_output.strip())
                except:
                    commit_count = 0

                # Get last commit hash
                try:
                    last_hash = self._run_git_command([
                        'rev-parse', branch_name
                    ]).strip()
                except:
                    last_hash = None

                branch = GitBranchNode(
                    id=branch_name,
                    name=branch_name,
                    is_head=(branch_name == current_branch),
                    commit_count=commit_count,
                    last_commit_hash=last_hash,
                )

                branches.append(branch)

            logger.info(f"Extracted {len(branches)} branches")
            return branches

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract branches: {e}")
            return []

    def extract_tags(self) -> List[GitTagNode]:
        """
        Extract all tags from the repository.

        Returns:
            List of GitTagNode objects
        """
        logger.info("Extracting tags")

        try:
            tags_output = self._run_git_command(['tag', '-l'])

            tags = []
            for tag_name in tags_output.strip().split('\n'):
                if not tag_name:
                    continue

                # Get commit hash this tag points to
                try:
                    commit_hash = self._run_git_command([
                        'rev-parse', tag_name + '^{}'
                    ]).strip()
                except:
                    continue

                # Get tag date
                try:
                    date_output = self._run_git_command([
                        'log', '-1', '--format=%cd', commit_hash
                    ])
                    tag_date = date_output.strip()
                except:
                    tag_date = ''

                # Check if this is a release tag (starts with 'v' followed by number)
                is_release = bool(re.match(r'^v\d+\.\d+', tag_name))

                # Get tag message (for annotated tags)
                try:
                    message_output = self._run_git_command([
                        'tag', '-l', tag_name, '--format=%(contents)'
                    ])
                    message = message_output.strip() or None
                except:
                    message = None

                tag = GitTagNode(
                    id=tag_name,
                    name=tag_name,
                    commit_hash=commit_hash,
                    tag_date=tag_date,
                    is_release=is_release,
                    message=message,
                )

                tags.append(tag)

            logger.info(f"Extracted {len(tags)} tags")
            return tags

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract tags: {e}")
            return []

    def extract_authors(self) -> List[GitAuthorNode]:
        """
        Aggregate commits by author.

        Returns:
            List of GitAuthorNode objects with aggregated stats
        """
        logger.info("Extracting authors")

        try:
            # Get all authors with commit counts
            shortlog_output = self._run_git_command([
                'shortlog', '-sne', '--all'
            ])

            authors = []
            for line in shortlog_output.strip().split('\n'):
                if not line:
                    continue

                # Parse: "    1234  John Doe <john@example.com>"
                match = re.match(r'\s+(\d+)\s+(.+?)\s+<([^>]+)>', line)
                if not match:
                    continue

                commits_count = int(match.group(1))
                name = match.group(2).strip()
                email = match.group(3)

                # Get lines added/removed by this author
                try:
                    # This can be slow for large repos, so we'll use a simpler approach
                    # Just get commits, not full stats
                    pass
                except Exception as e:
                    logger.warning(f"Failed to get author stats for {email}: {e}")

                author = GitAuthorNode(
                    id=email,
                    name=name,
                    email=email,
                    commits_count=commits_count,
                )

                authors.append(author)

            logger.info(f"Extracted {len(authors)} authors")
            return authors

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract authors: {e}")
            return []

    def get_file_blame(self, file_path: str, line_start: int, line_end: int) -> List[Dict[str, Any]]:
        """
        Get git blame information for a range of lines in a file.

        Args:
            file_path: Path to the file
            line_start: Start line number
            line_end: End line number

        Returns:
            List of blame info dictionaries
        """
        args = [
            'blame',
            '-L', f'{line_start},{line_end}',
            '--line-porcelain',
            file_path,
        ]

        try:
            output = self._run_git_command(args)
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to get blame for {file_path}: {e}")
            return []

        blame_info = []
        current_commit = {}
        current_code = []

        for line in output.split('\n'):
            if line.startswith('\t'):
                # This is a code line
                current_code.append(line[1:])
            elif line.startswith('author '):
                current_commit['author'] = line[7:].strip()
            elif line.startswith('author-mail '):
                current_commit['author_email'] = line[12:].strip()
            elif line.startswith('author-time '):
                timestamp = int(line[12:].strip())
                current_commit['date'] = datetime.fromtimestamp(timestamp).isoformat()
            elif line.startswith('summary '):
                current_commit['summary'] = line[8:].strip()
            elif re.match(r'^[0-9a-f]{40}', line):
                # Start of new blame entry
                if current_code:
                    # Save previous entry
                    current_commit['line_content'] = '\n'.join(current_code)
                    blame_info.append(current_commit.copy())
                    current_code = []

                current_commit = {'commit_hash': line[:40]}

        # Don't forget the last entry
        if current_code and current_commit:
            current_commit['line_content'] = '\n'.join(current_code)
            blame_info.append(current_commit)

        return blame_info
