import os
import sys
from pathlib import Path

os.environ["IRIS_SKIP_DOTENV"] = "1"

sys.path.insert(0, str(Path(__file__).resolve().parent))
