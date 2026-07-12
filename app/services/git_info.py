"""
Git information utilities for Meridian.
Retrieves branch name and commit hash for display in the UI footer.

Works both locally (via subprocess git commands) and in Docker (via git_info.txt).
"""
import os
import subprocess


def _run_git_command(args: list[str]) -> str | None:
    """Run a git command and return output, or None if it fails."""
    try:
        result = subprocess.run(
            ['git'] + args,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    return None


def _read_git_info_file() -> dict:
    """Read git info from git_info.txt (used in Docker builds)."""
    info = {'branch': None, 'commit': None}
    
    # Look for git_info.txt in project root
    # This file is in app/services/, so project root is 2 levels up
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    git_info_path = os.path.join(base_dir, 'git_info.txt')
    
    if os.path.exists(git_info_path):
        try:
            with open(git_info_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('branch='):
                        info['branch'] = line.split('=', 1)[1]
                    elif line.startswith('commit='):
                        info['commit'] = line.split('=', 1)[1]
        except Exception:
            pass
    
    return info


def get_git_info() -> dict:
    """
    Get current git branch and commit hash.
    
    Returns dict with keys:
        - branch: Current branch name (e.g., 'main', 'feature/xyz')
        - commit: Short commit hash (7 chars)
        - commit_full: Full commit hash
    
    Falls back to git_info.txt when .git folder unavailable (Docker).
    Returns None values if git info cannot be determined.
    """
    info = {
        'branch': None,
        'commit': None,
        'commit_full': None
    }
    
    # Try subprocess first (works locally)
    branch = _run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'])
    commit_full = _run_git_command(['rev-parse', 'HEAD'])
    
    if branch and commit_full:
        info['branch'] = branch
        info['commit_full'] = commit_full
        info['commit'] = commit_full[:7]
        return info
    
    # Fallback: read from git_info.txt (Docker builds)
    file_info = _read_git_info_file()
    
    if file_info['branch']:
        info['branch'] = file_info['branch']
    
    if file_info['commit']:
        info['commit_full'] = file_info['commit']
        info['commit'] = file_info['commit'][:7] if len(file_info['commit']) > 7 else file_info['commit']
    
    return info


