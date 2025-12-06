import os
import sys
import subprocess
import importlib.util
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, ".idea", "Config.py")


# (config_name, label, type, comment)
# Keep this in sync with .idea/Config.py
CONFIG_FIELDS = [
    (
        "DEMAND_PATH",
        "Demand points file path",
        "str",
        "# Demand points path (projected CRS, meters) (POINT_X, POINT_Y, demand)",
    ),
    (
        "CANDIDATE_PATH",
        "Candidate points file path",
        "str",
        "# Candidate points path (projected CRS, meters) (POINT_X, POINT_Y)",
    ),
    (
        "Demand_point_num",
        "Number of demand points",
        "int",
        "# Number of demand points",
    ),
    (
        "Candidate_point_num",
        "Number of candidate points",
        "int",
        "# Number of candidate points",
    ),
    (
        "P",
        "Number of facilities",
        "int",
        "# Number of facilities",
    ),
    (
        "Radius",
        "Coverage radius",
        "float",
        "# Coverage radius in raw data space",
    ),
    (
        "CSQI_class",
        "CSQI classes",
        "str",
        "# Initial CSQI classes, separated by commas",
    ),
    (
        "Distance",
        "Distance metric",
        "str",
        "# Distance type: Euclidean (straight-line) or RoadNetwork (road network distance)",
    ),
    (
        "OD_MATRIX_PATH",
        "OD matrix CSV path",
        "str",
        "# OD matrix CSV path, used only when Distance is RoadNetwork",
    ),
    (
        "RADIUS",
        "Coverage radius",
        "float",
        "# Coverage radius used in optimization model",
    ),
    (
        "w1",
        "Coverage weight",
        "float",
        "# Objective weight for coverage",
    ),
    (
        "w2",
        "Distance weight",
        "float",
        "# Objective weight for distance",
    ),
    (
        "da",
        "Distance segment a",
        "float",
        "# Distance breakpoint a",
    ),
    (
        "db",
        "Distance segment b",
        "float",
        "# Distance breakpoint b",
    ),
]


class CareNetGUI:
    def __init__(self, master: tk.Tk):
        self.master = master
        self.master.title("Care-Net Configuration and Control Panel")
        self.master.geometry("960x560")
        # Set window icon to heart SVG if possible
        self._icon_image = None  # keep reference for Tkinter
        self._set_window_icon()

        # Global style
        self._setup_style()

        # Header area
        header = ttk.Frame(self.master)
        header.pack(fill=tk.X, padx=16, pady=(12, 4))

        # Left teal accent bar
        accent = tk.Frame(header, width=4, height=40, bg="#008080")
        accent.pack(side="left", fill="y", padx=(0, 10))

        text_container = ttk.Frame(header)
        text_container.pack(side="left", fill="x", expand=True)

        title_lbl = ttk.Label(
            text_container,
            text="Care-Net Configuration",
            font=("Segoe UI", 14, "bold"),
            foreground="#333333",
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = ttk.Label(
            text_container,
            text="Configure data paths, problem size and distance metric before running the pipeline.",
            font=("Segoe UI", 9),
            foreground="#555555",
        )
        subtitle_lbl.pack(anchor="w", pady=(2, 0))

        # Main containers
        self.config_frame = ttk.LabelFrame(self.master, text="Data preparation")
        self.config_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(4, 12))

        # Keep a placeholder for future pipeline buttons, but do not show now
        self.button_frame = ttk.LabelFrame(self.master, text="Pipeline control")
        # Not packed yet; will be used if you decide to re‑enable buttons

        # Scrollable area for config fields
        self._build_config_form()
        # Buttons temporarily disabled
        self._build_buttons()

        # Load existing config values
        self.load_config()

    # ------------------------------------------------------------------
    # Config handling
    # ------------------------------------------------------------------
    def _setup_style(self):
        """Configure a modern teal style: clean, white, with teal accents."""
        style = ttk.Style()
        try:
            # Use a theme that looks decent on most platforms
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except Exception:
            pass

        # Core palette
        base_bg = "#FFFFFF"   # clean white background
        primary_teal = "#008080"  # main teal
        highlight_bg = "#E0F2F1"  # very light teal for selection/hover

        self.master.configure(bg=base_bg)

        # Base widgets
        style.configure("TFrame", background=base_bg)
        style.configure("TLabel", font=("Segoe UI", 9), background=base_bg, foreground="#333333")
        style.configure("TEntry", font=("Segoe UI", 9))
        
        # --- 修复 Combobox 灰色背景的关键部分 ---
        style.configure(
            "TCombobox",
            font=("Segoe UI", 9),
            fieldbackground=base_bg,
            background=base_bg,
            selectbackground=base_bg, # 设置默认选中背景为白色
            selectforeground="#333333" # 设置默认选中文字为深色
        )
        
        # 使用 map 强制覆盖所有状态（包括 readonly 和 active）下的颜色
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", "#FFFFFF"), ("active", "#FFFFFF")],
            background=[("readonly", "#FFFFFF"), ("active", "#FFFFFF")],
            foreground=[("readonly", "#333333"), ("active", "#333333")],
            # 关键：将 selectbackground (选中时的背景) 强制设为白色，去掉灰块
            selectbackground=[("readonly", "#FFFFFF"), ("!readonly", "#FFFFFF")],
            selectforeground=[("readonly", "#333333"), ("!readonly", "#333333")]
        )
        # -------------------------------------

        style.configure(
            "TLabelframe",
            background=base_bg,
            bordercolor=primary_teal,
        )
        style.configure(
            "TLabelframe.Label",
            font=("Segoe UI", 10, "bold"),
            background=base_bg,
            foreground=primary_teal,
        )

        # Buttons
        style.configure(
            "Primary.TButton",
            font=("Segoe UI", 9, "bold"),
            background=primary_teal,
            foreground="#FFFFFF",
            padding=(10, 4),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#1ABC9C")],
            foreground=[("disabled", "#DDDDDD")],
        )

    def _set_window_icon(self):
        """Try to set window icon from heart SVG file."""
        icon_svg = os.path.join(BASE_DIR, "像素爱心2.svg")
        if not os.path.exists(icon_svg):
            return
        try:
            import io  # local import to avoid unused at module level
            import cairosvg  # type: ignore
            from PIL import Image, ImageTk  # type: ignore

            png_bytes = cairosvg.svg2png(url=icon_svg)
            image = Image.open(io.BytesIO(png_bytes))
            self._icon_image = ImageTk.PhotoImage(image)
            # Use iconphoto so it works cross‑platform
            self.master.iconphoto(False, self._icon_image)
        except Exception as e:
            # 如果依赖不存在或转换失败，静默失败，使用默认图标
            print(f"Failed to set window icon from SVG: {e}")

    def _build_config_form(self):
        canvas = tk.Canvas(self.config_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.config_frame, orient="vertical", command=canvas.yview)
        self.form_inner = ttk.Frame(canvas)

        self.form_inner.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=self.form_inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.entries = {}
        self.distance_combobox = None
        self.od_entry = None
        self.od_browse_btn = None

        # Header row
        ttk.Label(self.form_inner, text="Parameter", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, sticky="w", padx=6, pady=4
        )
        ttk.Label(self.form_inner, text="Value", font=("Segoe UI", 9, "bold")).grid(
            row=0, column=1, sticky="w", padx=6, pady=4
        )

        row_offset = 1

        for idx, (name, label, typ, _comment) in enumerate(CONFIG_FIELDS, start=0):
            row = row_offset + idx
            
            # --- 修复部分开始 ---
            # 原来的写法：param_label = f"{label} ({name})"
            # 修改后的写法：只显示 label
            param_label = label
            # --- 修复部分结束 ---
            
            ttk.Label(self.form_inner, text=param_label).grid(
                row=row, column=0, sticky="w", padx=6, pady=4
            )

            entry_frame = ttk.Frame(self.form_inner)
            entry_frame.grid(row=row, column=1, sticky="we", padx=6, pady=4)
            self.form_inner.columnconfigure(1, weight=1)

            # Special widgets for some fields
            if name == "Distance":
                entry = ttk.Combobox(
                    entry_frame,
                    width=30,
                    state="readonly",
                    values=["Euclidean", "RoadNetwork"],
                )
                entry.bind("<<ComboboxSelected>>", self._on_distance_change)
                self.distance_combobox = entry
                btn = None
            else:
                entry = ttk.Entry(entry_frame, width=70)
                btn = None

            entry.pack(side="left", fill="x", expand=True)

            # For path fields, provide a small "..." button
            if name in ("DEMAND_PATH", "CANDIDATE_PATH", "OD_MATRIX_PATH"):
                btn = ttk.Button(
                    entry_frame,
                    text="...",
                    width=3,
                    command=lambda field=name: self.browse_file(field),
                )
                btn.pack(side="left", padx=(5, 0))

            if name == "OD_MATRIX_PATH":
                self.od_entry = entry
                self.od_browse_btn = btn

            self.entries[name] = (entry, typ)

        # Save button
        save_btn = ttk.Button(
            self.form_inner,
            text="Save configuration",
            command=self.save_config,
        )
        save_btn.grid(
            row=row_offset + len(CONFIG_FIELDS),
            column=0,
            columnspan=2,
            pady=12,
        )

        # Initialize OD matrix controls state based on current distance selection
        self._update_od_matrix_state()

    def _build_buttons(self):
        """Buttons are temporarily disabled (no controls created here)."""
        # If you want to re‑enable buttons later, restore the code here.
        return

    # ------------------------------------------------------------------
    # File dialog for path fields
    # ------------------------------------------------------------------
    def browse_file(self, field_name: str):
        initial_dir = BASE_DIR
        if field_name in self.entries:
            entry, _typ = self.entries[field_name]
            current = entry.get().strip()
            if current:
                # If user already set a path, try to use its directory
                candidate_dir = os.path.dirname(current)
                if os.path.isdir(candidate_dir):
                    initial_dir = candidate_dir

        file_path = filedialog.askopenfilename(initialdir=initial_dir)
        if file_path:
            entry, _typ = self.entries[field_name]
            # Save relative path if under BASE_DIR, otherwise absolute
            try:
                rel = os.path.relpath(file_path, BASE_DIR)
                if not rel.startswith(".."):
                    entry.delete(0, tk.END)
                    entry.insert(0, rel.replace("\\", "/"))
                else:
                    entry.delete(0, tk.END)
                    entry.insert(0, file_path)
            except ValueError:
                entry.delete(0, tk.END)
                entry.insert(0, file_path)

    # ------------------------------------------------------------------
    # Load and save config
    # ------------------------------------------------------------------
    def _update_od_matrix_state(self):
        """Enable OD matrix path only when Distance is RoadNetwork."""
        if self.distance_combobox is None or self.od_entry is None or self.od_browse_btn is None:
            return

        dist_val = self.distance_combobox.get().strip()
        is_road = dist_val == "RoadNetwork"

        state = "normal" if is_road else "disabled"
        self.od_entry.configure(state=state)
        if is_road:
            self.od_browse_btn.state(["!disabled"])
        else:
            self.od_browse_btn.state(["disabled"])

    def _on_distance_change(self, _event=None):
        """Callback when Distance combobox changes."""
        self._update_od_matrix_state()

    def load_config(self):
        """Load current values from Config.py if it exists."""
        if not os.path.exists(CONFIG_PATH):
            messagebox.showwarning(
                "Config.py not found",
                f"Config file not found at:\n{CONFIG_PATH}\n\n"
                "You can still edit values and click 'Save' to create it.",
            )
            return

        try:
            spec = importlib.util.spec_from_file_location("user_config", CONFIG_PATH)
            module = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(module)

            for name, (_entry, _typ) in self.entries.items():
                if hasattr(module, name):
                    value = getattr(module, name)
                    entry, _typ = self.entries[name]
                    entry.delete(0, tk.END)
                    entry.insert(0, str(value))

            # After loading all values, update OD matrix state
            self._update_od_matrix_state()
        except Exception as e:
            messagebox.showerror(
                "Error loading Config.py",
                f"Failed to load configuration:\n{e}",
            )

    def save_config(self):
        """Write current GUI values back into .idea/Config.py."""
        lines = ["", ""]

        for name, label, typ, comment in CONFIG_FIELDS:
            entry, _ = self.entries[name]
            raw_val = entry.get().strip()

            if raw_val == "":
                messagebox.showerror(
                    "Invalid value",
                    f"Field '{label} ({name})' cannot be empty.",
                )
                return

            try:
                if typ == "int":
                    value = int(raw_val)
                    value_str = str(value)
                elif typ == "float":
                    value = float(raw_val)
                    # Avoid trailing .0 if integer-like
                    value_str = str(int(value)) if value.is_integer() else str(value)
                else:  # str
                    # Always store as a normal Python string literal
                    value_str = repr(raw_val.replace("\\", "/"))
            except ValueError:
                messagebox.showerror(
                    "Invalid value",
                    f"Field '{label} ({name})' must be of type {typ}.",
                )
                return

            comment_part = f" {comment}" if comment else ""
            lines.append(f"{name} = {value_str}{comment_part}")

        lines.append("")

        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            messagebox.showinfo(
                "Config saved",
                f"Configuration has been saved to:\n{CONFIG_PATH}",
            )
        except Exception as e:
            messagebox.showerror(
                "Error saving Config.py",
                f"Failed to save configuration:\n{e}",
            )

    # ------------------------------------------------------------------
    # Button actions: run pipeline steps
    # ------------------------------------------------------------------
    def _run_script(self, script_name: str, title: str):
        """Run a Python script in a separate process."""
        script_path = os.path.join(BASE_DIR, script_name)
        if not os.path.exists(script_path):
            messagebox.showerror(
                f"{title} error",
                f"Script '{script_name}' not found in project root:\n{BASE_DIR}",
            )
            return

        python_exe = sys.executable or "python"

        try:
            # Use a new console on Windows so user can see progress/logs
            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

            subprocess.Popen(
                [python_exe, script_name],
                cwd=BASE_DIR,
                creationflags=creationflags,
            )

            messagebox.showinfo(
                title,
                f"{title} has been started in a separate window.\n\n"
                f"Script: {script_name}",
            )
        except Exception as e:
            messagebox.showerror(
                f"{title} error",
                f"Failed to start script '{script_name}':\n{e}",
            )

    def _run_notebook(self, notebook_rel_path: str, title: str):
        """Open or execute a Jupyter notebook in a separate process."""
        notebook_path = os.path.join(BASE_DIR, notebook_rel_path)
        if not os.path.exists(notebook_path):
            messagebox.showerror(
                f"{title} error",
                f"Notebook '{notebook_rel_path}' not found in project root:\n{BASE_DIR}",
            )
            return

        # Prefer 'jupyter' command; fallback to 'python -m jupyter'
        cmd = ["jupyter", "notebook", notebook_rel_path]

        try:
            creationflags = 0
            if os.name == "nt":
                creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)

            subprocess.Popen(
                cmd,
                cwd=BASE_DIR,
                creationflags=creationflags,
            )

            messagebox.showinfo(
                title,
                f"{title} notebook has been opened/started.\n\n"
                f"Notebook: {notebook_rel_path}",
            )
        except Exception as e:
            messagebox.showerror(
                f"{title} error",
                f"Failed to open notebook '{notebook_rel_path}':\n{e}",
            )

    def build_dataset(self):
        """Button: Build Dataset."""
        self._run_script("genarate_database.py", "Build Dataset")

    def start_training(self):
        """Button: Start Training."""
        self._run_script("run.py", "Start Training")

    def visualize_results(self):
        """Button: Visualize Results."""
        self._run_notebook("jupyter/EF_MCLP_DRL_distance_MF.ipynb", "Visualize Results")


def main():
    root = tk.Tk()
    app = CareNetGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()


