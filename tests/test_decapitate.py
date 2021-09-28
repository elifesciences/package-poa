import unittest
from packagepoa import decapitate_pdf


class TestDecapitate(unittest.TestCase):
    def setUp(self):
        pass

    def test_decapitate_pdf_no_executable(self):
        "set of tests building csv into xml and compare the output"
        # override the config first
        poa_config = None
        return_value = decapitate_pdf.decapitate_pdf_with_error_check(
            None, None, poa_config
        )
        self.assertFalse(return_value)
