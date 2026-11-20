"""Archive, shelve, and restore planetary bases in NMSE JSON exports."""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from pathlib import Path
import re

from replicator import (BaseInfo, ReplicationError, find_bases, get_at, load_json,
                        parse_nmsbase, replicate, serialize_json, write_outputs)


INITIAL_TEMPLATES = (
    '1_Base_Computer_Only.nmsbase',
    '2_Computer_Plus_Floor.nmsbase',
    '3_Small_Utility_Base.nmsbase',
)
ACTIONS = {'archive', 'shelve', 'export', 'displaced', 'restore'}
EXPORTED_BASES = 'Exported_Bases'


@dataclass(frozen=True)
class Template:
    path: Path
    label: str
    record: dict


@dataclass(frozen=True)
class StoredBase:
    path: Path
    record: dict
    array_path: tuple
    index: int
    action: str
    saved_at: str
    source_save: str


@dataclass(frozen=True)
class RestoreResult:
    backups: list[Path]
    moved_to: Path | None = None
    move_warning: str = ''


def discover_templates(directory: Path) -> list[Template]:
    files = sorted((path for path in directory.iterdir()
                    if path.is_file() and path.suffix.casefold() == '.nmsbase'),
                   key=lambda path: path.name.casefold()) if directory.is_dir() else []
    if len(files) != 3:
        expected = ', '.join(INITIAL_TEMPLATES)
        raise ReplicationError(
            f'{directory} must contain exactly three .nmsbase files. Found {len(files)}. '
            f'Initial filenames are {expected}.')
    templates = []
    for number, path in enumerate(files, 1):
        prefix, _, stem = path.stem.partition('_')
        label = ' '.join(stem.replace('_', ' ').split())
        if prefix != str(number) or not label:
            raise ReplicationError('Use one named template per prefix: 1_, 2_, and 3_.')
        try:
            record = parse_nmsbase(load_json(path))
            if not _is_planetary(record):
                raise ReplicationError('Choose a planetary base export.')
            objects = record['Objects']
            if any(not isinstance(obj, dict) or not isinstance(obj.get('ObjectID'), str)
                   or not obj['ObjectID'].strip() for obj in objects):
                raise ReplicationError('Every construction object must have an ObjectID.')
            if any(not _vector(obj.get(key)) for obj in objects for key in ('Position', 'Up', 'At')):
                raise ReplicationError('Every construction object must have valid Position, Up, and At vectors.')
            if sum(obj['ObjectID'] == '^BASE_FLAG' for obj in objects) != 1:
                raise ReplicationError('The template must contain exactly one Base Computer.')
            serialize_json(record)
        except (ValueError, TypeError) as exc:
            raise ReplicationError(f'Invalid placeholder {path.name}: {exc}') from exc
        templates.append(Template(path, label, record))
    if len({template.label.casefold() for template in templates}) != 3:
        raise ReplicationError('Use three distinct placeholder names.')
    return templates


def timestamped_json(directory: Path, now: datetime | None = None) -> Path:
    stamp = (now or datetime.now()).strftime('%Y-%m-%d_%H%M%S_%f')
    return directory / f'NMS_Base_Replicator_{stamp}.json'


def _catalog_path(path: Path) -> Path:
    return path.with_suffix('.archive.json')


def read_entry(path: Path) -> StoredBase:
    record = parse_nmsbase(load_json(path))
    if not _is_planetary(record):
        raise ReplicationError(f'{path.name} is not a planetary base.')
    details = load_json(_catalog_path(path))
    if not isinstance(details, dict) or details.get('version') != 1:
        raise ReplicationError(f'Unsupported catalog record for {path.name}.')
    array_path = details.get('array_path')
    index = details.get('index')
    action = details.get('action')
    saved_at = details.get('saved_at')
    source_save = details.get('source_save')
    if (not isinstance(array_path, list) or not array_path
            or array_path[-1] != 'PersistentPlayerBases'
            or any(not isinstance(key, str) and (type(key) is not int or key < 0)
                   for key in array_path)
            or type(index) is not int or index < 0 or not isinstance(action, str)
            or action not in ACTIONS or not isinstance(saved_at, str)
            or not isinstance(source_save, str)):
        raise ReplicationError(f'Invalid catalog record for {path.name}.')
    datetime.fromisoformat(saved_at)
    return StoredBase(path, record, tuple(array_path), index, action, saved_at, source_save)


def scan_catalog(*folders: Path) -> tuple[list[StoredBase], list[str]]:
    entries = []
    errors = []
    for folder in dict.fromkeys(folders):
        try:
            if not folder.exists():
                continue
            paths = list(folder.iterdir())
        except OSError as exc:
            errors.append(f'{folder}: {exc}')
            continue
        for path in paths:
            if path.is_file() and path.suffix.casefold() == '.nmsbase':
                try:
                    entries.append(read_entry(path))
                except (OSError, ValueError) as exc:
                    errors.append(f'{path.name}: {exc}')
    return sorted(entries, key=lambda entry: entry.saved_at, reverse=True), errors


def _write_backups(save, bases: list[BaseInfo], folder: Path, action: str,
                   source_save: Path, now: datetime) -> list[Path]:
    folder.mkdir(parents=True, exist_ok=True)
    outputs = {}
    paths = []
    stamp = now.strftime('%Y-%m-%d_%H%M%S_%f')
    for number, base in enumerate(bases, 1):
        name = re.sub(r'[^\w.-]+', '_', base.name).strip('_.')[:70] or 'Base'
        path = folder / f'{stamp}_{number:03d}_{name}.nmsbase'
        outputs[path] = serialize_json(get_at(save, base.path))
        outputs[_catalog_path(path)] = serialize_json({
            'version': 1,
            'action': action,
            'saved_at': now.isoformat(),
            'source_save': source_save.name,
            'array_path': base.path[:-1],
            'index': base.path[-1],
        })
        paths.append(path)
    write_outputs(outputs)
    for path, expected in outputs.items():
        if path.read_bytes() != expected:
            raise ReplicationError(f'Backup verification failed for {path}.')
    return paths


def _check_output(output: Path, source_save: Path) -> None:
    if output.suffix.casefold() != '.json' or output.resolve() == source_save.resolve():
        raise ReplicationError('Choose a new gamesave JSON output.')
    if output.exists() or not output.parent.is_dir():
        raise ReplicationError(f'The gamesave output path is unavailable: {output}')


def _move_to_exported_bases(entry: StoredBase, exports: Path) -> Path:
    """Copy and verify both files before removing the originals."""
    exports.mkdir(parents=True, exist_ok=True)
    destination = exports / entry.path.name
    source_metadata = _catalog_path(entry.path)
    base_data = entry.path.read_bytes()
    metadata = source_metadata.read_bytes()
    outputs = {destination: base_data, _catalog_path(destination): metadata}
    write_outputs(outputs)
    if any(path.read_bytes() != data for path, data in outputs.items()):
        raise ReplicationError(f'Could not verify the copy in {exports}. The shelf files are still available.')
    source_metadata.unlink()
    try:
        entry.path.unlink()
    except OSError:
        write_outputs({source_metadata: metadata})
        raise
    return destination


def store_bases(save, source_save: Path, selected: list[BaseInfo], action: str,
                folder: Path, output: Path | None = None,
                template: Template | None = None) -> list[Path]:
    """Verify all complete backups before publishing a modified gamesave."""
    available = {base.path for base in archive_candidates(save)}
    paths = {base.path for base in selected}
    if not paths or len(paths) != len(selected) or not paths <= available:
        raise ReplicationError('Select distinct bases from the current gamesave.')
    if action not in {'archive', 'shelve', 'export'}:
        raise ReplicationError('Choose an archive or shelving action.')
    if action != 'export':
        if output is None:
            raise ReplicationError('Choose where to save the modified gamesave.')
        _check_output(output, source_save)
    if action == 'shelve' and template is None:
        raise ReplicationError('Choose a valid placeholder.')

    data = None
    if action != 'export':
        modified = deepcopy(save)
        for path in sorted(paths, key=lambda path: path[-1], reverse=True):
            if action == 'archive':
                del get_at(modified, path[:-1])[path[-1]]
            else:
                get_at(modified, path)['Objects'] = deepcopy(template.record['Objects'])
        data = serialize_json(modified)
    backups = _write_backups(save, selected, folder, action, source_save, datetime.now())
    if data is not None:
        write_outputs({output: data})
    return backups


def _original_location(record):
    position = record.get('Position')
    address = record.get('GalacticAddress')
    if address is None or not _vector(position):
        raise ReplicationError('The stored record has no usable original location.')
    return address, position


def _vector(value):
    return (isinstance(value, list) and len(value) == 3
            and all((type(component) is float and isfinite(component))
                    or (type(component) is int and abs(component) <= 10**308) for component in value))


def _is_planetary(record):
    base_type = record.get('BaseType')
    if isinstance(base_type, dict):
        base_type = base_type.get('PersistentBaseTypes')
    return base_type in (None, 'HomePlanetBase')


def archive_candidates(save) -> list[BaseInfo]:
    return [base for base in find_bases(save) if _is_planetary(get_at(save, base.path))]


def _owner_id(record):
    owner = record.get('Owner')
    if not isinstance(owner, dict):
        return None
    return owner.get('UID') or owner.get('LID') or None


def original_destination(save, entry: StoredBase) -> BaseInfo | None:
    """Find the original site independently of the saved array index."""
    location = _original_location(entry.record)
    rid = entry.record.get('RID')
    owner = _owner_id(entry.record)
    matches = []
    for base in find_bases(save):
        candidate = get_at(save, base.path)
        same_location = (candidate.get('GalacticAddress'), candidate.get('Position')) == location
        same_rid = bool(rid) and candidate.get('RID') == rid
        if not (same_location or same_rid):
            continue
        candidate_owner = _owner_id(candidate)
        if (not same_location or (owner and candidate_owner and owner != candidate_owner)
                or (rid and candidate.get('RID') and not same_rid) or not _is_planetary(candidate)):
            raise ReplicationError('A different base conflicts with the stored base identity or location.')
        matches.append(base)
    if len(matches) > 1:
        raise ReplicationError('The original location matches more than one base.')
    return matches[0] if matches else None


def restore_base(save, source_save: Path, entry: StoredBase, output: Path,
                 shelf_folder: Path, destination: BaseInfo | None = None) -> RestoreResult:
    """Restore at the original site, or shelve an explicit destination before replacing it."""
    _check_output(output, source_save)
    if read_entry(entry.path) != entry:
        raise ReplicationError('The stored base changed. Reopen the catalog and select it again.')
    original = destination is None
    move_to_exports = (original and entry.action in {'shelve', 'displaced', 'restore'}
                       and entry.path.parent.resolve() == shelf_folder.resolve())
    exports = shelf_folder.parent / EXPORTED_BASES
    if original:
        destination = original_destination(save, entry)
    elif destination not in archive_candidates(save):
        raise ReplicationError('Choose a destination base from the current gamesave.')

    if destination is None:
        modified = deepcopy(save)
        try:
            bases = get_at(modified, entry.array_path)
        except (IndexError, KeyError, TypeError) as exc:
            raise ReplicationError('The original base array is missing from this gamesave.') from exc
        if not isinstance(bases, list):
            raise ReplicationError('The original base array is invalid.')
        bases.insert(min(entry.index, len(bases)), deepcopy(entry.record))
    else:
        modified, _, _ = replicate(save, destination.path, entry.record)
    data = serialize_json(modified)
    backups = []
    if destination is not None and (not original
                                    or get_at(save, destination.path)['Objects'] != entry.record['Objects']):
        action = 'restore' if original else 'displaced'
        backups = _write_backups(save, [destination], exports if move_to_exports else shelf_folder, action,
                                 source_save, datetime.now())
    write_outputs({output: data})
    if move_to_exports:
        try:
            if output.read_bytes() != data:
                raise ReplicationError('The new gamesave could not be verified.')
            return RestoreResult(backups, _move_to_exported_bases(entry, exports))
        except (OSError, ValueError) as exc:
            return RestoreResult(backups, move_warning=f'Could not move the shelf entry to {EXPORTED_BASES}. {exc}')
    return RestoreResult(backups)
