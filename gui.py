import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import sys
import os
from pathlib import Path
from typing import List, Optional
import threading
import queue
import pystray
from PIL import Image, ImageTk
import json
from config import Config, PRESET_PROFILES
import image_to_webp
import logging
import tkinterdnd2 as tkdnd
from concurrent.futures import ThreadPoolExecutor

class WebPConverterGUI:
    def __init__(self):
        self.config = Config()
        self.setup_logging()
        
        # Initialize main window
        self.root = tkdnd.Tk()
        self.root.title("Image to WebP Converter")
        self.root.geometry("1024x768")  # Larger default size
        self.root.minsize(800, 600)     # Set minimum window size
        self.root.protocol('WM_DELETE_WINDOW', self.on_closing)
        
        # Set application icon
        if getattr(sys, 'frozen', False):
            # Running in a bundle
            base_path = os.path.dirname(sys.executable)
        else:
            # Running in normal Python environment
            base_path = os.path.dirname(__file__)
        
        icon_path = os.path.join(base_path, "assets", "logo-square.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
                self.icon_photo = Image.open(icon_path)
            except Exception as e:
                logging.error(f"Failed to load icon: {e}")
        
        # Configure dark theme colors
        self.COLORS = {
            'bg': '#282828',
            'fg': '#ffffff',
            'accent': '#473CF3',  # Vibrant orange
            'accent_dark': '#cc4c00',  # Darker orange for hover states
            'gray_accent': '#404040',  # Keep some elements gray
            'highlight': '#505050',
            'button': '#383838',
            'button_pressed': '#484848',
            'border': '#404040',
            'selection': '#505050'
        }
        
        # Configure fonts
        default_font = ('Segoe UI', 10)
        header_font = ('Segoe UI', 11, 'bold')
        
        # Configure dark theme
        self.root.configure(bg=self.COLORS['bg'])
        style = ttk.Style()
        style.theme_use('default')  # Reset to default theme first
        
        # Configure common elements
        style.configure('.',
            background=self.COLORS['bg'],
            foreground=self.COLORS['fg'],
            fieldbackground=self.COLORS['bg'],
            font=default_font
        )
        
        # Configure specific elements
        style.configure('TFrame', background=self.COLORS['bg'])
        style.configure('TLabel', background=self.COLORS['bg'], foreground=self.COLORS['fg'])
        style.configure('TLabelframe', 
            background=self.COLORS['bg'], 
            foreground=self.COLORS['fg'],
            bordercolor=self.COLORS['border']
        )
        style.configure('TLabelframe.Label', 
            background=self.COLORS['bg'],
            foreground=self.COLORS['fg'],
            font=header_font
        )
        
        # Configure buttons
        style.configure('TButton',
            background=self.COLORS['button'],
            foreground=self.COLORS['fg'],
            bordercolor=self.COLORS['border'],
            focuscolor=self.COLORS['accent'],
            lightcolor=self.COLORS['button'],
            darkcolor=self.COLORS['button'],
            relief='flat',
            padding=5
        )
        style.map('TButton',
            background=[('pressed', self.COLORS['button_pressed']), 
                       ('active', self.COLORS['highlight'])],
            bordercolor=[('focus', self.COLORS['accent'])]
        )
        
        # Configure combobox
        style.configure('TCombobox',
            background=self.COLORS['gray_accent'],
            foreground=self.COLORS['fg'],
            fieldbackground=self.COLORS['gray_accent'],
            arrowcolor=self.COLORS['fg'],
            bordercolor=self.COLORS['border'],
            lightcolor=self.COLORS['gray_accent'],
            darkcolor=self.COLORS['gray_accent']
        )
        style.map('TCombobox',
            fieldbackground=[('readonly', self.COLORS['gray_accent'])],
            selectbackground=[('readonly', self.COLORS['selection'])]
        )
        
        # Configure entry
        style.configure('TEntry',
            fieldbackground=self.COLORS['gray_accent'],
            foreground=self.COLORS['fg'],
            bordercolor=self.COLORS['border'],
            lightcolor=self.COLORS['gray_accent'],
            darkcolor=self.COLORS['gray_accent']
        )
        
        # Configure scrollbar
        style.configure('Vertical.TScrollbar',
            background=self.COLORS['gray_accent'],
            bordercolor=self.COLORS['border'],
            arrowcolor=self.COLORS['fg'],
            troughcolor=self.COLORS['bg'],
            lightcolor=self.COLORS['gray_accent'],
            darkcolor=self.COLORS['gray_accent']
        )
        
        # Configure scale (slider)
        style.configure('Horizontal.TScale',
            background=self.COLORS['bg'],
            troughcolor=self.COLORS['gray_accent'],
            lightcolor=self.COLORS['accent'],
            darkcolor=self.COLORS['accent']
        )
        
        # Configure checkbutton
        style.configure('TCheckbutton',
            background=self.COLORS['bg'],
            foreground=self.COLORS['fg']
        )
        style.map('TCheckbutton',
            background=[('active', self.COLORS['bg'])],
            foreground=[('active', self.COLORS['fg'])],
            indicatorcolor=[('selected', self.COLORS['accent']),
                          ('pressed', self.COLORS['accent_dark'])]
        )
        
        # Configure progressbar
        style.configure('Horizontal.TProgressbar',
            background=self.COLORS['accent'],
            troughcolor=self.COLORS['gray_accent']
        )
        
        # Queue for communication between threads
        self.queue = queue.Queue()
        
        # Create thread pool for conversions
        self.thread_pool = ThreadPoolExecutor(max_workers=4)
        
        # Track active conversions and progress
        self.active_conversions = 0
        self.conversion_lock = threading.Lock()
        self.total_files = 0
        self.processed_files = 0
        self.pending_files = []
        self.is_converting = False
        self.stop_requested = False
        
        self.preview_after_id = None  # For debouncing preview updates
        
        self.setup_ui()
        self.setup_tray()
        
        # Start queue processing
        self.process_queue()

    def setup_logging(self):
        """Configure logging for the GUI application"""
        self.log_queue = queue.Queue()
        queue_handler = QueueHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        queue_handler.setFormatter(formatter)
        logging.getLogger().addHandler(queue_handler)
        logging.getLogger().setLevel(logging.INFO)
    
    def setup_ui(self):
        """Set up the main user interface"""
        # Update text widget colors
        text_opts = {
            'bg': self.COLORS['bg'],
            'fg': self.COLORS['fg'],
            'insertbackground': self.COLORS['fg'],
            'selectbackground': self.COLORS['selection'],
            'selectforeground': self.COLORS['fg'],
            'relief': 'flat',
            'borderwidth': 0
        }
        
        # Update canvas colors
        canvas_opts = {
            'bg': self.COLORS['bg'],
            'highlightthickness': 0,
            'borderwidth': 0
        }
        
        # Create main container with padding
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Create left and right columns with proper weights
        left_column = ttk.Frame(main_container)
        left_column.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        right_column = ttk.Frame(main_container)
        right_column.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        main_container.columnconfigure(0, weight=3)  # Left column takes 3/4
        main_container.columnconfigure(1, weight=1)  # Right column takes 1/4
        main_container.rowconfigure(0, weight=1)

        # Make both columns expand vertically
        left_column.rowconfigure(1, weight=1)  # Log frame expands
        right_column.rowconfigure(0, weight=1) # Settings frame expands

        # Left Column: Drop zone and Log
        # Drop zone
        self.drop_frame = ttk.LabelFrame(left_column, text="Drop Files Here", padding="20")
        self.drop_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        left_column.columnconfigure(0, weight=1)
        left_column.rowconfigure(0, weight=1)

        self.drop_label = ttk.Label(
            self.drop_frame,
            text="Drag and drop images or folders here\nor click to select files",
            justify=tk.CENTER
        )
        self.drop_label.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.drop_frame.columnconfigure(0, weight=1)
        self.drop_frame.rowconfigure(0, weight=1)

        # Configure drop zone
        self.drop_frame.drop_target_register(tkdnd.DND_FILES)
        self.drop_frame.dnd_bind('<<Drop>>', self.handle_drop)
        self.drop_frame.bind('<Button-1>', self.select_files)
        self.drop_label.bind('<Button-1>', self.select_files)

        # Log frame below drop zone
        log_frame = ttk.LabelFrame(left_column, text="Log", padding="10")
        log_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        left_column.rowconfigure(1, weight=2)  # Log takes more space than drop zone

        self.log_text = tk.Text(log_frame, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text['yscrollcommand'] = scrollbar.set

        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # Configure log text widget with dark theme
        self.log_text.configure(**text_opts)

        # Right Column: Settings and Progress
        settings_frame = ttk.LabelFrame(right_column, text="Settings", padding="10")
        settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 5))
        right_column.columnconfigure(0, weight=1)

        # Profile selection with better spacing
        profile_frame = ttk.Frame(settings_frame)
        profile_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        profile_frame.columnconfigure(1, weight=1)

        ttk.Label(profile_frame, text="Profile:").grid(row=0, column=0, sticky=tk.W)
        self.profile_var = tk.StringVar(value=self.config.config['default_profile'])
        self.profile_combo = ttk.Combobox(profile_frame, textvariable=self.profile_var)
        self.update_profile_list()
        self.profile_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        self.profile_combo.bind('<<ComboboxSelected>>', self.on_profile_changed)

        # Quality setting with label
        quality_frame = ttk.Frame(settings_frame)
        quality_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        quality_frame.columnconfigure(1, weight=1)

        ttk.Label(quality_frame, text="Quality:").grid(row=0, column=0, sticky=tk.W)
        self.quality_var = tk.IntVar(value=PRESET_PROFILES[self.profile_var.get()]['quality'])
        quality_scale = ttk.Scale(quality_frame, from_=1, to=100, orient=tk.HORIZONTAL,
                                variable=self.quality_var)
        quality_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        quality_scale.bind('<ButtonRelease-1>', self.on_quality_changed)
        ttk.Label(quality_frame, textvariable=self.quality_var).grid(row=0, column=2, padx=(5, 0))

        # Output directory
        output_frame = ttk.Frame(settings_frame)
        output_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)

        ttk.Label(output_frame, text="Output:").grid(row=0, column=0, sticky=tk.W)
        self.output_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_var).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(output_frame, text="Browse", command=self.select_output_dir).grid(row=0, column=2)

        # File naming options
        naming_frame = ttk.Frame(settings_frame)
        naming_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        naming_frame.columnconfigure(1, weight=1)

        ttk.Label(naming_frame, text="Prefix:").grid(row=0, column=0, sticky=tk.W)
        self.prefix_var = tk.StringVar()
        prefix_entry = ttk.Entry(naming_frame, textvariable=self.prefix_var)
        prefix_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        prefix_entry.bind('<KeyRelease>', self.on_name_option_changed)

        ttk.Label(naming_frame, text="Suffix:").grid(row=1, column=0, sticky=tk.W)
        self.suffix_var = tk.StringVar()
        suffix_entry = ttk.Entry(naming_frame, textvariable=self.suffix_var)
        suffix_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=5, pady=2)
        suffix_entry.bind('<KeyRelease>', self.on_name_option_changed)

        # Checkboxes in a grid
        options_frame = ttk.Frame(settings_frame)
        options_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        options_frame.columnconfigure((0, 1), weight=1)

        self.lossless_var = tk.BooleanVar(value=PRESET_PROFILES[self.profile_var.get()]['lossless'])
        self.preserve_timestamps_var = tk.BooleanVar(value=PRESET_PROFILES[self.profile_var.get()]['preserve_timestamps'])
        self.keep_original_var = tk.BooleanVar(value=PRESET_PROFILES[self.profile_var.get()]['preserve_originals'])
        self.recursive_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(options_frame, text="Lossless", variable=self.lossless_var,
                       command=lambda: self.on_setting_changed("Lossless", self.lossless_var.get())).grid(row=0, column=0, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Preserve Timestamps", variable=self.preserve_timestamps_var,
                       command=lambda: self.on_setting_changed("Preserve Timestamps", self.preserve_timestamps_var.get())).grid(row=0, column=1, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Keep Originals", variable=self.keep_original_var,
                       command=lambda: self.on_setting_changed("Keep Originals", self.keep_original_var.get())).grid(row=1, column=0, sticky=tk.W)
        ttk.Checkbutton(options_frame, text="Process Subdirectories", variable=self.recursive_var,
                       command=lambda: self.on_setting_changed("Process Subdirectories", self.recursive_var.get())).grid(row=1, column=1, sticky=tk.W)

        # Profile management buttons at the bottom
        profile_buttons = ttk.Frame(settings_frame)
        profile_buttons.grid(row=5, column=0, sticky=(tk.W, tk.E), pady=(10, 0))
        profile_buttons.columnconfigure((0, 1, 2), weight=1)

        ttk.Button(profile_buttons, text="Save Profile", command=self.save_profile).grid(row=0, column=0, padx=2, sticky=(tk.W, tk.E))
        ttk.Button(profile_buttons, text="Set Default", command=self.set_default_profile).grid(row=0, column=1, padx=2, sticky=(tk.W, tk.E))
        ttk.Button(profile_buttons, text="Use Last", command=self.use_last_settings).grid(row=0, column=2, padx=2, sticky=(tk.W, tk.E))

        # Progress frame at the bottom of right column
        progress_frame = ttk.LabelFrame(right_column, text="Progress", padding="10")
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))

        # Control buttons frame
        control_frame = ttk.Frame(progress_frame)
        control_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        control_frame.columnconfigure((0, 1), weight=1)

        self.start_button = ttk.Button(
            control_frame,
            text="Start Conversion",
            command=self.start_conversion,
            state=tk.DISABLED
        )
        self.start_button.grid(row=0, column=0, padx=2, sticky=(tk.W, tk.E))

        self.stop_button = ttk.Button(
            control_frame,
            text="Stop",
            command=self.stop_conversion,
            state=tk.DISABLED
        )
        self.stop_button.grid(row=0, column=1, padx=2, sticky=(tk.W, tk.E))

        progress_frame.columnconfigure(0, weight=1)
    
    def setup_tray(self):
        """Set up system tray icon and menu"""
        menu = (
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem("Exit", self.quit_app)
        )
        
        if getattr(sys, 'frozen', False):
            # Running in a bundle
            base_path = os.path.dirname(sys.executable)
        else:
            # Running in normal Python environment
            base_path = os.path.dirname(__file__)
        
        icon_path = os.path.join(base_path, "assets", "logo-square.ico")
        self.tray_icon = pystray.Icon(
            "WebP Converter",
            Image.open(icon_path),
            "WebP Converter",
            menu=pystray.Menu(*menu)
        )
        
    def show_window(self, _=None):
        """Show the main window"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        
    def hide_window(self):
        """Hide the main window."""
        self.root.withdraw()
        self.create_tray_icon()

    def quit_app(self, icon=None):
        """Properly quit the application."""
        try:
            # Shutdown thread pool
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)
            
            # Stop the tray icon if it exists
            if hasattr(self, 'icon') and self.icon:
                self.icon.stop()
            
            # Destroy all windows and quit
            if self.root:
                self.root.quit()
                self.root.destroy()
        except:
            pass
        finally:
            # Ensure the application exits
            sys.exit(0)

    def on_closing(self):
        """Handle window closing event."""
        self.quit_app()

    def handle_drop(self, event):
        """Handle dropped files"""
        files = self.parse_dropped_files(event.data)
        self.process_files(files)
    
    def parse_dropped_files(self, data: str) -> List[str]:
        """Parse dropped files data"""
        # Handle different formats of dropped data
        if '{' in data:  # Windows format
            files = data.split('} {')
            files = [f.strip('{}') for f in files]
        else:  # Unix format
            files = data.split()
        return files
    
    def select_files(self, _=None):
        """Open file dialog to select files"""
        files = filedialog.askopenfilenames(
            title="Select Images",
            filetypes=[
                ("Image files", "*.png;*.jpg;*.jpeg"),
                ("All files", "*.*")
            ]
        )
        if files:
            self.process_files(files)
    
    def show_error(self, title: str, message: str):
        """Show error dialog"""
        messagebox.showerror(title, message)
        self.queue.put(('log', f"Error: {message}"))

    def process_files(self, files: List[str]):
        """Process the selected or dropped files"""
        if not files:
            self.show_error("Error", "No files selected")
            return

        # Reset progress tracking and clear pending files
        with self.conversion_lock:
            self.total_files = 0
            self.processed_files = 0
            self.active_conversions = 0
            self.pending_files = []
            self.is_converting = False
            self.stop_requested = False

        # Get current settings
        try:
            profile = self.profile_var.get()
            settings = {
                'quality': self.quality_var.get(),
                'lossless': self.lossless_var.get(),
                'preserve_timestamps': self.preserve_timestamps_var.get(),
                'preserve_originals': self.keep_original_var.get(),
                'recursive': self.recursive_var.get(),
                'output_dir': self.output_var.get(),
                'prefix': self.prefix_var.get(),
                'suffix': self.suffix_var.get()
            }
            
            # Save as last used settings
            self.save_last_settings(settings)
            
            # Clear previous log entries with a separator
            self.queue.put(('log', "\n" + "-"*50 + "\n"))
            self.queue.put(('log', "Processing new files..."))
            
            # Count total files and collect file paths
            for file_path in files:
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in image_to_webp.SUPPORTED_FORMATS:
                        with self.conversion_lock:
                            self.total_files += 1
                            # Prepare output path
                            if settings['output_dir']:
                                input_filename = os.path.basename(file_path)
                                output_filename = self.get_output_filename(
                                    input_filename, 
                                    settings['prefix'], 
                                    settings['suffix']
                                )
                                output_path = os.path.join(settings['output_dir'], output_filename)
                            else:
                                input_filename = os.path.basename(file_path)
                                output_filename = self.get_output_filename(
                                    input_filename,
                                    settings['prefix'],
                                    settings['suffix']
                                )
                                output_path = str(Path(os.path.dirname(file_path)) / output_filename)
                            self.pending_files.append((file_path, output_path))
                    else:
                        self.queue.put(('log', f"Skipping unsupported file: {file_path}"))
                        
                elif os.path.isdir(file_path) and self.recursive_var.get():
                    self.queue.put(('log', f"Scanning directory: {file_path}"))
                    for root, _, filenames in os.walk(file_path):
                        for filename in filenames:
                            if os.path.splitext(filename)[1].lower() in image_to_webp.SUPPORTED_FORMATS:
                                file_path = os.path.join(root, filename)
                                with self.conversion_lock:
                                    self.total_files += 1
                                    # Prepare output path
                                    if settings['output_dir']:
                                        rel_path = os.path.relpath(file_path, os.path.dirname(file_path))
                                        output_path = os.path.join(settings['output_dir'], rel_path)
                                        output_path = str(Path(output_path).with_suffix('.webp'))
                                    else:
                                        output_path = None
                                    self.pending_files.append((file_path, output_path))
                else:
                    self.queue.put(('log', f"Skipping {file_path}: {'not a supported file or directory' if not os.path.isdir(file_path) else 'recursive processing disabled'}"))
            
            # Log settings and status
            self.queue.put(('log', f"\nFound {self.total_files} files to convert"))
            self.queue.put(('log', f"Using profile: {profile}"))
            self.queue.put(('log', f"Current settings:"))
            self.queue.put(('log', f"  - Quality: {settings['quality']}"))
            self.queue.put(('log', f"  - Lossless: {settings['lossless']}"))
            self.queue.put(('log', f"  - Preserve Timestamps: {settings['preserve_timestamps']}"))
            self.queue.put(('log', f"  - Keep Originals: {settings['preserve_originals']}"))
            self.queue.put(('log', f"  - Process Subdirectories: {settings['recursive']}"))
            self.queue.put(('log', f"  - Output directory: {settings['output_dir'] or 'Same as input (replace)'}\n"))
            
            # Enable start button if files were found
            if self.total_files > 0:
                self.start_button.configure(state=tk.NORMAL)
                self.queue.put(('log', "Ready to start conversion. Click 'Start Conversion' to begin."))
                self.queue.put(('log', "You can adjust settings before starting the conversion."))
            else:
                self.queue.put(('log', "No supported files found for conversion."))
            
        except Exception as e:
            self.show_error("Error", f"Failed to process files: {str(e)}")

    def start_conversion(self):
        """Start the conversion process"""
        if not self.pending_files or self.is_converting:
            return

        # Get current settings at start time
        settings = {
            'quality': self.quality_var.get(),
            'lossless': self.lossless_var.get(),
            'preserve_timestamps': self.preserve_timestamps_var.get(),
            'preserve_originals': self.keep_original_var.get(),
            'recursive': self.recursive_var.get(),
            'output_dir': self.output_var.get(),
            'prefix': self.prefix_var.get(),
            'suffix': self.suffix_var.get()
        }

        # Log final settings before starting
        self.queue.put(('log', "\nStarting conversion with final settings:"))
        self.queue.put(('log', f"  - Quality: {settings['quality']}"))
        self.queue.put(('log', f"  - Lossless: {settings['lossless']}"))
        self.queue.put(('log', f"  - Preserve Timestamps: {settings['preserve_timestamps']}"))
        self.queue.put(('log', f"  - Keep Originals: {settings['preserve_originals']}"))
        self.queue.put(('log', f"  - Process Subdirectories: {settings['recursive']}"))
        output_display = settings['output_dir'] if settings['output_dir'] else 'Same as input (replace)'
        self.queue.put(('log', f"  - Output directory: {os.path.basename(output_display) if settings['output_dir'] else output_display}"))
        if settings['prefix'] or settings['suffix']:
            example = self.get_output_filename("example.jpg", settings['prefix'], settings['suffix'])
            self.queue.put(('log', f"  - Filename pattern: {example}\n"))
        else:
            self.queue.put(('log', ""))

        # Update UI state
        self.is_converting = True
        self.stop_requested = False
        self.start_button.configure(state=tk.DISABLED)
        self.stop_button.configure(state=tk.NORMAL)

        # Initialize conversion tracking
        total_converted = {'success': 0, 'error': 0}

        # Process each file
        for file_path, output_path in self.pending_files:
            if self.stop_requested:
                break

            # Skip files in subdirectories if recursive is disabled
            if not settings['recursive'] and os.path.dirname(file_path) != os.path.dirname(self.pending_files[0][0]):
                self.queue.put(('log', f"Skipping {os.path.basename(file_path)}: in subdirectory"))
                with self.conversion_lock:
                    self.processed_files += 1
                    progress = (self.processed_files / self.total_files) * 100
                    self.queue.put(('progress', progress))
                continue

            # Start conversion in thread pool
            with self.conversion_lock:
                self.active_conversions += 1
            self.thread_pool.submit(
                self.convert_files_thread,
                [file_path],
                settings,
                output_path,
                total_converted
            )

    def stop_conversion(self):
        """Stop the conversion process"""
        if not self.is_converting:
            return

        self.stop_requested = True
        self.queue.put(('log', "Stopping conversion... Please wait for current operations to complete."))
        self.stop_button.configure(state=tk.DISABLED)

    def convert_files_thread(self, files: List[str], settings: dict, output_path: Optional[str] = None, total_converted: dict = None):
        """Convert files in a separate thread"""
        if self.stop_requested:
            with self.conversion_lock:
                self.active_conversions -= 1
                if self.active_conversions == 0:
                    self.finish_conversion(total_converted)
            return

        try:
            for file_path in files:
                if self.stop_requested:
                    break

                try:
                    # Generate output path with prefix/suffix if not provided
                    if not output_path:
                        input_filename = os.path.basename(file_path)
                        output_filename = self.get_output_filename(
                            input_filename,
                            settings.get('prefix', ''),
                            settings.get('suffix', '')
                        )
                        output_path = str(Path(os.path.dirname(file_path)) / output_filename)

                    success, input_path, result = image_to_webp.convert_to_webp(
                        file_path,
                        output_path=output_path,
                        quality=settings['quality'],
                        preserve_timestamps=settings['preserve_timestamps'],
                        lossless=settings['lossless'],
                        prefix=settings.get('prefix', ''),
                        suffix=settings.get('suffix', '')
                    )
                    
                    with self.conversion_lock:
                        self.processed_files += 1
                        progress = (self.processed_files / self.total_files) * 100
                        self.queue.put(('progress', progress))
                    
                    # Get relative paths for cleaner logging
                    input_name = os.path.basename(input_path)
                    result_name = os.path.basename(result) if result else None

                    if success:
                        with self.conversion_lock:
                            total_converted['success'] += 1
                        size_before = os.path.getsize(input_path)
                        size_after = os.path.getsize(result)
                        reduction = ((size_before - size_after) / size_before) * 100
                        
                        self.queue.put(('log', f" {input_name} → {result_name} ({reduction:.1f}% smaller)"))
                        
                        if not settings['preserve_originals']:
                            try:
                                os.remove(input_path)
                                self.queue.put(('log', f"  Original deleted"))
                            except Exception as e:
                                self.queue.put(('log', f"  Failed to delete original: {str(e)}"))
                    else:
                        with self.conversion_lock:
                            total_converted['error'] += 1
                        self.queue.put(('log', f" {input_name}: {result}"))
                
                except Exception as e:
                    with self.conversion_lock:
                        total_converted['error'] += 1
                        self.processed_files += 1
                        progress = (self.processed_files / self.total_files) * 100
                        self.queue.put(('progress', progress))
                    self.queue.put(('log', f" {os.path.basename(file_path)}: {str(e)}"))
            
        except Exception as e:
            self.queue.put(('log', f"Critical error during conversion: {str(e)}"))
            self.show_error("Error", f"Critical error during conversion: {str(e)}")
        finally:
            with self.conversion_lock:
                self.active_conversions -= 1
                if self.active_conversions == 0:
                    self.finish_conversion(total_converted)

    def finish_conversion(self, total_converted: dict):
        """Clean up after conversion is complete"""
        self.queue.put(('progress', 0))
        self.is_converting = False
        self.stop_requested = False
        self.start_button.configure(state=tk.NORMAL if self.total_files > self.processed_files else tk.DISABLED)
        self.stop_button.configure(state=tk.DISABLED)

        # Show final summary
        if self.processed_files > 0:
            summary = f"Conversion {'stopped' if self.stop_requested else 'completed'}!\n"
            summary += f"Successfully converted: {total_converted['success']} items\n"
            if total_converted['error'] > 0:
                summary += f"Failed to convert: {total_converted['error']} items"
                self.queue.put(('show_warning', ("Conversion Status", summary)))
            else:
                self.queue.put(('show_info', ("Conversion Status", summary)))

        # Clear pending files if all were processed
        if self.processed_files >= self.total_files:
            self.pending_files = []
    
    def on_quality_changed(self, *args):
        """Update quality label when slider moves"""
        self.queue.put(('log', f"Quality set to: {self.quality_var.get()}"))
    
    def on_profile_changed(self, event=None):
        """Update settings when profile is changed"""
        profile = self.profile_var.get()
        if profile in PRESET_PROFILES:
            settings = PRESET_PROFILES[profile]
        else:
            settings = self.config.config['custom_profiles'][profile]
        
        # Update all settings
        self.quality_var.set(settings['quality'])
        self.lossless_var.set(settings['lossless'])
        self.preserve_timestamps_var.set(settings['preserve_timestamps'])
        self.keep_original_var.set(settings['preserve_originals'])
        if 'recursive' in settings:
            self.recursive_var.set(settings['recursive'])
        if 'output_dir' in settings:
            self.output_var.set(settings['output_dir'])
        
        # Log changes
        self.queue.put(('log', f"\nProfile changed to: {profile}"))
        self.queue.put(('log', f"New settings: Quality={settings['quality']}, "
                            f"Lossless={settings['lossless']}, "
                            f"Preserve Timestamps={settings['preserve_timestamps']}, "
                            f"Keep Originals={settings['preserve_originals']}, "
                            f"Recursive={settings.get('recursive', True)}, "
                            f"Output directory={settings.get('output_dir', '')}"))
    
    def select_output_dir(self):
        """Open directory selection dialog for output"""
        directory = filedialog.askdirectory()
        if directory:
            self.output_var.set(directory)
            self.queue.put(('log', f"Output directory set to: {directory}"))
    
    def update_profile_list(self):
        """Update the profile dropdown with all available profiles"""
        profiles = list(PRESET_PROFILES.keys()) + list(self.config.config['custom_profiles'].keys())
        self.profile_combo['values'] = profiles
        
    def save_profile(self):
        """Save current settings as a new profile"""
        name = simpledialog.askstring("Save Profile", "Enter profile name:")
        if name:
            if name in PRESET_PROFILES:
                self.show_error("Error", "Cannot overwrite preset profiles")
                return
                
            settings = {
                'quality': self.quality_var.get(),
                'lossless': self.lossless_var.get(),
                'preserve_timestamps': self.preserve_timestamps_var.get(),
                'preserve_originals': self.keep_original_var.get(),
                'recursive': self.recursive_var.get(),
                'output_dir': self.output_var.get()
            }
            
            self.config.config['custom_profiles'][name] = settings
            self.config.save_config()
            self.update_profile_list()
            self.profile_var.set(name)
            self.queue.put(('log', f"Saved profile: {name}"))
            
    def set_default_profile(self):
        """Set current profile as default"""
        profile = self.profile_var.get()
        # Save current settings before setting as default
        settings = {
            'quality': self.quality_var.get(),
            'lossless': self.lossless_var.get(),
            'preserve_timestamps': self.preserve_timestamps_var.get(),
            'preserve_originals': self.keep_original_var.get(),
            'recursive': self.recursive_var.get(),
            'output_dir': self.output_var.get()
        }
        if profile in PRESET_PROFILES:
            # For preset profiles, save current settings as a custom profile
            custom_name = f"{profile}_custom"
            self.config.config['custom_profiles'][custom_name] = settings
            self.config.set_default_profile(custom_name)
            self.update_profile_list()
            self.profile_var.set(custom_name)
            self.queue.put(('log', f"Created custom profile '{custom_name}' from '{profile}' and set as default"))
        else:
            # Update existing custom profile with current settings
            self.config.config['custom_profiles'][profile] = settings
            self.config.set_default_profile(profile)
            self.queue.put(('log', f"Updated and set default profile to: {profile}"))
        self.config.save_config()
        
    def use_last_settings(self):
        """Load last used settings"""
        last_settings = self.config.config.get('last_used_settings')
        if last_settings:
            self.quality_var.set(last_settings['quality'])
            self.lossless_var.set(last_settings['lossless'])
            self.preserve_timestamps_var.set(last_settings['preserve_timestamps'])
            self.keep_original_var.set(last_settings['preserve_originals'])
            if 'recursive' in last_settings:
                self.recursive_var.set(last_settings['recursive'])
            if 'output_dir' in last_settings:
                self.output_var.set(last_settings['output_dir'])
            self.queue.put(('log', "Loaded last used settings"))
        else:
            self.show_error("Error", "No last used settings found")

    def save_last_settings(self, settings: dict):
        """Save current settings as last used"""
        full_settings = settings.copy()
        full_settings.update({
            'recursive': self.recursive_var.get(),
            'output_dir': self.output_var.get()
        })
        self.config.config['last_used_settings'] = full_settings
        self.config.save_config()
    
    def on_setting_changed(self, setting_name: str, value: bool):
        """Handle changes to boolean settings"""
        self.queue.put(('log', f"{setting_name} {'enabled' if value else 'disabled'}"))
    
    def on_name_option_changed(self, event=None):
        """Handle changes to filename prefix/suffix with debounce"""
        # Cancel any pending preview update
        if self.preview_after_id:
            self.root.after_cancel(self.preview_after_id)
        
        # Schedule new preview update after 500ms
        self.preview_after_id = self.root.after(500, self.update_filename_preview)
    
    def update_filename_preview(self):
        """Update the filename preview in the log"""
        prefix = self.prefix_var.get()
        suffix = self.suffix_var.get()
        if prefix or suffix:
            example = self.get_output_filename("example.jpg", prefix, suffix)
            self.queue.put(('log', f"Filename pattern: {example}"))

    def get_output_filename(self, input_filename: str, prefix: str = "", suffix: str = "") -> str:
        """Generate output filename with prefix and suffix"""
        name, _ = os.path.splitext(input_filename)
        return f"{prefix}{name}{suffix}.webp"
    
    def process_queue(self):
        """Process messages from the queue"""
        try:
            while True:
                msg_type, msg = self.queue.get_nowait()
                if msg_type == 'log':
                    self.log_text.insert(tk.END, msg + '\n')
                    self.log_text.see(tk.END)
                elif msg_type == 'progress':
                    self.progress_var.set(msg)
                elif msg_type == 'show_warning':
                    messagebox.showwarning(*msg)
                elif msg_type == 'show_info':
                    messagebox.showinfo(*msg)
        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)
    
    def run(self):
        """Start the application"""
        self.root.mainloop()


class QueueHandler(logging.Handler):
    """Handler to redirect logging messages to a queue"""
    def __init__(self, queue):
        super().__init__()
        self.queue = queue
    
    def emit(self, record):
        self.queue.put(('log', self.format(record)))


def main():
    app = WebPConverterGUI()
    app.run()


if __name__ == '__main__':
    main()
