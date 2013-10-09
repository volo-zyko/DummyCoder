#!/bin/bash

cd "$(dirname "$BASH_SOURCE")/.."

BASE_OUTPUT_DIR='/tmp/dumco'

COVERAGE_BEGIN_COMMAND=''
COVERAGE_APPEND_COMMAND=''
COVERAGE_REPORT_DIR="$BASE_OUTPUT_DIR/dumco_cov"

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
    run="$PWD/dumco.py"

    inp="$1"
    out="$BASE_OUTPUT_DIR/$(basename "$inp")"
    mode="$2"

    case "$mode" in
        dumpxsd)
            out="${out}${3}${4}"

            cmd=("$run")
            cmd+=('-i')
            cmd+=("$inp")
            cmd+=("$3")
            cmd+=("$4")
            cmd+=("$mode")
            cmd+=('--for-diffing')
            cmd+=('-o')
            cmd+=("$out")
            ;;
        rfilter)
            out="${out}${3}${4}"

            cmd=("$run")
            cmd+=('-i')
            cmd+=("$inp")
            cmd+=("$3")
            cmd+=("$4")
            cmd+=("$mode")
            cmd+=('-o')
            cmd+=("$out-C++")
            cmd+=("$5")
            ;;
    esac

    echo '###'
    echo "### ${cmd[@]}"
    $COVERAGE_APPEND_COMMAND "${cmd[@]}"

    if [ "$mode" = dumpxsd ]; then
        again="$BASE_OUTPUT_DIR/again"

        test -d "$again" && rm -rf "$again"

        echo "### $run -i $out dumpxsd --for-diffing -o $again"
        $run -i "$out" dumpxsd --for-diffing -o "$again"

        (
            res="$BASE_OUTPUT_DIR/$(basename "${out}").diff"

            set +o errexit
            diff -rub "$out" "$again" >"$res"

            if [ -s "$res" ]; then
                echo "### ERROR: Schemas at $out and $again are different, see $res"
                exit 1
            fi

            # Subshell succeeds.
            rm -rf "$again" "$res"
            exit 0
        )
    fi
}

set -o errexit

$COVERAGE_ERASE_COMMAND

$COVERAGE_BEGIN_COMMAND "$PWD/dumco.py" -h
$COVERAGE_APPEND_COMMAND "$PWD/dumco.py" --version

opts=('-n oxml')
opts+=('-n fb2')

for opt in "${opts[@]}"
do
    echo '###'
    echo "### Doing schema dump tests for '$opt'"
    echo '###'
    find "$PWD/UT/schemata" -mindepth 1 -maxdepth 1 -type d | while read dir
    do
        cont_s2c "$dir" dumpxsd $opt
    done
done

# content_class='--context-class V::None::LoadContext'
# content_class_header='--context-class-header Formats/None/LoadContext.h'

# prefices='--uri-prefices http://schemas.openxmlformats.org/ urn:schemas-microsoft-com:'
# cont_s2c UT/schemas/OXMLTran3/ '' rfilter "$prefices $content_class $content_class_header"

# prefices='--uri-prefices http://schemas.openxmlformats.org/ http://purl.org/'
# cont_s2c UT/schemas/OPC3/ '' rfilter "$prefices $content_class $content_class_header"

# prefices='--uri-prefices urn:oasis:names:tc:'
# cont_s2c UT/schemas/ODF12/ '' rfilter "$prefices $content_class $content_class_header"

# # prefices='--uri-prefices http://www.w3.org/'
# # cont_s2c UT/schemas/XHTML10/ '' rfilter "$prefices $content_class $content_class_header"

# content_class='--context-class V::Fb2::LoadContext'
# content_class_header='--context-class-header Formats/Fb2/LoadContext.h'
# prefices='--uri-prefices http://www.gribuser.ru/'
# cont_s2c UT/schemas/FB20/ '-n fb2' rfilter "$prefices $content_class $content_class_header"

if [ "$COVERAGE_BEGIN_COMMAND" != '' ]; then
    test -d "$COVERAGE_REPORT_DIR" && rm -rf "$COVERAGE_REPORT_DIR"
    coverage html -d "$COVERAGE_REPORT_DIR"

    if [ "$(uname -s)" == 'Darwin' ]; then
        open "$COVERAGE_REPORT_DIR/index.html"
    else
        xdg-open "$COVERAGE_REPORT_DIR/index.html"
    fi
fi
