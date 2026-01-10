#!/usr/bin/env python3
import glob
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def main():
    # Separate flags from positional arguments
    # Everything starting with '-' is a flag
    flags = [arg for arg in sys.argv[1:] if arg.startswith("-")]

    # Define our standard agent
    agent_path = "sre_agent"

    # Get project ID from env
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print(
            "WARNING: GOOGLE_CLOUD_PROJECT not set in .env. Using 'my-test-project' as fallback."
        )
        project_id = "my-test-project"

    print(f"Using Google Cloud Project ID: {project_id}")

    # Process eval files to substitute placeholder
    original_eval_files = glob.glob("eval/*.test.json")

    # Create a temporary directory for processed eval files
    with tempfile.TemporaryDirectory() as temp_dir:
        processed_eval_files = []

        for file_path in original_eval_files:
            try:
                with open(file_path) as f:
                    content = f.read()

                # key substitution
                modified_content = content.replace("TEST_PROJECT_ID", project_id)

                # Write to temp dir
                file_name = Path(file_path).name
                temp_file_path = os.path.join(temp_dir, file_name)

                with open(temp_file_path, "w") as f:
                    f.write(modified_content)

                processed_eval_files.append(temp_file_path)
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
                # Fallback to original file if processing fails
                processed_eval_files.append(file_path)

        # Construct the command with flags BEFORE positional arguments
        # adk eval [FLAGS] [AGENT] [FILES]
        cmd = ["adk", "eval", *flags, agent_path, *processed_eval_files]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
