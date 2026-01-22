import tkinter as tk
from tkinter import filedialog, messagebox
import numpy as np
import cv2  # Used for saving PNGs
import sys

class SpectroPainter:
    def __init__(self, resolution=360, init_width=1000):
        self.resolution = resolution
        self.width = init_width

        # Brush Settings
        self.brush_size = 10
        self.grid_y_active = False # Pitch
        self.grid_x_active = False # Rhythm

        # --- Grid Settings ---
        # Vertical (Pitch): 20 steps
        self.grid_steps_y = 20
        self.grid_spacing_y = self.resolution / self.grid_steps_y

        # Horizontal (Time): 50 pixels per "Beat"
        self.grid_spacing_x = 50

        # --- Data Backing Store ---
        self.data = np.zeros((self.resolution, self.width), dtype=np.uint8)

        # --- GUI Setup ---
        self.root = tk.Tk()
        self.root.title(f"SpectroPainter 3.1 (Split Grids)")

        # 1. Toolbar
        ctrl_frame = tk.Frame(self.root, bg="#333", pady=5)
        ctrl_frame.pack(side=tk.TOP, fill=tk.X)

        # Buttons
        tk.Button(ctrl_frame, text="💾 Save", command=self.save_data, bg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="🗑️ Clear", command=self.clear_canvas, bg="#ffcccc").pack(side=tk.LEFT, padx=5)

        # Brush Controls
        tk.Label(ctrl_frame, text=" | Size:", bg="#333", fg="white").pack(side=tk.LEFT)
        self.scale_brush = tk.Scale(ctrl_frame, from_=1, to=30, orient=tk.HORIZONTAL, bg="#333", fg="white", highlightthickness=0)
        self.scale_brush.set(self.brush_size)
        self.scale_brush.pack(side=tk.LEFT)

        # --- NEW: Split Grid Toggles ---

        # Pitch Grid (Y)
        self.var_grid_y = tk.BooleanVar()
        self.chk_grid_y = tk.Checkbutton(
            ctrl_frame, text="🎵 Pitch (Y)",
            variable=self.var_grid_y, command=self.toggle_grids,
            bg="#333", fg="#00ccff", selectcolor="#333"
        )
        self.chk_grid_y.pack(side=tk.LEFT, padx=5)

        # Rhythm Grid (X)
        self.var_grid_x = tk.BooleanVar()
        self.chk_grid_x = tk.Checkbutton(
            ctrl_frame, text="⏱️ Rhythm (X)",
            variable=self.var_grid_x, command=self.toggle_grids,
            bg="#333", fg="#ffcc00", selectcolor="#333"
        )
        self.chk_grid_x.pack(side=tk.LEFT, padx=5)

        # 2. Drawing Area
        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.h_scroll = tk.Scrollbar(self.canvas_frame, orient=tk.HORIZONTAL)
        self.h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        self.canvas = tk.Canvas(
            self.canvas_frame,
            bg="black",
            height=self.resolution,
            width=900,
            scrollregion=(0, 0, self.width, self.resolution),
            xscrollcommand=self.h_scroll.set,
            cursor="crosshair"
        )
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.h_scroll.config(command=self.canvas.xview)

        # Bindings
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<Button-1>", self.paint)

        # Initialize Grid Arrays
        self.grid_lines_h = [] # Horizontal (Pitch)
        self.grid_lines_v = [] # Vertical (Time)
        self.draw_grid_overlay()

    def toggle_grids(self):
        """Updates visibility based on checkboxes."""
        self.grid_y_active = self.var_grid_y.get()
        self.grid_x_active = self.var_grid_x.get()

        # Toggle Pitch Lines (Horizontal)
        state_h = "normal" if self.grid_y_active else "hidden"
        for line in self.grid_lines_h:
            self.canvas.itemconfigure(line, state=state_h)

        # Toggle Rhythm Lines (Vertical)
        state_v = "normal" if self.grid_x_active else "hidden"
        for line in self.grid_lines_v:
            self.canvas.itemconfigure(line, state=state_v)

    def draw_grid_overlay(self):
        # 1. Pitch Lines (Horizontal - Cyan Tint)
        for i in range(1, self.grid_steps_y):
            y = i * self.grid_spacing_y
            line = self.canvas.create_line(0, y, self.width, y, fill="#004455", state="hidden")
            self.grid_lines_h.append(line)

        # 2. Rhythm Lines (Vertical - Yellow Tint)
        num_v_lines = int(self.width / self.grid_spacing_x)
        for i in range(1, num_v_lines + 1):
            x = i * self.grid_spacing_x
            line = self.canvas.create_line(x, 0, x, self.resolution, fill="#443300", state="hidden")
            self.grid_lines_v.append(line)

    def paint(self, event):
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)

        # Auto-Expand
        if canvas_x > self.width - 100:
            self.expand_canvas()

        # --- GRID SNAPPING LOGIC ---

        # 1. Snap Pitch (Y)
        if self.grid_y_active:
            canvas_y = round(canvas_y / self.grid_spacing_y) * self.grid_spacing_y

        # 2. Snap Rhythm (X)
        if self.grid_x_active:
            # We snap to half-beats (grid_spacing_x / 2) for a bit of flexibility
            snap_x = self.grid_spacing_x / 2
            canvas_x = round(canvas_x / snap_x) * snap_x

        # Visual Draw
        r = self.scale_brush.get()
        color = "#FFFFFF"

        self.canvas.create_oval(
            canvas_x - r, canvas_y - r,
            canvas_x + r, canvas_y + r,
            fill=color, outline=color
        )

        # Data Draw (Numpy)
        ix, iy = int(canvas_x), int(canvas_y)
        y_min = max(0, iy - r)
        y_max = min(self.resolution, iy + r)
        x_min = max(0, ix - r)
        x_max = min(self.width, ix + r)

        if y_min < y_max and x_min < x_max:
            self.data[y_min:y_max, x_min:x_max] = 255

    def expand_canvas(self):
        add_width = 500
        old_width = self.width
        new_width = self.width + add_width

        # Expand Data
        new_chunk = np.zeros((self.resolution, add_width), dtype=np.uint8)
        self.data = np.hstack((self.data, new_chunk))

        # Expand View
        self.width = new_width
        self.canvas.config(scrollregion=(0, 0, self.width, self.resolution))

        # Extend Horizontal Lines
        for line in self.grid_lines_h:
            coords = self.canvas.coords(line)
            self.canvas.coords(line, coords[0], coords[1], self.width, coords[3])

        # Create NEW Vertical Lines
        start_idx = int(old_width / self.grid_spacing_x) + 1
        end_idx = int(new_width / self.grid_spacing_x) + 1

        state_v = "normal" if self.grid_x_active else "hidden"

        for i in range(start_idx, end_idx):
            x = i * self.grid_spacing_x
            line = self.canvas.create_line(x, 0, x, self.resolution, fill="#443300", state=state_v)
            self.grid_lines_v.append(line)

    def clear_canvas(self):
        self.canvas.delete("all")
        self.grid_lines_h = []
        self.grid_lines_v = []
        self.width = 1000
        self.data = np.zeros((self.resolution, self.width), dtype=np.uint8)
        self.canvas.config(scrollregion=(0, 0, self.width, self.resolution))
        self.draw_grid_overlay()
        self.toggle_grids() # Re-apply states

    def save_data(self):
            # 1. Ask for filename WITHOUT forcing a default extension immediately
            file_path = filedialog.asksaveasfilename(
                filetypes=[("Numpy Data", "*.npy"), ("Image PNG", "*.png")],
                title="Save Spectrogram"
            )

            if not file_path:
                return

            # 2. Check extensions and auto-fix if missing
            if file_path.lower().endswith('.png'):
                # User wants PNG
                try:
                    cv2.imwrite(file_path, self.data)
                    messagebox.showinfo("Saved", f"Saved PNG: {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not save PNG: {e}")

            elif file_path.lower().endswith('.npy'):
                # User wants NPY
                try:
                    np.save(file_path, self.data)
                    messagebox.showinfo("Saved", f"Saved NPY: {file_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not save NPY: {e}")

            else:
                # 3. No extension provided? Default to .npy
                # (or you could ask the user, but defaulting is safer)
                new_path = file_path + ".npy"
                try:
                    np.save(new_path, self.data)
                    messagebox.showinfo("Saved", f"No extension detected. Saved as: {new_path}")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not save: {e}")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SpectroPainter(resolution=360)
    app.run()
