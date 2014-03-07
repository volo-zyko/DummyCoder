#!/bin/bash

cd "$(dirname "$BASH_SOURCE")/.."

SOURCE_DIR="$PWD"
BASE_OUTPUT_DIR='/tmp/dumco'

COVERAGE_BEGIN_COMMAND=''
COVERAGE_APPEND_COMMAND=''
COVERAGE_REPORT_DIR="$BASE_OUTPUT_DIR/dumco_cov"
VALIDATE_SCHEMATA=0
DUMP_RNG=0
DUMP_RNG_DIR=''

function print_help()
{
    echo "Usage: $0 [-f|[-c [-d <dir>]] [-v] [-r [<dir>]]]"
    echo ' -f           do full check (includes all options below)'
    echo ' -c           generate coverage report'
    echo ' -d <dir>     place coverage report in <dir>'
    echo ' -v           validate XSD schemata (input and output)'
    echo " -r [<dir>]   dump RNG to <dir> for additional checks (default $BASE_OUTPUT_DIR/rng-dumps0)"
}

while [ $# -gt 0 ]
do
    case $1 in
        -f)
            shift
            COVERAGE_ERASE_COMMAND='coverage erase'
            COVERAGE_BEGIN_COMMAND='coverage run --branch'
            COVERAGE_APPEND_COMMAND='coverage run --branch --append'
            VALIDATE_SCHEMATA=1
            DUMP_RNG=1
            ;;
        -c)
            shift
            COVERAGE_ERASE_COMMAND='coverage erase'
            COVERAGE_BEGIN_COMMAND='coverage run --branch'
            COVERAGE_APPEND_COMMAND='coverage run --branch --append'
            ;;
        -d)
            shift
            COVERAGE_REPORT_DIR="$1"
            shift
            ;;
        -v)
            shift
            VALIDATE_SCHEMATA=1
            ;;
        -r)
            shift
            DUMP_RNG=1
            if [ $# -gt 0 -a -d "$1" ]; then
                DUMP_RNG_DIR="$1"
                shift
            fi
            ;;
        -h|*)
            print_help
            exit 1
    esac
done

function build_schema_validator()
{
    which cmake &>/dev/null || { echo 'cmake is not found' ; return 1 ; }

    build_dir="$1"

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
            syntax="$3"
            namer="$4"

            out="${out}-${syntax}-${namer}"

            cmd=("$run")
            cmd+=('-s')
            cmd+=("$syntax")
            cmd+=('-n')
            cmd+=("$namer")
            cmd+=('-i')
            cmd+=("$inp")
            cmd+=("$mode")
            cmd+=('-o')
            cmd+=("$out")
            if [ "$syntax" = 'rng' -a "$DUMP_RNG" -ne 0 ]; then
                cmd+=('--dump-rng-model-to-dir')
                cmd+=("$DUMP_RNG_DIR")
            fi
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

    if [ "$mode" = dumpxsd -a "$syntax" != 'rng' ]; then
        again="$BASE_OUTPUT_DIR/again"

        test -d "$again" && rm -rf "$again"

        echo "### $run -i $out dumpxsd -o $again"
        $run -i "$out" dumpxsd -o "$again"

        (
            res="$BASE_OUTPUT_DIR/$(basename "$out").diff"

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

if [ "$DUMP_RNG" -ne 0 ]; then
    if [ -z "$DUMP_RNG_DIR" ]; then
        DUMP_RNG_DIR="$BASE_OUTPUT_DIR/rng-dumps0"
    fi
    rm -rf "$DUMP_RNG_DIR"
fi

$COVERAGE_ERASE_COMMAND

$COVERAGE_BEGIN_COMMAND "$PWD/dumco.py" -h
$COVERAGE_APPEND_COMMAND "$PWD/dumco.py" --version

syntaxes=('xsd')
if [ -n "$COVERAGE_BEGIN_COMMAND" ]; then
    syntaxes+=('xsd')
fi
namers=('oxml')
if [ -n "$COVERAGE_BEGIN_COMMAND" ]; then
    namers+=('fb2')
fi

for syntax in "${syntaxes[@]}"
do
    for namer in "${namers[@]}"
    do
        echo '###'
        echo "### Doing schema dump tests for syntax='$syntax' with namer='$namer'"
        echo '###'
        find "$PWD/UT/schemata" -mindepth 1 -maxdepth 1 -type d | while read dir
        do
            if [ -n "$(find $dir -maxdepth 1 -name "*.$syntax")" ]; then
                single_run "$dir" dumpxsd "$syntax" "$namer"
            fi
        done
    done
done

if [ "$DUMP_RNG" -ne 0 ]; then
    outp="$BASE_OUTPUT_DIR/rng-dumps1"
    again="$BASE_OUTPUT_DIR/again"

    echo '###'
    echo '### Checking RNG re-loading'
    echo '###'

    for in_rng in $(find "$DUMP_RNG_DIR" -type f -name '*.rng')
    do
        rm -rf "$outp"
        mkdir -p "$outp"

        out_rng="$outp/$(basename "$in_rng")"
        res_diff="$BASE_OUTPUT_DIR/$(basename "$in_rng").diff"

        $COVERAGE_APPEND_COMMAND "$PWD/dumco.py" -s rng -n oxml -i "$in_rng" \
            dumpxsd -o "$again" --dump-rng-model-to-dir "$outp"

        set +o errexit
        diff -rub "$in_rng" "$out_rng" >"$res_diff"
        set -o errexit

        if [ -s "$res_diff" ]; then
            echo "### ERROR: '$in_rng' and '$out_rng' is different after reloading, see $res_diff" >&2
            false
        fi
        rm -f "$res_diff"
    done
fi

# content_class='--context-class V::None::LoadContext'
# content_class_header='--context-class-header Formats/None/LoadContext.h'

# prefixes='--uri-prefixes http://schemas.openxmlformats.org/ urn:schemas-microsoft-com:'
# single_run UT/schemas/OXMLTran3/ '' rfilter "$prefixes $content_class $content_class_header"

# prefixes='--uri-prefixes http://schemas.openxmlformats.org/ http://purl.org/'
# single_run UT/schemas/OPC3/ '' rfilter "$prefixes $content_class $content_class_header"

# prefixes='--uri-prefixes urn:oasis:names:tc:'
# single_run UT/schemas/ODF12/ '' rfilter "$prefixes $content_class $content_class_header"

# # prefixes='--uri-prefixes http://www.w3.org/'
# # single_run UT/schemas/XHTML10/ '' rfilter "$prefixes $content_class $content_class_header"

# content_class='--context-class V::Fb2::LoadContext'
# content_class_header='--context-class-header Formats/Fb2/LoadContext.h'
# prefixes='--uri-prefixes http://www.gribuser.ru/'
# single_run UT/schemas/FB20/ '-n fb2' rfilter "$prefixes $content_class $content_class_header"

if [ -n "$COVERAGE_BEGIN_COMMAND" ]; then
    test -d "$COVERAGE_REPORT_DIR" && rm -rf "$COVERAGE_REPORT_DIR"
    coverage html -d "$COVERAGE_REPORT_DIR"

    if [ "$(uname -s)" == 'Darwin' ]; then
        open "$COVERAGE_REPORT_DIR/index.html"
    else
        xdg-open "$COVERAGE_REPORT_DIR/index.html"
    fi
fi
