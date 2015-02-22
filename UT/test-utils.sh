function build_schema_validator()
{
    which cmake &>/dev/null || { echo 'cmake is not found'; return 1; }

    build_dir="$1"

    mkdir -p "$build_dir"

    (
        cd "$build_dir"

        compiler=''
        if [ -n "$CMAKE_CXX_COMPILER" ]; then
            compiler="-DCMAKE_CXX_COMPILER=$CMAKE_CXX_COMPILER"
        fi

        cmake "$compiler" "$SOURCE_DIR/UT/schema-validator"
        make
    )

    res=$?
    if [ "$res" -ne 0 ]; then
        echo -n 'Schema validator build failed; it may make sense to check that boost-system, '
        echo -n 'boost-filesystem xerces-c and libxml2 libraries are available for your compiler '
        echo 'which may be ajusted with CMAKE_CXX_COMPILER environment variable'
    fi

    return $res
}

function remove_current_output()
{
    rm -rf "$BASE_OUTPUT_DIR" "$DIFF_FILE" "$LOG_FILE" &>/dev/null
}

function get_renames()
{
    input="$1"

    find "$input" -mindepth 1 -maxdepth 1 -type f -name '*.rename'
}

function get_supported_list()
{
    input="$1"

    find "$input" -mindepth 1 -maxdepth 1 -type f -name '*.list'
}

function diff_schemata()
{
    output="$1"
    output2="$2"
    res="$3"

    if ! diff -rub "$output" "$output2" >"$res" || test -s "$res"; then
        echo "### ERROR: Schemata at $output and $output2 are different, see $res" >&2
        return 1
    fi

    rm -f "$res"
    return 0
}

function validate_schemata()
{
    if [ "$VALIDATE_SCHEMATA" -ne 0 ]; then
        dir="$1"

        echo "### Validating schemata in $dir"
        find "$dir" -mindepth 1 -maxdepth 1 -type f -name '*.xsd' -o -name '*.rng' | while read schema
        do
            "$VALIDATOR" "$schema"
        done
    fi
}

function single_schema_set_dump()
{
    input="$1"
    syntax="$2"
    dumpmode="$3"

    renames="$(get_renames "$input")"
    supported="$(get_supported_list "$input")"
    dump_output="$BASE_OUTPUT_DIR/schema-dumps"
    xsd_output="$dump_output/$(basename "$input")-${syntax}-xsd"
    xsd_output2="$dump_output/second-xsd-xsd-dump"
    # These variables can be unused when dumping non-RNG schemata.
    rng_output="$dump_output/$(basename "$input")-rng-rng"
    rng_output2="$dump_output/second-rng-rng-dump"
    xsd_output3="$dump_output/second-rng-xsd-dump"

    if [ "$dumpmode" = 'rdumpxsd' -a -n "$supported" ]; then
        xsd_output="$xsd_output-lst"
    fi

    test -d "$xsd_output2" && rm -rf "$xsd_output2"
    test -d "$rng_output2" && rm -rf "$rng_output2"
    test -d "$xsd_output3" && rm -rf "$xsd_output3"

    cmd=("$RUNNER")
    cmd+=('-s')
    cmd+=("$syntax")
    cmd+=('-i')
    cmd+=("$input")
    if [ "$dumpmode" = 'dumpxsd' -a -n "$renames" ]; then
        cmd+=('-n')
        cmd+=("$renames")
    fi
    cmd+=("$dumpmode")
    cmd+=('-o')
    cmd+=("$xsd_output")
    if [ "$syntax" = 'rng' -a "$DUMP_RNG" -ne 0 ]; then
        cmd+=('--dump-rng-model-to-dir')
        cmd+=("$rng_output")
    fi
    if [ "$dumpmode" = 'rdumpxsd' -a -n "$supported" ]; then
        cmd+=('-d')
        cmd+=("$supported")
    fi

    echo "### Test $input"

    validate_schemata "$input"

    echo "### ${cmd[@]}"
    $COVERAGE_APPEND_COMMAND "${cmd[@]}"

    echo "### $RUNNER -i $xsd_output dumpxsd -o $xsd_output2"
    $RUNNER -i "$xsd_output" dumpxsd -o "$xsd_output2"

    diff_schemata "$xsd_output" "$xsd_output2" "$dump_output/$(basename "$xsd_output").diff"

    validate_schemata "$xsd_output2"

    if [ "$syntax" = 'rng' -a "$DUMP_RNG" -ne 0 ]; then
        echo "### $RUNNER -i $rng_output dumpxsd -o $xsd_output3 --dump-rng-model-to-dir $rng_output2"
        $RUNNER -s rng -i "$rng_output" dumpxsd -o "$xsd_output3" --dump-rng-model-to-dir "$rng_output2"

        diff_schemata "$xsd_output2" "$xsd_output3" "$dump_output/$(basename "$xsd_output2").diff"
        diff_schemata "$rng_output" "$rng_output2" "$dump_output/$(basename "$rng_output").diff"

        validate_schemata "$rng_output2"
    fi

    if [ "$dumpmode" = 'dumpxsd' -a -n "$supported" ]; then
        echo ''
        single_schema_set_dump "$input" "$syntax" rdumpxsd
    fi

    rm -rf "$xsd_output2" "$xsd_output3" "$rng_output2" &>/dev/null
}

function single_generation_run()
{
    input="$1"
    output="$BASE_OUTPUT_DIR/$(basename "$input")"
    syntax="$2"

    output="${output}${3}${4}"

    cmd=("$RUNNER")
    cmd+=('-i')
    cmd+=("$input")
    cmd+=("$3")
    cmd+=("$4")
    cmd+=("$mode")
    cmd+=('-o')
    cmd+=("$output-c++")
    cmd+=("$5")
}
