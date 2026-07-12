"""
Shared pytest fixtures for Meridian tests.
"""
import os
import sys

# Ensure the project root is on sys.path so imports work without installation
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
