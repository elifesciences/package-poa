"""
open the zip file from EJP,
get the manifest.xml file
move the pdf
rename and move supp files to a new zipfile
find the pdf file and decapitate the cover page from it
move the PDF to the output directory
move the new zip file to the output directory
"""

import zipfile
import logging
import shutil
import os
from xml.etree import ElementTree
from func_timeout import func_timeout, FunctionTimedOut
from packagepoa.decapitate_pdf import decapitate_pdf_with_error_check
from packagepoa.conf import raw_config, parse_raw_config

# local logger
LOGGER = logging.getLogger("transform")
HDLR = logging.FileHandler("transform.log")
FORMATTER = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
HDLR.setFormatter(FORMATTER)
LOGGER.addHandler(HDLR)
LOGGER.setLevel(logging.INFO)

# global logger
MANIFEST_LOGGER = logging.getLogger("manifest")
MANIFEST_HDLR = logging.FileHandler("manifest.log")
MANIFEST_HDLR.setFormatter(FORMATTER)
MANIFEST_LOGGER.addHandler(MANIFEST_HDLR)
MANIFEST_LOGGER.setLevel(logging.INFO)
PDF_DECAPITATE_TIMEOUT = 120


def article_id_from_doi(doi):
    article_id = doi.split(".")[-1]
    return article_id


def gen_new_name_for_file(name, title, doi, filename_pattern):
    """
    take the following:
    and generates a file name like:
    """
    file_ext = name.split(".")[1]
    article_id = article_id_from_doi(doi)
    new_name_front = title.replace(" ", "_")
    new_name_front = new_name_front.replace("-", "_")
    new_name_front = new_name_front.replace("__", "_")
    new_name_front = new_name_front.replace("__", "_")
    if new_name_front == "Merged_PDF":
        # we ignore the main file name and just use our base POA convention
        new_name = filename_pattern.format(
            article_id=article_id, extra="", file_ext=file_ext
        )
    else:
        new_name = filename_pattern.format(
            article_id=article_id, extra="_" + new_name_front, file_ext=file_ext
        )
    return new_name


def get_doi_from_zipfile(ejp_input_zipfile):
    # print ejp_input_zipfile.namelist()
    manifest = ejp_input_zipfile.read("manifest.xml")
    tree = ElementTree.fromstring(manifest)
    doi = None
    for child in tree:
        if child.tag == "resource":
            if child.attrib["type"] == "doi":
                doi = child.text
    return doi


def get_filename_new_title_map(ejp_input_zipfile):
    MANIFEST_LOGGER.info("unpacking and renaming %s", ejp_input_zipfile.filename)
    file_title_map = {}
    manifest = ejp_input_zipfile.read("manifest.xml")
    tree = ElementTree.fromstring(manifest)
    for child in tree:
        if child.tag == "file":
            for file_tag in child:
                if file_tag.tag == "filename":
                    filename = file_tag.text
                if file_tag.tag == "title":
                    title = file_tag.text
            file_title_map[filename] = title
    MANIFEST_LOGGER.info("file_title_map: %s", file_title_map)
    return file_title_map


def get_new_zipfile_name(doi, filename_pattern):
    article_id = article_id_from_doi(doi)
    new_zipfile_name = None
    if filename_pattern:
        new_zipfile_name = filename_pattern.format(article_id=article_id)
    return new_zipfile_name


def gen_new_zipfile(doi, poa_config):
    filename_pattern = poa_config.get("zipfile_pattern")
    new_zipfile_name = get_new_zipfile_name(doi, filename_pattern)
    new_zipfile_name_plus_path = poa_config.get("tmp_dir") + "/" + new_zipfile_name
    return new_zipfile_name_plus_path


def move_files_into_new_zipfile(
    current_zipfile, file_title_map, new_zipfile, doi, poa_config
):
    filename_pattern = poa_config.get("filename_pattern")
    for name in file_title_map:
        title = file_title_map[name]
        new_name = gen_new_name_for_file(name, title, doi, filename_pattern)

        file_from_zip = current_zipfile.read(name)
        temp_file_name = poa_config.get("tmp_dir") + "/" + "temp_transfer"
        with open(temp_file_name, "wb") as file_p:
            file_p.write(file_from_zip)
        add_file_to_zipfile(new_zipfile, temp_file_name, new_name)


def add_file_to_zipfile(new_zipfile, name, new_name):
    """
    Simple add a file to a zip file
    """
    if not new_zipfile or not name or not new_name:
        return
    new_zipfile.write(name, new_name)


def extract_pdf_from_zip(name, current_zipfile, decap_name, poa_config):
    # we extract the pdf from the zipfile
    file_from_zip = current_zipfile.read(name)
    decap_name_plus_path = poa_config.get("tmp_dir") + "/" + decap_name
    # we save the pdf to a local file
    with open(decap_name_plus_path, "wb") as temp_file:
        temp_file.write(file_from_zip)
    return decap_name_plus_path


def pdf_new_name(pdf_name, title, doi, poa_config):
    new_name = gen_new_name_for_file(
        pdf_name, title, doi, poa_config.get("filename_pattern")
    )
    LOGGER.info("new_name: %s", new_name)
    return new_name


def pdf_decap_name(new_name):
    return "decap_" + new_name


def pdf_details(file_title_map):
    "find the PDF file name in the zip file map"
    pdf_name = None
    title = None
    for name in file_title_map:
        file_title = file_title_map[name]
        if file_title == "Merged PDF":
            LOGGER.info("title: %s", title)
            pdf_name = name
            title = file_title
    return pdf_name, title


def decap_the_pdf(decap_name_plus_path, poa_config):
    decap_status = None
    try:
        # pass the local file path, and the path to a temp dir, to the decapitation script
        decap_status = func_timeout(
            PDF_DECAPITATE_TIMEOUT,
            decapitate_pdf_with_error_check,
            args=(
                decap_name_plus_path,
                poa_config.get("decapitate_pdf_dir") + os.sep,
                poa_config,
            ),
        )
    except FunctionTimedOut:
        decap_status = False
        LOGGER.error(
            "PDF decap did not finish within %s seconds", PDF_DECAPITATE_TIMEOUT
        )
    return decap_status


def copy_pdf_to_output_dir(
    file_title_map, output_dir, doi, current_zipfile, poa_config
):
    """
    we will attempt to generate a headless pdf and move this pdf
    to the output directory.

    if this headless creation fails, we will raise an error in the log file

    the function that we call to decapitate the pdf is contained in decapitate_pdf.py.
    It manages some error handline, and tries to determine whether the pdf
    cover content has been cleanly removed.
    """

    name, title = pdf_details(file_title_map)
    new_name = pdf_new_name(name, title, doi, poa_config)
    decap_name = pdf_decap_name(new_name)
    decap_name_plus_path = extract_pdf_from_zip(
        name, current_zipfile, decap_name, poa_config
    )

    decap_status = decap_the_pdf(decap_name_plus_path, poa_config)

    if decap_status:
        # pass the local file path, and the path to a temp dir, to the decapiation script
        try:
            file_content = None
            pdf_file_name = os.path.join(
                poa_config.get("decapitate_pdf_dir"), decap_name
            )
            with open(pdf_file_name, "rb") as open_file:
                file_content = open_file.read()
            if file_content:
                with open(os.path.join(output_dir, new_name), "wb") as out_handler:
                    out_handler.write(file_content)
        except IOError as ioe:
            # The decap may return true but the file does not exist for some reason
            #  allow the transformation to continue in order to processes the supplementary files
            LOGGER.error("decap returned true but the pdf file is missing %s: %s", new_name, ioe)
    else:
        # if the decapitation script has failed
        LOGGER.error("could not decapitate %s", new_name)


def remove_pdf_from_file_title_map(file_title_map):
    new_map = {}
    for name in file_title_map:
        title = file_title_map[name]
        if title == "Merged PDF":
            continue
        new_map[name] = title
    return new_map


def move_new_zipfile(doi, poa_config):
    filename_pattern = poa_config.get("zipfile_pattern")
    new_zipfile_name = get_new_zipfile_name(doi, filename_pattern)
    new_zipfile_name_plus_path = poa_config.get("tmp_dir") + "/" + new_zipfile_name
    shutil.move(
        new_zipfile_name_plus_path,
        poa_config.get("output_dir") + "/" + new_zipfile_name,
    )


def process_zipfile(zipfile_name, poa_config=None):
    # configuration can be passed in or parsed from the config_section
    if not poa_config:
        poa_config = parse_raw_config(raw_config(None))

    # open the zip file
    with zipfile.ZipFile(zipfile_name, "r") as current_zipfile:
        doi = get_doi_from_zipfile(current_zipfile)
        file_title_map = get_filename_new_title_map(current_zipfile)
        copy_pdf_to_output_dir(
            file_title_map, poa_config.get("output_dir"), doi, current_zipfile, poa_config
        )
        pdfless_file_title_map = remove_pdf_from_file_title_map(file_title_map)

        # supplements zip file
        new_zipfile_path = gen_new_zipfile(doi, poa_config)
        with zipfile.ZipFile(new_zipfile_path, "w") as new_zipfile:
            move_files_into_new_zipfile(
                current_zipfile, pdfless_file_title_map, new_zipfile, doi, poa_config
            )

    move_new_zipfile(doi, poa_config)
    return True
