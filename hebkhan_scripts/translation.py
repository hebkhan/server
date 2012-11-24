'''
Created on Nov 4, 2012

@author: oferko
'''

from path3 import path
import re
import hashlib
import urllib2
import csv
import itertools
import sys
import ast

APP_ROOT = path(__file__).parent.parent

class TranslatableFile(object):
    HEADER = ""

    def __init__(self, f):
        self.relative_path = APP_ROOT.relpathto(f)
        self.file_digest = hashlib.md5(self.relative_path).hexdigest()[:DIGEST_LEN]
        check_collision(self.file_digest)
        self.path = f
        self.orig = f + ".orig"
        source = self.orig if self.orig.isfile() else f
        with open(source) as opened:
            self.text = opened.read()
    def __repr__(self):
        return "%s(%s - %s)" % (self.__class__.__name__, self.file_digest, self.relative_path)

    def preprocess(self, translation):
        return translation

    def translate(self, translations):
        if not self.orig.isfile():
            with open(self.orig, "w") as f:
                f.write(self.text)
            print self.relative_path, "->", self.orig
        translated_text = self.HEADER
        cursor = 0
        for orig_text, (st, end), line_no, text_digest in self.iter_translatables():
            translated_text += self.text[cursor:st]
            translation = self.preprocess(translations.get(text_digest))
            chunk = self.text[st:end]
            translated_text += chunk.replace(orig_text.strip(), translation) if translation is not None else chunk
            cursor = end
        translated_text += self.text[cursor:]

        with open(self.path, "w") as f:
            f.write(translated_text)
            print "%s: %s" % (self.path, len(translations))

    @classmethod
    def get_files(cls):
        for f in cls._get_files():
            yield cls(f)

class TranslatablePython(TranslatableFile, ast.NodeVisitor):
    HEADER = "# coding=utf8\n\n"
    @classmethod
    def _get_files(cls):
        for tmpl in (APP_ROOT + "/badges").walkfiles("*badge*.py"):
            yield tmpl

    def iter_translatables(self):
        self.lines = self.text.splitlines()
        self.line_breaks = [None,0] + [m.start() for m in RE_LINEBREAK.finditer(self.text+"\n")]
        self.strings = []
        tree = ast.parse(self.text, self.relative_path)
        self.visit(tree)
        for line_no, span, string in self.strings:
            line = self.lines[line_no-1]
            nice_text = line[line.find(string)-1:].strip()
            if len(set(nice_text.replace(string, ""))) == 1:
                # there's nothing but quotes around our string
                nice_text = string
            line = line.strip()
            if not (line.startswith("return") or "self.description" in line):
                continue
            digest = hashlib.md5(nice_text).hexdigest()[:DIGEST_LEN]
            yield nice_text, span, line_no, digest

    def preprocess(self, translation):
        if not translation:
            return
        return ("u" + translation
                if translation.startswith("\"")
                else ('"+u"%s' % translation)
                )

    def visit_Str(self, node):
        if node.s:
            st = self.line_breaks[node.lineno] + node.col_offset
            end = self.line_breaks[node.lineno+1]
            self.strings.append((node.lineno, (st, end), node.s))


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

class TranslatableHTML(TranslatableFile):

    @classmethod
    def _get_files(cls):
        for tmpl in (APP_ROOT + "/templates").walkfiles("*.html"):
            yield tmpl

        yield APP_ROOT + "/khan-exercises/exercises/khan-exercise.html"

        for tmpl in (APP_ROOT + "/clienttemplates").walkfiles("*.handlebars"):
            yield tmpl

    def iter_translatables(self):
        html = self.text
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


def iter_files():
    return itertools.chain(
                           TranslatableHTML.get_files(),
                           TranslatablePython.get_files(),
                           )

def extract_for_translation():
    data = get_translated_data(all=True)

    counter = lambda counter=itertools.count(1): str(next(counter))
    new_items = []
    with open("extracted_text3.tab","w") as output:
        print >>output, "\t".join("id,file digest,line no,text digest,text,translation".split(","))
        for f in iter_files():
            translations = data.get(f.file_digest) or {}
            if translations == "IGNORE":
                print "SKIPPING:", f
                print >>output, "%s\t'%s\t%s\t%s\t%s\tIGNORE" % (counter(), f.file_digest, "", "", f.relative_path)
                print >>output, counter()
                continue

            lines = []
            for text, _, line_no, text_digest in f.iter_translatables():
                translation = translations.get(text_digest, "")
                if translation == "NOOP":
                    translation = ""
                lines.append(("'"+f.file_digest, "#%s" % line_no, "'"+text_digest, "'%s" % text, "'%s" % translation))
                if text_digest not in translations:
                    new_items.append(lines[-1])

            if lines:
                print >>output, "\t".join((counter(), "'" + f.file_digest, "", "", f.relative_path))
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
    c = 0
    for i, file_digest, _tag, text_digest, _orig, trans in lines:
        c+=1
        if file_digest and not text_digest and trans=="IGNORE": # ignore entire file
            data[file_digest] = "IGNORE"
        if data.get(file_digest) == "IGNORE":
            pass
        elif text_digest:
            if all or (trans and trans!="IGNORE"):
                data.setdefault(file_digest,{})[text_digest] = "NOOP" if not trans else "" if trans == "BLANK" else trans
        if i == "Version":
            print "VERSION =", file_digest
        elif i and int(i) % 100 == 99:
            print ".",
    print "Read %s lines" % c
    return data

def import_translation():

    data = get_translated_data()

    for f in iter_files():
        translations = data.get(f.file_digest)
        if not translations or translations == "IGNORE":
            continue
        f.translate(translations)



