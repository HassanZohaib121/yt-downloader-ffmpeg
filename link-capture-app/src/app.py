"""Link Capture desktop application."""
import ctypes
from datetime import datetime
import hashlib
import os
from pathlib import Path
import queue
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import core

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Link Capture")
        self.root.geometry("1050x760")
        self.root.minsize(850, 650)
        self.settings = core.load_settings()
        self.events = queue.Queue()
        self.job = None
        self.worker = None
        self.captures = []
        self.choices = []
        self.snapshot = None
        self.current_id = None
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background="#f3f5f9", foreground="#17243b")
        style.configure("TButton", padding=(12, 7))
        style.configure("Accent.TButton", background="#2563eb", foreground="white")
        style.map("Accent.TButton", background=[("active", "#1d4ed8"), ("disabled", "#a7b7d4")])
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 24))
        style.configure("Sub.TLabel", foreground="#52617a")
        style.configure("Treeview", background="white", fieldbackground="white", rowheight=34)
        body = ttk.Frame(root, padding=22)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Link Capture", style="Title.TLabel").pack(anchor="w")
        ttk.Label(body, text="Capture in Firefox. Choose a source. Save with FFmpeg.", style="Sub.TLabel").pack(anchor="w", pady=(0, 16))
        top = ttk.Frame(body)
        top.pack(fill="x", pady=(0, 14))
        self.paste = tk.StringVar()
        ttk.Entry(top, textvariable=self.paste).pack(side="left", fill="x", expand=True)
        ttk.Button(top, text="Add media URL", command=self.add_url).pack(side="left", padx=(8, 0))
        content = ttk.Frame(body)
        content.pack(fill="both", expand=True)
        left = ttk.Frame(content, width=260)
        left.pack(side="left", fill="y", padx=(0, 18))
        ttk.Label(left, text="CAPTURED LINKS", style="Sub.TLabel").pack(anchor="w", pady=(0, 7))
        self.tree = ttk.Treeview(left, show="tree", height=16, selectmode="browse")
        self.tree.column("#0", width=255)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.choose_capture)
        ttk.Button(left, text="Remove selected capture", command=self.remove_capture).pack(fill="x", pady=(9, 0))
        right = ttk.Frame(content)
        right.pack(side="left", fill="both", expand=True)
        self.title = tk.StringVar(value="Waiting for a capture")
        ttk.Label(right, textvariable=self.title, font=("Segoe UI Semibold", 14), wraplength=650).pack(anchor="w")
        ttk.Label(right, text="Media source", style="Sub.TLabel").pack(anchor="w", pady=(16, 5))
        self.source = ttk.Combobox(right, state="readonly")
        self.source.pack(fill="x")
        self.source.bind("<<ComboboxSelected>>", self.choice_changed)
        self.note = tk.StringVar(value="In Firefox, click Open capture app or Send to app. You can also paste a direct media or playlist URL above.")
        ttk.Label(right, textvariable=self.note, wraplength=650, style="Sub.TLabel").pack(anchor="w", pady=(8, 12))
        self.local_frame = ttk.Frame(right)
        self.local_video = tk.StringVar()
        ttk.Label(self.local_frame, text="Downloaded video file").pack(anchor="w")
        local_row = ttk.Frame(self.local_frame)
        local_row.pack(fill="x")
        ttk.Entry(local_row, textvariable=self.local_video).pack(side="left", fill="x", expand=True)
        ttk.Button(local_row, text="Browse", command=self.browse_video).pack(side="left", padx=(8,0))
        self.local_frame.pack(fill="x", pady=(0, 10))
        self.local_frame.pack_forget()
        self.folder = tk.StringVar(value=self.settings["folder"])
        ttk.Label(right, text="Save folder", style="Sub.TLabel").pack(anchor="w")
        folder_row = ttk.Frame(right)
        folder_row.pack(fill="x", pady=(5, 10))
        ttk.Entry(folder_row, textvariable=self.folder).pack(side="left", fill="x", expand=True)
        ttk.Button(folder_row, text="Browse", command=self.browse_folder).pack(side="left", padx=(8,0))
        self.format = tk.StringVar(value=self.settings.get("format", "mkv") if self.settings.get("format", "mkv") in core.OUTPUT_FORMATS else "mkv")
        self.filename = tk.StringVar(value=self.new_filename())
        ttk.Label(right, text="Filename", style="Sub.TLabel").pack(anchor="w")
        name_row = ttk.Frame(right)
        name_row.pack(fill="x", pady=(5, 6))
        ttk.Entry(name_row, textvariable=self.filename).pack(side="left", fill="x", expand=True)
        ttk.Label(name_row, text="Format").pack(side="left", padx=(10, 5))
        self.format_select = ttk.Combobox(name_row, textvariable=self.format, values=core.OUTPUT_FORMATS, state="readonly", width=8)
        self.format_select.pack(side="left")
        self.format_select.bind("<<ComboboxSelected>>", self.format_changed)
        ttk.Label(right, text="Saves original codecs. Use MKV if another format rejects the streams.", style="Sub.TLabel", wraplength=650).pack(anchor="w", pady=(0, 12))
        buttons = ttk.Frame(right)
        buttons.pack(fill="x")
        self.download = ttk.Button(buttons, text="Download", style="Accent.TButton", command=self.start)
        self.download.pack(side="left")
        self.cancel = ttk.Button(buttons, text="Cancel", command=self.cancel_download, state="disabled")
        self.cancel.pack(side="left", padx=8)
        ttk.Button(buttons, text="Open folder", command=self.open_folder).pack(side="right")
        self.progress = ttk.Progressbar(right, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(16, 6))
        self.status = tk.StringVar(value="Ready")
        ttk.Label(right, textvariable=self.status, wraplength=650).pack(anchor="w")
        self.log = tk.Text(right, height=7, wrap="word", font=("Consolas", 9), relief="flat", background="#e9eef6")
        self.log.pack(fill="both", expand=True, pady=(10,0))
        self.log.configure(state="disabled")
        bottom = ttk.Frame(body)
        bottom.pack(fill="x", pady=(16,0))
        ttk.Label(bottom, text="FFmpeg").pack(side="left")
        self.ffmpeg = tk.StringVar(value=self.settings["ffmpeg"])
        ttk.Entry(bottom, textvariable=self.ffmpeg).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(bottom, text="Browse", command=self.browse_ffmpeg).pack(side="left")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.poll_captures()
        self.poll_events()

    def new_filename(self, title=None):
        return core.title_filename(title or "video", self.format.get())

    def format_changed(self, event=None):
        self.filename.set(core.change_extension(self.filename.get(), self.format.get()))

    def append_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        if int(self.log.index("end-1c").split(".")[0]) > 150:
            self.log.delete("1.0", "30.0")
        self.log.see("end")
        self.log.configure(state="disabled")

    def add_url(self):
        try:
            url = core.validate_url(self.paste.get().strip())
            core.add_capture({"action":"capture","title":"Pasted media URL",
                              "choices":[{"kind":"single","video":url,"label":"Media / playlist"}]})
            self.paste.set("")
        except Exception as exc:
            messagebox.showerror("Cannot add URL", str(exc), parent=self.root)

    def poll_captures(self):
        try:
            captures = core.list_captures()
            signature = tuple(row["id"] for row in captures)
            if signature != self.snapshot:
                self.snapshot = signature
                self.captures = captures
                previous = self.current_id
                self.tree.delete(*self.tree.get_children())
                for row in captures:
                    self.tree.insert("", "end", iid=str(row["id"]), text=row["title"])
                if captures:
                    selection = str(previous) if any(row["id"] == previous for row in captures) else str(captures[0]["id"])
                    # New captures are selected while idle; do not disturb active downloads.
                    if not self.worker or not self.worker.is_alive():
                        selection = str(captures[0]["id"])
                    self.tree.selection_set(selection)
                    self.choose_capture()
                else:
                    self.current_id = None
                    self.choices = []
                    self.source.set("")
                    self.source.configure(values=[])
                    self.title.set("Waiting for a capture")
        except Exception as exc:
            self.status.set("Capture inbox: " + str(exc))
        self.root.after(1000, self.poll_captures)

    def choose_capture(self, event=None):
        selection = self.tree.selection()
        if not selection:
            return
        capture = next((row for row in self.captures if str(row["id"]) == selection[0]), None)
        if not capture:
            return
        if self.current_id != capture["id"]:
            self.filename.set(self.new_filename(capture["title"]))
        self.current_id = capture["id"]
        self.choices = capture["choices"]
        self.title.set(capture["title"])
        self.source.configure(values=[f"{index+1}. {choice['label']}" for index,choice in enumerate(self.choices)])
        if self.choices:
            self.source.current(0)
        self.choice_changed()

    def choice_changed(self, event=None):
        index = self.source.current()
        if not 0 <= index < len(self.choices):
            return
        kind = self.choices[index]["kind"]
        if kind == "existing":
            self.local_frame.pack(fill="x", pady=(0,10), before=self.local_frame.master.winfo_children()[5])
            self.note.set("Choose your downloaded video. Its audio source will be checked before merging.")
        else:
            self.local_frame.pack_forget()
            self.note.set("Video and audio are checked before download. Links can expire; capture again if access fails."
                          if kind == "pair" else "This single source must contain audio. Video-only sources need a matching audio track.")

    def remove_capture(self):
        if self.current_id is not None:
            core.delete_capture(self.current_id)

    def browse_folder(self):
        path = filedialog.askdirectory(parent=self.root, initialdir=self.folder.get())
        if path:
            self.folder.set(path)

    def browse_video(self):
        path = filedialog.askopenfilename(parent=self.root, title="Choose downloaded video")
        if path:
            self.local_video.set(path)

    def browse_ffmpeg(self):
        path = filedialog.askopenfilename(parent=self.root, title="Choose ffmpeg.exe", filetypes=[("FFmpeg","ffmpeg.exe"),("All files","*")])
        if path:
            self.ffmpeg.set(path)

    def open_folder(self):
        try:
            folder = Path(self.folder.get()).expanduser().resolve()
            folder.mkdir(parents=True,exist_ok=True)
            os.startfile(folder)
        except Exception as exc:
            messagebox.showerror("Cannot open folder",str(exc),parent=self.root)

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        index = self.source.current()
        if not 0 <= index < len(self.choices):
            messagebox.showinfo("Select a source","Capture a link in Firefox or paste a media URL first.",parent=self.root)
            return
        try:
            core.tool_paths(self.ffmpeg.get())
            filename = core.change_extension(self.filename.get().strip(), self.format.get())
            self.filename.set(filename)
            if Path(filename).name != filename or any(c in filename for c in '<>:"/\\|?*') or Path(filename).suffix.lower().lstrip(".") not in core.OUTPUT_FORMATS:
                raise ValueError("Use a valid filename without folder separators.")
            output = Path(self.folder.get()).expanduser().resolve() / filename
            if output.exists():
                raise ValueError("That file already exists. Choose another filename.")
            choice = dict(self.choices[index])
            if choice["kind"] == "existing" and not Path(self.local_video.get()).is_file():
                raise ValueError("Choose your existing video file.")
            core.save_settings({"ffmpeg":self.ffmpeg.get(),"folder":self.folder.get(),"format":self.format.get()})
            self.progress.stop()
            self.progress.configure(mode="indeterminate")
            self.progress.start(12)
            self.download.configure(state="disabled")
            self.cancel.configure(state="normal")
            self.job = core.DownloadJob(self.ffmpeg.get(),choice,output,self.events,self.local_video.get())
            self.worker = threading.Thread(target=self.job.run,daemon=True)
            self.worker.start()
        except Exception as exc:
            messagebox.showerror("Cannot download",str(exc),parent=self.root)

    def cancel_download(self):
        if self.job:
            self.job.cancel()
            self.status.set("Cancelling…")

    def poll_events(self):
        try:
            while True:
                kind,value = self.events.get_nowait()
                if kind == "status":
                    self.status.set(value)
                elif kind == "log":
                    self.append_log(value)
                elif kind == "progress":
                    if value["percent"] is not None:
                        self.progress.stop()
                        self.progress.configure(mode="determinate",value=value["percent"])
                    self.status.set(f"Downloaded {value['seconds']:.0f}s of media · {value['speed']}")
                elif kind in ("done","error","cancelled"):
                    self.progress.stop()
                    self.progress.configure(mode="determinate",value=100 if kind == "done" else 0)
                    self.download.configure(state="normal")
                    self.cancel.configure(state="disabled")
                    self.status.set("Saved: " + value if kind == "done" else value)
                    self.append_log(("Saved: " if kind == "done" else "") + value)
        except queue.Empty:
            pass
        self.root.after(100,self.poll_events)

    def close(self):
        if self.worker and self.worker.is_alive():
            if not messagebox.askyesno("Stop download?","Cancel the active download and close?",parent=self.root):
                return
            self.job.cancel()
            self.status.set("Cancelling before closing…")
            self.wait_close()
        else:
            self.root.destroy()

    def wait_close(self):
        if self.worker and self.worker.is_alive():
            self.root.after(100,self.wait_close)
        else:
            self.root.destroy()

def acquire_single_instance():
    if os.name != "nt":
        return True, None
    name = "Local\\MediaLinkCapture-" + hashlib.sha256(str(core.APP_DIR).encode()).hexdigest()[:16]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p,ctypes.c_bool,ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    handle = kernel.CreateMutexW(None,False,name)
    if not handle:
        raise OSError("Could not create application mutex.")
    if ctypes.get_last_error() == 183:
        user = ctypes.WinDLL("user32")
        user.FindWindowW.argtypes = [ctypes.c_wchar_p,ctypes.c_wchar_p]
        user.FindWindowW.restype = ctypes.c_void_p
        user.ShowWindow.argtypes = [ctypes.c_void_p,ctypes.c_int]
        user.SetForegroundWindow.argtypes = [ctypes.c_void_p]
        window = user.FindWindowW(None,"Link Capture")
        if window:
            user.ShowWindow(window,9)
            user.SetForegroundWindow(window)
        return False, handle
    return True, handle

def main():
    smoke = "--smoke-test" in sys.argv
    temporary = tempfile.TemporaryDirectory() if smoke else None
    if smoke:
        core.DATA_DIR = Path(temporary.name)
    should_open, mutex = (True,None) if smoke else acquire_single_instance()
    if not should_open:
        return
    root = tk.Tk()
    app = App(root)
    if smoke:
        # Exercise inbox selection, including existing-video mode.
        core.add_capture({"action":"capture","title":"UI check","choices":[{"kind":"existing","audio":"https://example.test/audio","label":"Existing video + audio"}]})
        app.poll_captures()
        root.after(300,root.destroy)
    root.mainloop()
    if temporary:
        temporary.cleanup()

if __name__ == "__main__":
    main()
