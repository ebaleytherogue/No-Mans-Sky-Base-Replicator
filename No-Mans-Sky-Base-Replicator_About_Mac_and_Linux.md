# No-Mans-Sky-Base-Replicator on macOS and Linux

**Compatibility is untested on macOS and Linux.** These instructions use the checked-in source. The repository’s Python command line covers replication. The packaged wizard is a Windows executable.

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

The source uses the Python standard library. There are no packages to install with pip.

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

The source uses the Python standard library. There are no packages to install with pip.

Back up your save and prepare full JSON exports containing the source and destination planetary bases. Use the list command to find base numbers. For a single-save copy, pass the same JSON file as source and destination and select two distinct bases. For a raw source `.nmsbase`, pass it as `--source` and omit `--source-base`.

```bash
python main.py list "$HOME/Saves/source.json"
python main.py list "$HOME/Saves/destination.json"
python main.py replicate --source "$HOME/Saves/source.json" --source-base 1 --destination "$HOME/Saves/destination.json" --destination-base 2 --output-prefix "$HOME/Saves/replicated-base"
```

Use a fresh output prefix. The command creates a new full JSON export and a base-only `.nmsbase` export. Import through a compatible save editor and verify the destination in-game. See the [repository README](README.md) for the export and import workflow.

In a new terminal, return to the checkout and run `source .venv/bin/activate` before launching again.
