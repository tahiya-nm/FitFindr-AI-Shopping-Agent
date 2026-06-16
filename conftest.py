# conftest.py
import sys
import os

# Add the project root to sys.path so pytest can find tools, agent, and utils
sys.path.insert(0, os.path.dirname(__file__))