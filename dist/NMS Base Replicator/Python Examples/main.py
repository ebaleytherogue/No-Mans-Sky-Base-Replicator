"""NMS Base Replicator CLI — no additional Python packages required."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from replicator import (ReplicationError, find_bases, get_at, load_json,
                        parse_nmsbase, replicate, select_base, serialize_json, write_outputs)


def print_bases(bases) -> None:
    for i, base in enumerate(bases, 1):
        print(f'{i:>3}. {base.name} | {base.count} objects | address {base.address}')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Replicate planetary base geometry into an existing destination base.')
    sub = parser.add_subparsers(dest='command', required=True)
    listing = sub.add_parser('list', help='List bases in a JSON gamesave')
    listing.add_argument('save', type=Path)
    cmd = sub.add_parser('replicate', help='Create new .json and .nmsbase outputs')
    cmd.add_argument('--source', required=True, type=Path, help='Source .json gamesave or raw .nmsbase')
    cmd.add_argument('--source-base', help='Source base name or list number (not needed for .nmsbase)')
    cmd.add_argument('--destination', required=True, type=Path, help='Destination JSON gamesave')
    cmd.add_argument('--destination-base', required=True, help='Destination base name or list number')
    cmd.add_argument('--output-prefix', required=True, type=Path, help='Prefix for NEW output files')
    args = parser.parse_args(argv)
    try:
        if args.command == 'list':
            bases = find_bases(load_json(args.save))
            if not bases:
                raise ReplicationError('No recognized planetary bases found')
            print_bases(bases)
            return 0

        source = load_json(args.source)
        destination = load_json(args.destination)
        destination_bases = find_bases(destination)
        if not destination_bases:
            raise ReplicationError('No destination planetary bases found')
        dest_info = select_base(destination_bases, args.destination_base)
        if args.source.suffix.lower() == '.nmsbase':
            if args.source_base is not None:
                raise ReplicationError('--source-base must be omitted for .nmsbase input')
            source_base = parse_nmsbase(source)
            source_name = source_base.get('Name', '(unnamed)')
        else:
            source_bases = find_bases(source)
            if not args.source_base:
                raise ReplicationError('--source-base is required for a JSON gamesave source')
            source_info = select_base(source_bases, args.source_base)
            if args.source.resolve() == args.destination.resolve() and source_info.path == dest_info.path:
                raise ReplicationError('Source and destination must be different base records')
            source_base = get_at(source, source_info.path)
            source_name = source_info.name
        output, base_file, report = replicate(destination, dest_info.path, source_base)
        json_path = Path(str(args.output_prefix) + '.json')
        nmsbase_path = Path(str(args.output_prefix) + '.nmsbase')
        # Refuse to overwrite either of the input paths regardless of suffix.
        input_paths = {args.source.resolve(), args.destination.resolve()}
        if json_path.resolve() in input_paths or nmsbase_path.resolve() in input_paths:
            raise ReplicationError('Output path must not match an input path')
        write_outputs({json_path: serialize_json(output), nmsbase_path: serialize_json(base_file)})
        print(f'Replicated {source_name!r} → {dest_info.name!r}')
        print(f"Source objects: {report['source_objects']}; destination objects replaced: {report['replaced_objects']}")
        print('Verified: destination metadata and all other destination save data unchanged (JSON values).')
        print(f'Created: {json_path}\nCreated: {nmsbase_path}')
        print('CAUTION: .nmsbase NMSE import compatibility has not yet been tested against actual NMSE.')
        print('Before importing: exit NMS and Steam; back up your saves. Use NMSE Import, NOT Import as New.')
        return 0
    except (ReplicationError, OSError, ValueError, TypeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
