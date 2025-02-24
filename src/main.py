import os
import datetime
import random
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

import pollinations  # Ensure pollinations module is installed

# File where history is stored
HISTORY_FILE = "prompt_history.txt"


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines


def save_history(prompt):
    history = load_history()
    history.append(prompt)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for p in history:
            f.write(p + "\n")


def get_recent_history(n=5):
    history = load_history()
    return history[-n:]


class ImageGeneratorGUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("图像生成器")
        self.geometry("610x510")  # Adjusted window size
        self.resizable(False, False)

        # Last successful prompt
        self.last_prompt = ""
        self.create_widgets()

    def create_widgets(self):
        # Main frame
        frame = ttk.Frame(self, padding=10)
        frame.grid(row=0, column=0, sticky="NSEW")

        # Input Frame
        input_frame = ttk.LabelFrame(frame, text="图像生成参数", padding=10)
        input_frame.grid(row=0, column=0, sticky="EW", padx=5, pady=5)

        # Row 0: Prompt label and multiline Text widget
        prompt_label = ttk.Label(input_frame, text="图像生成提示词:")
        prompt_label.grid(row=0, column=0, sticky="NW", padx=5, pady=5)
        self.prompt_text = tk.Text(
            input_frame, wrap="word", width=60, height=4
        )  # Adjusted width
        self.prompt_text.grid(row=0, column=1, sticky="EW", padx=5, pady=5)
        self.prompt_text.bind("<KeyRelease>", self.on_text_change)
        self.prompt_text.bind("<Up>", self.on_up_arrow)

        # Row 1: Enhance checkbox
        self.enhance_var = tk.BooleanVar(value=False)
        enhance_check = ttk.Checkbutton(
            input_frame, text="增强提示词", variable=self.enhance_var
        )
        enhance_check.grid(row=1, column=0, sticky="W", padx=5, pady=5)

        # Row 2: Model selection drop-down
        model_label = ttk.Label(input_frame, text="图像生成模型:")
        model_label.grid(row=2, column=0, sticky="W", padx=5, pady=5)
        self.model_options = [
            "flux",
            "flux_realism",
            "flux_cablyai",
            "flux_anime",
            "flux_3d",
            "flux_pro",
            "any_dark",
            "turbo",
        ]
        self.model_var = tk.StringVar(value="flux_pro")
        self.model_combobox = ttk.Combobox(
            input_frame,
            textvariable=self.model_var,
            values=self.model_options,
            state="readonly",
            width=20,
        )
        self.model_combobox.grid(row=2, column=1, sticky="W", padx=5, pady=5)
        self.model_combobox.current(self.model_options.index("flux_pro"))

        # Row 3: Width controls
        width_label = ttk.Label(input_frame, text="图片宽度（像素）:")
        width_label.grid(row=3, column=0, sticky="W", padx=5, pady=5)
        self.width_var = tk.IntVar(value=1024)
        width_spin = ttk.Spinbox(
            input_frame,
            from_=256,
            to=2048,
            increment=1,
            textvariable=self.width_var,
            width=10,
        )
        width_spin.grid(row=3, column=1, sticky="W", padx=5, pady=5)

        # Row 4: Height controls
        height_label = ttk.Label(input_frame, text="图片高度（像素）:")
        height_label.grid(row=4, column=0, sticky="W", padx=5, pady=5)
        self.height_var = tk.IntVar(value=1024)
        height_spin = ttk.Spinbox(
            input_frame,
            from_=256,
            to=2048,
            increment=1,
            textvariable=self.height_var,
            width=10,
        )
        height_spin.grid(row=4, column=1, sticky="W", padx=5, pady=5)

        # Row 5: Generate Image button.
        self.generate_button = ttk.Button(
            input_frame, text="生成图像", command=self.generate_image
        )
        self.generate_button.grid(
            row=5, column=0, columnspan=2, pady=10, padx=5, sticky="EW"
        )

        # Add a new row for the "Open Image Directory" button.
        self.open_dir_button = ttk.Button(
            input_frame, text="打开输出文件夹", command=self.open_image_directory
        )
        self.open_dir_button.grid(
            row=6, column=0, columnspan=2, pady=5, padx=5, sticky="EW"
        )

        # Status label frame (outside input_frame)
        self.status_label = ttk.Label(frame, text="", foreground="blue")
        self.status_label.grid(row=1, column=0, pady=5, padx=5, sticky="W")

        # History frame with listbox.
        history_frame = ttk.LabelFrame(frame, text="历史提示词（最近5条，双击替换当前提示词）", padding=10)
        history_frame.grid(row=2, column=0, sticky="EW", padx=5, pady=5)
        self.history_listbox = tk.Listbox(history_frame, height=5, width=70)
        self.history_listbox.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)
        self.history_listbox.bind("<Double-Button-1>", self.on_history_double_click)

        # Allow column expansion in main frame.
        frame.columnconfigure(0, weight=1)
        input_frame.columnconfigure(1, weight=1)

        self.refresh_history()

    def on_text_change(self, event):
        """Auto-adjust the prompt text widget height based on its content."""
        content = self.prompt_text.get("1.0", "end-1c")
        num_lines = content.count("\n") + 1
        new_height = min(max(num_lines, 4), 10)
        self.prompt_text.config(height=new_height)

    def on_up_arrow(self, event):
        """Replace current prompt with last successful prompt on Up arrow."""
        if self.last_prompt:
            self.prompt_text.delete("1.0", tk.END)
            self.prompt_text.insert("1.0", self.last_prompt)
            return "break"  # Prevent default behavior

    def on_history_double_click(self, event):
        """Fill the prompt text with the double-clicked history prompt."""
        try:
            selection = self.history_listbox.curselection()
            if selection:
                prompt_text = self.history_listbox.get(selection[0])
                self.prompt_text.delete("1.0", tk.END)
                self.prompt_text.insert("1.0", prompt_text)
        except Exception as e:
            messagebox.showerror("Error", f"History selection error: {e}")

    def refresh_history(self):
        """Refresh the listbox with the five most recent prompts."""
        self.history_listbox.delete(0, tk.END)
        recent_prompts = get_recent_history(5)
        for prompt in reversed(recent_prompts):
            self.history_listbox.insert(tk.END, prompt)

    def open_image_directory(self):
        """Open the directory containing generated images."""
        image_dir = Path("image")
        image_dir.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(image_dir.resolve())
        except Exception as e:
            messagebox.showerror("Error", f"Could not open image directory: {e}")

    def generate_image(self):
        """Collect parameters, disable the UI, and start image generation."""
        prompt = self.prompt_text.get("1.0", "end-1c").strip()
        if not prompt:
            messagebox.showwarning("Input Error", "Please enter a prompt.")
            return

        enhance = self.enhance_var.get()
        width = self.width_var.get()
        height = self.height_var.get()
        seed = random.randint(0, 10000)

        # Get the selected model option.
        model_choice = self.model_var.get()
        try:
            model_function = getattr(pollinations.Image, model_choice)
            model_instance = model_function()
        except Exception as e:
            messagebox.showerror("Model Error", f"Error selecting model: {e}")
            return

        # Disable controls during generation.
        self.generate_button.config(state=tk.DISABLED)
        self.status_label.config(text="正在生成图像，请耐心等待")
        self.update_idletasks()

        threading.Thread(
            target=self.run_generation_thread,
            args=(prompt, enhance, width, height, seed, model_instance),
            daemon=True,
        ).start()

    def run_generation_thread(
        self, prompt, enhance, width, height, seed, model_instance
    ):
        """Perform image generation on a separate thread."""
        try:
            image_model = pollinations.Image(
                model=model_instance,
                seed=seed,
                width=width,
                height=height,
                enhance=enhance,
                nologo=True,
                private=True,
                safe=False,
                referrer="pollinations.py",
            )
        except Exception as e:
            result = {"success": False, "error": f"Model Error: {e}"}
            self.after(0, lambda: self.finish_generation(result))
            return

        try:
            image = image_model(prompt=prompt)
        except Exception as e:
            result = {"success": False, "error": f"Generation Error: {e}"}
            self.after(0, lambda: self.finish_generation(result))
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{seed}.png"
        image_dir = Path("image")
        image_dir.mkdir(parents=True, exist_ok=True)
        filepath = image_dir / filename

        try:
            image.save(filepath)
            result = {"success": True, "filepath": filepath, "prompt": prompt}
        except Exception as e:
            result = {"success": False, "error": f"Save Error: {e}"}

        self.after(0, lambda: self.finish_generation(result))

    def finish_generation(self, result):
        """Re-enable the UI and show results after generation."""
        self.generate_button.config(state=tk.NORMAL)
        self.status_label.config(text="")  # Clear progress message.

        if result.get("success"):
            filepath = result.get("filepath")
            prompt = result.get("prompt")
            messagebox.showinfo("Success", f"Image saved as {filepath}")
            self.last_prompt = prompt
            save_history(prompt)
            self.refresh_history()
            try:
                os.startfile(filepath)
            except Exception as e:
                messagebox.showwarning(
                    "Preview Error", f"Could not open image automatically: {e}"
                )
        else:
            error_msg = result.get("error", "Unknown error occurred")
            messagebox.showerror("Error", error_msg)


if __name__ == "__main__":
    app = ImageGeneratorGUI()
    app.mainloop()
