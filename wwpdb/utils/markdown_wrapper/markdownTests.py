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

import sys
import unittest
import traceback

from render_markdown import *


class markdownTests(unittest.TestCase):

    def setUp(self):
        self.__lfh = sys.stdout
        self.__verbose = True
        self.__testFileMermaid = "test-mermaid.md"
        self.__settingsFile = "markdown_render.ini"
        self.__outputFile = "export.html"

    def tearDown(self):
        pass

    def testRenderMermaid(self):
        """Test case -  render markdown with mermaid figure
        """
        self.__lfh.write("\nStarting %s %s\n" % (self.__class__.__name__,
                                                 sys._getframe().f_code.co_name))
        try:
            settings = getSettings(self.__settingsFile)
            md_data = unicode(open(self.__testFileMermaid, 'r').read(), 'utf-8')
            html = markdown2html(md_data, settings, markdownPath="inline-text")
            html = addMermaid(html)
            #
            with open(self.__outputFile, 'w') as ofh:
                ofh.write(html.encode('utf-8'))
        except:
            traceback.print_exc(file=self.__lfh)
            self.fail()


def suiteMermaid():
    suiteSelect = unittest.TestSuite()
    suiteSelect.addTest(markdownTests("testRenderMermaid"))
    return suiteSelect


if __name__ == '__main__':
    #
    mySuite = suiteMermaid()
    unittest.TextTestRunner(verbosity=2).run(mySuite)
