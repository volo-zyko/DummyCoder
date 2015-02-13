#!/bin/bash

set -o errexit

cd "$(dirname "$BASH_SOURCE")/.."

SOURCE_DIR="$PWD"
BASE_OUTPUT_DIR='/tmp/dumco'
RUNNER="$SOURCE_DIR/dumco.py"

if [ "$(uname -s)" = 'Darwin' ]; then
    COVERAGE=coverage
else
    COVERAGE=python-coverage
fi
COVERAGE_BEGIN_COMMAND=''
COVERAGE_APPEND_COMMAND=''
COVERAGE_REPORT_DIR="$SOURCE_DIR/htmlcov"

VALIDATE_SCHEMATA=0
VALIDATOR_BUILD_DIR="$BASE_OUTPUT_DIR/svbuild"

DUMP_RNG=0
DUMP_RNG_DIR="$BASE_OUTPUT_DIR/rng-dumps"

function print_help()
{
    echo "Usage: $0 -f|[-v [<dir>]] [-c [<dir>]] [-r [<dir>]]"
    echo ' -f           do full check (includes all options below)'
    echo " -v [<dir>]   build schema-validator in <dir> (default $VALIDATOR_BUILD_DIR) and validate XSD schemata"
    echo '              (both input and output), in order to build schema-validator one needs boost-system,'
    echo '              boost-filesystem, xerces-c and libxml2 libraries, set CMAKE_CXX_COMPILER environment variable'
    echo '              for changing default C++ compiler'
    echo " -c [<dir>]   generate coverage report to <dir> (default $COVERAGE_REPORT_DIR)"
    echo " -r [<dir>]   dump RNG to <dir> for additional checks (default $DUMP_RNG_DIR)"
}

if [ $# -eq 1 -a "$1" = '-f' ]; then
    set -- "-v" "-c" "-r"
fi

while [ $# -gt 0 ]
do
    case $1 in
        -c)
            shift
            COVERAGE_ERASE_COMMAND="$COVERAGE erase"
            COVERAGE_BEGIN_COMMAND="$COVERAGE run --branch"
            COVERAGE_APPEND_COMMAND="$COVERAGE run --branch --append"
            if [ $# -gt 0 -a "${1:0:1}" != '-' ]; then
                shift
                COVERAGE_REPORT_DIR="$1"
            fi
            which "$COVERAGE" &>/dev/null || { echo "$COVERAGE is not found" ; exit 1 ; }
            ;;
        -r)
            shift
            DUMP_RNG=1
            if [ $# -gt 0 -a "${1:0:1}" != '-' ]; then
                shift
                DUMP_RNG_DIR="$1"
            fi
            rm -rf "$DUMP_RNG_DIR"
            ;;
        -v)
            shift
            VALIDATE_SCHEMATA=1
            if [ $# -gt 0 -a "${1:0:1}" != '-' ]; then
                shift
                VALIDATOR_BUILD_DIR="$1"
            fi
            ;;
        -h|--help|*)
            print_help
            exit 1
    esac
done

. "$SOURCE_DIR/UT/test-utils.sh"

if [ "$VALIDATE_SCHEMATA" -ne 0 ]; then
    VALIDATOR="$VALIDATOR_BUILD_DIR/schema-validator"

    if ! build_schema_validator "$VALIDATOR_BUILD_DIR"; then
        VALIDATE_SCHEMATA=0
        echo 'Build of schema validator have failed; we continue with less tests'
    fi
fi

$COVERAGE_ERASE_COMMAND

$COVERAGE_BEGIN_COMMAND "$RUNNER" -h && echo '###'
$COVERAGE_APPEND_COMMAND "$RUNNER" dumpxsd --help && echo '###'
$COVERAGE_APPEND_COMMAND "$RUNNER" rdumpxsd --help && echo '###'
$COVERAGE_APPEND_COMMAND "$RUNNER" rfilter --help && echo '###'
$COVERAGE_APPEND_COMMAND "$RUNNER" --version

syntaxes=('xsd')
if [ -n "$COVERAGE_BEGIN_COMMAND" ]; then
    syntaxes+=('rng')
fi

for syntax in "${syntaxes[@]}"
do
    echo '###'
    echo "### Doing schema dump tests for syntax='$syntax'"
    echo '###'

    find "$PWD/UT/schemata" -mindepth 1 -maxdepth 1 -type d | while read dir
    do
        if [ -n "$(find "$dir" -maxdepth 1 -name "*.$syntax")" ]; then
            echo ''
            single_schema_set_dump "$dir" $syntax dumpxsd
        fi
    done
done

if [ -n "$COVERAGE_BEGIN_COMMAND" ]; then
    test -d "$COVERAGE_REPORT_DIR" && rm -rf "$COVERAGE_REPORT_DIR"
    $COVERAGE html -d "$COVERAGE_REPORT_DIR"

    if [ "$(uname -s)" = 'Darwin' ]; then
        open "$COVERAGE_REPORT_DIR/index.html"
    else
        xdg-open "$COVERAGE_REPORT_DIR/index.html"
    fi
fi
