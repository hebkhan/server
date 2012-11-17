'''
Created on Nov 4, 2012

@author: oferko
'''

from BeautifulSoup import BeautifulStoneSoup, NavigableString
from path3 import path
import re
import hashlib
import urllib2
import csv
import itertools
import sys

APP_ROOT = path(__file__).parent.parent

def get_htmls():
    for tmpl in (APP_ROOT + "/templates").walkfiles("*.html"):
        yield tmpl

    for tmpl in (APP_ROOT + "/clienttemplates").walkfiles("*.handlebars"):
        yield tmpl

NON_TEXT = set("[document] script style".split())

RE_TEMPLATE = re.compile("({{.*?}}|{%.*?%})")
from cgi import escape
def simple_escape(match):
    s = match.group(0)
    e = escape(s)
    return e

from HTMLParser import HTMLParser
htmlparser = HTMLParser()

RE_TAGS = re.compile("<(/?)(!|\w+)(.*?)(/?)>|\n", flags=re.DOTALL)
RE_ATTR_TAGS = {'input'     : re.compile("""(value|placeholder)=(?P<qt>\"|')(.+?)(?P=qt)"""),
                'textarea'  : re.compile("""(value|placeholder)=(?P<qt>\"|')(.+?)(?P=qt)"""),
                'a'         : re.compile("""(title)=(?P<qt>\"|')(.+?)(?P=qt)"""),
                'img'       : re.compile("""(title)=(?P<qt>\"|')(.+?)(?P=qt)"""),
                }
RE_LINEBREAK = re.compile("\n")
def iter_translateables(html):

    def iterator():
        line_breaks = [m.start() for m in RE_LINEBREAK.finditer(html+"\n")]
        line_no = 1
        cursor = 0
        current_tag = None
        matches = RE_TAGS.finditer(html)
        for match in matches:
            ended, tag, attrs, end = match.groups()
            tag_start, tag_end = match.span()
            if tag and not ended:
                if not end:
                    current_tag = tag
                regex = RE_ATTR_TAGS.get(tag)
                if regex:
                    attrs_start = tag_start + html[tag_start:tag_end].find(attrs)
                    for match in regex.finditer(attrs):
                        name, qt, value = match.groups()
                        attr_start, attr_end = match.start(), match.end()
                        while attrs_start+attr_start > line_breaks[line_no-1]:
                            line_no += 1
                        if value == "Ask a question about this video":
                            pass
                        yield value, (attrs_start+attr_start, attrs_start+attr_end), line_no


            if current_tag in NON_TEXT:
                for match in matches:
                    ended, tag, _, _ = match.groups()
                    if tag == current_tag:
                        assert ended, match.group(0)
                        tag_end = match.end()
                        current_tag = None
                        break
                else:
                    raise Exception("Could not close %s" % current_tag)
            else:
                while cursor > line_breaks[line_no-1]:
                    line_no += 1
                yield html[cursor:tag_start], (cursor, tag_start), line_no

            cursor = tag_end

        tag_start = len(html)
        while cursor > line_breaks[line_no-1]:
            line_no += 1
        yield html[cursor:tag_start], (cursor, tag_start), line_no

    for text, span, line_no in iterator():
        if text:
            nice_text = text.strip()
            if not is_translateable(nice_text):
                continue
            digest = hashlib.md5(nice_text).hexdigest()[:DIGEST_LEN]
            yield nice_text, span, line_no, digest

def is_translateable(nice_text):
    if not nice_text:
        return
    if nice_text.lower() == "x":
        return
    if "TODO" in nice_text:
        return
    cleaned = htmlparser.unescape(RE_TEMPLATE.sub("", nice_text)).strip()
    if not any(s.isalpha() for s in cleaned):
        return
    return True

DIGEST_LEN = 6

def check_collision(digest, _digests=set()):
    if digest in _digests:
        raise Exception("Collision!")
    _digests.add(digest)

def iter_htmls():
    htmls = list(get_htmls())
    for i, f in enumerate(htmls):
        relative_path = APP_ROOT.relpathto(f)
        file_digest = hashlib.md5(relative_path).hexdigest()[:DIGEST_LEN]
        check_collision(file_digest)
        print i, file_digest, relative_path
        yield f, file_digest, relative_path

def extract_for_translation():
    data = get_translated_data(all=True)

    counter = lambda counter=itertools.count(1): str(next(counter))
    new_items = []
    with open("extracted_text2.tab","w") as output:
        print >>output, "\t".join("id,file digest,line no,text digest,text,translation".split(","))
        for f, file_digest, relative_path in iter_htmls():
            if f.endswith("editexercise.html"):
                pass
            orig = f + ".orig"
            orig = orig if orig.isfile() else f
            orig_html = open(orig).read()
            translations = data.get(file_digest) or {}
            if translations == "IGNORE":
                print "SKIPPING:", f
                print >>output, "%s\t'%s\t%s\t%s\t%s\tIGNORE" % (counter(), file_digest, "", "", relative_path)
                print >>output, counter()
                continue

            lines = []
            for text, _, line_no, text_digest in iter_translateables(orig_html):
                translation = translations.get(text_digest, "")
                if translation == "NOOP":
                    translation = ""
                lines.append(("'"+file_digest, "#%s" % line_no, "'"+text_digest, "'%s" % text, "'%s" % translation))
                if text_digest not in translations:
                    new_items.append(lines[-1])

            if lines:
                print >>output, "\t".join((counter(), "'" + file_digest, "", "", relative_path))
                for line in lines:
                    print >>output, "\t".join((counter(),) + line)
                print >>output, counter()
                print "\t", len(lines)

    for line in new_items:
        print "\t".join((counter(),) + line)

TRANSLATION_URL = "https://docs.google.com/spreadsheet/pub?key=0Ap8djBdeiIG7dDF6VDJPbEpFSG5SNWtwOFVrU3Y5Qnc&single=true&gid=5&output=csv"

def get_translated_data(all=False):
    lines = csv.reader(urllib2.urlopen(TRANSLATION_URL))
    _header = next(lines)
    data = {}
    for i, file_digest, _tag, text_digest, _orig, trans in lines:
        if file_digest and not text_digest and trans=="IGNORE": # ignore entire file
            data[file_digest] = "IGNORE"
        if data.get(file_digest) == "IGNORE":
            pass
        elif text_digest:
            if all or (trans and trans!="IGNORE"):
                data.setdefault(file_digest,{})[text_digest] = "NOOP" if not trans else "" if trans == "BLANK" else trans
        if i and int(i) % 100 == 99:
            print i
    return data

def import_translation():

    data = get_translated_data()

    for html_file, file_digest, _pth in iter_htmls():
        translations = data.get(file_digest)
        if not translations or translations == "IGNORE":
            continue

        orig = html_file + ".orig"
        if not orig.isfile():
            html_file.copyfile(orig)
            print html_file, "->", orig
        orig_html = open(orig).read()
        translated_html = ""
        cursor = 0
        for orig_text, (st, end), line_no, text_digest in iter_translateables(orig_html):
            translated_html += orig_html[cursor:st]
            translation = translations.get(text_digest)
            chunk = orig_html[st:end]
            translated_html += chunk.replace(orig_text.strip(), translation) if translation else chunk
            cursor = end
        translated_html += orig_html[cursor:]

        with open(html_file, "w") as f:
            f.write(translated_html)
            print "    %s" % len(translations)

RE_CSS_ELEMENTS = re.compile("(?P<rt>right)|"
                             "(?P<lt>left)|"
                             "(?P<pd>\d+\w* \d+\w* \d+\w* \d+\w*)", re.DOTALL)

RE_CSS_BLOCKS = re.compile("{(.*?)}", re.DOTALL)
def _css_converter(match):
    rt, lt, pd = match.groups()
    if rt: return "left"
    if lt: return "right"
    if pd:
        a,b,c,d = pd.split()
        return "%s %s %s %s" % (a, d, c, b)

def flip_css_layout_direction(css_file):
    print css_file
    orig = css_file + ".orig"
    if not orig.isfile():
        css_file.copyfile(orig)
        print css_file, "->", orig
    orig_css = open(orig).read()
    new_css = RE_CSS_BLOCKS.sub(lambda match: RE_CSS_ELEMENTS.sub(_css_converter, match.group(0)), orig_css)
    with open(css_file, "w") as f:
        f.write(new_css)


if __name__ == '__main__':
    arg = sys.argv[1]
    if arg.endswith(".css"):
        flip_css_layout_direction(path(arg))
    else:
        if arg == "import":
            import_translation()
        elif arg == "export":
            extract_for_translation()



#===============================================================================
# 
#===============================================================================

def get_soup(html_file):
    with open(html_file) as f:
        html = f.read()

    html = RE_TEMPLATE.sub(simple_escape, html)
    return BeautifulStoneSoup(html)

def iter_translateables_soup(soup):
    for tag in soup.findAll(text=True):
        if tag.parent.name in NON_TEXT:
            continue
        parents = list(reversed([t.name for t in tag.parentGenerator() if t][:-1]))
        if "script" in parents:
            continue
        parents = ".".join(parents)
        for i, line in enumerate(tag.string.splitlines()):
            nice_text = line.strip()
            if not is_translateable(nice_text):
                continue
            digest = hashlib.md5(nice_text).hexdigest()[:DIGEST_LEN]
            yield (tag, i), "%s[%s]"%(parents, i), digest, nice_text

    for tag in soup.findAll(attrs=dict(placeholder=True)):
        placeholder = tag.attrMap['placeholder']
        parents = ".".join(reversed([t.name for t in tag.parentGenerator() if t][:-1]))
        digest = hashlib.md5(placeholder).hexdigest()[:DIGEST_LEN]
        yield (tag, 'placeholder'), "%s[placeholder]" % parents, digest, placeholder

    