##
# File: ImportTests.py
# Date:  06-Oct-2018  E. Peisach
#
# Updates:
##

import unittest

from wwpdb.utils.markdown_wrapper.render_markdown import markdown2html, addMermaid, getSettings  # noqa: F401 pylint: disable=unused-import


class ImportTests(unittest.TestCase):
    def testInstantiate(self):
        """Tests simple instantiation"""
        pass  # pylint: disable=unnecessary-pass


if __name__ == "__main__":
    unittest.main()
