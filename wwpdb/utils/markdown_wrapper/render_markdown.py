##
#  File:  render_markdown.py
#  Date:  Sep 2, 2016
#
#  Updates:
#    Nov 10, 2016   jdw   Refactor wsgi function separating rendering and configuration
#                         functions -
#
#    Nov 16, 2016   jdw   Add support for graphviz/dotgraph and mermaid code blocks -
#                         This is bolted on as post processing operation.  Resolved
#                         compatibility issues with code highlighting extension. Requires
#                         in-line comments to process dotgraph and mermaid fenced code
#                         blocks.
#    Nov 16, 2016   jdw   Split out wsgi entry point - move static configuration to
#                          settings (markdown_render.ini) file -
#
#    Nov 29, 2016   jdw   Add support for CDN delivery of CSS and JS dependencies.
#                         Preserving rendered HTML is the only option for saving the
#                         the output of Mermaid graphs at this point.  The PDF conversion
#                         of text labeling is quite broken in the current version of
#                         SVG -> PDF conversion owing to the use of HTML markup for
#                         laying out labels on GRAPHS.   This does not appear to be
#                         problem for sequence diagrams.
#    Jan 5, 2017  jdw     add support for Gnatt charts
#
import os
import os.path
import re
import sys
import markdown
import traceback
#
from graphviz import Source
from bs4 import BeautifulSoup
#
import markdown.extensions.codehilite

def parse_metadata(source_text):
    """ Parse Meta-Data and separate from the original text.

    This was copied from the Python-Markdown meta-data extension
    because we need to get the metadata *before* processing the text.
    """
    meta = {}
    key = None
    lines = source_text.split('\n')
    META_RE = re.compile(r'^[ ]{0,3}(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*)')
    META_MORE_RE = re.compile(r'^[ ]{4,}(?P<value>.*)')
    while True:
        line = lines.pop(0)
        if line.strip() == '':
            break  # blank line - done
        m1 = META_RE.match(line)
        if m1:
            key = m1.group('key').lower().strip()
            value = m1.group('value').strip()
            try:
                meta[key].append(value)
            except KeyError:
                meta[key] = [value]
        else:
            m2 = META_MORE_RE.match(line)
            if m2 and key:
                # Add another line to existing key
                meta[key].append(m2.group('value').strip())
            else:
                lines.insert(0, line)
                break  # no meta data - done
    return (meta, '\n'.join(lines))


def first_heading(source_text):
    """Scan through the text and return the first heading."""
    lines = source_text.split('\n')
    for l in lines:
        if l.startswith(u'#'):
            return l.strip(u'# ')
    return None


def getSettings(settingsFilePath):
    '''  Read configuration file and return dictionary of configuration options
    '''
    settings = {}
    try:
        conf_pat = re.compile(r'^(\S*)\s?=\s?(.*)$')
        fin = open(settingsFilePath)
        for conf_line in fin:
            m = conf_pat.match(conf_line)
            if m:
                s = m.group(1)
                v = m.group(2).strip('"\'')
                # convert various strings to their boolean value
                if v.lower() == 'yes' or v.lower() == 'on' or v == '1':
                    v = True
                elif v.lower() == 'no' or v.lower() == 'off' or v == '0':
                    v = False
                # support PHP-style array values
                if s.endswith('[]'):
                    s = s[:-2]
                    if s in settings:
                        settings[s].append(v)
                    else:
                        settings[s] = [v]
                else:
                    settings[s] = v
        fin.close()
    except:
        pass

    return settings


def renderDotgraph(dotText):
    """Render dot graph as SVG - """
    svgGraph = Source(dotText, format='svg')
    return svgGraph.pipe().decode('utf-8')


def addMermaid(html):
    preWrapFlag = False
    soup = BeautifulSoup(html, 'html.parser')
    try:
        for divC in soup.find_all('div', attrs={'class': 'codehilite'}):
            if len(divC.pre.find_all(text=re.compile("%% mermaid figure"))) > 0:
                divC.pre.span.extract()
                tt = divC.pre.string
                divC.pre.extract()
                divC.string = tt.replace("%% mermaid figure", "")
                divC.attrs['class'] = 'mermaid'
                divC.name = "code"
                #
                if preWrapFlag:
                    wrapper = soup.new_tag('pre')
                    divC.wrap(wrapper)
            elif len(divC.pre.find_all(text=re.compile("// dotgraph figure"))) > 0:
                divC.pre.span.extract()
                dotText = divC.pre.string
                divC.pre.extract()
                svg = renderDotgraph(dotText)
                svg_soup = BeautifulSoup(svg, 'html.parser')
                if preWrapFlag:
                    mypre = soup.new_tag('pre')
                    mypre.insert(0, svg_soup)
                    divC.replaceWith(mypre)
                else:
                    divC.replaceWith(svg_soup)

    except:
        traceback.print_exc(sys.stderr)

    return soup.prettify()


def markdown2html(source_text, settings, markdownPath="inline-text"):
    """ Render input markdown source text as HTML.   Control options stored in input settings dictionary.
        Text is labeled as 'markdownPath'  ...  Get extensions from config file --
    """
    #
    _debug = False
    # read some prefs
    include_toc = bool(int(settings.get('toc', 0)))
    toc_hidden = bool(int(settings.get('toc_hidden', 0)))
    meta_behavior = settings.get('metadata', 'ignore')
    link_attrs = settings.get('link_attrs', [])
    link_pattern = settings.get('link_pattern', None)
    text_version = bool(int(settings.get('text_version', 0)))
    text_suffix = settings.get('text_suffix', "text")
    md_ext = settings.get('md_extensions', [])
    cdn_url = settings.get("cdn_url", "")
    #
    # process metadata
    meta_title = None
    if meta_behavior != 'ignore':
        (metadata, source_text) = parse_metadata(source_text)
        # check for a title
        if 'title' in metadata and len(metadata['title'][0]) > 0:
            meta_title = metadata['title'][0]
            del metadata['title']
        # respect the per-document pref for table of contents
        if 'toc' in metadata:
            toc = metadata['toc'][0].lower()
            if toc == 'on' or toc == 'yes' or toc == '1':
                include_toc = True
            elif toc == 'off' or toc == 'no' or toc == '0':
                include_toc = False
            del metadata['toc']
        # display metadata?
        if meta_behavior == 'table':
            meta_html_table = '<table id="metadata">\n'
            for (name, values) in metadata.items():
                if link_pattern is not None and name in link_attrs:
                    newval = []
                    for target in values:
                        link = link_pattern.replace('%k', name).replace('%v', target)
                        newval.append('<a href="%s">%s</a>' % (link, target))
                    values = newval
                table_row = '''<tr>
                                <td class="mda">%s</td>
                                <td class="mdv">%s</td>
                                </tr>
                            ''' % (name, '<br>'.join(values))
                meta_html_table = meta_html_table + table_row
            meta_html_table = meta_html_table + '</table>\n'
            source_text = meta_html_table + source_text
    if _debug:
        sys.stderr.write("Document metadata %r\n" % metadata)
    toc_display = u''
    if include_toc:
        # make sure the required extension is loaded
        md_ext.append('toc')
        # molest the source
        source_text = u'<p id="showhide" class="controls" onClick="toggleVisibility(this, \'TOC\');">Hide Table of Contents</p>\n\n[TOC]\n\n' + source_text
        # set initial state for table of contents
        if toc_hidden:
            toc_display = u' onLoad="javascript:toggleVisibility(document.getElementById(\'showhide\'), \'TOC\');"'

    if text_version:
        text_href = '%s-%s' % (markdownPath, text_suffix)
        text_div = '<div class="controls" style="float: right"><a href="%s">View Original Text</a></div>' % text_href
        if sys.version_info[0] < 3:
            source_text = unicode(text_div, 'utf-8') + source_text
        else:
            source_text = text_div + source_text

    # Translate md_ext to new format
    md_ext_new = __translate_extensions(md_ext)
    # a Markdown object to do the work
    md = markdown.Markdown(extensions=md_ext_new,
                           output_format='html')
    # convert text to HTML
    mdown = md.convert(source_text)

    title = "Viewing Markdown (%s) as HTML" % os.path.basename(markdownPath)
    if meta_title is not None:
        # a title in the metadata takes precedence
        title = meta_title
    elif bool(int(settings.get('title_from_heading', 1))):
        heading = first_heading(source_text)
        if heading is not None:
            title = heading
    #
    stPL = []
    addMermaidStyle = False
    #
    # Add Mermaid JS if configured -
    #
    jsMermaid = ''
    if sys.version_info[0] == 2:
        mermaid_js_path = unicode(settings.get('mermaid_js_path', ''))
    else:
        mermaid_js_path = settings.get('mermaid_js_path', '')
    if len(mermaid_js_path) > 0:
        jsMermaid = '''
        <script src="%s%s"> </script>
        #
        <script type="text/javascript" charset="utf-8">
            mermaid.initialize({
                flowchart:{
                    htmlLabels: true,
                    useMaxWidth: false
                  },
                sequenceDiagram: {
                    diagramMarginX:10,
                    diagramMarginY:10,
                    boxTextMargin:10,
                    noteMargin:10,
                    messageMargin:35,
                    mirrorActors:true,
                    // Height of actor boxes
                    width:300,
                    height:40,
                    useMaxWidth: false
                },
               ganttConfig: {
                titleTopMargin:25,
                barHeight:20,
                barGap:4,
                topPadding:5,
                sidePadding:75,
                gridLineStartPadding:35,
                fontSize:11,
                numberSectionStyles:3
              },
              cloneCssStyles:true,
              startOnLoad:true
            });
        </script>
        ''' % (cdn_url, mermaid_js_path)
        # add Mermaid style details --
        addMermaidStyle = True
    #
    # Add other markdown style details --
    #
    if sys.version_info[0] >= 3:
        stPL.append((settings.get('markdown_screen_css_path', ''), 'screen'))
        stPL.append((settings.get('markdown_print_css_path', ''), 'print'))
        stPL.append((settings.get('codehilite_css_path', ''), 'screen'))
        if addMermaidStyle:
            stPL.append((settings.get('mermaid_css_path', ''), 'screen'))
    else:
        stPL.append((unicode(settings.get('markdown_screen_css_path', ''), 'utf-8'), 'screen'))
        stPL.append((unicode(settings.get('markdown_print_css_path', ''), 'utf-8'), 'print'))
        stPL.append((unicode(settings.get('codehilite_css_path', ''), 'utf-8'), 'screen'))
        if addMermaidStyle:
            stPL.append((unicode(settings.get('mermaid_css_path', ''), 'utf-8'), 'screen'))

    stL = []
    for st in stPL:
        if len(st[0]) > 0:
            stL.append('<link rel="stylesheet" href="%s%s" type="text/css" media="%s" charset="utf-8"></link>' % (cdn_url, st[0], st[1]))
    #
    html = u'''<html>
        <head>
          <meta http-equiv="Content-type" content="text/html; charset=utf-8">
          %s
          <title>%s</title>
          <script type="text/javascript" charset="utf-8">
            function toggleVisibility(theButton, targetName) {
              var target = document.getElementById(targetName);
              if ( target.style.opacity == '0' ) {
                // show
                target.style.left = '0px';
                target.style.position = 'relative';
                target.style.opacity = '1';
                theButton.innerHTML = "Hide Table of Contents";
              } else {
                // hide
                target.style.left = '-4000px';
                target.style.position = 'absolute';
                target.style.opacity = '0';
                theButton.innerHTML = "Show Table of Contents";
              }
              return true;
            }
          </script>
          %s

        </head>
        <body%s>
        %s
        </body>
        </html>

        ''' % ('\n'.join(stL), title, jsMermaid, toc_display, mdown)

    # use an ID instead of a class for the table of contents
    html = html.replace(u'div class="toc"', 'div id="TOC"')
    return html

def __translate_extensions(md_ext):
    translations = { 'codehilite' : markdown.extensions.codehilite.CodeHiliteExtension}
    ret = []
    for ext in md_ext:
        pos = ext.find("(")
        if pos > 0:
            ename = ext[:pos]
            opts = ext[pos+1:-1]
            configs = {}
            pairs = [x.split("=") for x in opts.split(",")]
            configs.update([(x.strip(), y.strip()) for (x, y) in pairs])
            if ename in translations:
                ret.append(translations[ename](**configs))
            else:
                print("Extension mapping for %s ename unknown --skipped" % ename)
        else:
            # No options pass through
            ret.append(ext)
    return ret
