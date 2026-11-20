# No-Mans-Sky-Base-Replicator on macOS and Linux

**Compatibility is untested on macOS and Linux.** The terminal instructions below use the checked-in source. `main.py` provides `list` and `replicate`.

## Archive, shelving, and restoration

The wizard can archive a copy of a base, archive and remove it from an exported save, or replace its construction with one of three configurable placeholders. You can restore a stored version to its original site or to an existing planetary base. A restore to another base verifies a complete backup of the destination before replacing its construction. Keep each `.nmsbase` and its matching `.archive.json` together so the restore catalog can find the stored base. [Wizard workflow and placeholder setup](README.md#archive-shelve-and-restore)

These workflows use the Tkinter wizard in `wizard.py`. Running it from source requires Python with Tkinter and a graphical desktop. The packaged executable is built for Windows, and the source wizard is unverified on macOS and Linux.

## macOS · Terminal

Use an existing Python 3.10 or later interpreter if available. Check it with `python3 --version`. Otherwise, with Homebrew installed, use:

```bash
brew install python@3.12
```

From Terminal, replace the example path with the path to your checkout. The block uses Homebrew Python. If using an existing installation, replace `"$(brew --prefix python@3.12)/bin/python3.12"` with its `python3` command or executable path.

```bash
cd "/path/to/No-Mans-Sky-Base-Replicator"
"$(brew --prefix python@3.12)/bin/python3.12" -m venv .venv
source .venv/bin/activate
python --version
```

The command line uses the Python standard library and needs no pip packages.

Back up your save and prepare full JSON exports containing the source and destination planetary bases. Use the list command to find base numbers. For a single-save copy, pass the same JSON file as source and destination and select two distinct bases. For a raw source `.nmsbase`, pass it as `--source` and omit `--source-base`.

```bash
python main.py list "$HOME/Saves/source.json"
python main.py list "$HOME/Saves/destination.json"
python main.py replicate --source "$HOME/Saves/source.json" --source-base 1 --destination "$HOME/Saves/destination.json" --destination-base 2 --output-prefix "$HOME/Saves/replicated-base"
```

Use a fresh output prefix. The command creates a new full JSON export and a base-only `.nmsbase` export. Import through a compatible save editor and verify the destination in-game. See the [repository README](README.md) for the export and import workflow.

## Linux · Bash

Use the command for your distribution if Python or its virtual environment support is missing. Check that `python3 --version` reports Python 3.10 or later.

```bash
# Ubuntu or Debian
sudo apt update
sudo apt install python3 python3-venv

# Fedora
sudo dnf install python3

# Arch Linux
sudo pacman -Syu python
```


```bash
cd "/path/to/No-Mans-Sky-Base-Replicator"
python3 -m venv .venv
source .venv/bin/activate
python --version
```

The command line uses the Python standard library and needs no pip packages.

Back up your save and prepare full JSON exports containing the source and destination planetary bases. Use the list command to find base numbers. For a single-save copy, pass the same JSON file as source and destination and select two distinct bases. For a raw source `.nmsbase`, pass it as `--source` and omit `--source-base`.

```bash
python main.py list "$HOME/Saves/source.json"
python main.py list "$HOME/Saves/destination.json"
python main.py replicate --source "$HOME/Saves/source.json" --source-base 1 --destination "$HOME/Saves/destination.json" --destination-base 2 --output-prefix "$HOME/Saves/replicated-base"
```

Use a fresh output prefix. The command creates a new full JSON export and a base-only `.nmsbase` export. Import through a compatible save editor and verify the destination in-game. See the [repository README](README.md) for the export and import workflow.

In a new terminal, return to the checkout and run `source .venv/bin/activate` before launching again.
