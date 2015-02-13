#!/usr/bin/env python

# Distributed under the GPLv2 License; see accompanying file COPYING.

import argparse
import os
import os.path
import sys
import time

# import dumco.cxx.rfilter.gendriver

import dumco.schema.namer
from dumco.schema.parsing.xml_parser import XmlLoader
from dumco.schema.parsing.relaxng.element_factory import RelaxElementFactory
from dumco.schema.parsing.xml_schema.element_factory import XsdElementFactory
from dumco.schema.dump_xsd import dump_xsd
from dumco.schema.opacity_manager import OpacityManager
import dumco.schema.xsd_types

from dumco.utils.ns_converter import NamespaceConverter
from dumco.utils.file_utils import PathNotExists
from dumco.utils.horn import horn


def name_patterns(text_patterns):
    problem_pattern = text_patterns
    result = None

    try:
        result = dumco.schema.namer.parse_name_patterns(text_patterns)
    except dumco.schema.namer.PatternParseException as ex:
        problem_pattern = ex.pattern
    except:
        pass

    if result is None:
        raise argparse.ArgumentTypeError(
            'Can\'t parse pattern \'{}\''.format(problem_pattern))

    return result


def process_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument('--version', action='version',
                        version='%(prog)s version 3.0')

    parser.add_argument(
        '-s', '--input-syntax', choices=['xsd', 'rng', 'rnc'],
        default='xsd', help='assume input schema files use one of 3 '
        'supported serializations {default: %(default)s}')
    parser.add_argument(
        '-n', '--naming-patterns', default=([], [], [], []), type=name_patterns,
        help='name anonymous or new schema entities according '
        'to these naming rules {default: %(default)s}')
    parser.add_argument(
        '-i', '--input-path', required=True,
        help='directory with schema files or single schema file')
    parser.add_argument(
        '--max-dir-depth', default=1,
        help='max directory depth where schema files are searched '
        '{default: %(default)d}')

    subparsers = parser.add_subparsers(dest='mode', help='processing modes')

    parser_dumpxsd = subparsers.add_parser(
        'dumpxsd', help='dump XSD serialization of schema files')
    parser_dumpxsd.add_argument(
        '--dump-rng-model-to-dir', default=None,
        help='dump loaded RelaxNG model in simple syntax to specified '
        'directory (works only for rng input syntax)')
    parser_dumpxsd.add_argument(
        '--xml-xsd-location', default=dumco.schema.xsd_types.XML_XSD_URI,
        help='location for xml.xsd which must be dumped in schema files '
        '{default: %(default)s}')
    parser_dumpxsd.add_argument(
        '-o', '--output-dir', required=True, help='output directory')

    parser_rdumpxsd = subparsers.add_parser(
        'rdumpxsd', help='dump reduced XSD serialization of schema files '
        '(only elements from supported elements file are dumped)')
    parser_rdumpxsd.add_argument(
        '--xml-xsd-location', default=dumco.schema.xsd_types.XML_XSD_URI,
        help='location for xml.xsd which must be dumped in schema files '
        '{default: %(default)s}')
    parser_rdumpxsd.add_argument(
        '-d', '--supported-elements-file', required=True, default=None,
        help='file with a list of supported schema elements (works only '
        'for xsd input syntax)')
    parser_rdumpxsd.add_argument(
        '-o', '--output-dir', required=True, help='output directory')

    parser_rfilter = subparsers.add_parser(
        'rfilter', help='generate read-only filter for schema files')
    parser_rfilter.add_argument(
        '-o', '--output-dir', required=True, help='output directory')
    parser_rfilter.add_argument(
        '--root-namespaces', default='V', help='root C++ namespaces in '
        'which code will be generated {default: %(default)s}')
    parser_rfilter.add_argument(
        '--uri-to-namespaces', nargs='+', metavar='MAPPING',
        help='uri to C++ namespaces mappings, e.g. http://net/!a,b,c '
        'maps to a list [a,b,c]')
    parser_rfilter.add_argument(
        '--uri-prefixes', nargs='+', metavar='PREFIX',
        help='uri prefixes that must be removed from XML namespaces to '
        'form C++ namespaces, e.g. PREFIX http://net/ maps URI '
        'http://net/a/b/c to a list [a,b,c]')
    parser_rfilter.add_argument(
        '--context-class', required=True,
        help='fully qualified class name of filter specific context class')
    parser_rfilter.add_argument(
        '--context-class-header', required=True,
        help='path to the header with context class declaration')

    # parser_dom = subparsers.add_parser(
    #     'dom', help='generate DOM corresponding to schema files')

    args = parser.parse_args()

    if args.mode == 'dumpxsd':
        if (args.dump_rng_model_to_dir is not None and
                args.input_syntax != 'rng' and args.input_syntax != 'rnc'):
            parser.error('--dump-rng-model-to-dir is only applicable to '
                         'RelaxNG input syntax')
    elif args.mode == 'rdumpxsd':
        if (args.supported_elements_file is not None and
                args.input_syntax != 'xsd'):
            parser.error('-d/--supported-elements-file is only applicable to '
                         'XML Schema input syntax')

    return args


if __name__ == '__main__':
    status = 0
    start_time = time.time()

    args = process_arguments()
    horn.set_verbosity(1)

    if not os.path.exists(args.input_path):
        raise PathNotExists()

    namer = dumco.schema.namer.Namer(args.naming_patterns)

    if args.input_syntax == 'xsd':
        factory = XsdElementFactory(args, namer)
    elif args.input_syntax == 'rng':
        factory = RelaxElementFactory(args, namer, '.rng')
    elif args.input_syntax == 'rnc':
        assert False, 'Not implemented'

    if args.input_syntax == 'xsd' or args.input_syntax == 'rng':
        loader = XmlLoader(factory)
    elif args.input_syntax == 'rnc':
        assert False, 'Not implemented'

    all_schemata = loader.load_xml(args.input_path, args.max_dir_depth)

    if args.mode == 'dumpxsd' or args.mode == 'rdumpxsd':
        elements_file = None
        if args.mode == 'rdumpxsd':
            elements_file = args.supported_elements_file

        opacity_manager = OpacityManager(elements_file)

        if opacity_manager.ensure_consistency(all_schemata):
            dump_xsd(all_schemata, args.output_dir, args.xml_xsd_location,
                     namer, opacity_manager)
        else:
            horn.honk('ERROR: Supported elements file is not consistent')
            status = 1
    elif args.mode == 'rfilter' or args.mode == 'dom':
        ns_converter = NamespaceConverter(args.root_namespaces.split(),
                                          args.uri_to_namespaces,
                                          args.uri_prefixes)
        opacity_manager = OpacityManager(None)

        if args.mode == 'rfilter':
            gd = dumco.cxx.rfilter.gendriver.RFilterGenerationDriver(
                all_schemata, ns_converter, opacity_manager,
                args.output_dir, args.context_class, args.context_class_header)
        elif args.mode == 'dom':
            assert False, 'Not implemented'

        gd.generate()

    horn.beep('{} in {} seconds!',
              ('Done' if status == 0 else 'Failed'),
              time.time() - start_time)
    sys.exit(status)
