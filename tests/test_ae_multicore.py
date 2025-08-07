from atlasexplorer import atlasexplorer
import locale
import os


def test_multicore():
    locale.setlocale(locale.LC_ALL, "")
    # example use of AtlasExplorer library,
    # this assumes that user has ran the script with the "configure" arg
    # Create an instance of the class using MIPS_ATLAS_CONFIG env variable
    config_str = os.environ.get("MIPS_ATLAS_CONFIG", "")
    try:
        apikey, channel, region = config_str.split(":")
    except ValueError:
        raise RuntimeError("MIPS_ATLAS_CONFIG environment variable must be set as 'apikey:channel:region'")
    aeinst = atlasexplorer.AtlasExplorer(
        apikey,
        channel,
        region,
        verbose=True,
    )
    # create a new experiment
    experiment = atlasexplorer.Experiment("myexperiments", aeinst, verbose=True)
    # add workloads to the experiment using absolute paths
    mandelbrot_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "resources", "mandelbrot_rv64_O0.elf"
        )
    )
    memcpy_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "resources", "memcpy_rv64.elf")
    )
    experiment.addWorkload(mandelbrot_path)
    experiment.addWorkload(memcpy_path)
    # set the core type for the experiment
    experiment.setCore("I8500_(2_threads)")
    # run an experiment
    experiment.run()

    total_cycles = experiment.getSummary().getTotalCycles()
    print(f"Total Cycles: {total_cycles}")
    assert total_cycles == 257577, "Total Cycles should be 257577"
