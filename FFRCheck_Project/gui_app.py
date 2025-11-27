"""
FFR Check GUI Application
A graphical interface for the FFR Check tool
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import sys
import json
from pathlib import Path
import queue
import os


class FFRCheckGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FFR Check - Fuse File Release Checker")
        self.root.geometry("900x700")
        
        # Load config if exists
        self.config_path = Path("config.json")
        self.config = self.load_config()
        
        # Queue for thread-safe output updates
        self.output_queue = queue.Queue()
        
        # Create UI
        self.create_widgets()
        
        # Start output queue processor
        self.process_output_queue()
        
    def load_config(self):
        """Load configuration from config.json"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
        return {}
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="FFR Check GUI", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # Required Arguments Section
        req_frame = ttk.LabelFrame(main_frame, text="Required Arguments", padding="5")
        req_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        req_frame.columnconfigure(1, weight=1)
        
        # Input Directory
        ttk.Label(req_frame, text="Input Directory (FFR):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.input_dir_var = tk.StringVar(value=self.config.get('default_arguments', {}).get('input_dir', '') or '')
        self.input_dir_entry = ttk.Entry(req_frame, textvariable=self.input_dir_var, width=50)
        self.input_dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
        ttk.Button(req_frame, text="Browse...", command=self.browse_input_dir).grid(row=0, column=2, padx=5, pady=3)
        
        # Output Directory
        ttk.Label(req_frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.output_dir_var = tk.StringVar(value=self.config.get('default_arguments', {}).get('output_dir', 'output'))
        self.output_dir_entry = ttk.Entry(req_frame, textvariable=self.output_dir_var, width=50)
        self.output_dir_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
        ttk.Button(req_frame, text="Browse...", command=self.browse_output_dir).grid(row=1, column=2, padx=5, pady=3)
        
        # Optional Arguments Section
        opt_frame = ttk.LabelFrame(main_frame, text="Optional Arguments", padding="5")
        opt_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        opt_frame.columnconfigure(1, weight=1)
        
        # SSPEC
        ttk.Label(opt_frame, text="SSPEC (QDF):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.sspec_var = tk.StringVar(value=self.config.get('default_arguments', {}).get('sspec', '') or '')
        self.sspec_entry = ttk.Entry(opt_frame, textvariable=self.sspec_var, width=50)
        self.sspec_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
        ttk.Label(opt_frame, text="e.g., L15H or L0V8,L0VS,L15E or *", 
                 font=('Arial', 8), foreground='gray').grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # UBE File
        ttk.Label(opt_frame, text="UBE File:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.ube_var = tk.StringVar(value=self.config.get('default_arguments', {}).get('ube', '') or '')
        self.ube_entry = ttk.Entry(opt_frame, textvariable=self.ube_var, width=50)
        self.ube_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
        ttk.Button(opt_frame, text="Browse...", command=self.browse_ube).grid(row=1, column=2, padx=5, pady=3)
        
        # MTL_OLF File
        ttk.Label(opt_frame, text="MTL_OLF.xml:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.mtlolf_var = tk.StringVar(value=self.config.get('default_arguments', {}).get('mtlolf', '') or '')
        self.mtlolf_entry = ttk.Entry(opt_frame, textvariable=self.mtlolf_var, width=50)
        self.mtlolf_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
        ttk.Button(opt_frame, text="Browse...", command=self.browse_mtlolf).grid(row=2, column=2, padx=5, pady=3)
        
        # ITF Directory
        ttk.Label(opt_frame, text="ITF Directory:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=3)
        self.ituff_var = tk.StringVar(value=self.config.get('default_arguments', {}).get('ituff', '') or '')
        self.ituff_entry = ttk.Entry(opt_frame, textvariable=self.ituff_var, width=50)
        self.ituff_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
        ttk.Button(opt_frame, text="Browse...", command=self.browse_ituff).grid(row=3, column=2, padx=5, pady=3)
        
        # VisualID Filter
        ttk.Label(opt_frame, text="VisualID Filter:").grid(row=4, column=0, sticky=tk.W, padx=5, pady=3)
        self.visualid_var = tk.StringVar(value=self.config.get('default_arguments', {}).get('visualid_filter', '') or '')
        self.visualid_entry = ttk.Entry(opt_frame, textvariable=self.visualid_var, width=50)
        self.visualid_entry.grid(row=4, column=1, sticky=(tk.W, tk.E), padx=5, pady=3)
        ttk.Label(opt_frame, text="e.g., U538G05900011 or U538G05900011,U538G09400164", 
                 font=('Arial', 8), foreground='gray').grid(row=4, column=2, sticky=tk.W, padx=5)
        
        # Options Section
        options_frame = ttk.LabelFrame(main_frame, text="Options", padding="5")
        options_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        self.log_var = tk.BooleanVar(value=self.config.get('default_arguments', {}).get('log', False))
        ttk.Checkbutton(options_frame, text="Enable Console Logging", 
                       variable=self.log_var).grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        
        self.html_var = tk.BooleanVar(value=self.config.get('default_arguments', {}).get('html_stats', True))
        ttk.Checkbutton(options_frame, text="Generate HTML Statistics Report", 
                       variable=self.html_var).grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)
        
        # Action Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.run_button = ttk.Button(button_frame, text="Run FFR Check", 
                                     command=self.run_ffr_check, style='Accent.TButton')
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", 
                                      command=self.stop_process, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Clear Output", 
                  command=self.clear_output).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Open Output Folder", 
                  command=self.open_output_folder).pack(side=tk.LEFT, padx=5)
        
        # Output Section
        output_frame = ttk.LabelFrame(main_frame, text="Output", padding="5")
        output_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(5, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD, 
                                                     height=15, font=('Consolas', 9))
        self.output_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        # Process variable
        self.process = None
        
    def browse_input_dir(self):
        directory = filedialog.askdirectory(title="Select Input Directory")
        if directory:
            self.input_dir_var.set(directory)
    
    def browse_output_dir(self):
        directory = filedialog.askdirectory(title="Select Output Directory")
        if directory:
            self.output_dir_var.set(directory)
    
    def browse_ube(self):
        filename = filedialog.askopenfilename(title="Select UBE File",
                                             filetypes=[("UBE files", "*.ube"), ("All files", "*.*")])
        if filename:
            self.ube_var.set(filename)
    
    def browse_mtlolf(self):
        filename = filedialog.askopenfilename(title="Select MTL_OLF.xml File",
                                             filetypes=[("XML files", "*.xml"), ("All files", "*.*")])
        if filename:
            self.mtlolf_var.set(filename)
    
    def browse_ituff(self):
        directory = filedialog.askdirectory(title="Select ITF Directory")
        if directory:
            self.ituff_var.set(directory)
    
    def clear_output(self):
        self.output_text.delete('1.0', tk.END)
    
    def open_output_folder(self):
        output_dir = self.output_dir_var.get() or "output"
        if Path(output_dir).exists():
            import os
            os.startfile(output_dir)
        else:
            messagebox.showwarning("Directory Not Found", 
                                 f"Output directory '{output_dir}' does not exist yet.")
    
    def append_output(self, text):
        """Thread-safe output append"""
        self.output_queue.put(text)
    
    def process_output_queue(self):
        """Process output queue in main thread"""
        try:
            while True:
                text = self.output_queue.get_nowait()
                self.output_text.insert(tk.END, text)
                self.output_text.see(tk.END)
                self.output_text.update_idletasks()
        except queue.Empty:
            pass
        
        # Schedule next check
        self.root.after(100, self.process_output_queue)
    
    def build_command(self):
        """Build the command line arguments"""
        input_dir = self.input_dir_var.get()
        if not input_dir:
            raise ValueError("Input directory is required!")
        
        output_dir = self.output_dir_var.get() or "output"
        
        # Find Python executable
        python_exe = sys.executable
        
        # Build command
        cmd = [python_exe, "-m", "src.main", input_dir, output_dir]
        
        # Add optional arguments
        if self.sspec_var.get():
            cmd.extend(["-sspec", self.sspec_var.get()])
        
        if self.ube_var.get():
            cmd.extend(["-ube", self.ube_var.get()])
        
        if self.mtlolf_var.get():
            cmd.extend(["-mtlolf", self.mtlolf_var.get()])
        
        if self.ituff_var.get():
            cmd.extend(["-ituff", self.ituff_var.get()])
        
        if self.visualid_var.get():
            cmd.extend(["-visualid", self.visualid_var.get()])
        
        if self.log_var.get():
            cmd.append("-log")
        
        if self.html_var.get():
            cmd.append("--html-stats")
        
        return cmd
    
    def run_ffr_check(self):
        """Run the FFR Check process"""
        try:
            cmd = self.build_command()
        except ValueError as e:
            messagebox.showerror("Validation Error", str(e))
            return
        
        # Clear output
        self.clear_output()
        
        # Disable run button, enable stop button
        self.run_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_var.set("Running...")
        
        # Show command
        self.append_output(f"=== Running FFR Check ===\n")
        self.append_output(f"Command: {' '.join(cmd)}\n")
        self.append_output("=" * 80 + "\n\n")
        
        # Run in thread
        thread = threading.Thread(target=self.run_process, args=(cmd,))
        thread.daemon = True
        thread.start()
    
    def run_process(self, cmd):
        """Run the process in a separate thread"""
        try:
            # Set environment variable for UTF-8 encoding
            import os
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=env,
                encoding='utf-8',
                errors='replace'
            )
            
            # Read output line by line
            for line in self.process.stdout:
                self.append_output(line)
            
            # Wait for process to complete
            return_code = self.process.wait()
            
            if return_code == 0:
                self.append_output("\n" + "=" * 80 + "\n")
                self.append_output("=== FFR Check completed successfully! ===\n")
                self.root.after(0, lambda: self.status_var.set("Completed successfully"))
                self.root.after(0, lambda: messagebox.showinfo("Success", 
                    "FFR Check completed successfully!\n\nCheck the output folder for results."))
            else:
                self.append_output("\n" + "=" * 80 + "\n")
                self.append_output(f"=== Process exited with code {return_code} ===\n")
                self.root.after(0, lambda: self.status_var.set(f"Completed with errors (code {return_code})"))
                self.root.after(0, lambda: messagebox.showwarning("Process Completed", 
                    f"Process exited with code {return_code}.\n\nCheck the output for details."))
            
        except Exception as e:
            self.append_output(f"\n=== ERROR ===\n{str(e)}\n")
            self.root.after(0, lambda: self.status_var.set("Error"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred:\n{str(e)}"))
        
        finally:
            # Re-enable buttons
            self.root.after(0, lambda: self.run_button.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
            self.process = None
    
    def stop_process(self):
        """Stop the running process"""
        if self.process:
            self.process.terminate()
            self.append_output("\n=== Process terminated by user ===\n")
            self.status_var.set("Stopped")
            self.run_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)


def main():
    # Headless support: if INPUT_DIR or other env vars are provided,
    # run processing without starting the Tk GUI.
    def env_truthy(v):
        return str(v).lower() in ('1', 'true', 'yes', 'on')

    def build_command_from_env(env):
        input_dir = env.get('INPUT_DIR')
        if not input_dir:
            return None

        output_dir = env.get('OUTPUT_DIR') or 'output'

        python_exe = sys.executable
        cmd = [python_exe, '-m', 'src.main', input_dir, output_dir]

        if env.get('SSPEC'):
            cmd.extend(['-sspec', env.get('SSPEC')])
        if env.get('UBE'):
            cmd.extend(['-ube', env.get('UBE')])
        if env.get('MTLOLF'):
            cmd.extend(['-mtlolf', env.get('MTLOLF')])
        if env.get('ITUFF'):
            cmd.extend(['-ituff', env.get('ITUFF')])
        if env.get('VISUALID'):
            cmd.extend(['-visualid', env.get('VISUALID')])

        if env_truthy(env.get('LOG')):
            cmd.append('-log')
        # HTML stats default is True in GUI; only add flag if explicitly truthy
        if env.get('HTML_STATS') is not None:
            if env_truthy(env.get('HTML_STATS')):
                cmd.append('--html-stats')

        return cmd

    def run_headless_from_env():
        env = os.environ
        cmd = build_command_from_env(env)
        if not cmd:
            return False

        print('=== Running headless FFR Check ===')
        print('Command:', ' '.join(cmd))

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=os.environ)
        for line in proc.stdout:
            print(line, end='')
        rc = proc.wait()
        if rc == 0:
            print('=== Completed successfully ===')
        else:
            print(f'=== Completed with code {rc} ===')
        return True

    # If environment contains an INPUT_DIR (or related), run headless and exit
    if os.environ.get('INPUT_DIR'):
        ran = run_headless_from_env()
        if ran:
            sys.exit(0)

    root = tk.Tk()

    # Set theme
    style = ttk.Style()
    try:
        style.theme_use('clam')  # Use a modern theme
    except:
        pass

    app = FFRCheckGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
