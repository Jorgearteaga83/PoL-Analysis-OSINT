import logging  # Import necessary module or component
import sys  # Import necessary module or component
import tkinter as tk  # Import necessary module or component
from tkinter import messagebox  # Import necessary module or component

def check_dependencies():  # Define function check_dependencies
    """
    Checks for all required third-party libraries before launching the app.
    Prevents ugly console crashes and provides a clear GUI error instead.
    """
    missing_libs = []  # Assign value to missing_libs
    
    # Map of module_name to pip_install_name
    dependencies = {  # Assign value to dependencies
        "pandas": "pandas",  # Execute statement or expression
        "PIL": "Pillow",  # Execute statement or expression
        "openpyxl": "openpyxl",  # Execute statement or expression
        "matplotlib": "matplotlib",  # Execute statement or expression
        "networkx": "networkx",  # Execute statement or expression
        "reverse_geocoder": "reverse_geocoder",  # Execute statement or expression
        "timezonefinder": "timezonefinder",  # Execute statement or expression
        "requests": "requests"  # Execute statement or expression
    }  # Close bracket/parenthesis

    for module, pip_name in dependencies.items():  # Iterate in a loop
        try:  # Start of try block for exception handling
            __import__(module)  # Call function __import__
        except ImportError:  # Handle specific exceptions
            missing_libs.append(pip_name)  # Close bracket/parenthesis

    if missing_libs:  # Check conditional statement
        # We spawn a hidden Tkinter window just to show the error dialog
        root = tk.Tk()  # Assign value to root
        root.withdraw()  # Close bracket/parenthesis
        
        libs_to_install = " ".join(missing_libs)  # Assign value to libs_to_install
        error_message = (  # Assign value to error_message
            f"Required libraries are missing: {', '.join(missing_libs)}\n\n"  # Execute statement or expression
            f"This usually happens if your editor is using a different Python environment "  # Execute statement or expression
            f"than your terminal.\n\n"  # Execute statement or expression
            f"Please run this command in your current terminal/environment:\n\n"  # Execute statement or expression
            f"pip install {libs_to_install}"  # Execute statement or expression
        )  # Close bracket/parenthesis
        
        messagebox.showerror("Missing Dependencies", error_message)  # Close bracket/parenthesis
        sys.exit(1)  # Close bracket/parenthesis

# ---------------------------------------------------------
# Run the dependency check BEFORE importing any local modules
# ---------------------------------------------------------
check_dependencies()  # Call function check_dependencies

# Now it is safe to import our local application modules
from app_gui import OSINTCleanGUI, ensure_directories  # Import necessary module or component

def setup_logging():  # Define function setup_logging
    """Configures centralized logging instead of blanket exception passing."""
    logging.basicConfig(  # Execute statement or expression
        level=logging.INFO,  # Assign value to level
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",  # Assign value to format
        handlers=[  # Assign value to handlers
            logging.FileHandler("osint_tool.log"),  # Execute statement or expression
            logging.StreamHandler(sys.stdout)  # Close bracket/parenthesis
        ]  # Close bracket/parenthesis
    )  # Close bracket/parenthesis
    logging.getLogger("matplotlib").setLevel(logging.WARNING)  # Close bracket/parenthesis

def main():  # Define function main
    setup_logging()  # Call function setup_logging
    logger = logging.getLogger(__name__)  # Assign value to logger
    
    try:  # Start of try block for exception handling
        ensure_directories()  # Call function ensure_directories
        logger.info("Starting OSINT Analysis Tool GUI.")  # Close bracket/parenthesis
        app = OSINTCleanGUI()  # Assign value to app
        app.mainloop()  # Close bracket/parenthesis
    except Exception as e:  # Handle specific exceptions
        logger.critical(f"Fatal error during application startup: {e}", exc_info=True)  # Close bracket/parenthesis
        # Attempt to show to user if Tkinter fails
        try:  # Start of try block for exception handling
            root = tk.Tk()  # Assign value to root
            root.withdraw()  # Close bracket/parenthesis
            messagebox.showerror("Fatal Error", f"Application failed to start:\n{e}")  # Close bracket/parenthesis
        except:  # Handle specific exceptions
            pass  # No-op placeholder
        sys.exit(1)  # Close bracket/parenthesis

if __name__ == "__main__":  # Check conditional statement
    main()  # Call function main
