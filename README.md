# NMS Base Replicator

Copy construction between No Man’s Sky planetary bases, archive complete base records, or shelve construction behind a small placeholder and restore it later. Replication replaces the destination’s object list while preserving its location and base metadata. The app works on NMSE exports and writes new files.

### After You Import Your Replicated Base
If you wish to manipulate your base in 3D space, use my **[No-Mans-Sky-3D-Base-Aligner](https://github.com/ebaleytherogue/No-Mans-Sky-3D-Base-Aligner)**
project.

## Prepare your exports

1. Claim the destination base in-game if needed, save, and exit the game. Back up the entire save folder.
2. In NMSE, open the destination save and use **Tools → Export JSON** to create a full gamesave export. It must already contain the destination planetary base.
3. If the source base is in that export, reuse the same JSON. Otherwise, in some other gamesave file, export its full gamesave as a separate JSON file or export the source base as a raw `.nmsbase` file.

## Install the Windows portable app

1. Find the Windows x64 portable ZIP for the build you want to use. The Python source is available in this repository.
2. Right-click the portable ZIP in File Explorer, select **Extract All**, and choose a folder you can write to.
3. Open the extracted **NMS Base Replicator** folder and double-click **NMS Base Replicator.exe**. Keep `_internal` beside the executable. The ZIP includes the runtime, so the wizard needs no installer or separate Python installation.

The portable folder also includes a quick-start guide and a **Python Examples** folder with optional command-line examples.

## Use the Windows wizard

1. On **Choose a workflow**, select one of the following and click **Next**.

   | Workflow | Files to choose |
   | --- | --- |
   | **One gamesave JSON** | One full JSON export containing two distinct bases. |
   | **Two gamesave JSON files** | Separate full JSON exports for the source and destination. |
   | **Source .nmsbase and destination gamesave JSON** | One raw source base export and one full destination JSON export. |

2. On **Choose input files**, click **Browse…** for each requested file, then click **Load bases**.
3. On **Choose bases**, select the source construction and the destination to replace. For a `.nmsbase` source, the wizard displays the source automatically. Use the names, object counts, and addresses to distinguish similarly named bases. Click **Review**.
4. On **Review and export**, check the source count, the destination address, and how many destination objects will be replaced. Click **Choose output and export**, then save under a new `.json` filename.
5. **Export complete** displays the two output paths. For example, choosing `replicated-base.json` creates that full destination gamesave and a matching `replicated-base.nmsbase` for the selected destination base. If either filename is in use, the wizard identifies the conflicting file and lets you retry with a new name. Existing files are protected.

## Archive, Shelve, and Restore

Open **Archive, Shelve, and Restore** and select a full NMSE gamesave JSON export. The wizard defaults to `Archived_Bases` and `Shelved_Bases` under Documents and remembers folder changes. Choose **Archive or Shelve**, then check planetary bases individually or use a case-insensitive name pattern such as `*001-*` and click **Select Matches**. **Clear Filter** shows every row and keeps the selection. **Clear Current Selections** also clears checked rows hidden by the filter.

- **Archive a copy and leave bases in the gamesave** saves the complete selected base records in `Archived_Bases`. This action produces only backup files.
- **Archive and remove bases from the exported gamesave** verifies the backups in `Archived_Bases` before writing a new JSON with those base records removed.
- **Shelve bases and replace construction with a placeholder** verifies the original records in `Shelved_Bases` before writing a new JSON. The same selected placeholder supplies the construction for each checked base. Each base keeps its name, owner, location, and other metadata.

### Configure the three placeholders

Create `Placeholder_Bases` beside the portable EXE or beside `wizard.py` when running from source. Extract the three files from [Base_Replicator_Base_Templates.zip](Base_Replicator_Base_Templates.zip) into that folder.

1. `1_Floor_Plus_Teleporter.nmsbase`
2. `2_Minimal_Shelter_Teleporter.nmsbase`
3. `3_Underwater_Hab_w_Short-Range_Teleporter_to_Higher_Ground.nmsbase`

You can substitute your own raw NMSE planetary `.nmsbase` exports. Keep exactly three `.nmsbase` files, one per prefix (`1_`, `2_`, and `3_`), with distinct names after the prefixes. The wizard turns underscores in those names into spaces for the picker. Each export needs exactly one Base Computer and valid object IDs and placement vectors. The wizard validates the files when opening the action screen and checks them again before shelving. Archive and restore are available independently of the placeholder files.

### Restore a stored base

Choose **Restore** to scan the configured archive and shelf folders. Keep each raw `.nmsbase` with its matching `.archive.json` catalog file. The catalog can show multiple versions and accepts wildcard filters for the base name, address, action, date, or source filename.

- **Restore to original location** looks for the saved galactic address and position, checks the base identity, and stops if the match is conflicting or ambiguous. It replaces only construction at a matching base. If the site is vacant, it reinserts the complete stored record into its original base list.
- **Restore to another location** uses an existing planetary base you select. The wizard verifies a complete backup of that destination in `Shelved_Bases` before writing the new JSON. The destination keeps its identity and location, and the stored source entry stays available.
- If an original-location restore replaces different construction, the wizard verifies a complete backup of the existing base before writing the new JSON. For an archived entry, that backup goes to `Shelved_Bases`. For a shelf entry returning to its original site, it goes to `Exported_Bases`, a folder beside `Shelved_Bases`. After verifying the output JSON, the wizard copies and verifies the restored shelf pair in `Exported_Bases` before removing the pair from the shelf.

Archive-and-remove, shelving, and restore produce a new timestamped gamesave JSON in the folder you choose. The input export remains available. Terrain data already present in the input stays in the new JSON. For a separate terrain backup, keep the full NMSE export and any terrain sidecars.

## Import and verify in NMSE

1. With the game closed and your backup available, open the destination save in NMSE. Use **Tools → Import JSON** with the generated full gamesave JSON. Review the destination base and its location before saving the result.
2. If you use the base-only output instead, select the existing destination base in NMSE and choose **Import**. The `.nmsbase` import route still needs in-game verification.
3. Load the game and visit the destination before committing to the result. Check the Base Computer, part placement, and connections.

The Replicator copies object data as-is. It applies no translation, rotation, height correction, or terrain edits. The same geometry can appear buried or floating on different terrain. The app works on exported files and supports planetary bases. Freighter, space-station, asteroid, and corvette bases are outside scope.


## Python command line

The command line supports `list` and `replicate` with Python 3.10 or later and the standard library. Use the wizard for archive, shelving, restoration, and placeholder selection. See the [macOS and Linux guide](No-Mans-Sky-Base-Replicator_About_Mac_and_Linux.md) for platform details. Run these commands from the folder containing `main.py`.

From this project folder:

```powershell
python main.py list "C:\Saves\original.json"
python main.py list "C:\Saves\destination.json"
```

Use the displayed 1-based base number or an exact unique base name:

```powershell
python main.py replicate --source "C:\Saves\original.json" --source-base 1 --destination "C:\Saves\destination.json" --destination-base 2 --output-prefix "C:\Saves\replicated-base"
```

If the source is a raw `.nmsbase`, **omit** `--source-base`:

```powershell
python main.py replicate --source "C:\Saves\building.nmsbase" --destination "C:\Saves\destination.json" --destination-base "New Planet Base" --output-prefix "C:\Saves\replicated-base"
```

For a same-save copy, pass the same JSON path to both arguments and choose two distinct bases. To run the repository tests:

```powershell
python -m unittest discover -s tests -v
```
