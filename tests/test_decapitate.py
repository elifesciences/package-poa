import unittest
from mock import Mock, patch
import configparser as configparser
import packagepoa.decapitate_pdf as decapitate_pdf
import packagepoa.conf as conf


class TestDecapitate(unittest.TestCase):

    def setUp(self):
        pass

    @patch.object(conf, 'config')
    def test_decapitate_pdf_no_executable(self, fake_config):
        "set of tests building csv into xml and compare the output"
        # override the config first
        fake_config = config = configparser.ConfigParser()
        return_value = decapitate_pdf.decapitate_pdf_with_error_check(None, None, None)
        self.assertFalse(return_value)

if __name__ == '__main__':
    unittest.main()
