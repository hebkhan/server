import re
import sys
from path3 import path


RE_CSS_ELEMENTS = re.compile("(?P<rt>right)|"
                             "(?P<lt>left)|"
                             "(?P<pd>-?\d+\S* -?\d+\S* -?\d+\S* -?\d+\S*)(;)"
                             ,re.DOTALL)

RE_CSS_BLOCKS = re.compile("{(.*?)}", re.DOTALL)
def _css_converter(match):
    rt, lt, pd, e = match.groups()
    if rt: return "left"
    if lt: return "right"
    if pd:
        a,b,c,d = pd.split()
        return "%s %s %s %s%s" % (a, d, c, b, e)

def flip_css_layout_direction(css_file):
    print css_file
    orig = css_file + ".orig"
    if not orig.isfile():
        css_file.copyfile(orig)
        print css_file, "->", orig
    orig_css = open(orig).read()
    process_block = lambda match: RE_CSS_ELEMENTS.sub(_css_converter, match.group(0))
    new_css = RE_CSS_BLOCKS.sub(process_block, orig_css)
    with open(css_file, "w") as f:
        f.write(new_css)

if __name__ == "__main__":
    for f in sys.argv[1:]:
        flip_css_layout_direction(path(f))
