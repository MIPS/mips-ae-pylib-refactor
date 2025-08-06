
import argparse
import locale
import os
import sys
from atlasexplorer.atlasexplorer import AtlasExplorer, Experiment

def main():

    parser = argparse.ArgumentParser(description="Run a single core experiment with ATLAS Explorer.")
    parser.add_argument("--elf", required=True, help="Path to the ELF workload file.")
    parser.add_argument("--expdir", default="myexperiments", help="Experiment directory (default: myexperiments)")
    parser.add_argument("--core", default="I8500_(1_thread)", help="Core type (default: I8500_(1_thread)")
    parser.add_argument("--apikey", help="Your ATLAS Explorer API key.")
    parser.add_argument("--region", help="Region")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output.")
    args = parser.parse_args()

    # Check for config file or ENV
    config_env = os.environ.get("MIPS_ATLAS_CONFIG")
    home_dir = os.path.expanduser("~")
    config_file = os.path.join(home_dir, ".config", "mips", "atlaspy", "config.json")
    if not args.apikey and not config_env and not os.path.exists(config_file):
        print("Atlas Explorer configuration not found.")
        print("Please run 'atlasexplorer configure' before using this script.")
        sys.exit(1)

    locale.setlocale(locale.LC_ALL, "")
    aeinst = AtlasExplorer(
        args.apikey,
        args.core,
        args.region,
        verbose=args.verbose,
    )
    experiment = Experiment(args.expdir, aeinst, verbose=args.verbose)
    experiment.addWorkload(args.elf)
    experiment.setCore(args.core)
    experiment.run()
    total_cycles = experiment.getSummary().getTotalCycles()
    print(f"Total Cycles: {total_cycles}")

if __name__ == "__main__":
    main()
