import os
import sys

# Ensure the proto directory is in sys.path so generated pb2 files can import each other
_proto_dir = os.path.dirname(os.path.abspath(__file__))
if _proto_dir not in sys.path:
    sys.path.insert(0, _proto_dir)