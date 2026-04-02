import logging
import sys
from tkinter import messagebox
from app_gui import OSINTCleanGUI, ensure_directories

def setup_logging():
    """Configures centralized logging instead of blanket exception passing."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler("osint_tool.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )

def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        ensure_directories()
        logger.info("Starting OSINT Analysis Tool GUI.")
        app = OSINTCleanGUI()
        app.mainloop()
    except Exception as e:
        logger.critical(f"Fatal error during application startup: {e}", exc_info=True)
        # Attempt to show to user if Tkinter fails
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("Fatal Error", f"Application failed to start: {e}")
        except:
            pass
        sys.exit(1)

if __name__ == "__main__":
    main()