"""
Extracts quotes and attributions from a WikiQuote dump.

Not perfect - it misses things and doesn't properly clean up everything,
but seems to catch the bulk of it.
"""

import re
import sys
import json
from lxml import etree

NAMESPACE = 'http://www.mediawiki.org/xml/export-0.10/'

# Identify quotes as beginning with *
QUOTE_RE = re.compile(r'^\*[^*]')
QUOTE_CLEAN_RE = re.compile(r'^\*[\s]?')

# Identify attributions as beginning with **
ATTR_RE = re.compile(r'^\*\*[\s]?')

# Sometimes a work will be listed,
# and all following quotes will be from that work
# The work is usually presented '=== WORK TITLE ==='
CONTEXT_RE = re.compile(r'={3}\s?(.+)\s?={3}')

# [[w:Rush Rhees|Rush Rhees]]
LINK_RE = re.compile(r'\[\[[^|\]]+\|([^\]]+)\]\]')

# [[strength]]
SIMPLE_LINK_RE = re.compile(r'\[\[([^\]]+)]\]')

# [http://movies.nytimes.com/movie/review?_r=1&res=9A00E0DA103BF934A25754C0A965948260&oref=slogin ''The New York Times'' (17 July 1983)]
URL_RE = re.compile(r'\[http:[^\s]+\s([^\]]+)\]')

# [http://www.mg.co.za/articlePage.aspx?articleid=294756&area=/breaking_news/breaking_news__international_news/]
SIMPLE_URL_RE = re.compile(r'\[http:[^\s]+\]')

# <!-- most likely 17th April -->
COMMENT_RE = re.compile(r'<!--[^-]+-->')

# {{gutenberg author|id=Archimedes|name=Archimedes}}
CITE_RE = re.compile(r'{{[^\}]+}}')


def _clean_markup(text):
    """
    Clean up MediaWiki markup and other things.
    """
    for m in LINK_RE.finditer(text):
        text = text.replace(m.group(0), m.group(1))
    for m in SIMPLE_LINK_RE.finditer(text):
        text = text.replace(m.group(0), m.group(1))
    for m in URL_RE.finditer(text):
        text = text.replace(m.group(0), m.group(1))
    text = SIMPLE_URL_RE.sub('', text)
    text = COMMENT_RE.sub('', text)
    text = text.replace("''", '')
    return text.strip()


def _find(elem, *tags):
        """
        Finds a particular subelement of an element.

        Args:
            | elem (lxml Element)  -- the MediaWiki text to cleanup.
            | *tags (strs)      -- the tag names to use. See below for clarification.

        Returns:
            | lxml Element -- the target element.

        You need to provide the tags that lead to it.
        For example, the `text` element is contained
        in the `revision` element, so this method would
        be used like so::

            _find(elem, 'revision', 'text')

        This method is meant to replace chaining calls
        like this::

            text_el = elem.find('{%s}revision' % NAMESPACE).find('{%s}text' % NAMESPACE)
        """
        for tag in tags:
            elem = elem.find('{%s}%s' % (NAMESPACE, tag))
        return elem


def process_element(elem):
    ns = int(_find(elem, 'ns').text)
    if ns != 0: return

    # Get the text of the page.
    text = _find(elem, 'revision', 'text').text
    text = CITE_RE.sub('', text)

    # Extract quotes
    quotes = []
    active_context = ''
    active_quote = {
        'body': []
    }
    for line in text.split('\n'):
        if CONTEXT_RE.match(line) is not None:
            match = CONTEXT_RE.match(line)
            active_context = _clean_markup(match.group(1)).strip('= ')
            active_quote['context'] = active_context

        if QUOTE_RE.match(line) is not None:
            active_quote['body'].append(
                _clean_markup(QUOTE_CLEAN_RE.sub('', line))
            )

        # Dialogue
        if line.startswith(':'):
            active_quote['body'].append(_clean_markup(line[1:]))

        if line.startswith('**'):
            active_quote['attr'] = _clean_markup(ATTR_RE.sub('', line))

        if not line:
            if active_quote['body']:
                quotes.append(active_quote)
                active_quote = {'body': [], 'context': active_context}

    title = _find(elem, 'title').text

    # Uncomment to see what pages are being missed
    #if not quotes:
        #print(text)

    return {
        'title': _clean_markup(title),
        'quotes': quotes
    }


def extract(file):
    """
    Parses a wiki pages-articles XML dump,
    """
    # Create the iterparse context
    context = etree.iterparse(file, events=('end',), tag='{%s}%s' % (NAMESPACE, 'page'))
    results = []

    # Iterate
    for event, elem in context:
        # Run process_element on the element.
        data = process_element(elem)
        if data is not None:
            results.append(data)

        # Uncomment to peek into what's being found
        #print(json.dumps(data, sort_keys=True, indent=4))

        # Clear the elem, since we're done with it
        elem.clear()

        # Eliminate now-empty refs from the root node
        # to the specified tag.
        while elem.getprevious() is not None:
            del elem.getparent()[0]

    # Clean up the context
    del context

    return results


if __name__ == '__main__':
    path = sys.argv[1]
    pages = extract(path)
    print(len(pages), 'pages')

    quotes = []
    for page in pages:
        title = page['title']
        for q in page['quotes']:
            attr = title
            if 'context' in q and q['context']:
                attr = attr + ', ' + q['context']
            if 'attr' in q and q['attr']:
                attr = attr + ', ' + q['attr']
            quote = {
                'body': '\n'.join(q['body']),
                'attr': attr
            }
            quotes.append(quote)


    print(len(quotes), 'quotes')
    with open('quotes.json', 'w') as f:
        json.dump(quotes, f)