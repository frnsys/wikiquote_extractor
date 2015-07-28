Extracts quotes and attributions from a WikiQuote dump.

WikiQuote dumps are [available here](https://dumps.wikimedia.org/enwikiquote/latest/).

Download the [`pages-articles` dump](https://dumps.wikimedia.org/enwikiquote/latest/enwikiquote-latest-pages-articles.xml.bz2), extract, then run the script:

    $ python main.py /path/to/wikiquotedump.xml

This is far from perfect; it probably does not grab _every_ quote, nor does it get the right attribution 100% of the time. It may fail to clean up some MediaWiki markup as well, though it seems to get most of it.