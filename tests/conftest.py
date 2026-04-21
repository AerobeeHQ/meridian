"""
Shared pytest fixtures for Codex tests.
"""
import os
import sys
import pytest

# Ensure the project root is on sys.path so imports work without installation
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
