#!/usr/bin/env python

# Distributed under the GPLv2 License; see accompanying file COPYING.

from __future__ import print_function

import sys
import os
import os.path
import time
import argparse

from dumco.xml.parser import XmlLoader
from dumco.xml.xsd.element_factory import XsdElementFactory
from dumco.xml.xsd.dump_xsd import dump_xsd
import dumco.schema.fb2_namer
import dumco.schema.oxml_namer

def process_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('--version', action='version',
                        version='%(prog)s version 3.0')

    parser.add_argument('-s', '--input-syntax', choices=['xsd', 'rng', 'rnc'],
                        default='xsd', help='assume input schema files use '
                        'one of 3 supported serializations '
                        '{default: %(default)s}')
    parser.add_argument('-n', '--element-namer', choices=['oxml', 'fb2'],
                        default='oxml', help='name anonymous schema entities '
                        'according to 1 of predefined policies '
                        '{default: %(default)s}')
    parser.add_argument('-i', '--input-dir', required=True,
                        help='directory with schema files')

    subparsers = parser.add_subparsers(dest='mode',
                                       help='generation modes')

    parser_dumpxsd = subparsers.add_parser(
        'dumpxsd', help='dump XSD serialization of schema files')
    parser_dumpxsd.add_argument('-o', '--output-dir', required=True,
                                help='output directory')

    parser_rfilter = subparsers.add_parser(
        'rfilter', help='generate read-only filter for schema files')

    parser_dom = subparsers.add_parser(
        'dom', help='generate DOM corresponding to schema files')

    args = parser.parse_args()
    return args

if __name__ == '__main__':
    start_time = time.time()

    # Change to script's directory.
    os.chdir(os.path.dirname(os.path.realpath(sys.argv[0])))

    args = process_arguments()

    if args.element_namer == 'oxml':
        namer = dumco.schema.oxml_namer.OxmlNamer()
    elif args.element_namer == 'fb2':
        namer = dumco.schema.fb2_namer.Fb2Namer()

    if args.input_syntax == 'xsd':
        factory = XsdElementFactory(namer)
    elif args.input_syntax == 'rng':
        assert False, 'Not implemented'
    elif args.input_syntax == 'rnc':
        assert False, 'Not implemented'

    if args.input_syntax == 'xsd' or args.input_syntax == 'rng':
        loader = XmlLoader(factory)
    elif args.input_syntax == 'rnc':
        assert False, 'Not implemented'

    all_schemata = loader.load_xml(args.input_dir)

    if args.mode == 'dumpxsd':
        dump_xsd(all_schemata, args.output_dir)
    elif args.mode == 'rfilter':
        assert False, 'Not implemented'
    elif args.mode == 'dom':
        assert False, 'Not implemented'

    print('Done in {0:f} seconds!'.format(time.time() - start_time))
