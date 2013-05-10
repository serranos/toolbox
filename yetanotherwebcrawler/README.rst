Introduction
============

Description
-----------

The `yetanotherwebcrawler` (YAWC) is a module that enables the creation of a web crawling infrastructure.

Two main entities exist: URL, Link. Although a Link is also defined as a Uniform Resource Locator (URL), in this context they are distinct entities.

* URL: represents a webpage and is the main entity of the crawler. A URL can have several links in it.
* Link: a link only exists associated with a URL.

Sequence:

1. Starts operation given a specific URL, parses its content to get links and to take a snapshot of it. Finally adds the links as URLs to be crawled;
2. Get a new URL from the PROCESSING queue;
3. If a valid URL is not found get a URL from the TODO queue;
4. If a valid URL is not found get a URL from the DONE queue;
5. If still no valid URL is found, wait a predefined time before another round.

The crawler does not download the content itself, it simply performs a hash of it. The rationale behind this is to make it faster and to reduce the storage requirements.

Considering the size of the Internet, crawlers have different strategies to identify which URLs to crawl first. Sometimes this is done by defining a value for the depth till which the crawler will follow URLs. Although this is possible with the current database schema defined, in this prototype I chose a different approach and what the user can do is define a filter that ensures only URLs with that suffix are crawled.


To allow immediate testing it is possible to run the file as a script (see `Usage`_).

Database
--------

This prototype uses a `SQLite <http://www.sqlite.org/>`_ database and to get a better understanding of the nits and grits of the data in it, a command line client is advised.

Table: urls
^^^^^^^^^^^

.. data:: id

    An autoincremented integer to serve as unique identifier of a URL record.

.. data:: url

    The URL value in its canonical form, unique in the database.

.. data:: status

    Describes if a URL is being crawled, ready to be crawled or already crawled. Possible values are: PROCESSING, TODO and DONE.

.. data:: digest

    A SHA512 digest of the webpage content, allowing to detect if it was changed since the last crawling. This can be useful to include in the crawling algorithm (e.g. fast changing webpages may have lower priority for being crawled).

.. data:: created

    Timestamp of the creation time of the URL record.

.. data:: updated

    Timestamp of the update time of the URL record. A URL is updated only when it is being crawled, i.e., when :data:`status`

Table: links
^^^^^^^^^^^^

.. data:: url_id

    The :data:`id` of the URL (webpage) where this link was found.

.. data:: link

    The link value, compliant with the URL canonical form.


Installation
------------

To install ``yetanotherwebcrawler.py`` script dependencies, change to the directory where the source code was extracted and execute:

    ::

        $ pip install -r requirements

Dependencies
------------

* `Requests: HTTP for Humans <http://docs.python-requests.org/en/latest/>`_
* `lxml - XML and HTML with Python <http://lxml.de/>`_

Usage
-----

Simply run the :file:`yetanotherwebcrawler.py` script with the `-h` flag set:

    ::

        $ ./yetanotherwebcrawler.py [-h] [-u <URL> [-f <filter hostname>]] [-g <URL>] [-a] [-d <level>]

        Options:

            -h, --help
            Show this help message and exit

            -u <URL>, --url=<URL>
            First URL to begin the crawling operation

            -f <filter hostname>, --filter-hostname=<filter hostname>
            Only crawl URLs from the hierarchy of a specific hostname.

            -g <URL>, --get-url=<URL>
            Get specific URL record from the database

            -a, --all
            Get all URLs records from the database

            -d, --debug <level>
            Filter out log messages with priority below level.
            Level may be: FATAL, ERROR, WARNING, NOTE, INFO, DEBUG.


To stop the script press CTRL+C.

Examples
--------

Start crawling from a specific URL (e.g. `Example website <http://example.org/>`_) without a specific end condition:

    ::

        $ ./yetanotherwebcrawler.py -u http://example.org/

Start crawling from a specific URL (e.g. `Example website <http://example.org/>`_) but limit the webpages to a specific hostname suffix (e.g. example.org):

    ::

        $ ./yetanotherwebcrawler.py -u http://example.org/ -f example.org

Restart crawling from a previously interrupted crawling operation:

    ::

        $ ./yetanotherwebcrawler.py

Get details of a specific URL from the database:

    ::

        $ ./yetanotherwebcrawler.py -g http://example.org/

Get all URLs from the database:

    ::

        $ ./yetanotherwebcrawler.py -a

TODO
----

**In no particular order of importance**

* Get more information from the data collected to define a better URL scheduling algorithm. For example: number of URLs with the same digest; URLs with the biggest number of URLs in its webpage; URLs (in particular the hostname part) most referenced by others; parse all the content of the webpages and use natural language analysis techniques to better characterize the relationships between webpages;
* Consider resource exhaustion constraints, whether at the source or at the destination of the crawling operations, avoiding being disruptive to the web and increasing crawling efficiency;
* Develop the "crawl to a certain depth" feature. This is simple, considering I already have the Links associated to the URL in the database, and their relationship;
* Reduce the connection timeout of the requests so that the crawler can be faster to understand broken Links, even create a different process to check for broken links in the database;
* Parse the existing URLs and get each segment of its path in order to reach certain URLs that may not be explicitly referenced by others. This algorithm is also known as the `path ascending algorithm <http://en.wikipedia.org/wiki/Web_crawler#Path-ascending_crawling>`;
* Provide the possibility to actually download a website, specifying what kind of content to download (e.g. images, stylesheets);
* Enable crawling using other operations (e.g. POST) and add support for AJAX requests;
* Allow crawling other types of schemes (e.g. FTP);
* Solutions for database bottleneck;
* Create a simple process to couple other storage solutions;
* Create a plugin funcionality making it easy to add new crawling algorithms;
* Enable multi-threading.
