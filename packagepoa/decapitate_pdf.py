from __future__ import print_function
import logging
import subprocess

FORMAT = logging.Formatter(
    "%(created)f - %(levelname)s - %(processName)s - %(name)s - %(message)s"
)
LOGFILE = "decapitate_pdf.log"
LOGGER = logging.getLogger(__file__)
LOGGER.setLevel(logging.DEBUG)
HDLR = logging.FileHandler(LOGFILE)
HDLR.setLevel(logging.INFO)
HDLR.setFormatter(FORMAT)
LOGGER.addHandler(HDLR)

PDF_EXECUTABLE_DEFAULT = "/opt/strip-coverletter/strip-coverletter-docker.sh"


def decapitate_pdf_with_error_check(pdf_in, pdf_out_dir, poa_config=None):
    # configuration
    pdf_executable = None
    if poa_config:
        pdf_executable = poa_config.get("strip_coverletter_executable")
    if not pdf_executable:
        return False

    # PDF out file name
    pdf_out = pdf_out_dir + pdf_in.split("/")[-1]

    process = subprocess.Popen(
        [pdf_executable, pdf_in, pdf_out],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stderr = process.stderr.read()
    stdout = process.stdout.read()

    # subprocess.Popen doesn't interleave pipe output,
    # so neither will these log messages
    [LOGGER.info(line.decode('utf-8')), stdout.splitlines()]
    [LOGGER.error(line.decode('utf-8')), stderr.splitlines()]

    return stderr != ""  # no errors


if __name__ == "__main__":
    import sys

    ARGS = sys.argv[1:]
    if len(ARGS) < 2:
        print("Usage: decapitate_pdf.py <pdf-in> <pdf-out>")
        exit(1)

    HANDLER = logging.StreamHandler()
    HANDLER.setLevel(logging.DEBUG)
    HANDLER.setFormatter(FORMAT)
    LOGGER.addHandler(HANDLER)

    PIN = ARGS[0]
    POUT = ARGS[1]
    CONFIG = {"strip_coverletter_executable": PDF_EXECUTABLE_DEFAULT}
    decapitate_pdf_with_error_check(PIN, POUT, CONFIG)
