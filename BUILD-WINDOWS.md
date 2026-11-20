# Build a Windows x64 portable release

Open Windows PowerShell or PowerShell 7 and switch to the Replicator repository.

```powershell
Set-Location -LiteralPath 'G:\Code_Repositories\No-Mans-Sky-Base-Replicator'
```

If your checkout is in a different folder, substitute its path. Run the remaining commands from that folder.

## 1. Decide whether to set up .venv

**Already have a working `.venv` with the current build dependencies? Skip to step 2.** The environment persists after you close PowerShell or restart Windows. The build script uses it automatically, so activation is optional.

- **First build, or no `.venv` folder.** Install Windows x64 Python 3.14 with Tcl/Tk, then create the environment.

  ```powershell
  py -3.14 -m venv .venv
  ```

  If `py` is unavailable, run the installed x64 Python 3.14 executable with `-m venv .venv`. Once the environment is created, install the dependencies using the command below.

- **Existing `.venv` with missing or outdated build dependencies.** Keep the environment and run the install command below. Run it again when `requirements-windows.txt` changes or the build reports missing dependencies.

  ```powershell
  & .\.venv\Scripts\python.exe -m pip install -r .\requirements-windows.txt
  ```

If `.venv` points to a removed Python installation or the build reports the wrong architecture, move the old folder aside and follow the first-build steps.

## 2. Build the portable ZIP

From the repository root, set the execution policy for the current PowerShell session before running the build. Run both commands in the same window and substitute your release version. The policy expires when you close the session.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\build-windows.ps1 -Version v1.2.3
```

The script uses `.venv\Scripts\python.exe` without activation. To use another prepared Windows x64 environment, pass `-Python 'C:\path\to\python.exe'`.

Use three numeric version components, each from 0 to 65535, with an optional leading `v`. The example builds `dist\NMS-Base-Replicator-Windows-x64-Portable_v1.2.3.zip` and stamps the EXE's File version and Product version as `1.2.3`. A repeat build replaces the portable folder and any ZIP with the same version.

Extract the ZIP into a fresh folder. Open `NMS Base Replicator` and check for the EXE, `_internal`, `Placeholder_Bases` with three `.nmsbase` files, `Python Examples`, `LICENSE`, and `Windows-Quick-Start.md`. Right-click the extracted EXE, select **Properties → Details**, and check both version fields. Launch the extracted EXE and confirm that the wizard opens.
