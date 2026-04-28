import os
import sys

# Add the project root to sys.path to allow absolute imports of 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import os
os.environ["TESTING"] = "True"
