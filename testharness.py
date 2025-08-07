from atlasexplorer import atlasexplorer 
import sys
import locale
import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()


def print_summary_metrics(summary, label="Experiment"):
    if not summary:
        print(f"No summary report found for {label}.")
        return
    print(f"{label} total cycles: " + locale.format_string("%d", summary.getTotalCycles(), grouping=True))
    print(f"{label} total instructions: " + locale.format_string("%d", summary.getTotalInstructions(), grouping=True))
    metric_keys = summary.getMetricKeys()
    print(f"\nAll Metric Keys in {label} summary:")
    for item in metric_keys:
        print(item)
    print(f"\nCache Metrics in {label} summary:")
    summary.printMetrics(".*Cache.*")
    cache_metric = "Level 1 Instruction Cache (L1ICache) Hits"
    if cache_metric in metric_keys:
        cacheHits = summary.getMetricValue(cache_metric)
        print(f"\n{label} {cache_metric}: " + locale.format_string("%d", cacheHits, grouping=True))
    else:
        print(f"Metric '{cache_metric}' not found in {label} summary.")

def run_experiment(exp_dir, core, workloads, aeinst, label):
    experiment = atlasexplorer.Experiment(exp_dir, aeinst, verbose=True)
    for wl in workloads:
        experiment.addWorkload(wl)
    experiment.setCore(core)
    experiment.run()
    summary = experiment.getSummary()
    print_summary_metrics(summary, label)
    # Load experiment from disk and print metrics again
    experiment2 = experiment.getExperiment(experiment.getRoot(), aeinst)
    if experiment2 is None:
        print(f"Error getting {label} from disk! Check your setup.")
        return
    print(f"{label}2 dir: " + experiment2.getRoot())
    summary2 = experiment2.getSummary()
    print_summary_metrics(summary2, f"{label}2")

def main():
    locale.setlocale(locale.LC_ALL, "")
    config_str = os.environ.get("MIPS_ATLAS_CONFIG")
    if not config_str:
        print("Error: MIPS_ATLAS_CONFIG not set. Please run 'atlasexplorer.py configure' or set it in your .env file.")
        sys.exit(1)
    try:
        apikey, channel, region = config_str.split(":")
    except Exception:
        print("Error: MIPS_ATLAS_CONFIG format invalid. Should be 'apikey:channel:region'.")
        sys.exit(1)
    aeinst = atlasexplorer.AtlasExplorer(apikey, channel, region, verbose=True)

    # Experiment 1
    run_experiment(
        exp_dir="myexperiments",
        core="I8500_(2_threads)",
        workloads=["resources/mandelbrot_rv64_O0.elf", "resources/memcpy_rv64.elf"],
        aeinst=aeinst,
        label="Experiment1"
    )

    # Experiment 2 (different core/workloads for demonstration)
    run_experiment(
        exp_dir="myexperiments",
        core="I8500_(2_threads)",
        workloads=["resources/mandelbrot_rv64_O3.elf"],
        aeinst=aeinst,
        label="Experiment2"
    )

if __name__ == "__main__":
    main()