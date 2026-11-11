import json
import tempfile
import unittest
from pathlib import Path

from replicator import (OutputExistsError, ReplicationError, find_bases, get_at, parse_nmsbase,
                        replicate, select_base, serialize_json, write_outputs)
from main import main


def base(name, address, parts):
    return {'Name': name, 'GalacticAddress': address, 'Position': [1, 2, 3],
            'Forward': [0, 0, 1], 'Owner': {'UID': 'example'}, 'Objects': parts}


class ReplicatorTests(unittest.TestCase):
    def setUp(self):
        self.save = {'PlayerStateData': {'PersistentPlayerBases': [
            base('Original', '0xAAA', [{'ObjectID': '^BASE_FLAG'}, {'ObjectID': '^WALL', 'Position': [2,3,4]}]),
            base('Destination', '0xBBB', [{'ObjectID': '^BASE_FLAG'}])
        ]}, 'SomeOtherData': {'Objects': ['untouched']}}

    def test_discovery_avoids_unrelated_objects(self):
        self.assertEqual([b.name for b in find_bases(self.save)], ['Original', 'Destination'])

    def test_same_save_replication_changes_only_target_objects(self):
        original = json.loads(json.dumps(self.save))
        entries = find_bases(self.save)
        output, raw_base, report = replicate(self.save, entries[1].path, get_at(self.save, entries[0].path))
        self.assertEqual(self.save, original)
        self.assertEqual(get_at(output, entries[0].path), get_at(original, entries[0].path))
        self.assertEqual(raw_base['GalacticAddress'], '0xBBB')
        self.assertEqual(raw_base['Position'], [1,2,3])
        self.assertEqual(len(raw_base['Objects']), 2)
        self.assertEqual(report, {'source_objects': 2, 'replaced_objects': 1})
        self.assertEqual(output['SomeOtherData'], original['SomeOtherData'])

    def test_duplicate_base_name_must_be_disambiguated(self):
        self.save['PlayerStateData']['PersistentPlayerBases'][1]['Name'] = 'Original'
        with self.assertRaises(ReplicationError):
            select_base(find_bases(self.save), 'Original')
        self.assertEqual(select_base(find_bases(self.save), '2').selector, '1')

    def test_reject_malformed_nmsbase(self):
        with self.assertRaises(ReplicationError):
            parse_nmsbase({'Objects': []})

    def test_cross_save_and_cli_outputs(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            source_path = directory / 'source.json'
            dest_path = directory / 'dest.json'
            source_path.write_bytes(serialize_json(self.save))
            other = {'PlayerStateData': {'PersistentPlayerBases': [base('Landing Site', '0xCCC', [])]}, 'Other': 99}
            dest_path.write_bytes(serialize_json(other))
            prefix = directory / 'replicated'
            rc = main(['replicate', '--source', str(source_path), '--source-base', 'Original',
                       '--destination', str(dest_path), '--destination-base', 'Landing Site',
                       '--output-prefix', str(prefix)])
            self.assertEqual(rc, 0)
            out = json.loads((directory / 'replicated.json').read_text(encoding='utf-8'))
            raw = json.loads((directory / 'replicated.nmsbase').read_text(encoding='utf-8'))
            self.assertEqual(raw, out['PlayerStateData']['PersistentPlayerBases'][0])
            self.assertEqual(out['Other'], 99)
            self.assertEqual(json.loads(dest_path.read_text(encoding='utf-8')), other)
            self.assertEqual(main(['replicate', '--source', str(source_path), '--source-base', 'Original',
                                   '--destination', str(dest_path), '--destination-base', 'Landing Site',
                                   '--output-prefix', str(prefix)]), 2)

    def test_nmsbase_input(self):
        source = base('Imported', '0xAAA', [{'ObjectID': '^FLOOR'}])
        output, newbase, _ = replicate(self.save, find_bases(self.save)[1].path, parse_nmsbase(source))
        self.assertEqual(newbase['Name'], 'Destination')
        self.assertEqual(newbase['GalacticAddress'], '0xBBB')
        self.assertEqual(newbase['Objects'], source['Objects'])

    def test_export_name_can_be_reused_after_both_paths_are_clear(self):
        with tempfile.TemporaryDirectory() as folder:
            json_path = Path(folder) / 'replicated-base.json'
            base_path = json_path.with_suffix('.nmsbase')
            outputs = {json_path: b'save', base_path: b'base'}
            write_outputs(outputs)
            json_path.unlink()
            with self.assertRaises(OutputExistsError) as conflict:
                write_outputs(outputs)
            self.assertEqual(conflict.exception.path, base_path)
            self.assertFalse(json_path.exists())
            self.assertEqual(base_path.read_bytes(), b'base')
            base_path.unlink()
            write_outputs(outputs)
            self.assertEqual(json_path.read_bytes(), b'save')
            self.assertEqual(base_path.read_bytes(), b'base')


if __name__ == '__main__':
    unittest.main()
