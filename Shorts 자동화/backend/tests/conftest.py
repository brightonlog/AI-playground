import os
import tempfile

# Point DATA_DIR at a temp dir before app modules read settings.
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="shorts-test-")
