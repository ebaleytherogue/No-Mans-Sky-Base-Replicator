"""Windows wizard for NMS Base Replicator."""
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from archive_ui import ArchiveUI
from replicator import (ReplicationError, find_bases, get_at, load_json,
                        parse_nmsbase, replicate, serialize_json, write_outputs)


WORKFLOWS = (
    "One gamesave JSON",
    "Two gamesave JSON files",
    "Source .nmsbase and destination gamesave JSON",
)


class Wizard:
    def __init__(self, root):
        self.root = root
        root.title("NMS Base Replicator")
        root.minsize(750, 520)
        self.body = ttk.Frame(root, padding=24)
        self.body.pack(fill="both", expand=True)
        self.mode = tk.IntVar(value=0)
        self.source = tk.StringVar()
        self.destination = tk.StringVar()
        self.archive = ArchiveUI(self)
        self.show_workflow()

    def page(self, title, description):
        for child in self.body.winfo_children():
            child.destroy()
        ttk.Label(self.body, text=title, font=("Segoe UI", 17, "bold")).pack(anchor="w")
        ttk.Label(self.body, text=description, wraplength=630).pack(anchor="w", pady=(8, 20))

    def navigation(self, back, label, command):
        bar = ttk.Frame(self.body)
        bar.pack(side="bottom", fill="x", pady=(20, 0))
        if back:
            ttk.Button(bar, text="Back", command=back).pack(side="left")
        ttk.Button(bar, text=label, command=command).pack(side="right")

    def show_workflow(self):
        self.page("1 of 4  |  Choose a workflow",
                  "Copy the construction from one base into an existing destination base.")
        for index, label in enumerate(WORKFLOWS):
            ttk.Radiobutton(self.body, text=label, variable=self.mode, value=index).pack(
                anchor="w", pady=5)
        ttk.Button(self.body, text="Archive, Shelve, and Restore", command=self.archive.open).pack(
            anchor="w", pady=(16, 0))
        self.navigation(None, "Next", self.show_files)

    def file_row(self, label, variable, extension):
        ttk.Label(self.body, text=label).pack(anchor="w", pady=(8, 3))
        row = ttk.Frame(self.body)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)

        def browse():
            path = filedialog.askopenfilename(parent=self.root, filetypes=[(label, f"*{extension}")])
            if path:
                variable.set(path)

        ttk.Button(row, text="Browse…", command=browse).pack(side="right", padx=(8, 0))

    def show_files(self):
        self.page("2 of 4  |  Choose input files", WORKFLOWS[self.mode.get()])
        mode = self.mode.get()
        if mode:
            label = "Source base export" if mode == 2 else "Source gamesave JSON"
            self.file_row(label, self.source, ".nmsbase" if mode == 2 else ".json")
        self.file_row("Destination gamesave JSON" if mode else "Gamesave JSON",
                      self.destination, ".json")
        self.navigation(self.show_workflow, "Load bases", self.load_inputs)

    def load_inputs(self):
        try:
            mode = self.mode.get()
            self.destination_path = Path(self.destination.get().strip()).resolve()
            self.source_path = Path(self.source.get().strip()).resolve() if mode else self.destination_path
            expected = ".nmsbase" if mode == 2 else ".json"
            if self.destination_path.suffix.lower() != ".json" or self.source_path.suffix.lower() != expected:
                raise ReplicationError(f"Choose a destination .json and a source {expected} file.")
            if mode == 1 and self.source_path.samefile(self.destination_path):
                raise ReplicationError("Choose two separate files or use the one-gamesave workflow.")
            self.destination_save = load_json(self.destination_path)
            self.source_data = load_json(self.source_path) if mode else self.destination_save
            self.destination_bases = find_bases(self.destination_save)
            self.source_bases = [] if mode == 2 else (
                find_bases(self.source_data) if mode else self.destination_bases)
            if not self.destination_bases or (mode != 2 and not self.source_bases):
                raise ReplicationError("No recognized bases were found in one of the gamesaves.")
            if not mode and len(self.destination_bases) < 2:
                raise ReplicationError("The gamesave must contain two distinct bases.")
            if mode == 2:
                self.source_record = parse_nmsbase(self.source_data)
            self.show_bases()
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not load inputs", str(exc), parent=self.root)

    def base_picker(self, label, bases):
        ttk.Label(self.body, text=label).pack(anchor="w", pady=(8, 3))
        choices = [f"{index}. {base.name}  |  {base.count} objects  |  {base.address}"
                   for index, base in enumerate(bases, 1)]
        picker = ttk.Combobox(self.body, values=choices, state="readonly")
        picker.pack(fill="x")
        return picker

    def show_bases(self):
        self.page("3 of 4  |  Choose bases", "Select the construction to copy and the base to replace.")
        if self.mode.get() == 2:
            name = self.source_record.get("Name") or self.source_path.stem
            ttk.Label(self.body, text=f"Source  •  {name}").pack(anchor="w")
        else:
            self.source_picker = self.base_picker("Source base", self.source_bases)
        self.target_picker = self.base_picker("Destination base", self.destination_bases)
        self.navigation(self.show_files, "Review", self.review)

    def review(self):
        destination_index = self.target_picker.current()
        if destination_index < 0:
            messagebox.showerror("Select a base", "Choose a destination base.", parent=self.root)
            return
        self.target = self.destination_bases[destination_index]
        if self.mode.get() != 2:
            source_index = self.source_picker.current()
            if source_index < 0 or (self.mode.get() == 0 and source_index == destination_index):
                messagebox.showerror("Select a base", "Choose a distinct source base.", parent=self.root)
                return
            source_info = self.source_bases[source_index]
            self.source_record = get_at(self.source_data, source_info.path)
        source_name = self.source_record.get("Name") or self.source_path.stem
        count = len(self.source_record["Objects"])
        self.page("4 of 4  |  Review and export",
                  "The export preserves the destination location and metadata. Original files stay intact.")
        summary = (f"Source: {source_name} ({count} objects)\n"
                   f"Destination: {self.target.name} ({self.target.count} objects to replace)\n"
                   f"Destination address: {self.target.address}\n\n"
                   "Two new files will be created: a full gamesave and a replacement base export.")
        ttk.Label(self.body, text=summary, wraplength=630, justify="left").pack(anchor="w")
        self.navigation(self.show_bases, "Choose output and export", self.export)

    def export(self):
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Name the new gamesave and base export",
            defaultextension=".json", filetypes=[("Gamesave JSON", "*.json")],
            initialfile="replicated-base.json", confirmoverwrite=False)
        if not path:
            return
        json_path = Path(path)
        if json_path.suffix.lower() != ".json":
            messagebox.showerror("Choose a JSON filename", "Use a .json extension.", parent=self.root)
            return
        base_path = json_path.with_suffix(".nmsbase")
        try:
            self.root.configure(cursor="watch")
            self.root.update_idletasks()
            save, base, _ = replicate(self.destination_save, self.target.path, self.source_record)
            write_outputs({json_path: serialize_json(save), base_path: serialize_json(base)})
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Export failed", str(exc), parent=self.root)
            return
        finally:
            self.root.configure(cursor="")
        self.page("Export complete", "Your replicated gamesave and replacement base are ready.")
        ttk.Label(self.body, text=f"{json_path}\n{base_path}", wraplength=630).pack(anchor="w")
        self.navigation(None, "Start again", self.restart)

    def restart(self):
        self.source_data = self.destination_save = self.source_record = None
        self.show_workflow()


if __name__ == "__main__":
    root = tk.Tk()
    Wizard(root)
    root.mainloop()
