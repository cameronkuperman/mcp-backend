"""Photo analysis module - gradual migration wrapper"""
# This module wraps the existing photo_analysis.py functionality
# and gradually migrates it to a modular structure

# For now, we'll import and re-export the existing router
# This ensures backward compatibility while we migrate
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import the existing photo_analysis module
from api import photo_analysis

# Re-export the router for backward compatibility
router = photo_analysis.router