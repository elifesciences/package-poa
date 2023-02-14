import unittest
import os
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

    def test_decapitate_pdf(self):
        "mock the process to test logging"
        poa_config = {"strip_coverletter_executable": "tests/test.sh"}
        pdf_in = os.path.join("test_data", "decap_elife_poa_212717.pdf")
        pdf_out_dir = "tmp"
        return_value = decapitate_pdf.decapitate_pdf_with_error_check(
            pdf_in, pdf_out_dir, poa_config
        )
        self.assertEqual(return_value, True)
