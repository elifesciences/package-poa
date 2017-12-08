import zipfile
import glob
import logging
import shutil
import os
from xml.dom.minidom import Document
from collections import namedtuple
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.etree import ElementTree
from xml.dom import minidom
from packagepoa.decapitate_pdf import decapitate_pdf_with_error_check
from elifearticle import article as ea
from conf import raw_config, parse_raw_config

"""
open the zip file from EJP,
get the manifest.xml file
move the pdf
rename and move supp files to a new zipfile
find the pdf file and decapitate the cover page from it
move the PDF to the output directory
move the new zip file to the output directory
"""

# local logger
logger = logging.getLogger('transform')
hdlr = logging.FileHandler('transform.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

# global logger
manifest_logger = logging.getLogger('manifest')
hdlr = logging.FileHandler('manifest.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
manifest_logger.addHandler(hdlr)
manifest_logger.setLevel(logging.INFO)


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
            article_id=article_id, extra='', file_ext=file_ext)
    else:
        new_name = filename_pattern.format(
            article_id=article_id, extra='_' + new_name_front, file_ext=file_ext)
    return new_name

def get_doi_from_zipfile(ejp_input_zipfile):
    #print ejp_input_zipfile.namelist()
    manifest = ejp_input_zipfile.read("manifest.xml")
    tree = ElementTree.fromstring(manifest)
    for child in tree:
        if child.tag == "resource":
            if child.attrib["type"] == "doi":
                doi = child.text
            elif child.attrib["type"] == "resourceid":
                doi_base = "10.7554/eLife."
                article_number = child.text.split("-")[-1]
                doi = doi_base + article_number
    return doi

def get_filename_new_title_map_from_zipfile(ejp_input_zipfile):
    manifest_logger.info("unpacking and renaming " + str(ejp_input_zipfile.filename))
    file_title_map = {}
    manifest = ejp_input_zipfile.read("manifest.xml")
    tree = ElementTree.fromstring(manifest)
    for child in tree:
        if child.tag == "file":
            for file in child:
                if file.tag == "filename":
                    filename = file.text
                if file.tag == "title":
                    title = file.text
            file_title_map[filename] = title
    return file_title_map

def get_new_zipfile_name(doi, filename_pattern):
    article_id = article_id_from_doi(doi)
    new_zipfile_name = None
    if filename_pattern:
        new_zipfile_name = filename_pattern.format(article_id=article_id)
    return new_zipfile_name

def gen_new_zipfile(doi, poa_config):
    filename_pattern = poa_config.get('zipfile_pattern')
    new_zipfile_name = get_new_zipfile_name(doi, filename_pattern)
    new_zipfile_name_plus_path = poa_config.get('tmp_dir') + "/" + new_zipfile_name
    new_zipfile = zipfile.ZipFile(new_zipfile_name_plus_path, 'w')
    return new_zipfile

def move_files_into_new_zipfile(current_zipfile, file_title_map, new_zipfile, doi,
                                poa_config):
    filename_pattern = poa_config.get('filename_pattern')
    for name in file_title_map.keys():
        title = file_title_map[name]
        new_name = gen_new_name_for_file(name, title, doi, filename_pattern)

        file_from_zip = current_zipfile.read(name)
        temp_file_name = poa_config.get('tmp_dir') + "/" + "temp_transfer"
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

def copy_pdf_to_output_dir(file_title_map, output_dir, doi, current_zipfile, poa_config):
    """
    we will attempt to generate a headless pdf and move this pdf
    to the output directory.

    if this headless creation fails, we will raise an error in the log file

    the function that we call to decapitate the pdf is contained in decapitate_pdf.py.
    It manages some error handline, and tries to determine whether the pdf
    cover content has been cleanly removed.
    """

    for name in file_title_map.keys():
        # we extract the pdf from the zipfile
        title = file_title_map[name]

        if title == "Merged PDF":
            print title
            new_name = gen_new_name_for_file(name, title, doi, poa_config.get('filename_pattern'))
            file = current_zipfile.read(name)
            print new_name
            decap_name = "decap_" + new_name
            decap_name_plus_path = poa_config.get('tmp_dir') + "/" + decap_name
            # we save the pdf to a local file
            temp_file = open(decap_name_plus_path, "wb")
            temp_file.write(file)
            temp_file.close()

    if decapitate_pdf_with_error_check(
        decap_name_plus_path, poa_config.get('decapitate_pdf_dir') + os.sep, poa_config):
        # pass the local file path, and teh path to a temp dir, to the decapiation script
        try:
            move_file = open(os.path.join(poa_config.get('decapitate_pdf_dir'), decap_name), "rb").read()
            out_handler = open(os.path.join(output_dir, new_name), "wb")
            out_handler.write(move_file)
            out_handler.close()
        except:
            # The decap may return true but the file does not exist for some reason
            #  allow the transformation to continue in order to processes the supplementary files
            alert_message = "decap returned true but the pdf file is missing " + new_name
            logger.error(alert_message)
    else:
        # if the decapitation script has failed, we move the original pdf file
        move_file = file
        alert_message = "could not decapitate " + new_name
        logger.error(alert_message)


def remove_pdf_from_file_title_map(file_title_map):
    new_map = {}
    for name in file_title_map.keys():
        title = file_title_map[name]
        if title == "Merged PDF":
            continue
        else:
            new_map[name] = title
    return new_map

def move_new_zipfile(doi, poa_config):
    filename_pattern = poa_config.get('zipfile_pattern')
    new_zipfile_name = get_new_zipfile_name(doi, filename_pattern)
    new_zipfile_name_plus_path = poa_config.get('tmp_dir') + "/" + new_zipfile_name
    shutil.move(new_zipfile_name_plus_path, poa_config.get('output_dir') + "/" + new_zipfile_name)


def process_zipfile(zipfile_name, config_section=None, poa_config=None):
    # configuration can be passed in or parsed from the config_section
    if not poa_config:
        poa_config = parse_raw_config(raw_config(config_section))

    # open the zip file
    current_zipfile = zipfile.ZipFile(zipfile_name, 'r')
    doi = get_doi_from_zipfile(current_zipfile)
    file_title_map = get_filename_new_title_map_from_zipfile(current_zipfile)
    copy_pdf_to_output_dir(file_title_map, poa_config.get('output_dir'), doi,
                               current_zipfile, poa_config)
    pdfless_file_title_map = remove_pdf_from_file_title_map(file_title_map)

    # supplements zip file
    new_zipfile = gen_new_zipfile(doi, poa_config)
    move_files_into_new_zipfile(current_zipfile, pdfless_file_title_map, new_zipfile, doi,
                                poa_config)

    # Close zip file before moving
    new_zipfile.close()
    move_new_zipfile(doi, poa_config)
    return True
