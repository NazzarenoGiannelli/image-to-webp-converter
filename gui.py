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

class WebPConverterGUI:
    def __init__(self):
        self.config = Config()
        self.setup_logging()
        
        # Initialize main window
        self.root = tkdnd.Tk()
        self.root.title("Image to WebP Converter")
        self.root.geometry("1024x768")  # Larger default size
        self.root.minsize(800, 600)     # Set minimum window size
        self.root.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)
        
        # Set application icon
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "logo-square.ico")
        if os.path.exists(icon_path):
            self.root.iconbitmap(icon_path)
            self.icon_photo = Image.open(icon_path)
        
        # Configure dark theme colors
        self.COLORS = {
            'bg': '#282828',
            'fg': '#ffffff',
            'accent': '#ff5f00',  # Vibrant orange
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
        
        # Track active conversions
        self.active_conversions = 0
        self.conversion_lock = threading.Lock()
        
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

        # Right Column: Settings and Progress (now in a scrollable frame)
        # Create a canvas with scrollbar for settings
        canvas = tk.Canvas(right_column)
        scrollbar = ttk.Scrollbar(right_column, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=canvas.winfo_reqwidth())
        
        # Configure canvas with dark theme
        canvas.configure(**canvas_opts)

        # Configure canvas to expand with window
        canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        canvas.configure(yscrollcommand=scrollbar.set)
        right_column.columnconfigure(0, weight=1)

        # Settings frame inside scrollable frame
        settings_frame = ttk.LabelFrame(scrollable_frame, text="Settings", padding="10")
        settings_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0, 5))
        scrollable_frame.columnconfigure(0, weight=1)

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

        # Profile management buttons in a horizontal frame with wrapping
        profile_buttons = ttk.Frame(settings_frame)
        profile_buttons.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        profile_buttons.columnconfigure((0, 1, 2), weight=1)

        ttk.Button(profile_buttons, text="Save Profile", command=self.save_profile).grid(row=0, column=0, padx=2, sticky=(tk.W, tk.E))
        ttk.Button(profile_buttons, text="Set Default", command=self.set_default_profile).grid(row=0, column=1, padx=2, sticky=(tk.W, tk.E))
        ttk.Button(profile_buttons, text="Use Last", command=self.use_last_settings).grid(row=0, column=2, padx=2, sticky=(tk.W, tk.E))

        # Quality setting with label
        quality_frame = ttk.Frame(settings_frame)
        quality_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        quality_frame.columnconfigure(1, weight=1)

        ttk.Label(quality_frame, text="Quality:").grid(row=0, column=0, sticky=tk.W)
        self.quality_var = tk.IntVar(value=PRESET_PROFILES[self.profile_var.get()]['quality'])
        self.quality_label = ttk.Label(quality_frame, text=str(self.quality_var.get()))
        self.quality_label.grid(row=0, column=2, sticky=tk.E, padx=5)

        self.quality_scale = ttk.Scale(
            quality_frame,
            from_=0,
            to=100,
            variable=self.quality_var,
            orient=tk.HORIZONTAL,
            command=self.on_quality_changed
        )
        self.quality_scale.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)

        # Output directory
        output_frame = ttk.Frame(settings_frame)
        output_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(1, weight=1)

        ttk.Label(output_frame, text="Output:").grid(row=0, column=0, sticky=tk.W)
        self.output_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_var).grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(output_frame, text="Browse", command=self.select_output_dir).grid(row=0, column=2)

        # Checkboxes in a grid
        options_frame = ttk.Frame(settings_frame)
        options_frame.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        options_frame.columnconfigure((0, 1), weight=1)

        self.lossless_var = tk.BooleanVar(value=PRESET_PROFILES[self.profile_var.get()]['lossless'])
        ttk.Checkbutton(
            options_frame,
            text="Lossless",
            variable=self.lossless_var
        ).grid(row=0, column=0, sticky=tk.W)

        self.keep_original_var = tk.BooleanVar(value=PRESET_PROFILES[self.profile_var.get()]['preserve_originals'])
        ttk.Checkbutton(
            options_frame,
            text="Keep Originals",
            variable=self.keep_original_var
        ).grid(row=0, column=1, sticky=tk.W)

        self.preserve_timestamps_var = tk.BooleanVar(value=PRESET_PROFILES[self.profile_var.get()]['preserve_timestamps'])
        ttk.Checkbutton(
            options_frame,
            text="Preserve Timestamps",
            variable=self.preserve_timestamps_var
        ).grid(row=1, column=0, sticky=tk.W)

        self.recursive_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="Process Subdirectories",
            variable=self.recursive_var
        ).grid(row=1, column=1, sticky=tk.W)

        # Progress frame at the bottom of right column
        progress_frame = ttk.LabelFrame(right_column, text="Progress", padding="10")
        progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        progress_frame.columnconfigure(0, weight=1)

        # Update canvas scroll region when window is resized
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            # Update canvas width to match scrollable frame
            canvas_width = right_column.winfo_width() - scrollbar.winfo_width() - 5
            canvas.itemconfig(canvas.find_withtag("all")[0], width=max(canvas_width, 200))

        scrollable_frame.bind("<Configure>", _on_frame_configure)

        # Update canvas width when window is resized
        def _on_canvas_configure(event):
            canvas_width = event.width - 5
            canvas.itemconfig(canvas.find_withtag("all")[0], width=canvas_width)

        canvas.bind("<Configure>", _on_canvas_configure)

    def setup_tray(self):
        """Set up system tray icon and menu"""
        menu = (
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem("Exit", self.quit_app)
        )
        
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "logo-square.ico")
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
        
    def minimize_to_tray(self):
        """Minimize the application to system tray"""
        self.root.withdraw()
        if not self.tray_icon.visible:
            self.tray_icon_thread = threading.Thread(target=self.tray_icon.run)
            self.tray_icon_thread.daemon = True
            self.tray_icon_thread.start()
    
    def quit_app(self, _=None):
        """Quit the application"""
        if self.tray_icon.visible:
            self.tray_icon.stop()
        self.root.quit()
    
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

        # Get current settings
        try:
            profile = self.profile_var.get()
            settings = {
                'quality': self.quality_var.get(),
                'lossless': self.lossless_var.get(),
                'preserve_timestamps': self.preserve_timestamps_var.get(),
                'preserve_originals': self.keep_original_var.get()
            }
            
            # Save as last used settings
            self.save_last_settings(settings)
            
            # Get output directory
            output_dir = self.output_var.get()
            if output_dir and not os.path.exists(output_dir):
                try:
                    os.makedirs(output_dir)
                except Exception as e:
                    self.show_error("Error", f"Failed to create output directory: {e}")
                    return
            
            # Initialize conversion tracking
            with self.conversion_lock:
                self.active_conversions = 0
                total_converted = {'success': 0, 'error': 0}
            
            # Process each input
            for file_path in files:
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file_path)[1].lower()
                    if ext in image_to_webp.SUPPORTED_FORMATS:
                        # For single files
                        if output_dir:
                            # Create output path preserving relative structure
                            rel_path = os.path.basename(file_path)
                            output_path = os.path.join(output_dir, rel_path)
                            output_path = str(Path(output_path).with_suffix('.webp'))
                        else:
                            output_path = None
                            
                        # Start conversion in a thread
                        with self.conversion_lock:
                            self.active_conversions += 1
                        thread = threading.Thread(
                            target=self.convert_files_thread,
                            args=([file_path], settings, output_path, total_converted)
                        )
                        thread.daemon = True
                        thread.start()
                    else:
                        self.queue.put(('log', f"Skipping unsupported file: {file_path}"))
                        
                elif os.path.isdir(file_path):
                    # For directories
                    if output_dir:
                        # Create corresponding output subdirectory
                        rel_path = os.path.basename(file_path)
                        dir_output = os.path.join(output_dir, rel_path)
                    else:
                        dir_output = None
                        
                    # Start directory processing in a thread
                    with self.conversion_lock:
                        self.active_conversions += 1
                    thread = threading.Thread(
                        target=self.process_directory_thread,
                        args=(file_path, settings, dir_output, total_converted)
                    )
                    thread.daemon = True
                    thread.start()
                    
            # Log settings being used
            self.queue.put(('log', f"Using profile: {profile}"))
            self.queue.put(('log', f"Settings: Quality={settings['quality']}, "
                                  f"Lossless={settings['lossless']}, "
                                  f"Preserve Timestamps={settings['preserve_timestamps']}, "
                                  f"Keep Originals={settings['preserve_originals']}"))
            if output_dir:
                self.queue.put(('log', f"Output directory: {output_dir}"))
            
        except Exception as e:
            self.show_error("Error", f"Failed to start conversion: {str(e)}")

    def process_directory_thread(self, directory: str, settings: dict, output_dir: Optional[str] = None, total_converted: dict = None):
        """Process a directory in a separate thread"""
        try:
            # Use the process_directory function from image_to_webp
            image_to_webp.process_directory(
                directory_path=directory,
                quality=settings['quality'],
                recursive=True,
                output_dir=output_dir,
                preserve_originals=settings['preserve_originals'],
                preserve_timestamps=settings['preserve_timestamps']
            )
            with self.conversion_lock:
                total_converted['success'] += 1
        except Exception as e:
            with self.conversion_lock:
                total_converted['error'] += 1
            self.queue.put(('log', f"Error processing directory {directory}: {e}"))
        finally:
            with self.conversion_lock:
                self.active_conversions -= 1
                if self.active_conversions == 0:
                    # Show final summary
                    summary = f"Conversion completed!\n"
                    summary += f"Successfully converted: {total_converted['success']} items\n"
                    if total_converted['error'] > 0:
                        summary += f"Failed to convert: {total_converted['error']} items"
                        self.queue.put(('show_warning', ("Conversion Complete", summary)))
                    else:
                        self.queue.put(('show_info', ("Conversion Complete", summary)))

    def convert_files_thread(self, files: List[str], settings: dict, output_path: Optional[str] = None, total_converted: dict = None):
        """Convert files in a separate thread"""
        total_files = len(files)
        converted_count = 0
        error_count = 0
        
        try:
            for i, file_path in enumerate(files, 1):
                try:
                    success, input_path, result = image_to_webp.convert_to_webp(
                        file_path,
                        output_path=output_path,
                        quality=settings['quality'],
                        preserve_timestamps=settings['preserve_timestamps'],
                        lossless=settings['lossless']
                    )
                    if success:
                        converted_count += 1
                        with self.conversion_lock:
                            total_converted['success'] += 1
                        self.queue.put(('log', f"✓ Converted: {input_path} -> {result}"))
                        if not settings['preserve_originals']:
                            try:
                                os.remove(input_path)
                                self.queue.put(('log', f"  Deleted original: {input_path}"))
                            except Exception as e:
                                self.queue.put(('log', f"  Failed to delete original {input_path}: {e}"))
                    else:
                        error_count += 1
                        with self.conversion_lock:
                            total_converted['error'] += 1
                        self.queue.put(('log', f"✗ Failed to convert {input_path}: {result}"))
                
                except Exception as e:
                    error_count += 1
                    with self.conversion_lock:
                        total_converted['error'] += 1
                    self.queue.put(('log', f"✗ Error processing {file_path}: {e}"))
                
                # Update progress
                progress = (i / total_files) * 100
                self.queue.put(('progress', progress))
            
        except Exception as e:
            self.queue.put(('log', f"Critical error during conversion: {e}"))
            self.show_error("Error", f"Critical error during conversion: {str(e)}")
        finally:
            self.queue.put(('progress', 0))
            with self.conversion_lock:
                self.active_conversions -= 1
                if self.active_conversions == 0:
                    # Show final summary
                    summary = f"Conversion completed!\n"
                    summary += f"Successfully converted: {total_converted['success']} items\n"
                    if total_converted['error'] > 0:
                        summary += f"Failed to convert: {total_converted['error']} items"
                        self.queue.put(('show_warning', ("Conversion Complete", summary)))
                    else:
                        self.queue.put(('show_info', ("Conversion Complete", summary)))

    def on_quality_changed(self, *args):
        """Update quality label when slider moves"""
        self.quality_label.config(text=str(self.quality_var.get()))

    def on_profile_changed(self, event=None):
        """Update settings when profile is changed"""
        profile = self.profile_var.get()
        if profile in PRESET_PROFILES:
            settings = PRESET_PROFILES[profile]
        else:
            settings = self.config.config['custom_profiles'][profile]
        
        # Update all settings
        self.quality_var.set(settings['quality'])
        self.quality_label.config(text=str(settings['quality']))
        self.lossless_var.set(settings['lossless'])
        self.preserve_timestamps_var.set(settings['preserve_timestamps'])
        self.keep_original_var.set(settings['preserve_originals'])
        
        self.queue.put(('log', f"Applied {profile} profile settings"))
    
    def select_output_dir(self):
        """Open dialog to select output directory"""
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            mustexist=False
        )
        if directory:
            self.output_var.set(directory)
            
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
                'preserve_originals': self.keep_original_var.get()
            }
            
            self.config.config['custom_profiles'][name] = settings
            self.config.save_config()
            self.update_profile_list()
            self.profile_var.set(name)
            self.queue.put(('log', f"Saved profile: {name}"))
            
    def set_default_profile(self):
        """Set current profile as default"""
        profile = self.profile_var.get()
        self.config.set_default_profile(profile)
        self.queue.put(('log', f"Set default profile to: {profile}"))
        
    def use_last_settings(self):
        """Load last used settings"""
        last_settings = self.config.config.get('last_used_settings')
        if last_settings:
            self.quality_var.set(last_settings['quality'])
            self.lossless_var.set(last_settings['lossless'])
            self.preserve_timestamps_var.set(last_settings['preserve_timestamps'])
            self.keep_original_var.set(last_settings['preserve_originals'])
            self.queue.put(('log', "Loaded last used settings"))
        else:
            self.show_error("Error", "No last used settings found")

    def save_last_settings(self, settings: dict):
        """Save current settings as last used"""
        self.config.config['last_used_settings'] = settings.copy()
        self.config.save_config()

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
