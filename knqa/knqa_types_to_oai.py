#!/usr/bin/env python3
"""Keep the OAI-PMH (oai_openaire) export in step with the KNQA document-type vocabulary.

Reads   dspace/config/controlled-vocabularies/knqa_types.xml   (the source of truth)
Writes  the "KNQA types" block in dspace/config/crosswalks/oai/metadataFormats/oai_openaire.xsl

Each selectable type carries <hasNote>COAR: <coar type></hasNote>, where <coar type> is a type the
stock crosswalk already maps (e.g. "report", "text", "technical documentation", "research report").
The script maps every KNQA label to that type's COAR URI, and to OpenAIRE's resourceTypeGeneral
("literature" for textual types, "dataset" for datasets). "COAR: other" uses the crosswalk default.

Run from the repository root after editing the vocabulary:
    python3 knqa/knqa_types_to_oai.py           # rewrite the block
    python3 knqa/knqa_types_to_oai.py --check   # exit 1 if the block is out of date
"""
import re
import sys
import xml.etree.ElementTree as ET

VOCAB = 'dspace/config/controlled-vocabularies/knqa_types.xml'
XSL = 'dspace/config/crosswalks/oai/metadataFormats/oai_openaire.xsl'
START = '            <!-- KNQA types (generated from controlled-vocabularies/knqa_types.xml; see KNQA_CONFIG.md) -->\n'
END = '            <!-- end KNQA types -->\n'
BLOCK_RE = re.compile(re.escape(START) + '.*?' + re.escape(END), re.S)
LITERATURE = {'technical documentation', 'report', 'text', 'research report', 'policy report', 'working paper',
              'research proposal', 'journal article', 'book', 'book part', 'conference paper',
              'conference proceedings', 'thesis', 'periodical', 'other type of report', 'internal report'}
GENERAL = {'dataset': 'dataset'}


def types():
    out = []
    for node in ET.parse(VOCAB).getroot().iter('node'):
        if node.get('selectable', 'true').lower() == 'false':
            continue
        note = (node.findtext('hasNote') or '').strip()
        if not note.startswith('COAR:'):
            sys.exit(f'{VOCAB}: type "{node.get("label")}" needs <hasNote>COAR: ...</hasNote>')
        out.append((node.get('label'), note[5:].strip().lower()))
    labels = [label.lower() for label, _ in out]
    dupes = {x for x in labels if labels.count(x) > 1}
    if dupes:
        sys.exit(f'{VOCAB}: duplicate type labels: {", ".join(sorted(dupes))}')
    return out


def template(xsl, name):
    a = xsl.index(f'<xsl:template name="{name}">')
    return a, xsl.index('</xsl:template>', a)


def stock_map(xsl, name):
    a, b = template(xsl, name)
    seg = BLOCK_RE.sub('', xsl[a:b])
    return dict(re.findall(r"\$lc_dc_type = '([^']+)'\">\s*<xsl:text>([^<]+)</xsl:text>", seg))


def clause(lc, value):
    lc = lc.replace("'", '&apos;')
    return (f"            <xsl:when test=\"$lc_dc_type = '{lc}'\">\n"
            f"                <xsl:text>{value}</xsl:text>\n"
            f"            </xsl:when>\n")


def with_block(xsl, name, clauses):
    a, b = template(xsl, name)
    seg = BLOCK_RE.sub('', xsl[a:b])
    i = seg.rindex('<xsl:otherwise>')
    i = seg.rindex('\n', 0, i) + 1
    prev = seg.rfind('\n', 0, i - 1) + 1
    if seg[prev:i].strip() == '<!-- other -->':
        i = prev
    return xsl[:a] + seg[:i] + START + ''.join(clauses) + END + seg[i:] + xsl[b:]


def main():
    raw = open(XSL, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in raw else '\n'
    xsl = raw.replace('\r\n', '\n')
    uri_of = stock_map(xsl, 'resolveResourceTypeURI')
    general_of = stock_map(xsl, 'resolveResourceTypeGeneral')
    uri_block, gen_block = [], []
    for label, coar in types():
        lc = label.lower()
        if coar == 'other':
            continue
        if coar not in uri_of:
            sys.exit(f'"{label}": COAR type "{coar}" is not mapped in {XSL}; pick one that is')
        if lc not in uri_of:
            uri_block.append(clause(lc, uri_of[coar]))
        general = GENERAL.get(coar) or ('literature' if coar in LITERATURE else None)
        if general and lc not in general_of:
            gen_block.append(clause(lc, general))
    new = with_block(xsl, 'resolveResourceTypeGeneral', gen_block)
    new = with_block(new, 'resolveResourceTypeURI', uri_block)
    if '--check' in sys.argv:
        if new != xsl:
            sys.exit(f'{XSL} is out of date: run python3 knqa/knqa_types_to_oai.py')
        print('OAI crosswalk is up to date')
        return
    open(XSL, 'w', encoding='utf-8', newline='').write(new.replace('\n', nl))
    print(f'{XSL}: {len(uri_block)} URI and {len(gen_block)} resourceTypeGeneral mappings')


if __name__ == '__main__':
    main()
