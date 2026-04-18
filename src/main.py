import logging
import sys
import tkinter as tk
from tkinter import messagebox

def check_dependencies():
    """
    Checks for all required third-party libraries before launching the app to prevent console crashes.

    Args:
        None

    Returns:
        None
    """
    missing_libs = []
    
    dependencies = {
        "pandas": "pandas",
        "PIL": "Pillow",
        "openpyxl": "openpyxl",
        "matplotlib": "matplotlib",
        "networkx": "networkx",
        "reverse_geocoder": "reverse_geocoder",
        "timezonefinder": "timezonefinder",
        "requests": "requests"
    }

    for module, pip_name in dependencies.items():
        try:
            __import__(module)
        except ImportError:
            missing_libs.append(pip_name)

    if missing_libs:
        root = tk.Tk()
        root.withdraw()
        
        libs_to_install = " ".join(missing_libs)
        error_message = (
            f"Required libraries are missing: {', '.join(missing_libs)}\n\n"
            f"This usually happens if your editor is using a different Python environment "
            f"than your terminal.\n\n"
            f"Please run this command in your current terminal/environment:\n\n"
            f"pip install {libs_to_install}"
        )
        
        messagebox.showerror("Missing Dependencies", error_message)
        sys.exit(1)

check_dependencies()

from app_gui import OSINTCleanGUI, ensure_directories

def setup_logging():
    """
    Configures centralized logging for the application.

    Args:
        None

    Returns:
        None
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("osint_tool.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

def main():
    """
    Main entry point for the OSINT application, initializing directories, logging, and the GUI.

    Args:
        None

    Returns:
        None
    """
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        ensure_directories()
        logger.info("Starting OSINT Analysis Tool GUI.")
        app = OSINTCleanGUI()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Fatal error during application startup: {e}", exc_info=True)
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error", f"Application failed to start:\n{e}")
        except Exception:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()
