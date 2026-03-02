import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from typing import Any

# Global process handles for cleanup
backend_proc: subprocess.Popen[Any] | None = None
frontend_proc: subprocess.Popen[Any] | None = None
react_proc: subprocess.Popen[Any] | None = None


def cleanup(signum: int | None, frame: object) -> None:
    """Handle cleanup on signal."""
    print("\n🛑 Stopping services...")

    if frontend_proc:
        print("Killing Frontend...")
        frontend_proc.terminate()
        try:
            frontend_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            frontend_proc.kill()

    if react_proc:
        print("Killing React UI...")
        react_proc.terminate()
        try:
            react_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            react_proc.kill()

    if backend_proc:
        print("Killing Backend...")
        backend_proc.terminate()
        try:
            backend_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            backend_proc.kill()

    print("✅ All services stopped.")
    sys.exit(0)


def check_command(cmd_name: str) -> bool:
    """Check if a command exists in path."""
    return shutil.which(cmd_name) is not None


def cleanup_port(port: int) -> None:
    """Kill any process using the specified port."""
    try:
        # Try to use fuser to kill the port
        subprocess.run(["fuser", "-k", f"{port}/tcp"], check=False, capture_output=True)
    except Exception:
        pass


def start_backend() -> bool:
    """Start the Python backend."""
    global backend_proc

    if not check_command("uv"):
        print(
            "❌ 'uv' command not found! Please install uv (https://github.com/astral-sh/uv)."
        )
        return False

    print("🚀 Cleaning up port 8001...")
    cleanup_port(8001)

    print("🚀 Starting Backend (ADK Agent)...")

    # Use unbuffered output for Python to see logs immediately
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    # Run only a single worker for local dev to avoid interleaved logs in stdout
    env["WEB_CONCURRENCY"] = "1"

    # Enforce local execution mode even if SRE_AGENT_ID is in .env for deployments
    if "SRE_AGENT_ID" in env:
        print(
            "[INFO] Unsetting SRE_AGENT_ID to force local execution mode for development."
        )
        env.pop("SRE_AGENT_ID")

    backend_proc = subprocess.Popen(
        ["uv", "run", "poe", "web"],
        cwd=os.getcwd(),
        env=env,
    )

    print("⏳ Waiting for Backend to initialize (5s)...")
    time.sleep(5)

    if backend_proc and backend_proc.poll() is not None:
        print("❌ Backend failed to start!")
        return False
    return True


def start_frontend() -> bool:
    """Start the Flutter frontend."""
    global frontend_proc

    if not check_command("flutter"):
        print("⚠️  'flutter' command not found! Skipping Flutter frontend.")
        print(
            "   If you need it, please install Flutter: https://docs.flutter.dev/get-started/install"
        )
        return True  # Return True to continue with other services

    print("🚀 Starting Frontend (Flutter)...")

    frontend_dir = os.path.join(os.getcwd(), "autosre")

    # 1. Read Client ID
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        try:
            from dotenv import load_dotenv

            load_dotenv(os.path.join(frontend_dir, ".env"))
            client_id = os.getenv("GOOGLE_CLIENT_ID")
        except ImportError:
            pass

    flutter_cmd = [
        "flutter",
        "run",
        "-d",
        "chrome",
        "--web-hostname",
        "localhost",
        "--web-port",
        "8080",
    ]

    if client_id:
        print("🔑 Passing Google Client ID to Flutter via --dart-define...")
        flutter_cmd.append(f"--dart-define=GOOGLE_CLIENT_ID={client_id}")

    try:
        frontend_proc = subprocess.Popen(
            flutter_cmd,
            cwd=frontend_dir,
        )
    except Exception as e:
        print(f"❌ Failed to spawn flutter: {e}")
        return False

    if frontend_proc and frontend_proc.poll() is not None:
        print("❌ Frontend failed to start!")
        return False
    return True


def start_react() -> bool:
    """Start the React Agent Graph UI."""
    global react_proc

    if not check_command("npm"):
        print("⚠️  'npm' command not found! Skipping React UI.")
        print("   If you need it, please install Node.js and npm: https://nodejs.org/")
        return True  # Return True to continue

    print("🚀 Starting React UI (Vite)...")

    react_dir = os.path.join(os.getcwd(), "agent_ops_ui")

    try:
        react_proc = subprocess.Popen(
            ["npm", "run", "dev"],
            cwd=react_dir,
        )
    except Exception as e:
        print(f"❌ Failed to spawn npm: {e}")
        return False

    if react_proc and react_proc.poll() is not None:
        print("❌ React UI failed to start!")
        return False
    return True


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="SRE Agent Development Environment")
    parser.add_argument(
        "--frontend",
        choices=["flutter", "react", "both"],
        default="both",
        help="Which frontend to start (default: both)",
    )
    return parser.parse_args()


def main() -> None:
    """Run the development environment."""
    args = parse_args()

    # Register signal handlers
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    frontend_label = {
        "both": "Flutter + React frontends",
        "flutter": "Flutter frontend only",
        "react": "React frontend only",
    }[args.frontend]

    print("🔥 Starting SRE Agent Development Environment...")
    print(f"   Frontend mode: {frontend_label}")
    print("===============================================")

    if not start_backend():
        cleanup(None, None)
        return

    if args.frontend in ("flutter", "both"):
        if not start_frontend():
            cleanup(None, None)
            return

    if args.frontend in ("react", "both"):
        if not start_react():
            cleanup(None, None)
            return

    print("\n✅ API running at http://127.0.0.1:8001")
    if frontend_proc:
        print("✅ Web UI starting in Chrome (Flutter)")
    if react_proc:
        print("✅ React UI starting via Vite")
    print("\nPRESS CTRL+C TO STOP ALL SERVICES\n")

    # Keep main thread alive
    try:
        while True:
            # Check if processes are still alive
            if backend_proc and backend_proc.poll() is not None:
                print("\n❌ Backend crashed unexpectedly!")
                cleanup(None, None)

            if frontend_proc and frontend_proc.poll() is not None:
                print("\n❌ Frontend crashed unexpectedly!")
                cleanup(None, None)

            if react_proc and react_proc.poll() is not None:
                print("\n❌ React UI crashed unexpectedly!")
                cleanup(None, None)

            time.sleep(1)
    except KeyboardInterrupt:
        cleanup(None, None)


if __name__ == "__main__":
    main()
