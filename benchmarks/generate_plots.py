import json
from pathlib import Path

import matplotlib.pyplot as plt


BASE_DIR = Path(__file__).resolve().parents[1]
BENCHMARKS_DIR = BASE_DIR / "benchmarks"
RESULTS_FILE = BENCHMARKS_DIR / "benchmark_results.json"
PLOTS_DIR = BENCHMARKS_DIR / "plots"


COLORS = {
    "Python": "#3776AB",
    "Java": "#E76F00",
    "C": "#5C6BC0",
    "JSON": "#3776AB",
    "Hierarchical": "#2CA02C",
    "SQLite": "#9467BD",
    "TSV": "#FF7F0E",
    "Time": "#D62728",
    "ID": "#2CA02C",
}


def load_results() -> dict:
    if not RESULTS_FILE.is_file():
        raise FileNotFoundError(
            "There is no benchmarks/benchmark_results.json. "
            "Run run_benchmarks.py first."
        )

    with RESULTS_FILE.open("r", encoding="utf-8") as file:
        results = json.load(file)

    if not isinstance(results, dict):
        raise ValueError(
            "benchmark_results.json must contain a JSON object."
        )

    return results


def save_figure(
    figure,
    filename: str,
) -> Path:
    PLOTS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = PLOTS_DIR / filename

    figure.tight_layout()
    figure.savefig(
        output_path,
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(figure)

    print(f"[OK] Graph saved: {output_path}")
    return output_path


def annotate_bars(
    axis,
    *,
    decimals: int = 2,
    suffix: str = "",
) -> None:
    for bar in axis.patches:
        height = bar.get_height()

        axis.annotate(
            f"{height:.{decimals}f}{suffix}",
            (
                bar.get_x() + bar.get_width() / 2,
                height,
            ),
            ha="center",
            va="bottom",
            fontsize=8,
            xytext=(0, 3),
            textcoords="offset points",
        )


def plot_indexing_speed(results: dict) -> Path:
    indexing = results["indexing_speed"]

    languages = ["Python", "Java", "C"]
    means_seconds = [
        indexing[language]["mean_ms"] / 1000
        for language in languages
    ]

    stddev_seconds = [
        indexing[language]["stddev_ms"] / 1000
        for language in languages
    ]

    figure, axis = plt.subplots(
        figsize=(8, 5),
    )

    axis.bar(
        languages,
        means_seconds,
        yerr=stddev_seconds,
        capsize=6,
        color=[
            COLORS["Python"],
            COLORS["Java"],
            COLORS["C"],
        ],
    )

    axis.set_title(
        "Indexing time by language"
    )
    axis.set_xlabel("Language")
    axis.set_ylabel("Average time (s)")
    axis.grid(
        axis="y",
        alpha=0.25,
    )

    annotate_bars(
        axis,
        decimals=2,
        suffix=" s",
    )

    return save_figure(
        figure,
        "indexing_speed.png",
    )


def plot_storage_footprint(results: dict) -> Path:
    storage = results["storage_footprint"]

    labels = []
    logical_kib = []
    colors = []

    for name, metrics in storage.items():
        short_name = (
            name.replace("Python ", "Py ")
            .replace("Java ", "Java ")
            .replace("Monolithic ", "JSON ")
            .replace("Hierarchical", "Hier.")
        )

        labels.append(short_name)
        logical_kib.append(metrics["logical_kib"])

        if "JSON" in name:
            colors.append(COLORS["JSON"])
        elif "Hierarchical" in name:
            colors.append(COLORS["Hierarchical"])
        elif "SQLite" in name:
            colors.append(COLORS["SQLite"])
        else:
            colors.append(COLORS["TSV"])

    figure, axis = plt.subplots(
        figsize=(12, 6),
    )

    axis.bar(
        labels,
        logical_kib,
        color=colors,
    )

    axis.set_title(
        "Logical size by index structure"
    )
    axis.set_xlabel("Structure")
    axis.set_ylabel("Logical size (KiB)")
    axis.tick_params(
        axis="x",
        rotation=40,
    )
    axis.grid(
        axis="y",
        alpha=0.25,
    )

    annotate_bars(
        axis,
        decimals=1,
        suffix=" KiB",
    )

    return save_figure(
        figure,
        "storage_footprint.png",
    )


def plot_query_latency(results: dict) -> Path:
    structures = (
        results["query_latency"]["structures"]
    )

    labels = []
    means = []
    colors = []

    label_mapping = {
        "Python monolithic JSON in memory":
            "JSON en memoria",
        "Python hierarchical direct file":
            "Jerárquico",
        "Python SQLite":
            "SQLite",
        "C TSV sequential scan":
            "TSV secuencial",
    }

    color_mapping = {
        "Python monolithic JSON in memory":
            COLORS["JSON"],
        "Python hierarchical direct file":
            COLORS["Hierarchical"],
        "Python SQLite":
            COLORS["SQLite"],
        "C TSV sequential scan":
            COLORS["TSV"],
    }

    for name, metrics in structures.items():
        labels.append(
            label_mapping.get(name, name)
        )
        means.append(
            metrics["per_query_mean_ms"]
        )
        colors.append(
            color_mapping.get(name, "#7F7F7F")
        )

    figure, axis = plt.subplots(
        figsize=(9, 5),
    )

    axis.bar(
        labels,
        means,
        color=colors,
    )

    axis.set_title(
        "Average latency per query"
    )
    axis.set_xlabel("Structure")
    axis.set_ylabel("Average latency (ms)")
    axis.grid(
        axis="y",
        alpha=0.25,
    )

    annotate_bars(
        axis,
        decimals=4,
        suffix=" ms",
    )

    return save_figure(
        figure,
        "query_latency.png",
    )


def plot_growth_scaling(results: dict) -> Path:
    growth = (
        results["growth_scaling"]["measurements"]
    )

    sizes = sorted(
        int(size)
        for size in growth
    )

    times_seconds = [
        growth[str(size)]["total_indexing_ms"]
        / 1000
        for size in sizes
    ]

    json_sizes_kib = [
        growth[str(size)]["json_size_bytes"]
        / 1024
        for size in sizes
    ]

    figure, time_axis = plt.subplots(
        figsize=(9, 5),
    )

    size_axis = time_axis.twinx()

    time_line = time_axis.plot(
        sizes,
        times_seconds,
        marker="o",
        linewidth=2,
        color=COLORS["Python"],
        label="Indexing time",
    )

    size_line = size_axis.plot(
        sizes,
        json_sizes_kib,
        marker="s",
        linewidth=2,
        color=COLORS["TSV"],
        label="JSON size",
    )

    time_axis.set_title(
        "Python index growth"
    )
    time_axis.set_xlabel(
        "Books num"
    )
    time_axis.set_ylabel(
        "Tiempo total (s)",
        color=COLORS["Python"],
    )
    size_axis.set_ylabel(
        "JSON size (KiB)",
        color=COLORS["TSV"],
    )

    time_axis.set_xticks(sizes)
    time_axis.grid(
        alpha=0.25,
    )

    lines = time_line + size_line
    labels = [
        line.get_label()
        for line in lines
    ]

    time_axis.legend(
        lines,
        labels,
        loc="upper left",
    )

    return save_figure(
        figure,
        "growth_scaling.png",
    )


def plot_datalake_lookup(results: dict) -> Path:
    datalake = results["datalake_lookup"]

    labels = [
        "Layout temporal",
        "Layout by ID",
    ]

    medians = [
        datalake["time_layout"]["median_ms"],
        datalake["id_layout"]["median_ms"],
    ]

    figure, axis = plt.subplots(
        figsize=(7, 5),
    )

    axis.bar(
        labels,
        medians,
        color=[
            COLORS["Time"],
            COLORS["ID"],
        ],
    )

    axis.set_title(
        "Search cost in the data lake"
    )
    axis.set_xlabel("Layout")
    axis.set_ylabel("Median (ms)")
    axis.grid(
        axis="y",
        alpha=0.25,
    )

    annotate_bars(
        axis,
        decimals=4,
        suffix=" ms",
    )

    return save_figure(
        figure,
        "datalake_lookup.png",
    )


def main() -> None:
    results = load_results()

    generated_files = [
        plot_indexing_speed(results),
        plot_storage_footprint(results),
        plot_query_latency(results),
        plot_growth_scaling(results),
        plot_datalake_lookup(results),
    ]

    print()
    print(
        f"[OK] They have been generated"
        f"{len(generated_files)} graphs."
    )

    for path in generated_files:
        print(f"  - {path}")


if __name__ == "__main__":
    main()