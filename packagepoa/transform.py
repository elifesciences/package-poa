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

get the manifext.xml file

move the pdf to the hw staging dir

rename and move supp files to a new zipfile called
    elife_poa_e000213_supporting_files.zip

find the pdf file and move this to the hw ftp staging directory

generate a new manifest and instert into the new zip file

move the new zip file to the HW staging site

move the old ejp zip file to the processed files directory
"""

# local logger
logger = logging.getLogger('transformEjpToHWZip')
hdlr = logging.FileHandler('transformEjpToHWZip.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

# global logger
workflow_logger = logging.getLogger('ejp_to_hw_workflow')
hdlr = logging.FileHandler('ejp_to_hw_workflow.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
workflow_logger.addHandler(hdlr)
workflow_logger.setLevel(logging.INFO)


class manifestXML(object):

    def __init__(self, doi, new_zipfile, filename_pattern):
        """
        set the root node
        get the article type from the object passed in to the class
        set default values for items that are boilder plate for this XML
        """

        self.root = Element('datasupp')
        self.root.set("sitecode", "elife")
        self.resource = SubElement(self.root, "resource")
        self.resource.set("type", "doi")
        self.resource.text = str(doi)

        self.linktext = SubElement(self.root, "linktext")
        self.linktext.text = "Supplementary data"

        # Add file elements to the manifest
        self.simple_manifest(new_zipfile, doi, filename_pattern)

    def simple_manifest(self, new_zipfile, doi, filename_pattern):
        """
        Add a simple XML file element to the manifest
        Note: linktext element must come before title (order matters)
        """
        # Filename is the folder inside the zip file
        filename_text = get_new_internal_zipfile_name(doi, filename_pattern)
        linktext_text = "Download zip folder"
        title_text = "Any figures and tables for this article are included in the PDF."
        title_text += " The zip folder contains additional supplemental files."

        # Add XML
        self.file = SubElement(self.root, "file")
        self.filename = SubElement(self.file, "filename")
        self.filename.text = filename_text

        self.description = SubElement(self.file, "linktext")
        self.description.text = linktext_text

        self.title = SubElement(self.file, "title")
        self.title.text = title_text

    def prettyXML(self):
        publicId = '-//HIGHWIRE//DTD HighWire Data Supplement Manifest//EN'
        systemId = 'http://schema.highwire.org/public/hwx/ds/datasupplement_manifest.dtd'
        encoding = 'ISO-8859-1'
        namespaceURI = None
        qualifiedName = "datasupp"

        doctype = ElifeDocumentType(qualifiedName)
        doctype._identified_mixin_init(publicId, systemId)

        rough_string = ElementTree.tostring(self.root, encoding)
        reparsed = minidom.parseString(rough_string)
        if doctype:
            reparsed.insertBefore(doctype, reparsed.documentElement)
        return reparsed.toprettyxml(indent="\t", encoding=encoding)

class ElifeDocumentType(minidom.DocumentType):
    """
    Override minidom.DocumentType in order to get
    double quotes in the DOCTYPE rather than single quotes
    """
    def writexml(self, writer, indent="", addindent="", newl=""):
        writer.write("<!DOCTYPE ")
        writer.write(self.name)
        if self.publicId:
            writer.write('%s  PUBLIC "%s"%s  "%s"'
                         % (newl, self.publicId, newl, self.systemId))
        elif self.systemId:
            writer.write('%s  SYSTEM "%s"' % (newl, self.systemId))
        if self.internalSubset is not None:
            writer.write(" [")
            writer.write(self.internalSubset)
            writer.write("]")
        writer.write(">"+newl)

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
    workflow_logger.info("unpacking and renaming" + str(ejp_input_zipfile))
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

def get_new_internal_zipfile_name(doi, filename_pattern):
    article_id = article_id_from_doi(doi)
    new_zipfile_folder_name = None
    if filename_pattern:
        new_zipfile_folder_name = filename_pattern.format(article_id=article_id)
    return new_zipfile_folder_name

def gen_new_internal_zipfile(doi, poa_config):
    filename_pattern = poa_config.get('internal_zipfile_pattern')
    new_zipfile_name = get_new_internal_zipfile_name(doi, filename_pattern)
    new_zipfile_name_plus_path = poa_config.get('tmp_dir') + "/" + new_zipfile_name
    new_zipfile = zipfile.ZipFile(new_zipfile_name_plus_path, 'w')
    return new_zipfile

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

        file = current_zipfile.read(name)
        temp_file_name = poa_config.get('tmp_dir') + "/" + "temp_transfer"
        f = open(temp_file_name, "wb")
        f.write(file)
        f.close()
        new_zipfile.write(temp_file_name, new_name)

def add_file_to_zipfile(new_zipfile, name, new_name):
    """
    Simple add a file to a zip file
    """
    if not new_zipfile or not name or not new_name:
        return
    new_zipfile.write(name, new_name)

def copy_pdf_to_hw_staging_dir(file_title_map, output_dir, doi, current_zipfile, poa_config):
    """
    we will attempt to generate a headless pdf and move this pdf
    to the ftp staging site.

    if this headless creation fails, we will raise an error to
    production@elifesciecnes.org, and try to copy the original pdf
    file to ftp staging

    the function that we call to decapitate the pdf is contained in decapitatePDF.py.
    It manages some error handline, and tries to determine witheher the pdf
    cover content has been celanly removed.

    TODO: - elife - ianm - tidy up paths to temporary pdf decpitation paths
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

def generate_hw_manifest(new_zipfile, doi, poa_config):
    filename_pattern = poa_config.get('internal_zipfile_pattern')
    manifestObject = manifestXML(doi, new_zipfile, filename_pattern)
    manifest = manifestObject.prettyXML()
    return manifest

def move_new_zipfile(doi, poa_config):
    filename_pattern = poa_config.get('zipfile_pattern')
    new_zipfile_name = get_new_zipfile_name(doi, filename_pattern)
    new_zipfile_name_plus_path = poa_config.get('tmp_dir') + "/" + new_zipfile_name
    shutil.move(new_zipfile_name_plus_path, poa_config.get('output_dir') + "/" + new_zipfile_name)

def add_hw_manifest_to_new_zipfile(new_zipfile, hw_manifest, poa_config):
    temp_file_name = poa_config.get('tmp_dir') + "/" + "temp_transfer"
    f = open(temp_file_name, "w")
    f.write(hw_manifest)
    f.close()
    new_zipfile.write(temp_file_name, "manifest.xml")

def process_zipfile(zipfile_name, poa_config, config_section=None):
    # configuration
    if not poa_config:
        poa_config = parse_raw_config(raw_config(config_section))

    # open the zip file
    current_zipfile = zipfile.ZipFile(zipfile_name, 'r')
    doi = get_doi_from_zipfile(current_zipfile)
    file_title_map = get_filename_new_title_map_from_zipfile(current_zipfile)
    copy_pdf_to_hw_staging_dir(file_title_map, poa_config.get('output_dir'), doi,
                               current_zipfile, poa_config)
    pdfless_file_title_map = remove_pdf_from_file_title_map(file_title_map)

    # Internal zip file
    internal_zipfile = gen_new_internal_zipfile(doi, poa_config)
    move_files_into_new_zipfile(current_zipfile, pdfless_file_title_map, internal_zipfile, doi,
                                poa_config)
    internal_zipfile.close()

    # Outside wrapping zip file
    new_zipfile = gen_new_zipfile(doi, poa_config)
    new_name = internal_zipfile.filename.split("/")[-1]
    add_file_to_zipfile(new_zipfile, internal_zipfile.filename, new_name)

    hw_manifest = generate_hw_manifest(new_zipfile, doi, poa_config)
    add_hw_manifest_to_new_zipfile(new_zipfile, hw_manifest, poa_config)
    # Close zip file before moving
    new_zipfile.close()
    move_new_zipfile(doi, poa_config)
    return True
