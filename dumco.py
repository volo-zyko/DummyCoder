#!/usr/bin/env python

# Distributed under the GPLv2 License; see accompanying file COPYING.

from __future__ import print_function

import argparse
import os
import os.path
import sys
import time

import dumco.cxx.rfilter.gendriver
from dumco.cxx.opacity_manager import OpacityManager

import dumco.schema.fb2_namer
import dumco.schema.oxml_namer

from dumco.utils.ns_converter import NamespaceConverter

from dumco.xml.parser import XmlLoader
from dumco.xml.xsd.element_factory import XsdElementFactory
from dumco.xml.xsd.dump_xsd import dump_xsd

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
    parser.add_argument('--max-dir-depth', default=1,
                        help='max directory depth where schema files are '
                        'searched {default: %(default)d}')

    subparsers = parser.add_subparsers(dest='mode',
                                       help='generation modes')

    parser_dumpxsd = subparsers.add_parser(
        'dumpxsd', help='dump XSD serialization of schema files')
    parser_dumpxsd.add_argument('-o', '--output-dir', required=True,
                                help='output directory')
    parser_dumpxsd.add_argument('--for-diffing', action='store_true',
                                help='prepare dumped schemata for diffing '
                                '{default: %(default)s}')

    parser_rfilter = subparsers.add_parser(
        'rfilter', help='generate read-only filter for schema files')
    parser_rfilter.add_argument('-o', '--output-dir', required=True,
                                help='output directory')
    parser_rfilter.add_argument('--root-namespaces',
                                default='V', help='root C++ namespaces in '
                                'which code will be generated '
                                '{default: %(default)s}')
    parser_rfilter.add_argument('--uri-to-namespaces',
                                nargs='+', metavar='MAPPING',
                                help='uri to C++ namespaces mappings, e.g. '
                                'http://net/!a,b,c maps to a list [a,b,c]')
    parser_rfilter.add_argument('--uri-prefices',
                                nargs='+', metavar='PREFIX',
                                help='uri prefices that must be removed from '
                                'XML namespaces to form C++ namespaces, e.g. '
                                'PREFIX http://net/ maps URI http://net/a/b/c '
                                'to a list [a,b,c]')
    parser_rfilter.add_argument('--context-class', required=True,
                                help='fully qualified class name of filter '
                                'specific context class')
    parser_rfilter.add_argument('--context-class-header', required=True,
                                help='path to the header with context class '
                                'declaration')

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

    all_schemata = loader.load_xml(args.input_dir, args.max_dir_depth)

    if args.mode == 'dumpxsd':
        dump_xsd(all_schemata, args.output_dir, args.for_diffing)
    elif args.mode == 'rfilter' or args.mode == 'dom':
        ns_converter = NamespaceConverter(args.root_namespaces.split(),
                                          args.uri_to_namespaces,
                                          args.uri_prefices)
        opacity_manager = OpacityManager(None)

        if args.mode == 'rfilter':
            gd = dumco.cxx.rfilter.gendriver.RFilterGenerationDriver(
                all_schemata, ns_converter, opacity_manager,
                args.output_dir, args.context_class, args.context_class_header)
        elif args.mode == 'dom':
            assert False, 'Not implemented'

        gd.generate()

    print('Done in {0:f} seconds!'.format(time.time() - start_time))
