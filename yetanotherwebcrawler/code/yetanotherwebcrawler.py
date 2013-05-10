#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""A simple crawler that wishes to crawl where no crawler has crawled before.

If no URL is provided, the crawler will check for previously started crawling operations.
Simple `show` operations are also available, if more detailed access is required one must
access the database directly.

Usage: yetanotherwebcrawler.py [-h] [-u <URL> [-f <filter hostname>]] [-g <URL>] [-a] [-d <level>]

Options:

    -h, --help
    Show this help message and exit

    -u <URL>, --url=<URL>
    First URL to begin the crawling operation

    -f <filter hostname>, --filter-hostname=<filter hostname>
    Only crawl URLs from the hierarchy of a specific hostname

    -g <URL>, --get-url=<URL>
    Get specific URL record from the database

    -a, --all
    Get all URLs records from the database

    -d, --debug <level>
    Filter out log messages with priority below level.
    Level may be: DEBUG, INFO, WARNING, ERROR, CRITICAL
"""

__author__ = "Serrano M."
__author_email__ = "serrano.miser[at]gmail.com"
__license__ = "GPLv3"
__version__ = "0.1"

import os
import sys
import getopt
import sqlite3
import requests
from urlparse import urlparse
import datetime
import time
from lxml import etree
import hashlib
from settings import *
import pdb


class Usage(Exception):
    """The rules for the script inputs are not being respected."""
    def __init__(self, msg):
        self.msg = msg


class YetAnotherWebCrawlerException(Exception):
    """An Exception related to the Crawler."""
    pass


class YetAnotherWebCrawler():
    """
    The main entry to the crawling infrastructure

    :param url: The current URL being processed.
    :type url: :class:`str`

    :param db_hdl: The database handler.
    :type db_hdl: class:`sqlite3.Connection`

    :param url_digest: The URL webpage content digest.
    :type url_digest: class:`str`
    """

    def __init__(self, db_hdl, url=None):
        self.url = url
        self.db_hdl = db_hdl
        self.url_digest = None
        with db_hdl:
            self.db_cur = db_hdl.cursor()

    def url_valid_by_sufix(self, url, filter_hostname):
        """
        Check if a URL has a specific sufix.

        :param url: The URL to filter.
        :type url: :class:`str`

        :param filter_hostname: The filter to be applied to the network location part of the URL.
        :type filter_hostname: :class:`str`

        :returns :class:`bool` -- True if URL has a specific sufix.
        """

        logger = logging.getLogger('url_valid_by_sufix')

        if not url:
            return False

        url_struct = urlparse(url)
        if filter_hostname and not url_struct.netloc.endswith(filter_hostname):
            logger.debug('URL {} - not allowed by filter.'.format(url.encode('utf8')))
            return False
        else:
            logger.debug('URL {} - allowed by filter.'.format(url.encode('utf8')))
            return True

    def prepare_url(self, url, parent_url=None, filter_hostname=None):
        """
        Prepare a URL to its canonical format.

        :param url: The URL to prepare.
        :type url: :class:`str`

        :param parent_url: The main webpage URL, used to canonicalize URLs if they are absolut (Default is None).
        :type parent_url: :class:`str`

        :param filter_hostname: The filter to be applied to the network location part of the URL (Default is None).
        :type filter_hostname: :class:`str`

        :returns :class:`str` -- The URL in canonical format or None if not possible.
        """

        logger = logging.getLogger('prepare_url')
        try:
            url_struct = urlparse(url)
            # If a URL scheme does not exist prefix it with the main URL
            if url_struct.scheme and url_struct.scheme in ALLOWED_URL_SCHEMES and url_struct.netloc:
                if not self.url_valid_by_sufix(url, filter_hostname):
                    return None
                url = '{}://{}'.format(url_struct.scheme, url_struct.netloc.encode('utf8'))
            # If the URL is absolut than create a new one based on the webpage URL
            elif not url_struct.scheme:
                if not parent_url:
                    return None
                else:
                    parent_url_struct = urlparse(parent_url)
                    url = '{}://{}'.format(parent_url_struct.scheme, parent_url_struct.netloc.encode('utf8'))
                    if not self.url_valid_by_sufix(parent_url, filter_hostname):
                        return None
            # If none of the above conditions are true it means the URL is invalid
            else:
                return None

            # Start creating the rest of the URL (i.e. add path;params?query_string)
            if url_struct.path:
                if url_struct.path[0] == '/':
                    url = '{}{}'.format(url, url_struct.path.encode('utf8'))
                else:
                    url = '{}/{}'.format(url, url_struct.path.encode('utf8'))
            else:
                url = '{}/'.format(url, url_struct.path.encode('utf8'))
            if url_struct.params:
                url = '{};{}'.format(url, url_struct.params.encode('utf8'))
            if url_struct.query:
                url = '{}?{}'.format(url, url_struct.query.encode('utf8'))

            logger.debug('URL {} - prepared.'.format(url))

        except AttributeError, err:
            logger.debug('URL {} - preparation error.'.format(err))
            url = None

        return url

    def parse_content(self, url):
        """
        Parse a webpage and create a list of URLs found in it.

        :param url: The webpage URL.
        :type url: :class:`str`

        :returns: :class:`list` -- A list of URLs (an empty list if none are found).
        """

        logger = logging.getLogger('parse_content')
        try:
            url_list = []
            tree = None
            logger.debug("URL {} - requesting.".format(url))
            webpage = requests.get(url, headers=CRAWLER_USER_AGENT)
            # Parse the webpage
            try:
                tree = etree.HTML(webpage.text)
                self.url_digest = hashlib.sha512(webpage.text.encode('utf-8')).hexdigest()
            except ValueError, err:
                logger.debug('URL {} - Error parsing webpage - {}'.format(url, err))
            except etree.XMLSyntaxError, err:
                logger.debug('URL {} - Error parsing webpage - {}'.format(url, err))
            # Search for URLs
            if tree is not None:
                url_list = tree.xpath('//a/@href') + tree.xpath('//link/@href')
        except requests.ConnectionError, err:
            # This means the webserver may not be responding or does not exist
            # Usually this is due to broken links or network problems
            logger.debug('ConnectionError {} for URL {}'.format(err, url))

        return url_list

    def add_url_to_db(self, url, status=URL_STATUS_TODO):
        """
        Add a URL to the database.

        :param url: The URL to add.
        :type url: :class:`str`

        :param status: The URL Status.
        :type status: :class:`int`
        """

        logger = logging.getLogger('add_url_to_db')
        now = convert_timestamp(datetime.datetime.now())
        try:
            # Add the URL record to the database and rollback if an error occurs.
            # Prepared statements are used to avoid SQL injection vulnerabilities.
            with self.db_hdl:
                self.db_cur.execute('INSERT INTO urls(url, status, created, updated) VALUES (?, ?, ?, ?)', (url.decode('utf8'), status, now, now))
            logger.debug('URL {} added to the database.'.format(url))
        except sqlite3.IntegrityError, err:
            try:
                # Update the URL record in the database and rollback if an error occurs.
                # Prepared statements are used to avoid SQL injection vulnerabilities.
                with self.db_hdl:
                    self.db_cur.execute('UPDATE urls SET status=?, updated=? WHERE url=?', (status, now, url.decode('utf8')))
                logger.debug('URL {} updated in the database.'.format(url))
            except sqlite3.IntegrityError, err:
                # An error ocurred and rollback is done
                logger.debug('URL {} - could not be updated! {}'.format(url, err))

    def add_link_to_url(self, parent_url, link):
        """
        Add a link to a URL webpage in the database.

        Links are in essence a URL but with no context and associated with a webpage (identified by a URL).
        This entity allows us to know which places in the Internet are referenced.

        :param parent_url: The parent URL.
        :type parent_url: :class:`str`

        :param link: The link to add to the URL.
        :type link: :class:`str`
        """
        logger = logging.getLogger('add_link_to_url')
        if link and parent_url:
            try:
                # Add the record to the database and rollback if an error occurs
                # Prepared statements are used to avoid SQL injection vulnerabilities
                with self.db_hdl:
                    parent_url_record = self.get_url_from_db(parent_url)
                    if parent_url_record:
                        parent_url_id = parent_url_record[0]
                        if not self.get_link_from_db(parent_url_id, link):
                            self.db_cur.execute('INSERT INTO links(url_id, link) VALUES (?, ?)', (parent_url_id, link.decode('utf8')))
                logger.debug('Link {} added to the database.'.format(link))
            except sqlite3.IntegrityError, err:
                # An error ocurred and rollback is done
                logger.debug('Link {} - could not be added! {}'.format(link, err))

    def set_url_details_in_db(self, url, digest, status=URL_STATUS_DONE):
        """
        Set the current URL details in the database.

        :param url: The URL to set.
        :type url: :class:`str`

        :param status: The URL status.
        :type status: :class:`int`

        :param url_digest: The URL webpage content digest. Useful to detect changes between crawling cicles.
        :type url_digest: class:`str`
        """

        logger = logging.getLogger('do_url')
        if status == URL_STATUS_DONE:
            logger.info("URL {} - processing done!".format(url))
        elif status == URL_STATUS_TODO:
            logger.debug("URL {} - to be done!".format(url))
        elif status == URL_STATUS_PROCESSING:
            logger.info("URL {} - being processed!".format(url))
        now = convert_timestamp(datetime.datetime.now())
        try:
            # Change the status of the URL in the database to state its processing is complete
            # Prepared statements are used to avoid SQL injection vulnerabilities
            with self.db_hdl:
                if digest:
                    self.db_cur.execute('UPDATE urls SET digest=?, status=?, updated=? WHERE url=?', (digest, status, now, url))
                else:
                    self.db_cur.execute('UPDATE urls SET status=?, updated=? WHERE url=?', (status, now, url))
        except sqlite3.IntegrityError:
            # An error ocurred and rollback is done
            logger.debug("URL {} - could not be updated!".format(url))

    def get_link_from_db(self, url_id, link):
        """
        Get the link record from the database.

        :param url_id: The parent URL identifier.
        :type url_id: :class:`int`

        :param link: The link to search in the database.
        :type link: :class:`str`

        :returns: :class:`array` -- The database record of the link specified.
        """

        # Prepared statements are used to avoid SQL injection vulnerabilities
        self.db_cur.execute('SELECT url_id FROM links WHERE url_id=? and link=?', (url_id, link.decode('utf8')))
        return self.db_cur.fetchone()

    def get_url_from_db(self, url):
        """
        Get the URL record from the database.

        :param url: The URL to search in the database.
        :type url: :class:`str`

        :returns: :class:`array` -- The database record of the URL specified.
        """

        # Prepared statements are used to avoid SQL injection vulnerabilities
        self.db_cur.execute('SELECT id, url, status, digest, created, updated FROM urls WHERE url=?', (url.decode('utf8'),))
        return self.db_cur.fetchone()

    def get_all_urls_from_db(self):
        """
        Get all the URLs present in the database.

        :returns: :class:`iterator` -- All the URL fields from the database.
        """

        return self.db_cur.execute('SELECT url FROM urls')

    def get_next_url_from_db(self, filter_hostname=None):
        """
        Get the next URL to be processed from the database.

        The rules to define which URL is next are the following, by priority:
            1. Status = PROCESSING
            2. Status = TODO and more recent
            3. Status = DONE and ((now - updated) < CRAWLER_UPDATE_DELTA)

        :param filter_hostname: The filter to be applied to the network location part of the URL (Default is None).
        :type filter_hostname: :class:`str`

        :returns: :class:`str` -- The next URL to be processed.
        """

        logger = logging.getLogger('get_next_url_from_db')
        next_url = None
        # Get a URL with status STATUS_PROCESSING and a valid hostname suffix
        for next_url in self.db_cur.execute('SELECT url FROM urls WHERE status=?', (URL_STATUS_PROCESSING,)):
            if self.url_valid_by_sufix(next_url[0], filter_hostname):
                next_url = next_url[0]
                break
            else:
                next_url = None

        if next_url is None:
            # Get the oldest URLs with STATUS_TODO and a valid hostname suffix
            for next_url in self.db_cur.execute('SELECT url,updated FROM urls WHERE status=? ORDER BY updated ASC', (URL_STATUS_TODO,)):
                if self.url_valid_by_sufix(next_url[0], filter_hostname):
                    next_url = next_url[0]
                    break
                else:
                    next_url = None

            if next_url is None:
                # Get the oldest URLs with STATUS_DONE, if the delta time defined for the Crawler update has expired and a valid hostname suffix
                now = convert_timestamp(datetime.datetime.now())
                for next_url in self.db_cur.execute('SELECT url,updated FROM urls WHERE status=? ORDER BY updated ASC', (URL_STATUS_DONE,)):
                    if ((now - next_url[1]) > CRAWLER_UPDATE_DELTA) and self.url_valid_by_sufix(next_url[0], filter_hostname):
                        # If the oldest record isn't older than the UPDATE delta parameter skip it
                        next_url = next_url[0]
                        break
                    else:
                        next_url = None

        return next_url

    def set_url(self, url):
        """
        Set the crawler URL attribute.

        This attribute changes for each page content parsing operation.

        :param url: The URL value to set.
        :type url: :class:`str`
        """

        self.url = url

    def set_urls(self, urls, filter_hostname=None):
        """
        Set the crawler URL list attribute.

        Removes duplicates and prepares URL canonical format from a list of URLs.
        This attribute changes for each page content parsing operation.

        :param urls: The list of URLs to set.
        :type urls: :class:`list`

        :param filter_hostname: The filter to be applied to the network location part of the URL (Default is None).
        :type filter_hostname: :class:`str`
        """

        if self.url:
            self.urls = set()
            # Remove duplicates
            uniq_urls = set(urls)
            for url in uniq_urls:
                # Set the URL to its canonical form
                good_url = self.prepare_url(url, self.url, filter_hostname)
                if good_url:
                    # Add the URL in canonical form to the Crawler URL list
                    self.urls.add(good_url)

    def start_crawling(self, url=None, filter_hostname=None):
        """
        Let the crawling begin!

        :param url: The first URL to begin crawling (default None).
        :type url: :class:`str`
        """

        logger = logging.getLogger('start_crawling')

        # If the user didn't give a starting URL we try the database
        if url is None:
            url = self.get_next_url_from_db(filter_hostname)
            if url:
                self.set_url(url)
            elif not self.get_all_urls_from_db().fetchone():
                raise YetAnotherWebCrawlerException("No URLs found in the database - nothing to do!")
        else:
            # Check if the URL is valid
            if self.prepare_url(url, None, filter_hostname):
                self.set_url(url)
                self.add_url_to_db(url, URL_STATUS_PROCESSING)
            else:
                raise YetAnotherWebCrawlerException("URL {} - invalid!")

        # Infinit loop to crawl the web till exhaustion (probably not going to happen...)
        # If no more URLs are found ready to crawl, the Crawler waits for the refresh period to end.
        # When the refresh period ends, the Crawler enables refreshing alerady existing database records.
        while True:
            if self.url is None:
                logger.info('No URLs found in database to crawl, waiting {} seconds...'.format(CRAWLER_REFRESH_PERIOD))
                time.sleep(CRAWLER_REFRESH_PERIOD)
            else:
                url_list = self.parse_content(self.url)
                # Get all URLs from the webpage and add them to the database
                if url_list:
                    self.set_urls(url_list, filter_hostname)
                    for good_url in self.urls:
                        self.add_url_to_db(good_url)
                        self.add_link_to_url(self.url, good_url)
                # The URL was processed - the details can be saved in the database
                self.set_url_details_in_db(self.url, self.url_digest, URL_STATUS_DONE)
            # Get the next available URL to crawl from the database
            url = self.get_next_url_from_db(filter_hostname)
            if url:
                self.set_url(url)
                self.set_url_details_in_db(self.url, None, URL_STATUS_PROCESSING)
            else:
                self.set_url(None)


def convert_timestamp(dt):
    """
    Convert a date and time to a timestamp.

    :param dt: The date and time to be converted.
    :type dt: :class:`datetime`

    :returns: :class:`float` -- The timestamp.
    """
    return time.mktime(dt.timetuple())


def create_schema(db_hdl):
    """
    Create the database schema.

    :param db_hdl: The database handler.
    :type db_hdl: class:`sqlite3.Connection`
    """

    db_hdl.execute('CREATE TABLE urls\
 (id integer primary key autoincrement, url varchar unique, status integer DEFAULT NULL, digest varchar DEFAULT NULL, created long, updated long)')
    db_hdl.execute('CREATE TABLE links (url_id integer key, link varchar DEFAULT NULL)')


def database_exists(db_location):
    """
    Check if database exists.

    Note: in practice I am simply checking for a file, in a real production environment
        this would depend on the database used. However this method could always be used to encapsulate the logic.

    :param db_location: The location of the database.
    :type db_location: :class:`str`

    :returns: :class:`bool` -- True if database exists.
    """

    return os.path.isfile(db_location)


def connect_to_database(db_location):
    """
    Create a connection to the DB.

    If DB does not exist create a new one.
    If a file with the same name already exists but not of sqlite format, an exception is thrown.

    :param db_location: The Location of the database.
    :type db_location: :class:`str`

    :returns: :class:`sqlite3.Connection` -- The handler of a connection to the database.
    """

    db_exists = database_exists(db_location)
    db_hdl = None
    db_hdl = sqlite3.connect(db_location, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)

    # If DB file does not exist we need to create it
    if not db_exists:
        create_schema(db_hdl)

    return db_hdl


def main(argv=None):

    logger = logging.getLogger('MAIN')

    url = None
    get_url = None
    filter_hostname = None
    operation = None
    db_hdl = None

    if argv is None:
        argv = sys.argv
    try:
        try:
            options, args = getopt.getopt(argv[1:], "hu:f:g:ad:", ["help",
                "url=", "filter=", "get=", "all", "debug"])
            for opt, arg in options:
                if opt in ('-h', '--help'):
                    raise Usage(__doc__)
                elif opt in ('-d', '--debug') and arg in LOGGING_LEVEL:
                    # Logger configuration
                    logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', level=arg)
                elif opt in ('-u', '--url'):
                    url = arg
                elif opt in ('-f', '--filter'):
                    filter_hostname = arg
                elif opt in ('-g', '--get'):
                    operation = OPERATION_GET
                    get_url = arg
                elif opt in ('-a', '--all'):
                    operation = OPERATION_ALL

        except getopt.error, err:
            raise Usage(msg)

        try:
            db_hdl = connect_to_database(DB_NAME)
            crawl = YetAnotherWebCrawler(db_hdl)
            if (operation is None and url is None) or (url):
                crawl.start_crawling(url, filter_hostname)
            elif operation == OPERATION_GET and get_url:
                url_record = crawl.get_url_from_db(get_url)
                if url_record is not None:
                    print('<ID> <URL> <STATUS> <DIGEST> <CREATION TIMESTAMP> <UPDATED TIMESTAMP>')
                    status = ''
                    if url_record[2] == URL_STATUS_PROCESSING:
                        status = 'PROCESSING'
                    elif url_record[2] == URL_STATUS_TODO:
                        status = 'TODO'
                    elif url_record[2] == URL_STATUS_DONE:
                        status = 'DONE'
                    print('{} {} {} {} {} {}'.format(url_record[0], url_record[1], status, url_record[3],\
                            datetime.datetime.fromtimestamp(url_record[4]), datetime.datetime.fromtimestamp(url_record[5])))
                else:
                    print('No Database Record was found for URL: {}'.format(get_url))
            elif operation == OPERATION_ALL:
                url_records = crawl.get_all_urls_from_db()
                if url_records is not None:
                    for url in url_records:
                        print('{}'.format(url[0]))
                else:
                    print('No Database Record was found.')

        except sqlite3.Error, e:
            logger.debug('Error connecting to database %s' % e.args[0])
            sys.exit(1)

    except Usage, err:
        print >>sys.stderr, err.msg
        return 2
    except Exception, err:
        logging.error("Caught exception '{}' :: Rolling back.".format(err))
        if db_hdl:
            # An error ocurred and rollback is done to the database (only till the last commit)
            db_hdl.rollback()
    finally:
        # Always(!) close the database connection to ensure no leaks exist
        if db_hdl:
            db_hdl.close()


if __name__ == "__main__":
    sys.exit(main())
