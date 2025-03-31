#!/usr/bin/env python
import unittest
import sys
import os

if __name__ == "__main__":
    # Add the parent directory to the Python path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    
    # Discover and run all tests
    test_suite = unittest.defaultTestLoader.discover('tests', pattern='test_*.py')
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Return non-zero exit code if any tests failed
    sys.exit(0 if result.wasSuccessful() else 1) 