import unittest
import time
import shutil
import os
import zipfile
from mock import MagicMock, patch
from packagepoa import transform

TEST_BASE_PATH = os.path.dirname(os.path.abspath(__file__)) + os.sep
TEST_DATA_PATH = TEST_BASE_PATH + "test_data" + os.sep
transform.settings.TMP_DIR = TEST_BASE_PATH + transform.settings.TMP_DIR
transform.settings.FTP_DIR = TEST_BASE_PATH + transform.settings.FTP_DIR
transform.settings.DECAPITATE_PDF_DIR = TEST_BASE_PATH + transform.settings.DECAPITATE_PDF_DIR


def mock_decapitate_pdf(filename):
    "copy a file to simulate the PDF decapitation process"
    from_filename = os.path.join(TEST_DATA_PATH, filename)
    to_filename = os.path.join(transform.settings.DECAPITATE_PDF_DIR, filename)
    shutil.copy(from_filename, to_filename)

def list_test_dir(dir_name, ignore=('.keepme')):
    "list the contents of a directory ignoring the ignore files"
    file_names = os.listdir(dir_name)
    return [file_name for file_name in file_names if file_name not in ignore]

def clean_test_dir(dir_name, ignore=('.keepme')):
    "clean files from a test directory ignoring the .keepme file"
    file_names = list_test_dir(dir_name, ignore)
    for file_name in file_names:
        os.remove(os.path.join(dir_name, file_name))

def clean_test_directories(ignore=('.keepme')):
    "clean each of the testing directories"
    dir_names = [transform.settings.TMP_DIR, transform.settings.FTP_DIR,
                 transform.settings.DECAPITATE_PDF_DIR]
    for dir_name in dir_names:
        clean_test_dir(dir_name, ignore)


class TestTransform(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        # clean up the test directories
        clean_test_directories()

    @patch.object(transform, 'decapitate_pdf_with_error_check')
    def test_process_zipfile(self, fake_decapitate):
        fake_decapitate = mock_decapitate_pdf('decap_elife_poa_e12717.pdf')
        zipfile_name = os.path.join(TEST_DATA_PATH,
                                    '18022_1_supp_mat_highwire_zip_268991_x75s4v.zip')
        output_dir = transform.settings.FTP_DIR
        return_value = transform.process_zipfile(zipfile_name, output_dir)
        # check return value
        self.assertTrue(return_value)
        # check directory contents
        self.assertEqual(list_test_dir(transform.settings.TMP_DIR),
                        ['decap_elife_poa_e12717.pdf', 'elife12717_Supplemental_files.zip',
                         'temp_transfer'])
        self.assertEqual(list_test_dir(transform.settings.DECAPITATE_PDF_DIR),
                        ['decap_elife_poa_e12717.pdf'])
        self.assertEqual(list_test_dir(transform.settings.FTP_DIR),
                        ['elife_poa_e12717.pdf', 'elife_poa_e12717_ds.zip'])
        # check the ds zip contents
        zip_file_name = os.path.join(transform.settings.FTP_DIR, 'elife_poa_e12717_ds.zip')
        with zipfile.ZipFile(zip_file_name, 'r') as zip_file:
            self.assertEqual(zip_file.namelist(), ['elife12717_Supplemental_files.zip',
                                                   'manifest.xml'])
        # clean the test directories
        clean_test_directories()


if __name__ == '__main__':
    unittest.main()
