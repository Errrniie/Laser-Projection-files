#!/usr/bin/env python3
"""
Vision Configuration Launcher
=============================

Launch script for the vision system configuration tools.
Choose between GUI and command-line interfaces.
"""

import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def main():
    """Main launcher interface - automatically launches GUI"""
    
    print("🎯 GooseProject Vision Configuration")
    print("="*40)
    print("Launching GUI interface...")
    
    try:
        from Config.Config_Gui.config_gui import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"❌ Error: Failed to import GUI module: {e}")
        print("Make sure tkinter is installed: pip install tk")
    except Exception as e:
        print(f"❌ Error launching GUI: {e}")


if __name__ == "__main__":
    main()