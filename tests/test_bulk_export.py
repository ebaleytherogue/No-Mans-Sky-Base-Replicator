from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from archive import store_bases
from bulk_export import ALL, MANIFEST, OTHER, OWNED, UNKNOWN, export_bases
from replicator import find_bases, load_json
from wizard import Wizard


STAMP = '2026-11-20_1104'


def record(name, uid='', lid='', kind='', **extra):
    return {'Name': name, 'GalacticAddress': '0x20010900000003', 'Objects': [],
            'Owner': {'UID': uid, 'LID': lid, 'PTK': 'ST'},
            'BaseType': {'PersistentBaseTypes': kind}, **extra}


def gamesave(*records):
    return {'BaseContext': {'PlayerStateData': {'PersistentPlayerBases': list(records)}}}


class BulkExportTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name)
        self.source = self.folder / 'world.json'
        self.owned = record('Home', 'me', 'local-me', 'HomePlanetBase')
        self.other = record('Neighbor', 'them', 'local-them', 'ExternalPlanetBase')
        self.unknown = record('Unnamed owner')
        self.save = gamesave(self.other, self.unknown, self.owned)

    def export(self, mode=ALL, save=None, **kwargs):
        return export_bases(self.save if save is None else save, self.source,
                            self.folder, mode, STAMP, **kwargs)

    def test_all_records_in_order_and_legacy_archive_bytes(self):
        freighter = record('Freighter', 'me', 'local-me', 'FreighterBase')
        del freighter['GalacticAddress']
        self.save['ExpeditionContext'] = gamesave(freighter)['BaseContext']
        result = self.export()
        self.assertEqual([row.name for row in result.rows],
                         ['Neighbor', 'Unnamed owner', 'Home', 'Freighter'])
        self.assertEqual(result.counts, {'Exported': 4})
        folder = result.folders[ALL]
        self.assertEqual(folder.name, f'Exported_Bases_ALL_{STAMP}')
        original = next(base for base in find_bases(self.save) if base.name == 'Home')
        [legacy] = store_bases(self.save, self.source, [original], 'export', self.folder / 'archive')
        self.assertEqual((folder / 'Home.nmsbase').read_bytes(), legacy.read_bytes())
        self.assertEqual(load_json(folder / 'Freighter.nmsbase'), freighter)

    def test_other_and_unknown_routing_is_independent_of_order(self):
        for save in (self.save, gamesave(self.owned, self.unknown, self.other)):
            result = self.export(OTHER, save)
            self.assertEqual({row.name: row.ownership for row in result.rows},
                             {'Home': OWNED, 'Neighbor': OTHER, 'Unnamed owner': UNKNOWN})
            self.assertEqual(result.counts, {'Exported': 2, 'Skipped': 1})
            self.assertEqual(set(result.folders), {OTHER, UNKNOWN})
            self.assertEqual(set(result.folders[OTHER].glob('*.nmsbase')),
                             {result.folders[OTHER] / 'Neighbor.nmsbase'})
            self.assertEqual(set(result.folders[UNKNOWN].glob('*.nmsbase')),
                             {result.folders[UNKNOWN] / 'Unnamed owner.nmsbase'})
            for category, folder in result.folders.items():
                self.assertIn(f'{category}_{STAMP}', folder.name)
                self.assertEqual(folder.parent, self.folder)
                self.assertTrue((folder / MANIFEST).is_file())

    def test_missing_and_conflicting_identity_is_unknown(self):
        inconsistent = record('Mixed', 'me', 'different', 'ExternalPlanetBase')
        guest_home = record('Guest', 'me', 'local-me', 'ExternalPlanetBase')
        result = self.export(OTHER, gamesave(self.owned, inconsistent, guest_home))
        self.assertEqual([row.ownership for row in result.rows], [OWNED, UNKNOWN, UNKNOWN])
        for records in ((self.other,), (self.owned, record('Second home', 'another', '', 'HomePlanetBase'))):
            result = self.export(OTHER, gamesave(*records))
            self.assertTrue(all(row.ownership == UNKNOWN for row in result.rows))

    def test_collision_safe_names_and_windows_sanitization(self):
        existing = self.folder / 'My exports'
        existing.mkdir()
        (existing / 'Base.nmsbase').write_bytes(b'keep')
        save = gamesave(*(record(name) for name in ('Base', 'base', 'Base', 'A/B:*?', 'NUL.txt', '...')))
        result = self.export(save=save, folder_name=existing.name)
        self.assertEqual(result.folders[ALL].name, 'My exports_2')
        self.assertEqual([row.filename for row in result.rows],
                         ['Base.nmsbase', 'base_2.nmsbase', 'Base_3.nmsbase',
                          'A_B___.nmsbase', '_NUL.txt.nmsbase', 'Base_4.nmsbase'])
        self.assertEqual((existing / 'Base.nmsbase').read_bytes(), b'keep')

    def test_empty_categories_leave_no_directories(self):
        self.assertEqual(self.export(save=gamesave()).folders, {})
        self.assertEqual(self.export(OTHER, gamesave(self.owned)).folders, {})
        self.assertEqual(list(self.folder.iterdir()), [])
        self.assertEqual(set(self.export(OTHER, gamesave(self.owned, self.other)).folders), {OTHER})

    def test_manifest_records_success_skip_failure_and_escaped_metadata(self):
        bad = record('Bad|base\nname', 'them', 'local-them', Objects=[float('nan')])
        result = self.export(OTHER, gamesave(self.owned, bad, self.other))
        self.assertEqual(result.counts, {'Skipped': 1, 'Failed': 1, 'Exported': 1})
        [manifest] = result.manifests
        content = manifest.read_text(encoding='utf-8')
        for expected in (STAMP, self.source.name, 'Bases considered: 3', 'Exported: 1', 'Skipped: 1',
                         'Failed: 1', r'Bad\|base name', 'Neighbor.nmsbase', 'RealityIndex 9',
                         'UID=them', 'Owned by the current player.', 'Out of range float'):
            self.assertIn(expected, content)

    def test_wizard_cancel_parent_and_folder_name(self):
        wizard = SimpleNamespace(root=Mock(), last_load_directory=self.folder)
        for parent in ('', str(self.folder)):
            with (patch('wizard.filedialog.askdirectory', return_value=parent) as browser,
                  patch('wizard.simpledialog.askstring', return_value=None),
                  patch('wizard.export_bases') as export):
                Wizard.run_bulk_export(wizard, self.save, self.source, ALL, Mock())
            self.assertEqual(browser.call_args.kwargs['initialdir'], str(self.folder))
            export.assert_not_called()
            self.assertEqual(list(self.folder.iterdir()), [])

    def test_nmsbase_selection_sets_shared_destination_start(self):
        wizard = SimpleNamespace(root=Mock(), body=Mock(), browsed_paths={}, last_load_directory=None)
        file = self.folder / 'template.nmsbase'
        variable = Mock()
        with (patch('wizard.ttk.Label'), patch('wizard.ttk.Frame'), patch('wizard.ttk.Entry'),
              patch('wizard.ttk.Button') as button,
              patch('wizard.filedialog.askopenfilename', return_value=str(file))):
            Wizard.file_row(wizard, 'Source base export', variable, '.nmsbase')
            button.call_args.kwargs['command']()
        variable.set.assert_called_once_with(str(file))
        self.assertEqual(wizard.last_load_directory, self.folder)
        with patch('wizard.filedialog.askdirectory', return_value='') as browser:
            Wizard.run_bulk_export(wizard, self.save, self.source, OTHER, Mock())
        self.assertEqual(browser.call_args.kwargs['initialdir'], str(self.folder))

    def test_wizard_exports_loaded_save_even_with_filtered_selection(self):
        wizard = SimpleNamespace(root=Mock(), last_load_directory=self.folder / 'missing',
                                 body=Mock(), page=Mock(), navigation=Mock(), restart=Mock(),
                                 bases=[self.owned], selected={0})
        with (patch('wizard.filedialog.askdirectory', return_value=str(self.folder)) as browser,
              patch('wizard.simpledialog.askstring', return_value='Filtered test'),
              patch('wizard.ttk.Label')):
            Wizard.run_bulk_export(wizard, self.save, self.source, ALL, Mock())
        self.assertEqual(browser.call_args.kwargs['initialdir'], str(self.folder))
        self.assertEqual(len(list((self.folder / 'Filtered test').glob('*.nmsbase'))), 3)
