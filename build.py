#!/usr/bin/env python3
"""
Build script for creating standalone executables using PyInstaller.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

def run_command(cmd, cwd=None):
    """Run a command and return the result."""
    print(f"Running: {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Command failed: {result.stderr}")
        sys.exit(1)
    return result.stdout

def create_spec_file():
    """Create PyInstaller spec file."""
    
    # Determine platform-specific executable name
    system = platform.system().lower()
    if system == "windows":
        exe_name = "auth0-export-windows.exe"
    elif system == "darwin":
        exe_name = "auth0-export-macos"
    else:
        exe_name = "auth0-export-linux"
    
    # Platform-specific hidden imports
    hidden_imports = [
        'auth0_export.cli',
        'auth0_export.exporter',
        'auth0.authentication',
        'auth0.management',
        'pandas',
        'openpyxl',
        'rich',
        'click',
        'dotenv',
        'logging',
        'json',
        'time',
        'datetime',
        'pathlib',
        'typing',
        'os',
        'sys',
        'random',
    ]
    
    # Only add blessings on non-Windows platforms
    if system != "windows":
        hidden_imports.append('blessings')
    
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

# Define the main script path
main_script = Path('auth0_export') / 'cli.py'

a = Analysis(
    [str(main_script)],
    pathex=[],
    binaries=[],
    datas=[
        ('auth0_export/*.py', 'auth0_export'),
    ],
    hiddenimports={hidden_imports},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='{exe_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    with open('auth0-export.spec', 'w') as f:
        f.write(spec_content)
    
    print(f"Created spec file for {exe_name}")
    return exe_name

def main():
    """Main build function."""
    print("🔨 Building Auth0 Export standalone executable...")
    
    # Check if we're in the right directory
    if not Path('auth0_export').exists():
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)
    
    # Install build dependencies
    print("📦 Installing build dependencies...")
    run_command("uv sync --group build")
    
    # Create spec file
    exe_name = create_spec_file()
    
    # Build executable
    print("🏗️  Building executable with PyInstaller...")
    run_command("uv run pyinstaller auth0-export.spec --clean --noconfirm")
    
    # Test executable
    print("🧪 Testing executable...")
    exe_path = Path('dist') / exe_name
    
    if platform.system() != "Windows":
        os.chmod(exe_path, 0o755)
        test_cmd = f"./dist/{exe_name} --help"
    else:
        test_cmd = f".\\dist\\{exe_name} --help"
    
    try:
        result = subprocess.run(test_cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print("✅ Executable test passed!")
        else:
            print(f"⚠️  Executable test failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("⚠️  Executable test timed out")
    
    # Create archive
    print("📦 Creating distribution archive...")
    system = platform.system().lower()
    
    if system == "windows":
        import zipfile
        archive_name = f"{exe_name}.zip"
        with zipfile.ZipFile(f"dist/{archive_name}", 'w') as zf:
            zf.write(exe_path, exe_name)
    else:
        import tarfile
        archive_name = f"{exe_name}.tar.gz"
        with tarfile.open(f"dist/{archive_name}", "w:gz") as tar:
            tar.add(exe_path, arcname=exe_name)
    
    print(f"✅ Build completed successfully!")
    print(f"📁 Executable: dist/{exe_name}")
    print(f"📦 Archive: dist/{archive_name}")
    print(f"💡 Test with: ./dist/{exe_name} --help")

if __name__ == "__main__":
    main()