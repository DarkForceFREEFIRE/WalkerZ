import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
PROTO_DIR = os.path.join(PROJECT_ROOT, "proto")

if PROTO_DIR not in sys.path:
    sys.path.insert(0, PROTO_DIR)

from app import app