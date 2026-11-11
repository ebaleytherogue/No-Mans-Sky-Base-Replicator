from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from archive import (Template, discover_templates, read_entry, restore_base, scan_catalog,
                     store_bases, timestamped_json)
from replicator import ReplicationError, find_bases, get_at, load_json, serialize_json


def part(object_id):
    return dict(ObjectID=object_id, Position=[0, 0, 0], Up=[0, 1, 0], At=[0, 0, 1])


def record(name, location):
    return dict(Name=name, GalacticAddress=123, Position=[location, 0, 0], Forward=[0, 0, 1],
                Owner={'UID': 'owner'}, RID=f'rid-{location}',
                Objects=[part('^BASE_FLAG'), part(f'^PART{location}')])


class ArchiveTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.source = self.directory / 'original.json'
        self.archive = self.directory / 'Archived_Bases'
        self.shelf = self.directory / 'Shelved_Bases'
        self.save = {'PlayerStateData': {'PersistentPlayerBases': [
            record('Source', 1), record('Destination', 2), record('Third', 3)]},
            'TerrainEditData': {'Example': [1, 2, 3]}}
        self.original_bytes = serialize_json(self.save)
        self.source.write_bytes(self.original_bytes)
        self.bases = find_bases(self.save)

    def tearDown(self):
        self.assertEqual(self.source.read_bytes(), self.original_bytes)

    def test_discovery_uses_live_filenames_and_requires_three_valid_templates(self):
        templates = self.directory / 'Placeholder_Bases'
        templates.mkdir()
        with self.assertRaisesRegex(ReplicationError, 'exactly three'):
            discover_templates(templates)
        for number, name in enumerate(('Test_Alpha', 'Test_Beta', 'Test_Gamma'), 1):
            (templates / f'{number}_{name}.nmsbase').write_bytes(serialize_json(record(name, number)))
        self.assertEqual([item.label for item in discover_templates(templates)],
                         ['Test Alpha', 'Test Beta', 'Test Gamma'])
        changed = (templates / '2_Test_Beta.nmsbase').rename(templates / '2_Renamed.nmsbase')
        self.assertEqual(discover_templates(templates)[1].label, 'Renamed')
        changed.write_bytes(b'{"GalacticAddress": 123, "Objects": []}')
        with self.assertRaisesRegex(ReplicationError, 'Base Computer'):
            discover_templates(templates)

    def test_archive_batch_then_restore_complete_record(self):
        output = timestamped_json(self.directory)
        paths = store_bases(self.save, self.source, [self.bases[0], self.bases[2]],
                            'archive', self.archive, output)
        removed = load_json(output)
        self.assertEqual([base.name for base in find_bases(removed)], ['Destination'])
        catalog, errors = scan_catalog(self.archive, self.shelf)
        self.assertEqual(len(catalog), 2)
        self.assertEqual(errors, [])
        restored = timestamped_json(self.directory)
        result = restore_base(removed, output, read_entry(paths[0]), restored, self.shelf)
        self.assertEqual(result.backups, [])
        self.assertEqual(get_at(load_json(restored), self.bases[0].path), get_at(self.save, self.bases[0].path))
        self.assertEqual(load_json(restored)['TerrainEditData'], self.save['TerrainEditData'])
        self.assertTrue(paths[0].is_file())

    def test_original_restore_moves_shelf_pair_only_after_export(self):
        shelved_path = timestamped_json(self.directory)
        template_record = record('Template test fixture', 9)
        template_record['Objects'].pop()
        template = Template(self.directory / 'unused', 'Test fixture', template_record)
        paths = store_bases(self.save, self.source, [self.bases[0]], 'shelve',
                            self.shelf, shelved_path, template)
        shelved = load_json(shelved_path)
        output = timestamped_json(self.directory)
        entry = read_entry(paths[0])
        with patch('archive.write_outputs', side_effect=OSError('disk write failed')):
            with self.assertRaises(OSError):
                restore_base(shelved, shelved_path, entry, output, self.shelf)
        self.assertTrue(paths[0].is_file())
        self.assertFalse(output.exists())
        result = restore_base(shelved, shelved_path, entry, output, self.shelf)
        self.assertEqual(load_json(output), self.save)
        self.assertEqual(result.moved_to.parent.name, 'Exported_Bases')
        self.assertEqual(read_entry(result.moved_to).record, entry.record)
        self.assertEqual(scan_catalog(self.shelf), ([], []))

    def test_cross_location_shelves_before_writing_and_keeps_archive(self):
        paths = store_bases(self.save, self.source, [self.bases[0]], 'export', self.archive)
        entry = read_entry(paths[0])
        output = timestamped_json(self.directory)
        blocked = self.directory / 'Blocked'
        blocked.write_text('A file occupies the backup directory path.')
        with self.assertRaises(OSError):
            restore_base(self.save, self.source, entry, output, blocked, self.bases[1])
        self.assertFalse(output.exists())
        result = restore_base(self.save, self.source, entry, output, self.shelf, self.bases[1])
        expected = deepcopy(self.save)
        original_destination = get_at(self.save, self.bases[1].path)
        get_at(expected, self.bases[1].path)['Objects'] = entry.record['Objects']
        self.assertEqual(load_json(output), expected)
        self.assertEqual(read_entry(result.backups[0]).record, original_destination)
        self.assertTrue(paths[0].is_file())

    def test_restore_refuses_a_conflicting_base_at_the_original_location(self):
        entry = read_entry(store_bases(self.save, self.source, [self.bases[0]], 'export', self.archive)[0])
        conflicting = deepcopy(self.save)
        get_at(conflicting, self.bases[0].path)['RID'] = 'unrelated'
        output = timestamped_json(self.directory)
        with self.assertRaisesRegex(ReplicationError, 'conflicts'):
            restore_base(conflicting, self.source, entry, output, self.shelf)
        self.assertFalse(output.exists())

    def test_exported_bases_collision_keeps_the_shelf_pair(self):
        shelved_path = timestamped_json(self.directory)
        template = Template(self.directory / 'unused', 'Test fixture', record('Template fixture', 9))
        path = store_bases(self.save, self.source, [self.bases[0]], 'shelve',
                           self.shelf, shelved_path, template)[0]
        entry = read_entry(path)
        exports = self.directory / 'Exported_Bases'
        exports.mkdir()
        collision = exports / path.name
        collision.write_bytes(b'existing export')
        output = timestamped_json(self.directory)
        result = restore_base(load_json(shelved_path), shelved_path, entry, output, self.shelf)
        self.assertIn('Could not move', result.move_warning)
        self.assertEqual(load_json(output), self.save)
        self.assertEqual(read_entry(path), entry)
        self.assertEqual(collision.read_bytes(), b'existing export')
