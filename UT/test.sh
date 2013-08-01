#!/bin/bash

COVERAGE_BEGIN_COMMAND=''
COVERAGE_APPEND_COMMAND=''
COVERAGE_REPORT_DIR='/tmp/dumco/dumco_cov/'

print_help ()
{
    echo "Usage: $0 [-c [-d <dir>]]"
    echo " -c           generate coverage report"
    echo " -d <dir>     place coverage report in <dir>"
}

while [ $# -gt 0 ]
do
    case $1 in
        -c)
            shift
            COVERAGE_ERASE_COMMAND='coverage erase'
            COVERAGE_BEGIN_COMMAND='coverage run --branch'
            COVERAGE_APPEND_COMMAND='coverage run --branch --append'
            ;;
        -d)
            shift
            COVERAGE_REPORT_DIR=$1
            shift
            ;;
        -h|*)
            print_help
            exit 1
    esac
done

cd "$(dirname "$BASH_SOURCE")"

$COVERAGE_ERASE_COMMAND

$COVERAGE_BEGIN_COMMAND ../dumco.py -h
$COVERAGE_APPEND_COMMAND ../dumco.py --version

$COVERAGE_APPEND_COMMAND \
    ../dumco.py -i UT/schemas/OXMLTran2/ dumpxsd -o /tmp/dumco/OXMLTran2/

$COVERAGE_APPEND_COMMAND \
    ../dumco.py -i UT/schemas/OXMLTran3/ dumpxsd -o /tmp/dumco/OXMLTran3/

$COVERAGE_APPEND_COMMAND \
    ../dumco.py -i UT/schemas/OPC3/ dumpxsd -o /tmp/dumco/OPC3/

$COVERAGE_APPEND_COMMAND \
    ../dumco.py -i UT/schemas/ODF12/ dumpxsd -o /tmp/dumco/ODF12/

$COVERAGE_APPEND_COMMAND \
    ../dumco.py -i UT/schemas/XHTML10/ dumpxsd -o /tmp/dumco/XHTML10/

$COVERAGE_APPEND_COMMAND \
    ../dumco.py -i UT/schemas/FB20/ -n fb2 dumpxsd -o /tmp/dumco/FB20/

$COVERAGE_APPEND_COMMAND \
    ../dumco.py -i UT/schemas/NewML12/ -n fb2 dumpxsd -o /tmp/dumco/NewML12/

$COVERAGE_APPEND_COMMAND \
    ../dumco.py -i UT/schemas/ebXML204/ -n fb2 dumpxsd -o /tmp/dumco/ebXML204/

$COVERAGE_APPEND_COMMAND \
    ../dumco.py -i UT/schemas/Docbook50/ -n fb2 dumpxsd -o /tmp/dumco/Docbook50/

if [ "$COVERAGE_BEGIN_COMMAND" != '' ]; then
    test -d "$COVERAGE_REPORT_DIR" && rm -rf "$COVERAGE_REPORT_DIR"
    coverage html -d "$COVERAGE_REPORT_DIR"

    if [ "$(uname -s)" == 'Darwin' ]; then
        open "$COVERAGE_REPORT_DIR/index.html"
    else
        xdg-open "$COVERAGE_REPORT_DIR/index.html"
    fi
fi
