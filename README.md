# NMS Base Replicator — Phase 1 prototype

A standalone, standard-library Python CLI for **replicating** the construction geometry of one planetary base into an **existing** destination planetary base. The source base is not removed or changed. No geometry transformation is performed.

**Status:** Prototype. Tested on synthetic JSON fixtures only, **not yet tested with a real NMS gamesave or against NMSE's `.nmsbase` importer**. Do not trust these outputs with your live save without a backup and manual test.

## Requirements

- Python 3.10 or newer (Windows, macOS, Linux)
- Source: an NMSE / GoatFungus whole-save JSON export, or an NMSE raw `.nmsbase` file (JSON object).
- Destination: a whole-save JSON export **already containing the destination planetary base**.
- No pip packages required.

## Usage

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

Two files are created:

- `replicated-base.json` — full destination save with only the selected destination base's `Objects` array replaced.
- `replicated-base.nmsbase` — raw selected destination base record containing destination metadata and the replicated `Objects` array.

Inputs are never written to. **Existing output files are never overwritten.** A same-save copy is supported: use the same JSON path for `--source` and `--destination`, selecting two *different* bases.

## Recommended NMSE workflow

1. In No Man's Sky, claim a fresh destination base; save and quit.
2. Exit NMS **and Steam** to avoid Cloud Sync overwrites. Back up the **entire save folder**.
3. Export whole-save JSON in NMSE (Tools → Export JSON) or GoatFungus; keep the original untouched.
4. Run the Replicator and examine the new output files and counts.
5. **Preferred first test:** In NMSE open the correct destination save and use **Tools → Import JSON** for the generated full-save `.json`; review the selected base before saving back to disk.
6. **Alternative, not yet validated:** Select the *existing* destination planetary base in NMSE and choose **Import** (not *Import as New*) with the generated `.nmsbase`. Verify its location and name before saving. This route may need format adjustments after testing against an actual NMSE export.
7. Load the game, visit the destination base, inspect before saving. If incorrect, exit without saving and restore backup.

**Important:** Terrain may cause the replicated construction to appear underground or floating. The app preserves the source object geometry and destination metadata; it does not move, rotate, or elevate parts. It also does **not** copy terrain-edit sidecars (`.terrain.json`) or edit game saves directly.

## Validation and limits

- The code discovers records within `PersistentPlayerBases` arrays that contain `Name`, `GalacticAddress`, and an `Objects` list, independent of where the array sits in the save.
- It preserves the **JSON values** of every other field and record in the destination save. Indentation, whitespace, and numeric text representation may change when exported.
- It refuses to silently guess when duplicate base names exist: select by list number.
- Planetary bases only. Freighter, space-station, asteroid, and corvette bases are outside scope.
- Actual save formats can vary by game version and editor; real sample files are needed to validate field shapes and compatibility.
- Some base computer and ownership behavior requires an in-game test. The code replaces exactly one array, matching the established manual checklist.

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Future steps

1. Test with redacted real whole-save and `.nmsbase` exports, ideally from NMSE v1.5.12.
2. Compare raw `.nmsbase` export with the generated file; verify NMSE Import behavior.
3. Add a graphical interface once the core workflow is verified.

No connection to NMS 3D Base Aligner is required or planned.
