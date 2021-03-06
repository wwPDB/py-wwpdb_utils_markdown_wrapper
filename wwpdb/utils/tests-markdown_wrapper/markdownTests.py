##
#
# File:    markdownTests.py
# Author:  J. Westbrook
# Date:    15-Nov-2016
# Version: 0.001
#
# Updates:
#    1-Dec-2016 jdw sync with latest file conventions and add installation details
#
##
"""
 Installation - for project api documentation following recommendations from ReadTheDocs -

    #  For markdown with code higlighting
    pip install Pygments
    pip install markdown==2.6.6
    # for Sphinx and api docs with extra support for Google style comments
    pip install sphinx
    pip install sphinx-autobuild
    pip install recommonmark==0.4.0
    pip install CommonMark==0.5.5
    #
    pip install sphinx_bootstrap_theme
    pip install sphinxcontrib-napoleon==0.5.0

    # Needed for handling inline mermaid and graphviz dot format
    pip install beautifulsoup4
    pip install graphviz

"""
__docformat__ = "restructuredtext en"
__author__ = "John Westbrook"
__email__ = "jwest@rcsb.rutgers.edu"
__license__ = "Creative Commons Attribution 3.0 Unported"
__version__ = "V0.01"

import filecmp
import sys
import unittest
import platform
import os
import os.path

try:
    from unittest import mock
except ImportError:
    import mock
import graphviz

from wwpdb.utils.markdown_wrapper.render_markdown import getSettings, markdown2html, addMermaid

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

orig_backend_run = graphviz.backend.run
run_under_mock = os.environ.get("MOCKEXE")


def simple_graphviz_render(cmd, input=None, capture_output=False, check=False, encoding=None, quiet=False, **kwargs):  # pylint: disable=redefined-builtin
    # logger.error("Graphviz cmd is %s input is %s capture %s check is %s encoding is %s kwargs is %s", cmd, input, capture_output, check, encoding, kwargs)
    logger.debug("Graphviz cmd is %s", cmd)
    if run_under_mock:
        return b"<!---- mock svg --->", ""
    else:
        return orig_backend_run(cmd, input=input, capture_output=capture_output, check=check, encoding=encoding, quiet=quiet, **kwargs)  # ignore kwargs


class markdownTests(unittest.TestCase):
    def setUp(self):
        here = os.path.abspath(os.path.dirname(__file__))
        testoutput = os.path.join(here, "test-output", platform.python_version())
        if not os.path.exists(testoutput):  # pragma: no cover
            os.makedirs(testoutput)

        self.__testFileMermaid = os.path.join(here, "test-mermaid.md")
        self.__settingsFile = os.path.join(here, "markdown_render.ini")
        self.__outputFile = os.path.join(testoutput, "export.html")
        if run_under_mock:
            self.__refFile = os.path.join(here, "export.ref")
        else:
            self.__refFile = os.path.join(here, "exportmock.ref")

    def tearDown(self):
        pass

    @mock.patch("graphviz.backend.run", side_effect=simple_graphviz_render)
    def testRenderMermaid(self, mfunc):  # pylint: disable=unused-argument
        """Test case -  render markdown with mermaid figure"""
        logger.info("Starting")
        try:
            settings = getSettings(self.__settingsFile)
            with open(self.__testFileMermaid, "r") as fin:
                md_data_in = fin.read()
            if sys.version_info[0] == 2:
                md_data = unicode(md_data_in, "utf-8")  # noqa: F821 pylint: disable=undefined-variable
            else:
                md_data = md_data_in
            html = markdown2html(md_data, settings, markdownPath="inline-text")
            html = addMermaid(html)
            #
            with open(self.__outputFile, "w") as ofh:
                if sys.version_info[0] >= 3:
                    ofh.write(html)
                else:
                    ofh.write(html.encode("utf-8"))
        except Exception as e:
            logger.exception("Exception %s", e)
            self.fail()

        self.assertTrue(filecmp.cmp(self.__refFile, self.__outputFile, "Failed to compare file output"))


# noinspection PyPep8Naming
def suiteMermaid():
    suiteSelect = unittest.TestSuite()
    suiteSelect.addTest(markdownTests("testRenderMermaid"))
    return suiteSelect


if __name__ == "__main__":
    #
    mySuite = suiteMermaid()
    unittest.TextTestRunner(verbosity=2).run(mySuite)
