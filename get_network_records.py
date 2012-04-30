#!/usr/bin/env python

"""Tool to search for IP addresses belonging to specific networks

Usage: get_network_records.py [-h] [-s <filename>.csv] [-n <filename>.csv] [-v]

Options:
    -h, --help
    show this help message and exit

    -s <sources>, --sources=<filename>
    CSV file with IP addresses, format is: <source-name>,<source-filename>

    -n <filename>, --networks=<filename>
    CSV file with IP networks, format is: <network-name>,<IP network address>

    -v, --verbose
    increase verbosity level
"""

__author__ = "Serrano <serrano.miser[at]gmail.com>"
__version__ = "0.1"

import ipaddr
import sys
import getopt
import csv

sources = dict()
networks = dict()


class Usage(Exception):
    def __init__(self, msg):
        self.msg = msg


def get_records(sources_file, network_file, verbose):
    try:
        with open(sources_file) as csv_hdl:
            reader = csv.DictReader(csv_hdl)
            for row in reader:
                sources[row['name']] = row['file']
        with open(network_file) as csv_hdl:
            reader = csv.DictReader(csv_hdl)
            for row in reader:
                if row['name'] not in networks.keys():
                    networks[row['name']] = set()
                networks[row['name']].add(row['network'])
    except Exception, e:
        print "problem getting data"
        sys.exit(1)

    for source, sfile in sources.iteritems():
        if verbose:
            print "SOURCE: %s - SOURCE FILE: %s" % (source, sfile)
        for line in open(sfile, 'r'):
            words = line.split()
            if words:
                word_raw = words[0]
                if not word_raw.startswith('#'):
                    try:
                        ip = ipaddr.IPAddress(word_raw)
                        for service, ip_networks in networks.iteritems():
                            for network in ip_networks:
                                if ip in ipaddr.IPNetwork(network):
                                    print ("%s %s") % (service, line)
                                    break
                    except:
                        continue


def main(argv=None):
    verbose = False
    sources_file = ''
    networks_file = ''

    if argv is None:
        argv = sys.argv
    try:
        try:
            options, args = getopt.getopt(argv[1:], "hs:n:v", ["help",
                "sources=", "networks=", "verbose"])
            for opt, arg in options:
                if opt in ('-h', '--help'):
                    raise Usage(__doc__)
                elif opt in ('-s', '--sources'):
                    sources_file = arg
                elif opt in ('-n', '--networks'):
                    networks_file = arg
                elif opt in ('-v', '--verbose'):
                    verbose = True
            if verbose:
                print "OPTIONS: ", options
        except getopt.error, msg:
            raise Usage(msg)

        if sources_file and networks_file:
            get_records(sources_file, networks_file, verbose)
        else:
            raise Usage(__doc__)
            sys.exit()

    except Usage, err:
        print >>sys.stderr, err.msg
        return 2

if __name__ == "__main__":
    sys.exit(main())
