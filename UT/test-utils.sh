function build_schema_validator()
{
    which cmake &>/dev/null || { echo 'cmake is not found'; return 1; }

    local build_dir="$1"

    mkdir -p "$build_dir"

    (
        cd "$build_dir"

        local compiler=''
        if [ -n "$CMAKE_CXX_COMPILER" ]; then
            compiler="-DCMAKE_CXX_COMPILER=$CMAKE_CXX_COMPILER"
        fi

        cmake "$compiler" "$SOURCE_DIR/UT/schema-validator"
        make
    )

    local res="$?"
    if [ "$res" -ne 0 ]; then
        echo -n 'Schema validator build failed; it may make sense to check that boost-system, '
        echo -n 'boost-filesystem, xerces-c, and libxml2 libraries are available for your compiler '
        echo 'which can be adjusted with CMAKE_CXX_COMPILER environment variable'
    fi

    return $res
}

function remove_current_output()
{
    rm -rf "$BASE_OUTPUT_DIR" "$DIFF_FILE" "$LOG_FILE" &>/dev/null
}

function get_renames()
{
    local input="$1"

    find "$input" -mindepth 1 -maxdepth 1 -type f -name '*.rename'
}

function get_supported_list()
{
    local input="$1"

    find "$input" -mindepth 1 -maxdepth 1 -type f -name '*.list'
}

function log_run()
{
    echo "### $@"
    "$@"
}

function diff_schemata()
{
    local output="$1"
    local output2="$2"
    local res="$3"

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
        local dir="$1"

        echo "### Validating schemata in $dir"
        find "$dir" -mindepth 1 -maxdepth 1 -type f -name '*.xsd' -o -name '*.rng' | while read schema
        do
            "$VALIDATOR" "$schema"
        done
    fi
}

function single_schema_set_dump()
{
    # During schema dumps testing we check the following scenarios ('->' means various kinds of dumping):
    #
    # 1) xsd0[valid] -> xsd1 -> xsd2[valid] : diff(xsd1, xsd2)
    #                        -> dcm2        : diff(dcm1, dcm2)
    #                -> dcm1 -> xsd3[valid] : diff(xsd2, xsd3)
    #
    # 2) rng0[valid] -> xsd1 -> xsd2[valid] : diff(xsd1, xsd2)
    #                        -> dcm2        : diff(dcm1, dcm2)
    #                -> dcm1 -> xsd4[valid] : diff(xsd2, xsd4)
    #                -> rng1 -> xsd3[valid] : diff(xsd2, xsd3)
    #                        -> dcm3        : diff(dcm2, dcm3)
    #                        -> rng2[valid] : diff(rng1, rng2)


    local input="$1"
    local syntax="$2"
    # During the first run we do dumpxsd, in the second run we do dumpxsd along with reduction of the
    # schemata if list file (with supported components) is present.
    local runcounter="$3"

    local renames="$(get_renames "$input")"
    local supported="$(get_supported_list "$input")"
    local dump_output="$BASE_OUTPUT_DIR/schema-dumps"
    local xsd_output="$dump_output/$(basename "$input")-${syntax}-xsd"
    local xsd_output2="$dump_output/second-xsd-xsd-dump"
    # These variables can be unused when dumping non-RNG schemata.
    local rng_output="$dump_output/$(basename "$input")-rng-rng"
    local rng_output2="$dump_output/second-rng-rng-dump"
    local xsd_output3="$dump_output/second-rng-xsd-dump"

    if [ "$runcounter" = '2' -a -n "$supported" ]; then
        xsd_output="$xsd_output-lst"
    fi

    test -d "$xsd_output2" && rm -rf "$xsd_output2"
    test -d "$rng_output2" && rm -rf "$rng_output2"
    test -d "$xsd_output3" && rm -rf "$xsd_output3"

    local cmd=("$RUNNER")
    cmd+=('-s')
    cmd+=("$syntax")
    cmd+=('-i')
    cmd+=("$input")
    if [ "$runcounter" = '1' -a -n "$renames" ]; then
        cmd+=('-n')
        cmd+=("$renames")
    fi
    cmd+=('dumpxsd')
    cmd+=('-o')
    cmd+=("$xsd_output")
    if [ "$syntax" = 'rng' -a "$DUMP_RNG" -ne 0 ]; then
        cmd+=('--dump-rng-model-to-dir')
        cmd+=("$rng_output")
    fi
    if [ "$runcounter" = '2' -a -n "$supported" ]; then
        cmd+=('-d')
        cmd+=("$supported")
    fi

    echo "### Test $input"

    validate_schemata "$input"

    log_run $COVERAGE_APPEND_COMMAND "${cmd[@]}"

    log_run $RUNNER -i "$xsd_output" dumpxsd -o "$xsd_output2"

    diff_schemata "$xsd_output" "$xsd_output2" "$dump_output/$(basename "$xsd_output").diff"

    validate_schemata "$xsd_output2"

    if [ "$syntax" = 'rng' -a "$DUMP_RNG" -ne 0 ]; then
        log_run $RUNNER -s rng -i "$rng_output" dumpxsd -o "$xsd_output3" --dump-rng-model-to-dir "$rng_output2"

        diff_schemata "$xsd_output2" "$xsd_output3" "$dump_output/$(basename "$xsd_output2").diff"
        diff_schemata "$rng_output" "$rng_output2" "$dump_output/$(basename "$rng_output").diff"

        validate_schemata "$rng_output2"
    fi

    if [ "$runcounter" = '1' -a -n "$supported" ]; then
        echo ''
        let "runcounter++"
        single_schema_set_dump "$input" "$syntax" "$runcounter"
    fi

    rm -rf "$xsd_output2" "$xsd_output3" "$rng_output2" &>/dev/null
}

function single_generation_run()
{
    local input="$1"
    local output="$BASE_OUTPUT_DIR/$(basename "$input")"
    local syntax="$2"

    local output="${output}${3}${4}"

    local cmd=("$RUNNER")
    cmd+=('-i')
    cmd+=("$input")
    cmd+=("$3")
    cmd+=("$4")
    cmd+=("$mode")
    cmd+=('-o')
    cmd+=("$output-c++")
    cmd+=("$5")
}
