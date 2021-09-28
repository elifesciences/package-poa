import unittest
import shutil
import os
import zipfile
from mock import patch
from func_timeout import FunctionTimedOut
from packagepoa import transform
from packagepoa.conf import raw_config, parse_raw_config

POA_CONFIG = parse_raw_config(raw_config("elife"))
TEST_BASE_PATH = os.path.dirname(os.path.abspath(__file__)) + os.sep
TEST_DATA_PATH = TEST_BASE_PATH + "test_data" + os.sep
POA_CONFIG["tmp_dir"] = TEST_BASE_PATH + POA_CONFIG["tmp_dir"]
POA_CONFIG["output_dir"] = TEST_BASE_PATH + POA_CONFIG["output_dir"]
POA_CONFIG["decapitate_pdf_dir"] = TEST_BASE_PATH + POA_CONFIG["decapitate_pdf_dir"]


def mock_decapitate_pdf(filename):
    "copy a file to simulate the PDF decapitation process"
    from_filename = os.path.join(TEST_DATA_PATH, filename)
    to_filename = os.path.join(POA_CONFIG.get("decapitate_pdf_dir"), filename)
    shutil.copy(from_filename, to_filename)


def list_test_dir(dir_name, ignore=(".keepme")):
    "list the contents of a directory ignoring the ignore files"
    file_names = os.listdir(dir_name)
    return [file_name for file_name in file_names if file_name not in ignore]


def clean_test_dir(dir_name, ignore=(".keepme")):
    "clean files from a test directory ignoring the .keepme file"
    file_names = list_test_dir(dir_name, ignore)
    for file_name in file_names:
        os.remove(os.path.join(dir_name, file_name))


def clean_test_directories(ignore=(".keepme")):
    "clean each of the testing directories"
    dir_names = [
        POA_CONFIG.get("tmp_dir"),
        POA_CONFIG.get("output_dir"),
        POA_CONFIG.get("decapitate_pdf_dir"),
    ]
    for dir_name in dir_names:
        clean_test_dir(dir_name, ignore)


class TestTransform(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        # clean up the test directories
        clean_test_directories()

    @patch.object(transform, "decapitate_pdf_with_error_check")
    def test_process_zipfile(self, fake_decapitate):
        mock_decapitate_pdf("decap_elife_poa_e12717.pdf")
        fake_decapitate.return_value = True
        zipfile_name = os.path.join(
            TEST_DATA_PATH, "18022_1_supp_mat_highwire_zip_268991_x75s4v.zip"
        )
        # pass in the POA_CONFIG which has the testing directories modified
        return_value = transform.process_zipfile(zipfile_name, POA_CONFIG)
        # check return value
        self.assertTrue(return_value)
        # check directory contents
        self.assertEqual(
            sorted(list_test_dir(POA_CONFIG.get("tmp_dir"))),
            ["decap_elife_poa_e12717.pdf", "temp_transfer"],
        )
        self.assertEqual(
            sorted(list_test_dir(POA_CONFIG.get("decapitate_pdf_dir"))),
            ["decap_elife_poa_e12717.pdf"],
        )
        self.assertEqual(
            sorted(list_test_dir(POA_CONFIG.get("output_dir"))),
            ["elife_poa_e12717.pdf", "elife_poa_e12717_ds.zip"],
        )
        # check the ds zip contents
        zip_file_name = os.path.join(
            POA_CONFIG.get("output_dir"), "elife_poa_e12717_ds.zip"
        )
        with zipfile.ZipFile(zip_file_name, "r") as zip_file:
            self.assertEqual(
                sorted(zip_file.namelist()),
                [
                    "elife_poa_e12717_Figure_1_figure_supplement_1.pdf",
                    "elife_poa_e12717_Figure_2_figure_supplement_1.pdf",
                    "elife_poa_e12717_Figure_2_figure_supplement_2.pdf",
                    "elife_poa_e12717_Figure_3_figure_supplement_1.pdf",
                    "elife_poa_e12717_Figure_3_figure_supplement_2.pdf",
                    "elife_poa_e12717_Figure_3_figure_supplement_3.pdf",
                    "elife_poa_e12717_Figure_4_figure_supplement_1.pdf",
                    "elife_poa_e12717_Figure_4_figure_supplement_2.pdf",
                    "elife_poa_e12717_Figure_6_figure_supplement_1.pdf",
                    "elife_poa_e12717_Figure_6_figure_supplement_2.pdf",
                    "elife_poa_e12717_Figure_7_figure_supplement_1.pdf",
                    "elife_poa_e12717_Figure_8_figure_supplement_1.pdf",
                    "elife_poa_e12717_Supplementary_File_1.xls",
                    "elife_poa_e12717_Supplementary_File_2.xlsx",
                    "elife_poa_e12717_Supplementary_File_3.xls",
                    "elife_poa_e12717_Video_1.mov",
                    "elife_poa_e12717_Video_10.mov",
                    "elife_poa_e12717_Video_11.mov",
                    "elife_poa_e12717_Video_12.mov",
                    "elife_poa_e12717_Video_2.mov",
                    "elife_poa_e12717_Video_3.mov",
                    "elife_poa_e12717_Video_4.mov",
                    "elife_poa_e12717_Video_5.mov",
                    "elife_poa_e12717_Video_6.mov",
                    "elife_poa_e12717_Video_7.mov",
                    "elife_poa_e12717_Video_8.mov",
                    "elife_poa_e12717_Video_9.mov",
                ],
            )

    @patch.object(transform, "decapitate_pdf_with_error_check")
    def test_process_zipfile_failed_pdf(self, fake_decapitate):
        "tests of when pdf decapitaion fails, for test coverage"
        # first example is pdf decapitator returns False due to an error
        fake_decapitate.return_value = False
        zipfile_name = os.path.join(
            TEST_DATA_PATH, "18022_1_supp_mat_highwire_zip_268991_x75s4v.zip"
        )
        return_value = transform.process_zipfile(zipfile_name, None)
        # for now it still returns True
        self.assertTrue(return_value)
        # second example returns True but the pdf file is not found in the expected folder
        fake_decapitate.return_value = True
        zipfile_name = os.path.join(
            TEST_DATA_PATH, "18022_1_supp_mat_highwire_zip_268991_x75s4v.zip"
        )
        return_value = transform.process_zipfile(zipfile_name, None)
        # for now it still returns True
        self.assertTrue(return_value)

    @patch.object(transform, "decapitate_pdf_with_error_check")
    def test_copy_pdf_to_output_dir_timed_out_pdf(self, fake_decapitate):
        "tests of when pdf decapitaion reaches timeout"
        zipfile_name = os.path.join(
            TEST_DATA_PATH, "18022_1_supp_mat_highwire_zip_268991_x75s4v.zip"
        )
        file_title_map = {"18022_1_merged_1463214271.pdf": "Merged PDF"}
        fake_decapitate.side_effect = FunctionTimedOut
        doi = "10.7554/eLife.12717"
        with zipfile.ZipFile(zipfile_name, "r") as current_zipfile:
            with self.assertRaises(Exception):
                transform.copy_pdf_to_output_dir(
                    file_title_map, None, doi, current_zipfile, POA_CONFIG
                )

    def test_add_file_to_zipfile(self):
        "test adding files to a zip file"
        zip_file_name = os.path.join(POA_CONFIG.get("tmp_dir"), "test.zip")
        file_name = os.path.join(POA_CONFIG.get("tmp_dir"), ".keepme")
        # try to add a file not specifying a new name
        with zipfile.ZipFile(zip_file_name, "w") as zip_file:
            transform.add_file_to_zipfile(zip_file, file_name, None)
            self.assertEqual(zip_file.namelist(), [])
