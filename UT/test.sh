#!/bin/bash

COVERAGE_BEGIN_COMMAND=''
COVERAGE_APPEND_COMMAND=''
COVERAGE_REPORT_DIR='/tmp/dumco/dumco_cov/'

function print_help()
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

function cont_s2c()
{
    run='../dumco.py'

    inp="$1"
    out="/tmp/dumco/$(basename "$inp")"
    aux="$2"
    mode="$3"

    case "$mode" in
        dumpxsd)
            run="$run -i $inp $aux $mode -o $out"
            ;;
        rfilter)
            run="$run -i $inp $aux $mode -o $out-C++ $4"
            ;;
    esac

    echo "$run"
    $COVERAGE_APPEND_COMMAND $run
}

cd "$(dirname "$BASH_SOURCE")"

$COVERAGE_ERASE_COMMAND

$COVERAGE_BEGIN_COMMAND ../dumco.py -h
$COVERAGE_APPEND_COMMAND ../dumco.py --version

cont_s2c UT/schemas/OXMLTran2/ '' dumpxsd

cont_s2c UT/schemas/OXMLTran3/ '' dumpxsd

cont_s2c UT/schemas/OPC3/ '' dumpxsd

cont_s2c UT/schemas/ODF12/ '' dumpxsd

cont_s2c UT/schemas/XHTML10/ '' dumpxsd

cont_s2c UT/schemas/FB20/ '-n fb2' dumpxsd

cont_s2c UT/schemas/NewML12/ '-n fb2' dumpxsd

cont_s2c UT/schemas/ebXML204/ '-n fb2' dumpxsd

cont_s2c UT/schemas/Docbook50/ '-n fb2' dumpxsd

content_class='--context-class V::None::LoadContext'
content_class_header='--context-class-header Formats/None/LoadContext.h'

prefices='--uri-prefices http://schemas.openxmlformats.org/ urn:schemas-microsoft-com:'
cont_s2c UT/schemas/OXMLTran3/ '' rfilter "$prefices $content_class $content_class_header"

prefices='--uri-prefices http://schemas.openxmlformats.org/ http://purl.org/'
cont_s2c UT/schemas/OPC3/ '' rfilter "$prefices $content_class $content_class_header"

prefices='--uri-prefices urn:oasis:names:tc:'
cont_s2c UT/schemas/ODF12/ '' rfilter "$prefices $content_class $content_class_header"

# prefices='--uri-prefices http://www.w3.org/'
# cont_s2c UT/schemas/XHTML10/ '' rfilter "$prefices $content_class $content_class_header"

content_class='--context-class V::Fb2::LoadContext'
content_class_header='--context-class-header Formats/Fb2/LoadContext.h'
prefices='--uri-prefices http://www.gribuser.ru/'
cont_s2c UT/schemas/FB20/ '-n fb2' rfilter "$prefices $content_class $content_class_header"

if [ "$COVERAGE_BEGIN_COMMAND" != '' ]; then
    test -d "$COVERAGE_REPORT_DIR" && rm -rf "$COVERAGE_REPORT_DIR"
    coverage html -d "$COVERAGE_REPORT_DIR"

    if [ "$(uname -s)" == 'Darwin' ]; then
        open "$COVERAGE_REPORT_DIR/index.html"
    else
        xdg-open "$COVERAGE_REPORT_DIR/index.html"
    fi
fi
