"""Export raw gamesave base records and report the outcome of each export."""
from collections import Counter
from dataclasses import dataclass
from itertools import count
from pathlib import Path
import re

from replicator import OutputExistsError, ReplicationError, iter_base_records, serialize_json, write_outputs


ALL = 'ALL'
OWNED = 'OWNED'
OTHER = 'OTHER_PLAYERS'
UNKNOWN = 'OWNERSHIP_UNKNOWN'
MANIFEST = 'Export_Manifest.md'
LOCAL_TYPES = {'HomePlanetBase', 'FreighterBase'}
INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f\ud800-\udfff]')
DEVICE_NAME = re.compile(r'(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[0-9¹²³])', re.I)


@dataclass(frozen=True)
class ExportRow:
    name: str
    galaxy: str
    ownership: str
    owner: str
    status: str
    filename: str = ''
    detail: str = ''
    category: str = ''


@dataclass
class ExportResult:
    rows: list[ExportRow]
    folders: dict[str, Path]
    manifests: list[Path]
    manifest_errors: list[str]

    @property
    def counts(self):
        return Counter(row.status for row in self.rows)


def fields(value):
    return value if isinstance(value, dict) else {}


def owner_fields(record):
    owner = fields(record.get('Owner'))
    return {key: owner[key].strip() for key in ('UID', 'LID', 'PTK', 'USN')
            if isinstance(owner.get(key), str) and owner[key].strip()}


def identity_fields(owner):
    return {key: owner[key] for key in ('UID', 'LID', 'PTK')
            if owner.get(key) and owner[key] not in {'0', '-1'}}


def base_type(record):
    value = fields(record.get('BaseType')).get('PersistentBaseTypes')
    return value if isinstance(value, str) else ''


def current_player(records):
    # Home/freighter types identify the save's local records. Require consensus
    # across those records so conflicting IDs or platforms never elect an owner.
    values = {}
    profiles = []
    for record in records:
        if base_type(record) not in LOCAL_TYPES:
            continue
        owner = identity_fields(owner_fields(record))
        if not {'UID', 'LID'}.intersection(owner):
            continue
        profiles.append(owner)
        for key, value in owner.items():
            if key in values and values[key] != value:
                return {}
            values[key] = value
    if 'UID' in values and 'LID' in values and not any(
            'UID' in owner and 'LID' in owner for owner in profiles):
        return {}
    return values


def classify(record, owner, player):
    identity = identity_fields(owner)
    comparisons = [identity[key] == player[key] for key in ('UID', 'LID')
                   if key in identity and key in player]
    if not comparisons:
        return UNKNOWN, 'No comparable current-player and base owner IDs.'
    own_type = base_type(record)
    platform_differs = ('PTK' in identity and 'PTK' in player and identity['PTK'] != player['PTK'])
    if all(comparisons) and not platform_differs and own_type != 'ExternalPlanetBase':
        return OWNED, ''
    if not any(comparisons) and own_type not in LOCAL_TYPES:
        if not platform_differs or own_type == 'ExternalPlanetBase':
            return OTHER, ''
    return UNKNOWN, 'Owner IDs, platform, or base type give conflicting or ambiguous evidence.'


def galaxy(record):
    address = record.get('GalacticAddress')
    index = record.get('RealityIndex', fields(address).get('RealityIndex'))
    if type(index) is int and 0 <= index <= 255:
        return f'RealityIndex {index}'
    if isinstance(address, str) and re.fullmatch(r'0[xX][0-9a-fA-F]{1,14}', address):
        address = int(address, 16)
    elif isinstance(address, str) and re.fullmatch(r'[0-9]{1,17}', address):
        address = int(address)
    if type(address) is int and 0 <= address < 1 << 56:
        # In a packed universal address, bits 32 through 39 store RealityIndex.
        return f'RealityIndex {(address >> 32) & 0xff}'
    return 'Unavailable'


def default_folder(category, timestamp):
    return f'Exported_Bases_{category}_{timestamp}'


def reserved(name):
    return DEVICE_NAME.fullmatch(name.split('.')[0].rstrip(' ')) is not None


def validate_folder_name(name):
    if (not name or name.endswith((' ', '.')) or INVALID_FILENAME.search(name)
            or reserved(name) or len(name.encode('utf-16-le')) > 480):
        raise ReplicationError('Enter a valid Windows folder name of up to 240 UTF-16 characters.')


def candidates(stem, extension=''):
    yield f'{stem}{extension}'
    for number in count(2):
        yield f'{stem}_{number}{extension}'


def new_folder(parent, name):
    for candidate in candidates(name):
        path = parent / candidate
        try:
            path.mkdir()
        except FileExistsError:
            continue
        return path


def write_base(folder, name, record, occupied):
    stem = INVALID_FILENAME.sub('_', name).strip(' .')[:100].rstrip(' .') or 'Base'
    if reserved(stem):
        stem = '_' + stem
    data = serialize_json(record)
    for candidate in candidates(stem, '.nmsbase'):
        key = candidate.casefold()
        if key in occupied:
            continue
        try:
            write_outputs({folder / candidate: data})
        except OutputExistsError:
            occupied.add(key)
            continue
        occupied.add(key)
        return candidate


def cell(value):
    # Escape table separators and Markdown/HTML punctuation in user-entered text.
    return re.sub(r'([\\|<>*_~\x60\[\]&])', r'\\\1', ' '.join(value.splitlines()))


def manifest_text(rows, category, timestamp, source):
    lines = ['# Export Manifest', '', f'- Export timestamp: {timestamp}',
             f'- Export type: {category}', f'- Source gamesave: {cell(source.name) if source else "Unavailable"}',
             f'- Bases considered: {len(rows)}']
    counts = Counter(row.status if row.category == category else 'Skipped' for row in rows)
    lines.extend(f'- {status}: {counts[status]}' for status in ('Exported', 'Skipped', 'Failed'))
    lines.extend(['', '| Base | Exported filename | Galaxy | Ownership | Owner identification | Status | Details |',
                  '| --- | --- | --- | --- | --- | --- | --- |'])
    for row in rows:
        status, filename, detail = row.status, row.filename, row.detail
        if row.category and row.category != category:
            status, filename = 'Skipped', ''
            detail = f'Assigned to {row.category}. {detail}'.strip()
        values = (row.name or 'Unavailable', filename or '—', row.galaxy,
                  row.ownership, row.owner, status, detail or '—')
        lines.append('| ' + ' | '.join(map(cell, values)) + ' |')
    return '\n'.join(lines) + '\n'


def export_bases(save, source, parent, mode, timestamp, folder_name=None, progress=None):
    """Process every canonical base-list entry in gamesave order."""
    if mode not in (ALL, OTHER):
        raise ReplicationError(f'Unsupported bulk export mode: {mode}')
    if mode == ALL and folder_name is not None:
        validate_folder_name(folder_name)
    records = [value for _, value in iter_base_records(save)]
    player = current_player(fields(value) for value in records)
    result = ExportResult([], {}, [], [])
    occupied = {}
    folder_errors = {}
    for index, value in enumerate(records, 1):
        record = fields(value)
        name = record.get('Name')
        name = name if isinstance(name, str) else ''
        owner = owner_fields(record)
        ownership, detail = classify(record, owner, player)
        category = ALL if mode == ALL else (ownership if ownership != OWNED else '')
        filename = ''
        status = 'Skipped'
        if progress:
            progress(index, len(records))
        if category:
            try:
                if category in folder_errors:
                    raise ReplicationError(folder_errors[category])
                if category not in result.folders:
                    try:
                        proposed = folder_name if category == ALL and folder_name is not None else default_folder(
                            category, timestamp)
                        result.folders[category] = new_folder(parent, proposed)
                    except OSError as exc:
                        folder_errors[category] = str(exc)
                        raise
                    occupied[category] = set()
                if not isinstance(record.get('Objects'), list):
                    raise ReplicationError('Base record is missing an Objects array.')
                filename = write_base(result.folders[category], name, record, occupied[category])
                status = 'Exported'
            except (OSError, ValueError, TypeError, RecursionError) as exc:
                status = 'Failed'
                detail = f'{detail} {exc}'.strip()
        else:
            detail = 'Owned by the current player.'
        identification = ', '.join(f'{key}={value}' for key, value in owner.items()) or 'Unavailable'
        result.rows.append(ExportRow(name, galaxy(record), ownership, identification,
                                     status, filename, detail, category))
    for category, folder in result.folders.items():
        path = folder / MANIFEST
        try:
            data = manifest_text(result.rows, category, timestamp, source).encode('utf-8', errors='replace')
            write_outputs({path: data})
        except (OSError, ValueError) as exc:
            result.manifest_errors.append(f'{path} — {exc}')
        else:
            result.manifests.append(path)
    return result
