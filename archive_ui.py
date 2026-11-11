"""Archive, Shelve, and Restore workflow for the Windows wizard."""
from fnmatch import fnmatchcase
from pathlib import Path
from tempfile import NamedTemporaryFile
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from archive import (EXPORTED_BASES, RestoreResult, archive_candidates, discover_templates,
                     original_destination, restore_base, scan_catalog, store_bases, timestamped_json)
from replicator import ReplicationError, load_json, serialize_json


class ArchiveUI:
    def __init__(self, wizard):
        self.wizard = wizard
        self.root = wizard.root
        self.body = wizard.body
        app = Path(sys.executable) if getattr(sys, 'frozen', False) else Path(__file__)
        self.templates_folder = app.resolve().parent / 'Placeholder_Bases'
        self.settings = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'NMS Base Replicator' / 'folders.json'
        try:
            settings = load_json(self.settings) if self.settings.exists() else {}
        except ReplicationError:
            settings = {}
        self.folders = {}
        for name in ('Archived_Bases', 'Shelved_Bases'):
            saved = settings.get(name) if isinstance(settings, dict) else None
            self.folders[name] = tk.StringVar(value=saved if isinstance(saved, str) and saved else
                                               str(Path.home() / 'Documents' / name))

    def open(self):
        self.wizard.page('Archive, Shelve, and Restore', 'Choose an NMSE gamesave JSON export.')
        self.wizard.file_row('Gamesave JSON', self.wizard.destination, '.json')
        for name, variable in self.folders.items():
            ttk.Label(self.body, text=name.replace('_', ' ')).pack(anchor='w', pady=(8, 3))
            row = ttk.Frame(self.body)
            row.pack(fill='x')
            ttk.Entry(row, textvariable=variable, state='readonly').pack(side='left', expand=True, fill='x')
            ttk.Button(row, text='Change…', command=lambda name=name: self.choose_folder(name)).pack(
                side='right', padx=(8, 0))
        bar = ttk.Frame(self.body)
        bar.pack(side='bottom', fill='x', pady=(20, 0))
        ttk.Button(bar, text='Back', command=self.wizard.show_workflow).pack(side='left')
        ttk.Button(bar, text='Restore', command=lambda: self.load(True)).pack(side='right')
        ttk.Button(bar, text='Archive or Shelve', command=lambda: self.load(False)).pack(side='right', padx=8)

    def choose_folder(self, name):
        path = filedialog.askdirectory(parent=self.root, title=f'Choose a parent folder for {name}')
        if not path:
            return
        folder = Path(path)
        if folder.name.casefold() != name.casefold():
            folder /= name
        values = {key: variable.get() for key, variable in self.folders.items()}
        values[name] = str(folder)
        temporary = None
        try:
            self.settings.parent.mkdir(parents=True, exist_ok=True)
            with NamedTemporaryFile(dir=self.settings.parent, delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(serialize_json(values))
            temporary.replace(self.settings)
        except OSError as exc:
            self.error(exc)
            return
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.folders[name].set(str(folder))

    def load(self, restoring):
        try:
            path = Path(self.wizard.destination.get().strip()).resolve()
            if path.suffix.casefold() != '.json':
                raise ReplicationError('Choose a gamesave .json export.')
            self.save = load_json(path)
            self.source = path
            self.bases = archive_candidates(self.save)
            self.selected = set()
            if restoring:
                self.catalog()
            else:
                self.select_bases()
        except (OSError, ValueError) as exc:
            self.error(exc)

    def table(self, columns):
        row = ttk.Frame(self.body)
        row.pack(fill='both', expand=True)
        tree = ttk.Treeview(row, columns=[label for label, _ in columns],
                            show='headings', selectmode='browse', height=9)
        for label, width in columns:
            tree.heading(label, text=label)
            tree.column(label, width=width, minwidth=width, stretch=label == 'Base')
        scroll = ttk.Scrollbar(row, command=tree.yview)
        tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        tree.pack(side='left', expand=True, fill='both')
        return tree

    def filter_row(self, pattern):
        row = ttk.Frame(self.body)
        row.pack(fill='x', pady=(0, 8))
        ttk.Label(row, text='Filter (* and ?)').pack(side='left')
        ttk.Entry(row, textvariable=pattern).pack(side='left', fill='x', expand=True, padx=8)
        ttk.Button(row, text='Clear Filter', command=lambda: pattern.set('')).pack(side='right')

    @staticmethod
    def matches(pattern, value):
        return fnmatchcase(value.casefold(), pattern.strip().casefold() or '*')

    def select_bases(self):
        self.wizard.page('Choose bases to archive or shelve', 'Check bases individually or select the filtered matches.')
        pattern = tk.StringVar()
        self.filter_row(pattern)
        tree = self.table([('Select', 60), ('Base', 230), ('Objects', 65), ('Address', 130)])
        summary = ttk.Label(self.body)
        summary.pack(anchor='w', pady=(8, 0))

        def visible():
            return [index for index, base in enumerate(self.bases) if self.matches(pattern.get(), base.name)]

        def update(*_):
            rows = visible()
            focus = tree.focus()
            tree.delete(*tree.get_children())
            for index in rows:
                base = self.bases[index]
                mark = '☑' if index in self.selected else '☐'
                tree.insert('', 'end', iid=str(index), values=(mark, base.name, base.count, base.address))
            if focus and tree.exists(focus):
                tree.focus(focus)
                tree.selection_set(focus)
            shown = len(self.selected.intersection(rows))
            summary.configure(text=f'{len(self.selected)} selected ({shown} visible, '
                                   f'{len(self.selected) - shown} hidden by filter)')

        def toggle(item):
            if item:
                tree.focus(item)
                self.selected.symmetric_difference_update({int(item)})
                update()
            return 'break'

        def click(event):
            if tree.identify_column(event.x) == '#1':
                item = tree.identify_row(event.y)
                if item:
                    tree.focus_set()
                    return toggle(item)
            return None

        def select_matches():
            self.selected.update(visible())
            update()

        def clear():
            self.selected.clear()
            update()

        tree.bind('<Button-1>', click)
        tree.bind('<space>', lambda _: toggle(tree.focus()))
        buttons = ttk.Frame(self.body)
        buttons.pack(fill='x', pady=(8, 0))
        ttk.Button(buttons, text='Select Matches', command=select_matches).pack(side='left')
        ttk.Button(buttons, text='Clear Current Selections', command=clear).pack(side='left', padx=8)
        pattern.trace_add('write', update)
        update()
        self.wizard.navigation(self.open, 'Choose action', self.choose_action)

    def choose_action(self):
        if not self.selected:
            self.error('Select at least one base.')
            return
        self.wizard.page('Choose an archive or shelving action', f'{len(self.selected)} bases selected.')
        action = tk.StringVar(value='export')
        choices = (('export', 'Archive a copy and leave bases in the gamesave'),
                   ('archive', 'Archive and remove bases from the exported gamesave'),
                   ('shelve', 'Shelve bases and replace construction with a placeholder'))
        for value, label in choices:
            ttk.Radiobutton(self.body, text=label, variable=action, value=value).pack(anchor='w', pady=3)
        try:
            templates = discover_templates(self.templates_folder)
            warning = ''
        except (OSError, ValueError, OverflowError) as exc:
            templates = []
            warning = str(exc)
        picker = ttk.Combobox(self.body, values=[template.label for template in templates], state='readonly')
        picker.pack(fill='x', pady=(12, 0))
        if templates:
            picker.current(0)
        else:
            picker.configure(state='disabled')
            ttk.Label(self.body, text=warning, wraplength=630).pack(anchor='w', pady=8)

        def run():
            mode = action.get()
            template = None
            if mode == 'shelve':
                index = picker.current()
                if index < 0:
                    self.error(warning or 'Choose a placeholder.')
                    return
                try:
                    current = discover_templates(self.templates_folder)
                    if current != templates:
                        self.choose_action()
                        raise ReplicationError('The placeholders changed. Review the refreshed choices.')
                    template = current[index]
                except (OSError, ValueError, OverflowError) as exc:
                    self.error(exc)
                    return
            output = self.output_path() if mode != 'export' else None
            if mode != 'export' and output is None:
                return
            folder = self.folder('Shelved_Bases' if mode == 'shelve' else 'Archived_Bases')
            label = dict(choices)[mode]
            detail = f'{label}?\n\nBases: {len(self.selected)}\nBackups: {folder}'
            if template:
                detail += f'\nPlaceholder: {template.label}'
            if output:
                detail += f'\nGamesave: {output}'
            if not messagebox.askokcancel('Confirm archive or shelving', detail, parent=self.root):
                return
            selected = [self.bases[index] for index in sorted(self.selected)]
            self.finish(lambda: store_bases(self.save, self.source, selected, mode, folder, output, template),
                        output)

        self.wizard.navigation(self.select_bases, 'Continue', run)

    def catalog(self):
        self.wizard.page('Find a stored base', 'Choose an archived or shelved version to restore.')
        entries, errors = scan_catalog(self.folder('Archived_Bases'), self.folder('Shelved_Bases'))
        pattern = tk.StringVar()
        self.filter_row(pattern)
        tree = self.table([('Base', 150), ('Action', 72), ('Saved', 143), ('Address', 124), ('Objects', 55)])
        if errors:
            ttk.Button(self.body, text=f'View {len(errors)} unreadable entries',
                       command=lambda: self.error('\n'.join(errors[:10]))).pack(anchor='w')
        if not entries:
            ttk.Label(self.body, text='No stored bases found in the selected folders.').pack(anchor='w')

        def update(*_):
            tree.delete(*tree.get_children())
            for index, entry in enumerate(entries):
                record = entry.record
                name = record.get('Name') or '(unnamed)'
                address = str(record['GalacticAddress'])
                if any(self.matches(pattern.get(), str(value)) for value in
                       (name, address, entry.action, entry.saved_at, entry.source_save)):
                    tree.insert('', 'end', iid=str(index), values=(
                        name, entry.action.capitalize(), entry.saved_at[:19].replace('T', ' '),
                        address, len(record['Objects'])))

        def pick():
            rows = tree.selection()
            if rows:
                self.restore_options(entries[int(rows[0])])
            else:
                self.error('Select a stored base.')

        pattern.trace_add('write', update)
        update()
        self.wizard.navigation(self.open, 'Choose destination', pick)

    def restore_options(self, entry):
        self.wizard.page('Choose a restore destination',
                         f'{entry.record.get("Name") or "(unnamed)"}  |  {entry.saved_at[:19].replace("T", " ")}'
                         f'  |  {entry.source_save}')
        another = tk.BooleanVar(value=False)
        ttk.Radiobutton(self.body, text='Restore to original location', variable=another, value=False).pack(anchor='w')
        ttk.Radiobutton(self.body, text='Restore to another location', variable=another, value=True).pack(anchor='w')
        picker = self.wizard.base_picker('Destination for restore to another location', self.bases)

        def run():
            target = None
            try:
                if another.get():
                    if picker.current() < 0:
                        raise ReplicationError('Choose a destination base.')
                    target = self.bases[picker.current()]
                    existing = target
                else:
                    existing = original_destination(self.save, entry)
            except (OSError, ValueError) as exc:
                self.error(exc)
                return
            output = self.output_path()
            if output is None:
                return
            shelf = self.folder('Shelved_Bases')
            returns_from_shelf = (not another.get() and entry.action in {'shelve', 'displaced', 'restore'}
                                  and entry.path.parent.resolve() == shelf.resolve())
            detail = (f'Shelve {existing.name} at {existing.address}, then replace its construction?'
                      if existing else f'Reinsert the complete base at {entry.record["GalacticAddress"]}?')
            detail += f'\n\nGamesave: {output}'
            if existing:
                detail += f'\nBackup folder: {shelf.parent / EXPORTED_BASES if returns_from_shelf else shelf}'
            if returns_from_shelf:
                detail += f'\nMove restored shelf entry to: {shelf.parent / EXPORTED_BASES}'
            if messagebox.askokcancel('Confirm restore', detail, parent=self.root):
                self.finish(lambda: restore_base(self.save, self.source, entry, output, shelf, target), output)

        self.wizard.navigation(self.catalog, 'Continue', run)

    def folder(self, name):
        return Path(self.folders[name].get())

    def output_path(self):
        folder = filedialog.askdirectory(parent=self.root, title='Choose a folder for the new gamesave JSON',
                                        initialdir=self.source.parent)
        return timestamped_json(Path(folder)) if folder else None

    def finish(self, operation, output):
        try:
            self.root.configure(cursor='watch')
            self.root.update_idletasks()
            result = operation()
        except (OSError, ValueError, TypeError) as exc:
            self.error(exc)
            return
        finally:
            self.root.configure(cursor='')
        backups = result.backups if isinstance(result, RestoreResult) else result
        self.wizard.page('Export complete', f'{len(backups)} base backups written.')
        if backups:
            ttk.Label(self.body, text=str(backups[0].parent), wraplength=630).pack(anchor='w')
        if output:
            ttk.Label(self.body, text=str(output), wraplength=630).pack(anchor='w', pady=(8, 0))
        if isinstance(result, RestoreResult):
            if result.moved_to:
                ttk.Label(self.body, text=f'Restored shelf entry moved to {result.moved_to}',
                          wraplength=630).pack(anchor='w', pady=(8, 0))
            if result.move_warning:
                ttk.Label(self.body, text=result.move_warning, wraplength=630).pack(anchor='w', pady=(8, 0))
        self.wizard.navigation(None, 'Start again', self.wizard.restart)

    def error(self, error):
        messagebox.showerror('Archive, Shelve, and Restore', str(error), parent=self.root)
