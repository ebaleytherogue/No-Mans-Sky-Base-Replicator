"""Core functions for geometry-only NMS base replication.

Inputs are decoded JSON saves or NMSE raw .nmsbase objects. Only the
selected destination base's Objects list is modified.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator
import json


class ReplicationError(ValueError):
    """An input or selection is unsafe or unsupported."""


@dataclass(frozen=True)
class BaseInfo:
    path: tuple[str | int, ...]
    name: str
    count: int
    address: str

    @property
    def selector(self) -> str:
        return str(self.path[-1])


def load_json(path: Path) -> Any:
    try:
        with path.open('r', encoding='utf-8-sig') as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReplicationError(f'Cannot read JSON from {path}: {exc}') from exc


def _walk(value: Any, path: tuple[str | int, ...] = ()) -> Iterator[tuple[tuple[str | int, ...], Any]]:
    if isinstance(value, dict):
        yield path, value
        for key, child in value.items():
            yield from _walk(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _walk(child, path + (index,))


def find_bases(save: Any) -> list[BaseInfo]:
    """Find planetary base records inside canonical PersistentPlayerBases arrays.

    This intentionally excludes unrelated Objects arrays and freighter bases.
    """
    found: list[BaseInfo] = []
    for path, node in _walk(save):
        if not isinstance(node, dict):
            continue
        bases = node.get('PersistentPlayerBases')
        if not isinstance(bases, list):
            continue
        for idx, base in enumerate(bases):
            if not isinstance(base, dict) or not isinstance(base.get('Objects'), list):
                continue
            # Only conventional planetary records have a galactic address.
            if 'GalacticAddress' not in base:
                continue
            name = str(base.get('Name') or f'(unnamed #{idx})')
            found.append(BaseInfo(path + ('PersistentPlayerBases', idx), name,
                                  len(base['Objects']), str(base.get('GalacticAddress', ''))))
    return found


def parse_nmsbase(file_data: Any) -> dict[str, Any]:
    """Accept NMSE raw base JSON object, not a complete save or objects-only list."""
    if not isinstance(file_data, dict) or not isinstance(file_data.get('Objects'), list):
        raise ReplicationError('.nmsbase must contain a raw JSON base record with an Objects array')
    if 'GalacticAddress' not in file_data:
        raise ReplicationError('.nmsbase is missing GalacticAddress; cannot verify base type')
    return file_data


def get_at(data: Any, path: tuple[str | int, ...]) -> Any:
    for key in path:
        data = data[key]
    return data


def select_base(bases: list[BaseInfo], selector: str) -> BaseInfo:
    """Choose by numbered list position (1-based) or exact unique name."""
    if selector.isdecimal():
        index = int(selector) - 1
        if 0 <= index < len(bases):
            return bases[index]
        raise ReplicationError(f'Base number {selector} is out of range (1–{len(bases)})')
    matches = [b for b in bases if b.name == selector]
    if len(matches) != 1:
        raise ReplicationError(f'Expected one base named {selector!r}, found {len(matches)}. Use its list number.')
    return matches[0]


def replicate(destination_save: Any, destination_path: tuple[str | int, ...],
              source_base: dict[str, Any]) -> tuple[Any, dict[str, Any], dict[str, int]]:
    """Return (modified save, replacement raw base, report). Never mutate inputs."""
    source_base = parse_nmsbase(source_base)
    target = get_at(destination_save, destination_path)
    if not isinstance(target, dict) or not isinstance(target.get('Objects'), list):
        raise ReplicationError('Destination must be an existing base with an Objects array')
    if 'GalacticAddress' not in target:
        raise ReplicationError('Destination is not a recognized planetary base')
    original_count = len(target['Objects'])
    output = deepcopy(destination_save)
    copied = deepcopy(source_base['Objects'])
    get_at(output, destination_path)['Objects'] = copied
    generated_base = deepcopy(get_at(output, destination_path))

    # Assert that only the selected destination Objects array differs.
    comparison = deepcopy(output)
    get_at(comparison, destination_path)['Objects'] = deepcopy(target['Objects'])
    if comparison != destination_save:
        raise ReplicationError('Verification failure: data outside destination Objects changed')
    if get_at(output, destination_path)['Objects'] != source_base['Objects']:
        raise ReplicationError('Verification failure: source geometry not copied exactly')
    metadata_check = deepcopy(generated_base)
    metadata_check['Objects'] = deepcopy(target['Objects'])
    if metadata_check != target:
        raise ReplicationError('Verification failure: destination base metadata changed')
    return output, generated_base, {'source_objects': len(copied), 'replaced_objects': original_count}


def serialize_json(data: Any) -> bytes:
    # Avoid ASCII escaping of names and preserve object order. Semantic preservation,
    # not original whitespace / serialization, is what the verification guarantees.
    return (json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def write_outputs(outputs: dict[Path, bytes]) -> None:
    """Write only new files, refusing existing paths and cleaning up on failure."""
    targets = list(outputs)
    if len(set(p.resolve() for p in targets)) != len(targets):
        raise ReplicationError('Output paths must be distinct')
    for path in targets:
        if path.exists():
            raise ReplicationError(f'Refusing to overwrite existing file: {path}')
        if not path.parent.is_dir():
            raise ReplicationError(f'Output folder does not exist: {path.parent}')
    created: list[Path] = []
    try:
        for path, data in outputs.items():
            with path.open('xb') as handle:
                created.append(path)
                handle.write(data)
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
