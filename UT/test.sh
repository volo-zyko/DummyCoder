#!/bin/bash

cd "$(dirname "$BASH_SOURCE")/.."

SOURCE_DIR=$PWD
BASE_OUTPUT_DIR='/tmp/dumco'

COVERAGE_BEGIN_COMMAND=''
COVERAGE_APPEND_COMMAND=''
COVERAGE_REPORT_DIR="$BASE_OUTPUT_DIR/dumco_cov"
VALIDATE_SCHEMATA=0

function print_help()
{
    echo "Usage: $0 [-c [-d <dir>]] [-v]"
    echo ' -c           generate coverage report'
    echo ' -d <dir>     place coverage report in <dir>'
    echo ' -v           validate schemata'
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
        -v)
            shift
            VALIDATE_SCHEMATA=1
            ;;
        -h|*)
            print_help
            exit 1
    esac
done

function build_schema_validator()
{
    which cmake &>/dev/null || { echo 'cmake is not found' ; return 1 ; }

    build_dir=$1

    mkdir -p "$build_dir"
    pushd "$PWD" &>/dev/null
    cd "$build_dir"

    compiler=''
    if [ -n "$CMAKE_CXX_COMPILER" ]; then
        compiler="-DCMAKE_CXX_COMPILER=$CMAKE_CXX_COMPILER"
    fi

    cmake "$compiler" "$SOURCE_DIR/UT/schema-validator"
    make

    res=$?
    if [ "$res" -ne 0 ]; then
        echo -n 'Schema validator build failed; it may make sense to check that boost-system, '
        echo -n 'boost-filesystem and xerces-c libraries are available for your compiler which '
        echo 'may be ajusted with CMAKE_CXX_COMPILER environment variable'
    fi

    popd &>/dev/null
    return $res
}

if [ "$VALIDATE_SCHEMATA" -ne 0 ]; then
    svbuild_dir="$BASE_OUTPUT_DIR/svbuild"
    schema_validator="$svbuild_dir/schema-validator"

    build_schema_validator "$svbuild_dir"
    if [ $? -ne 0 ]; then
        schema_validator=''
        echo 'Build of schema validator have failed; we continue with less tests'
    fi
fi

function single_run()
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

        echo "### $run -i $out dumpxsd -o $again"
        $run -i "$out" dumpxsd -o "$again"

        (
            res="$BASE_OUTPUT_DIR/$(basename "${out}").diff"

            set +o errexit
            diff -rub "$out" "$again" >"$res"

            if [ "$VALIDATE_SCHEMATA" -ne 0 -a -x "$schema_validator" ]; then
                echo '### Validating input schemata'
                find "$inp" -mindepth 1 -maxdepth 1 -type f -name '*.xsd' | while read xsd
                do
                    "$schema_validator" "$xsd"
                done

                echo '### Validating dumped schemata'
                find "$again" -mindepth 1 -maxdepth 1 -type f -name '*.xsd' | while read xsd
                do
                    "$schema_validator" "$xsd"
                done
            fi

            if [ -s "$res" ]; then
                echo "### ERROR: Schemata at $out and $again are different, see $res" >&2
                exit 1
            fi

            # Subshell succeeds.
            rm -rf "$again"
            rm -f "$res"
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
        if [ -n "$(find $dir -maxdepth 1 -name '*.xsd')" ]; then
            single_run "$dir" dumpxsd $opt
        fi
    done
done

# content_class='--context-class V::None::LoadContext'
# content_class_header='--context-class-header Formats/None/LoadContext.h'

# prefices='--uri-prefices http://schemas.openxmlformats.org/ urn:schemas-microsoft-com:'
# single_run UT/schemas/OXMLTran3/ '' rfilter "$prefices $content_class $content_class_header"

# prefices='--uri-prefices http://schemas.openxmlformats.org/ http://purl.org/'
# single_run UT/schemas/OPC3/ '' rfilter "$prefices $content_class $content_class_header"

# prefices='--uri-prefices urn:oasis:names:tc:'
# single_run UT/schemas/ODF12/ '' rfilter "$prefices $content_class $content_class_header"

# # prefices='--uri-prefices http://www.w3.org/'
# # single_run UT/schemas/XHTML10/ '' rfilter "$prefices $content_class $content_class_header"

# content_class='--context-class V::Fb2::LoadContext'
# content_class_header='--context-class-header Formats/Fb2/LoadContext.h'
# prefices='--uri-prefices http://www.gribuser.ru/'
# single_run UT/schemas/FB20/ '-n fb2' rfilter "$prefices $content_class $content_class_header"

if [ "$COVERAGE_BEGIN_COMMAND" != '' ]; then
    test -d "$COVERAGE_REPORT_DIR" && rm -rf "$COVERAGE_REPORT_DIR"
    coverage html -d "$COVERAGE_REPORT_DIR"

    if [ "$(uname -s)" == 'Darwin' ]; then
        open "$COVERAGE_REPORT_DIR/index.html"
    else
        xdg-open "$COVERAGE_REPORT_DIR/index.html"
    fi
fi
