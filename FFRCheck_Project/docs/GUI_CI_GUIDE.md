Running GUI apps in CI
======================

This guide explains how to run or test GUI applications (Tkinter, PyQt/PySide, Matplotlib GUIs) on GitHub Actions and other CI systems.

General approaches
- Use a Linux runner and Xvfb (X virtual framebuffer) to create a headless X11 display.
- For Qt apps prefer `QT_QPA_PLATFORM=offscreen` when possible (works without Xvfb).
- For Matplotlib, set backend to `Agg` to avoid any X11 requirements.

Tkinter (used in this project)
- On Ubuntu runners start Xvfb and set `DISPLAY` to the Xvfb display (example workflow in `.github/workflows/gui.yml`).
- Minimal smoke test: `python -c "import tkinter; print(tkinter.TkVersion)"`.
- To run your GUI-driven smoke tests, invoke the entrypoint under the Xvfb display; avoid long-running interactive loops.

PyQt / PySide
- Prefer `QT_QPA_PLATFORM=offscreen` for pure rendering: `env: QT_QPA_PLATFORM: offscreen`.
- If that fails (some features require an X server), use Xvfb like Tkinter.

Matplotlib
- Use `matplotlib.use('Agg')` or set `MPLBACKEND=Agg` env var to render plots to files without X11.

Windows runners
- Windows runners don't provide Xvfb. If you must run GUI tests on Windows, use `runs-on: windows-latest` and run actual GUI tests there.
- For automated CI, prefer Linux + Xvfb or Qt offscreen to stay cross-platform.

Artifacts and Debugging
- Capture screenshots with `import -window root /tmp/screen.png` (ImageMagick) or `xwd` to help debug X failures.
- Upload artifacts with `actions/upload-artifact`.

Notes for this repo
- This project uses Tkinter via `gui_app.py`. See `.github/workflows/gui.yml` for an example workflow that starts Xvfb and runs a smoke test.
