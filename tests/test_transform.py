import unittest
import time
import shutil
import os
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


class TestTransform(unittest.TestCase):

    def setUp(self):
        pass

    @patch.object(transform, 'decapitate_pdf_with_error_check')
    def test_process_zipfile(self, fake_decapitate):
        fake_decapitate = mock_decapitate_pdf('decap_elife_poa_e12717.pdf')
        zipfile_name = os.path.join(TEST_DATA_PATH,
                                    '18022_1_supp_mat_highwire_zip_268991_x75s4v.zip')
        output_dir = transform.settings.TMP_DIR
        return_value = transform.process_zipfile(zipfile_name, output_dir)
        self.assertTrue(return_value)


if __name__ == '__main__':
    unittest.main()
