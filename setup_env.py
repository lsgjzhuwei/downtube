#!/usr/bin/env python3
import os
import subprocess
import sys
import platform
import time

def run_command(command, shell=False):
    """Run a command and return its output"""
    try:
        print(f"Running: {' '.join(command) if isinstance(command, list) else command}")
        result = subprocess.run(
            command,
            shell=shell,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"Error output: {e.stderr}")
        return None

def create_virtual_env():
    """Create a virtual environment for the application"""
    print("Creating virtual environment...")
    venv_path = "downtube_venv"
    
    # Check if venv already exists
    if os.path.exists(venv_path):
        print(f"Virtual environment '{venv_path}' already exists.")
        return venv_path
    
    # Create virtual environment
    result = run_command([sys.executable, "-m", "venv", venv_path])
    if result is None:
        print("Failed to create virtual environment.")
        return None
    
    print(f"Virtual environment created at '{venv_path}'")
    
    # Wait a moment for the virtual environment to be fully created
    time.sleep(1)
    
    return venv_path

def get_pip_path(venv_path):
    """Get the correct pip path based on OS"""
    if platform.system() == "Windows":
        pip_path = os.path.join(venv_path, "Scripts", "pip")
        if not os.path.exists(pip_path + '.exe'):
            pip_path = os.path.join(venv_path, "Scripts", "pip3")
    else:
        pip_path = os.path.join(venv_path, "bin", "pip")
        if not os.path.exists(pip_path):
            pip_path = os.path.join(venv_path, "bin", "pip3")
    
    # Verify pip exists
    if platform.system() == "Windows":
        if not os.path.exists(pip_path + '.exe'):
            print(f"Error: Could not find pip at {pip_path}")
            return None
    else:
        if not os.path.exists(pip_path):
            print(f"Error: Could not find pip at {pip_path}")
            return None
            
    return pip_path

def install_dependencies(venv_path):
    """Install required dependencies in the virtual environment"""
    print("Installing dependencies...")
    
    # Determine the pip executable path based on the OS
    pip_path = get_pip_path(venv_path)
    if not pip_path:
        return False
    
    # Get the Python executable path
    if platform.system() == "Windows":
        python_path = os.path.join(venv_path, "Scripts", "python")
    else:
        python_path = os.path.join(venv_path, "bin", "python")
    
    # Upgrade pip first using the Python executable
    print("Upgrading pip...")
    run_command([python_path, "-m", "pip", "install", "--upgrade", "pip"])
    
    # Install dependencies
    dependencies = [
        "PyQt6==6.6.1",       # Specific version of PyQt6
        "PyQt6-sip==13.6.0",  # Compatible sip version
        "pytubefix",          # YouTube downloader
        "yt-dlp",             # Alternative YouTube downloader
        "pysocks",            # For SOCKS proxy support
    ]
    
    for dep in dependencies:
        print(f"Installing {dep}...")
        result = run_command([python_path, "-m", "pip", "install", dep])
        if result is None:
            print(f"Failed to install {dep}.")
            return False
    
    print("All dependencies installed successfully.")
    return True

def run_application(venv_path):
    """Run the main application from the virtual environment"""
    print("Starting application...")
    
    # Determine the python executable path based on the OS
    if platform.system() == "Windows":
        python_path = os.path.join(venv_path, "Scripts", "python")
    else:
        python_path = os.path.join(venv_path, "bin", "python")
    
    # Run the main.py script
    try:
        subprocess.run([python_path, "main.py"])
    except Exception as e:
        print(f"Error running application: {e}")
        return False
    
    return True

def main():
    print("Setting up environment for DownTube...")
    
    # Create virtual environment
    venv_path = create_virtual_env()
    if not venv_path:
        print("Failed to set up environment. Exiting.")
        return 1
    
    # Install dependencies
    if not install_dependencies(venv_path):
        print("Failed to install dependencies. Exiting.")
        return 1
    
    # Run the application
    print("\nSetup complete!")
    print(f"To run the application, use the following command:")
    
    if platform.system() == "Windows":
        print(f"{os.path.join(venv_path, 'Scripts', 'python')} main.py")
    else:
        print(f"{os.path.join(venv_path, 'bin', 'python')} main.py")
    
    choice = input("\nDo you want to run the application now? (y/n): ")
    if choice.lower() == 'y':
        run_application(venv_path)
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 