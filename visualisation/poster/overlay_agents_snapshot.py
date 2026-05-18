import argparse
from io import BytesIO
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.offsetbox import AnnotationBbox, OffsetImage
from PIL import Image


ROLE_COLORS = {
    "Passenger": "#2E5EAA",
    "Fire Marshal": "#D55E00",
    "Fire Brigade Officer": "#009E73",
    "Unknown": "#666666",
}

ACTION_COLORS = {
    "move": "#0072B2",
    "wait": "#E69F00",
    "unknown": "#1A1A1A",
}

ACTION_MARKERS = {
    "move": "o",
    "wait": "o",
    "unknown": "o",
}

ACTION_EDGE_COLORS = {
    "move": "#1A1A1A",
    "wait": "#1A1A1A",
    "unknown": "#1A1A1A",
}

ACTION_EDGE_WIDTHS = {
    "move": 1.2,
    "wait": 1.2,
    "unknown": 1.2,
}

ACTION_LABELS = {
    "move": "Moving toward destination",
    "wait": "Waiting",
    "unknown": "Firefighters securing escalator\nand directing evacuation",
}

# Defaults from base-map render output, used to align coordinate overlays.
DEFAULT_XLIM = (-73.387816, 5.064624)
DEFAULT_YLIM = (-42.5690113, 53.9351173)

# Approximate midpoint of the platform 1/2 escalator area in simulation coordinates.
DEFAULT_FIRE_ICON_XY = (-8.0, 10.0)


def load_svg_rgba(svg_path: Path) -> np.ndarray:
    """Rasterize an SVG into an RGBA array for Matplotlib overlay."""
    try:
        import cairosvg
    except ImportError as exc:
        raise ImportError(
            "cairosvg is required to render SVG overlays. Install it with: pip install cairosvg"
        ) from exc

    png_bytes = cairosvg.svg2png(url=str(svg_path))
    with Image.open(BytesIO(png_bytes)) as img:
        return np.asarray(img.convert("RGBA"))


def find_latest_e3_run(e3_root: Path) -> Path:
    run_dirs = sorted([p for p in e3_root.glob("run_*") if p.is_dir()])
    if not run_dirs:
        raise FileNotFoundError(f"No run_* directories found in {e3_root}")
    return run_dirs[-1]


def load_snapshot(history_path: Path, target_time: float) -> dict:
    closest = None
    closest_delta = float("inf")

    with history_path.open() as handle:
        for line in handle:
            record = json.loads(line)
            delta = abs(float(record["time"]) - target_time)
            if delta < closest_delta:
                closest = record
                closest_delta = delta

    if closest is None:
        raise ValueError(f"No records found in {history_path}")

    return closest


def load_role_map(run_dir: Path) -> dict[str, str]:
    positions_path = run_dir / "agent_decisions_positions.json"
    if not positions_path.exists():
        return {}

    with positions_path.open() as handle:
        payload = json.load(handle)

    return payload.get("agent_roles", {})


def infer_role(agent_id: str, role_map: dict[str, str]) -> str:
    if agent_id in role_map:
        return role_map[agent_id]
    if agent_id.startswith("agent_"):
        return "Passenger"
    return "Unknown"


def style_key_for_agent(agent_id: str, snapshot: dict, role_map: dict[str, str], color_by: str) -> str:
    if color_by == "action":
        state = snapshot.get("agent_states", {}).get(agent_id, {})
        return state.get("action_type", "unknown")
    return infer_role(agent_id, role_map)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Overlay agent positions on the pre-rendered level -1 base map image."
    )
    parser.add_argument(
        "--base-image",
        type=Path,
        default=Path("results/figures/base_map_level_minus_1.png"),
        help="Path to the base map image.",
    )
    parser.add_argument(
        "--e3-root",
        type=Path,
        default=Path("results/E3"),
        help="Directory containing E3 run_* outputs.",
    )
    parser.add_argument(
        "--run-dir",
        type=Path,
        default=None,
        help="Optional explicit run directory. If omitted, the latest E3 run is used.",
    )
    parser.add_argument(
        "--time",
        type=float,
        default=9.5,
        help="Simulation time to visualize.",
    )
    parser.add_argument(
        "--color-by",
        choices=["role", "action"],
        default="action",
        help="Color points by agent role or action type.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/figures/e3_agents_overlay_t9_5_actions.png"),
        help="Output image path.",
    )
    parser.add_argument(
        "--fire-icon",
        type=Path,
        default=Path("results/figures/fire.svg"),
        help="Path to SVG icon used to mark the fire location.",
    )
    parser.add_argument(
        "--fire-icon-x",
        type=float,
        default=DEFAULT_FIRE_ICON_XY[0],
        help="X coordinate for the fire icon center.",
    )
    parser.add_argument(
        "--fire-icon-y",
        type=float,
        default=DEFAULT_FIRE_ICON_XY[1],
        help="Y coordinate for the fire icon center.",
    )
    parser.add_argument(
        "--fire-icon-zoom",
        type=float,
        default=0.5,
        help="Scale factor for the fire icon.",
    )
    parser.add_argument(
        "--firefighter-color",
        type=str,
        default="#1A1A1A",
        help="Color for the firefighter action category in action mode.",
    )
    parser.add_argument("--dpi", type=int, default=300, help="Output DPI.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    run_dir = args.run_dir if args.run_dir is not None else find_latest_e3_run(args.e3_root)
    history_path = run_dir / "agent_decisions_history.jsonl"
    if not history_path.exists():
        raise FileNotFoundError(f"Missing file: {history_path}")
    if not args.base_image.exists():
        raise FileNotFoundError(f"Missing file: {args.base_image}")

    snapshot = load_snapshot(history_path, args.time)
    role_map = load_role_map(run_dir)
    positions = snapshot.get("positions", {})

    if args.color_by == "role":
        palette = dict(ROLE_COLORS)
    else:
        palette = dict(ACTION_COLORS)
        palette["unknown"] = args.firefighter_color
    grouped_points: dict[str, list[tuple[float, float]]] = {k: [] for k in palette}
    grouped_points.setdefault("Unknown", [])

    for agent_id, point in positions.items():
        key = style_key_for_agent(agent_id, snapshot, role_map, args.color_by)
        if key not in grouped_points:
            key = "Unknown"
        grouped_points[key].append((float(point[0]), float(point[1])))

    fig, ax = plt.subplots(figsize=(8, 12), facecolor="none")
    ax.set_facecolor("none")

    image = mpimg.imread(args.base_image)
    ax.imshow(
        image,
        extent=[DEFAULT_XLIM[0], DEFAULT_XLIM[1], DEFAULT_YLIM[0], DEFAULT_YLIM[1]],
        origin="upper",
        zorder=1,
    )

    if args.fire_icon.exists():
        # Add a high-contrast badge so the fire symbol remains visible over blue map areas.
        ax.scatter(
            [args.fire_icon_x],
            [args.fire_icon_y],
            s=420,
            marker="o",
            c="#FFFFFF",
            edgecolors="#B22222",
            linewidths=2.2,
            alpha=0.97,
            zorder=2.4,
        )

        fire_rgba = load_svg_rgba(args.fire_icon)
        fire_image = OffsetImage(fire_rgba, zoom=args.fire_icon_zoom)
        fire_ab = AnnotationBbox(
            fire_image,
            (args.fire_icon_x, args.fire_icon_y),
            frameon=False,
            box_alignment=(0.5, 0.5),
            zorder=2.6,
        )
        ax.add_artist(fire_ab)

    for label, points in grouped_points.items():
        if not points:
            continue
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        legend_label = ACTION_LABELS.get(label, label) if args.color_by == "action" else label
        marker = ACTION_MARKERS.get(label, "o") if args.color_by == "action" else "o"
        edge_color = ACTION_EDGE_COLORS.get(label, "#1A1A1A") if args.color_by == "action" else "#1A1A1A"
        edge_width = ACTION_EDGE_WIDTHS.get(label, 1.2) if args.color_by == "action" else 1.2
        ax.scatter(
            xs,
            ys,
            s=120,
            marker=marker,
            c=palette.get(label, ROLE_COLORS["Unknown"]),
            edgecolors=edge_color,
            linewidths=edge_width,
            alpha=0.98,
            label=legend_label,
            zorder=2,
        )

    legend = ax.legend(
        title=None,
        loc="lower left",
        frameon=True,
        facecolor="white",
        edgecolor="#BBBBBB",
        fontsize=14,
        title_fontsize=16,
        markerscale=1.35,
        borderpad=0.8,
        labelspacing=0.6,
        handletextpad=0.6,
    )
    legend.get_frame().set_alpha(0.95)

    ax.set_xlim(DEFAULT_XLIM)
    ax.set_ylim(DEFAULT_YLIM)
    ax.set_aspect("equal")
    ax.axis("off")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(pad=0.1)
    fig.savefig(args.output, dpi=args.dpi, bbox_inches="tight", facecolor="none", transparent=True)
    plt.close(fig)

    actual_time = float(snapshot["time"])
    delta = abs(actual_time - args.time)
    print(f"Run directory: {run_dir}")
    print(f"Target time: {args.time}, plotted time: {actual_time}, delta: {delta}")
    print(f"Color mode: {args.color_by}")
    if args.color_by == "action":
        print(f"Firefighter color: {palette['unknown']}")
    print(f"Plotted agents: {len(positions)}")
    print(f"Saved overlay to {args.output}")


if __name__ == "__main__":
    main()
