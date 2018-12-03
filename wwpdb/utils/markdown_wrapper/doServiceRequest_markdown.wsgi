##
#  File:  doServiceRequest_markdown.py
#  Date:  Sep 2, 2016
#
#  Updates:
#    Nov 10, 2016   jdw   Refactor wsgi function separating rendering and configuration
#                         functions -
#    Nov 16, 2016   jdw   Split off wsgi request module - with supporting settings file -
#
#
import os
import sys
from urllib import unquote
from wwpdb.utils.markdown_wrapper.render_markdown import markdown2html, addMermaid, getSettings


def application(environ, start_response):
    """  WSGI entry point --  Renders input URL containing a file target containing Markdown
         markup as HTML.

    """
    status = '200 OK'
    show_text = False
    _debug = True

    # read the INI settings
    pwd = os.path.dirname(environ['SCRIPT_FILENAME'])
    settingsPath = os.path.join(pwd, 'markdown_render.ini')
    settings = getSettings(settingsPath)

    # get the source file path
    relMarkdownPath = unquote(environ['REQUEST_URI'])
    docPath = environ['DOCUMENT_ROOT']
    source_file = os.path.join(docPath, relMarkdownPath[1:])
    if _debug:
        sys.stderr.write("Document path %s\n" % docPath)
        sys.stderr.write("Source path %s\n" % source_file)
        sys.stderr.write("Relative path %s\n" % relMarkdownPath)
        sys.stderr.flush()

    source_text = unicode(open(source_file).read(), 'utf-8')

    # display original text?
    if show_text:
        source_text = source_text.encode('utf-8')
        response_headers = [
            ('Content-type', 'text/plain;charset=utf-8'),
            ('Content-Length', str(len(source_text))),
        ]
        start_response(status, response_headers)

        return [source_text]

    html = markdown2html(source_text, settings, relMarkdownPath)
    html = addMermaid(html)
    #
    html = html.encode('utf-8')
    response_headers = [
        ('Content-type', 'text/html'),
        ('Content-Length', str(len(html))),
    ]
    start_response(status, response_headers)
    return [html]
