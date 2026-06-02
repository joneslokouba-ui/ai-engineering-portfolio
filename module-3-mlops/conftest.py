"""
conftest.py — auto-loaded by pytest before any test
Adds project root to sys.path so all module imports resolve.
"""
import sys
import os

# Insert project root at the front of the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))