#!/bin/bash

set -o errexit

NOW="$(echo $(gnudate +%F)-$(printf "%05d" $[$[$(gnudate +%s) - $(gnudate -d "today 00:00:00" +%s)] % 86400]))"

WORKING_DIR="$PWD"
SCRIPT_DIR="$(dirname "$BASH_SOURCE")/.."
SOURCE_DIR="$(cd "$SCRIPT_DIR" && pwd)"
BASE_OUTPUT_DIR="$WORKING_DIR/dumco-$NOW"
LAST_OUTPUT_DIR="$WORKING_DIR/dumco-last"
RUNNER="$SOURCE_DIR/dumco.py"
READLINK='readlink -f'
if [ "$(uname -s)" = 'Darwin' ]; then
    READLINK=readlink
fi

if [ "$(uname -s)" = 'Darwin' ]; then
    COVERAGE=coverage
else
    COVERAGE=python-coverage
fi
COVERAGE_BEGIN_COMMAND=''
COVERAGE_APPEND_COMMAND=''
COVERAGE_REPORT_DIR="$WORKING_DIR/htmlcov"

VALIDATE_SCHEMATA=0
VALIDATOR_BUILD_DIR="$WORKING_DIR/svbuild"

DUMP_RNG=0

function print_help()
{
    echo "Usage: $0 -f|[-v [<dir>]] [-c [<dir>]] [-r]"
    echo ' -f           do full check (includes all options below)'
    echo " -v [<dir>]   build schema-validator in <dir> (default $VALIDATOR_BUILD_DIR) and validate XSD schemata"
    echo '              (both input and output), in order to build schema-validator one needs boost-system,'
    echo '              boost-filesystem, xerces-c and libxml2 libraries, set CMAKE_CXX_COMPILER environment variable'
    echo '              for changing default C++ compiler'
    echo " -c [<dir>]   generate coverage report to <dir> (default $COVERAGE_REPORT_DIR)"
    echo ' -r           dump RNG model for additional checks'
    echo ''
    echo "Note: DUMCO_DIFF_VIEWER environment variable is used for showing differences between tests' runs"
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

    find "$SOURCE_DIR/UT/schemata" -mindepth 1 -maxdepth 1 -type d | while read dir
    do
        if [ -n "$(find "$dir" -maxdepth 1 -name "*.$syntax")" ]; then
            echo ''
            single_schema_set_dump "$dir" $syntax dumpxsd
        fi
    done
done

if [ -d "$LAST_OUTPUT_DIR" ]; then
    last_output_path=$($READLINK "$LAST_OUTPUT_DIR")
    diff_file="$WORKING_DIR/dumco-$NOW.diff"

    if diff -urb "$last_output_path" "$BASE_OUTPUT_DIR" >"$diff_file"; then
        # There is no difference between test runs and thus no point in storing their results.
        rm -rf "$BASE_OUTPUT_DIR" "$diff_file"
    else
        while true; do
            echo 'There are changes between dumped schemata and schemata from previous run. What shall we do?'
            echo 'A(ccept them as new standard)/R(eject and fix dumping)/V(iew diff)'
            read action

            if [ "$action" = 'A' -o "$action" = 'a' ]; then
                ln -shF "$BASE_OUTPUT_DIR" "$LAST_OUTPUT_DIR"
                break
            elif [ "$action" = 'R' -o "$action" = 'r' ]; then
                rm -rf "$BASE_OUTPUT_DIR" "$diff_file"
                break
            elif [ "$action" = 'V' -o "$action" = 'v' ]; then
                if [ -z "$DUMCO_DIFF_VIEWER" ]; then
                    cat "$diff_file" | less
                else
                    $DUMCO_DIFF_VIEWER "$diff_file"
                fi
            fi
        done
    fi
else
    ln -shF "$BASE_OUTPUT_DIR" "$LAST_OUTPUT_DIR"
fi

if [ -n "$COVERAGE_BEGIN_COMMAND" ]; then
    test -d "$COVERAGE_REPORT_DIR" && rm -rf "$COVERAGE_REPORT_DIR"
    $COVERAGE html -d "$COVERAGE_REPORT_DIR"

    if [ "$(uname -s)" = 'Darwin' ]; then
        open "$COVERAGE_REPORT_DIR/index.html"
    else
        xdg-open "$COVERAGE_REPORT_DIR/index.html"
    fi
fi
