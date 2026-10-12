#!/usr/bin/env python3
"""Render the platform level with a train beside every platform."""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from evacusim.visualization.train_geometry import compute_train_polygons
from evacusim.visualization.video_generation_helper import VideoGenerationHelper
from matplotlib.patches import Polygon


def render_preview(network_path: Path, output_path: Path, dpi: int = 180) -> None:
    geometry = VideoGenerationHelper.load_geometry_from_network(network_path)
    if not geometry:
        raise RuntimeError(f"Could not load geometry from {network_path}")

    level = geometry["levels"]["level_-1"]
    trains = compute_train_polygons(geometry)
    fig, axis = plt.subplots(figsize=(11, 8), facecolor="#F4F7F8")
    axis.set_facecolor("#F4F7F8")

    for coords in level.get("walkable_areas", {}).values():
        axis.add_patch(Polygon(coords, facecolor="#DCE5E8", edgecolor="#708087", linewidth=0.8))
    for name, coords in level.get("platform_areas", {}).items():
        axis.add_patch(Polygon(coords, facecolor="#AFC7D2", edgecolor="#425C66", linewidth=1.2))
        points = coords[:-1] if coords[0] == coords[-1] else coords
        axis.text(
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
            f"Platform {name.rsplit('_', 1)[-1]}",
            ha="center",
            va="center",
            fontsize=9,
            color="#18333D",
            weight="bold",
        )
    for coords in level.get("obstacles", []):
        axis.add_patch(Polygon(coords, facecolor="#718087", edgecolor="#455158", linewidth=0.5))

    for exit_name, coords in trains.items():
        platform_num = exit_name.rsplit("_", 1)[-1]
        axis.add_patch(
            Polygon(
                coords,
                facecolor="#D7DEE2",
                edgecolor="#26343A",
                linewidth=1.5,
                zorder=5,
            )
        )
        points = coords
        axis.text(
            sum(point[0] for point in points) / len(points),
            sum(point[1] for point in points) / len(points),
            f"TRAIN P{platform_num}",
            ha="center",
            va="center",
            fontsize=7,
            color="#172126",
            weight="bold",
            zorder=6,
        )

    all_points = [point for coords in level.get("walkable_areas", {}).values() for point in coords]
    all_points.extend(point for coords in trains.values() for point in coords)
    xs = [point[0] for point in all_points]
    ys = [point[1] for point in all_points]
    axis.set_xlim(min(xs) - 3, max(xs) + 3)
    axis.set_ylim(min(ys) - 3, max(ys) + 3)
    axis.set_aspect("equal")
    axis.axis("off")
    axis.set_title("Monument platform-level train placement", fontsize=14, weight="bold")
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--network-path", type=Path, default=Path("geometry/monument/network"))
    parser.add_argument(
        "--output", type=Path, default=Path("results/figures/train_layout_preview.png")
    )
    args = parser.parse_args()
    render_preview(args.network_path, args.output)
    print(f"Saved train layout preview to {args.output}")


if __name__ == "__main__":
    main()
