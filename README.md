# NMS Base Replicator

Copy construction from one No Man’s Sky planetary base into an existing destination planetary base. Replication replaces the destination’s object list with a copy of the source’s object list. The destination keeps its location and base metadata, and the source and original files stay intact.

### After You Import Your Replicated Base
If you wish to manipulate your base in 3D space, use my **[No-Mans-Sky-3D-Base-Aligner](https://github.com/ebaleytherogue/No-Mans-Sky-3D-Base-Aligner)**
project.

## Prepare your exports

1. Claim the destination base in-game if needed, save, and exit the game. Back up the entire save folder.
2. In NMSE, open the destination save and use **Tools → Export JSON** to create a full gamesave export. It must already contain the destination planetary base.
3. If the source base is in that export, reuse the same JSON. Otherwise, in some other gamesave file, export its full gamesave as a separate JSON file or export the source base as a raw `.nmsbase` file.

## Install the Windows portable app

1. Find **`NMS Base Replicator - Windows x64 Portable.zip`**. The repository’s `NMS-Base-Replicator - Python.zip` is a separate Python source archive.
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
5. **Export complete** displays the two output paths. For example, choosing `replicated-base.json` creates that full destination gamesave and a matching `replicated-base.nmsbase` for the selected destination base. Both filenames must be available. The wizard protects existing files.

## Archive, Shelve, and Restore

Open **Archive, Shelve, and Restore** in the wizard and select an NMSE gamesave JSON export. Choose where to keep **Archived Bases** and **Shelved Bases**. The app remembers those folders. Check individual bases or use a wildcard such as `*001-*` and **Select Matches**. **Clear Filter** shows all rows while keeping your selection. **Clear Current Selections** deselects every base, including hidden rows.

- **Archive a copy** exports the selected records to `Archived_Bases`.
- **Archive and remove** exports the complete records before removing them from a new gamesave JSON.
- **Shelve** exports the complete records to `Shelved_Bases` and replaces only the construction in the new gamesave JSON. Each base keeps its name, owner, location, and other base metadata.

Put exactly three NMSE raw planetary base exports in `Placeholder_Bases` beside the portable EXE (or beside `wizard.py` when running from source). Start with `1_Base_Computer_Only.nmsbase`, `2_Computer_Plus_Floor.nmsbase`, and `3_Small_Utility_Base.nmsbase`. Each export needs one Base Computer. The wizard reads the files when you open the action screen and checks them again before shelving. To change the three choices, replace or rename the files while keeping one file per prefix (`1_`, `2_`, and `3_`). The remainder of each filename becomes its display label.

**Restore** scans the current archive and shelf folders. Keep each raw `.nmsbase` with its matching `.archive.json` so the catalog can rebuild the entry and locate its original slot. Search by name, address, action, date, or source filename. The catalog can show multiple historical versions of a base.

- **Restore to original location** replaces construction at the matching site or reinserts the complete record if the site is vacant. After a successful original-location restore from the shelf, the app moves the restored file pair into `Exported_Bases` beside `Shelved_Bases`. Any displaced construction from that operation is also backed up in `Exported_Bases`.
- **Restore to another location** verifies a complete backup of the destination in `Shelved_Bases` before writing the output. The destination keeps its identity and only its construction changes.

The wizard writes modified saves to a new timestamped JSON file. Terrain data already in the selected gamesave stays in that export. Archive files contain the base record and catalog information. For separate terrain backups, keep the full NMSE gamesave export and any NMSE terrain sidecars.

## Import and verify in NMSE

1. With the game closed and your backup available, open the destination save in NMSE. Use **Tools → Import JSON** with the generated full gamesave JSON. Review the destination base and its location before saving the result.
2. If you use the base-only output instead, select the existing destination base in NMSE and choose **Import**. The `.nmsbase` import route still needs in-game verification.
3. Load the game and visit the destination before committing to the result. Check the Base Computer, part placement, and connections.

The Replicator copies object data as-is. It applies no translation, rotation, height correction, or terrain edits. The same geometry can appear buried or floating on different terrain. The app works on exported files and supports planetary bases. Freighter, space-station, asteroid, and corvette bases are outside scope.


## Python command line

The repository source and portable ZIP’s **Python Examples** require Python 3.10 or later and use the standard library. Run these commands from the folder containing `main.py`.

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
