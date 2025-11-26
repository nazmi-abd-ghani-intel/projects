#!/usr/bin/env python3
"""
Smoke test for the Tkinter GUI: launch the main window briefly and exit.

This script is intended for CI (headless) environments where Xvfb
provides a virtual display.
"""
import os
import sys
import tkinter as tk

# Ensure the project root is on sys.path so imports work when the test
# is executed from CI or when invoked as a script from the `tests` folder.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from gui_app import FFRCheckGUI


def main():
    # Ensure DISPLAY is set (Xvfb usually exposes :99 in CI workflows)
    os.environ.setdefault('DISPLAY', os.getenv('DISPLAY', ':99'))
    # Debug: print environment inputs received (visible in CI logs)
    print('ENV INPUT_DIR=', os.getenv('INPUT_DIR'))
    print('ENV OUTPUT_DIR=', os.getenv('OUTPUT_DIR'))
    print('ENV SSPEC=', os.getenv('SSPEC'))
    print('ENV UBE=', os.getenv('UBE'))

    root = tk.Tk()
    try:
        app = FFRCheckGUI(root)

        # Populate GUI fields from environment variables (workflow inputs)
        input_dir = os.getenv('INPUT_DIR', '')
        output_dir = os.getenv('OUTPUT_DIR', '')
        sspec = os.getenv('SSPEC', '')
        ube = os.getenv('UBE', '')

        if input_dir:
            try:
                app.input_dir_var.set(input_dir)
            except Exception:
                pass

        if output_dir:
            try:
                app.output_dir_var.set(output_dir)
            except Exception:
                pass

        if sspec:
            try:
                app.sspec_var.set(sspec)
            except Exception:
                pass

        if ube:
            try:
                app.ube_var.set(ube)
            except Exception:
                pass

        # Schedule the app to close after 2 seconds to keep the test fast
        root.after(2000, root.destroy)
        root.mainloop()
        print("GUI smoke test completed successfully")
    except Exception as exc:
        print("GUI smoke test failed:", exc)
        raise


if __name__ == '__main__':
    main()
