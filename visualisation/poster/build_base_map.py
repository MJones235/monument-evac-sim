import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np


def parse_shape(shape_str: str) -> np.ndarray:
    """Convert a SUMO-style shape string into an Nx2 numpy array."""
    points = []
    for pair in shape_str.strip().split():
        x_coord, y_coord = pair.split(",")
        points.append((float(x_coord), float(y_coord)))
    return np.array(points)


FLOOR = "#D6E8F5"
PLATFORM = "#B8D0E8"
OBSTACLE = "#8FAABB"


SHAPES = {
    "main_area": "-15.229481,49.411192 -66.307270,46.833872 -65.955817,44.373703 -64.784308,44.373703 -64.432855,37.110348 -69.821796,37.578952 -69.704646,35.353085 -17.455348,33.361520 -17.338198,38.047555 -11.129200,38.047555 -11.012049,30.393985 -12.841116,30.393985 -12.691804,27.594394 -11.982574,27.631722 -12.057230,25.616016 -19.149528,25.728000 -19.112200,30.580625 -21.426529,30.468641 -22.512488,-33.397458 -19.801558,-33.591096 -19.704739,-13.646399 -4.407350,-13.743218 -6.634185,-37.754309 -4.310531,-38.044766 1.498604,26.823909 -0.825050,26.630271 -1.018688,25.855719 -8.667383,25.758901 -8.280107,41.056289 -15.541526,41.056289 -15.251069,49.382716 -15.229481,49.411192",
    "platform_3": "-66.335393,46.979934 -66.062135,44.138042 -15.454609,46.979934 -15.399958,49.548566 -66.499349,46.925282 -66.335393,46.979934",
    "platform_4": "-69.680638,37.624417 -69.680638,35.303963 -17.590460,33.463604 -17.510444,35.624026 -69.760654,37.544401 -69.680638,37.624417",
    "platform_2": "-21.363856,30.585112 -22.535365,-32.910670 -19.840894,-33.144972 -19.255140,30.467961 -21.598158,30.585112 -21.363856,30.585112",
    "platform_1": "-1.096752,26.601982 -1.096752,18.987174 -6.719995,-37.948159 -4.259826,-38.182460 1.480568,26.601982 -1.331054,26.719133 -1.096752,26.601982",
    "esc_a_down": "-25.806022,40.057628 -23.924889,40.068564 -23.930702,41.068547 -25.811835,41.057611",
    "esc_b_up": "-25.814610,38.653586 -23.927975,38.642681 -23.922194,39.642664 -25.808829,39.653570",
    "esc_c_up": "-25.767389,37.174088 -23.874944,37.195840 -23.886437,38.195774 -25.778883,38.174022",
    "esc_d_down": "-7.421172,17.488479 -8.028323,15.706841 -7.081776,15.384274 -6.474625,17.165912",
    "esc_e_up": "-5.679925,16.987937 -6.314917,15.082960 -5.366234,14.766733 -4.731242,16.671709",
    "esc_f_up": "-3.711641,14.192753 -3.001248,16.019477 -3.933253,16.381923 -4.643645,14.555199",
}


OBSTACLES = [
    "-62.693310,44.521747 -62.282704,37.130826 -41.670246,36.268551 -41.629185,41.195832 -40.849033,41.154771 -40.890093,45.794627 -62.734371,44.562807",
    "-39.176744,45.779696 -39.139416,41.113711 -37.198366,41.113711 -37.161038,45.929008 -39.251399,45.854352",
    "-9.540206,-5.968879 -9.474077,-7.754352 -3.522501,-7.886610 -3.456373,-6.035008 -9.540206,-6.035008",
    "-19.657885,-9.539825 -19.724014,-11.655941 -13.177280,-11.589812 -13.111152,-9.738211 -19.724014,-9.605954",
    "-9.540206,-9.804340 -9.540206,-11.788198 -4.051530,-11.854327 -3.787016,-9.804340 -9.606335,-9.804340",
    "-6.400112,17.272628 -11.183142,2.944609 -10.382459,2.628549 -5.704781,16.956569",
    "-4.777674,16.682651 -9.539634,2.207137 -8.802162,1.933219 -3.955920,16.345521",
    "-21.938249,40.044701 -32.309655,40.056595 -32.297761,39.604630 -21.950142,39.580842 -21.950142,40.056595",
    "-21.962036,38.653125 -32.309655,38.653125 -32.309655,38.201160 -21.962036,38.213053 -21.950142,38.653125",
    "-39.475367,37.567562 -39.512694,36.037119 -36.974398,36.037119 -36.937070,37.604890 -39.512694,37.567562",
    "-35.239347,46.019422 -35.264843,41.022314 -24.021350,41.073305 -24.046846,37.248988 -35.060879,37.147006 -35.060879,35.846739 -21.726760,35.591784 -21.599283,46.835276 -35.264843,46.044917",
    "-19.569905,46.917759 -19.610966,41.046083 -17.557932,40.963961 -17.475811,46.999880 -19.652026,46.958819",
    "-19.137418,23.791827 -19.249401,20.768268 -12.231759,20.768268 -12.157103,23.791827 -19.212074,23.754499",
    "-8.424315,23.605188 -8.461643,20.730940 -0.921410,20.954908 -0.921410,23.754499 -8.424315,23.717171",
    "-19.268148,18.819409 -19.587651,-3.652262 -13.197602,-3.865264 -13.197602,0.714271 -7.553059,17.434898 -2.973524,15.837386 -8.298565,-1.096243 -9.576575,-1.415745 -9.470074,-4.078265 -3.399528,-4.078265 -1.163011,19.032410 -19.268148,18.712908",
    "-19.657885,-5.836622 -19.724014,-7.622095 -13.177280,-7.754352 -12.978894,-5.770494 -19.724014,-5.770494",
]


def build_base_map(output_path: Path, dpi: int = 300) -> tuple[tuple[float, float], tuple[float, float]]:
    """Render and save a clean level -1 base map for publication-quality figures."""
    fig, ax = plt.subplots(figsize=(8, 12), facecolor="none")
    ax.set_facecolor("none")

    ax.add_patch(
        Polygon(
            parse_shape(SHAPES["main_area"]),
            closed=True,
            facecolor=FLOOR,
            edgecolor="#5A7A8A",
            linewidth=0.8,
            zorder=1,
        )
    )

    for platform_name in ["platform_3", "platform_4", "platform_2", "platform_1"]:
        ax.add_patch(
            Polygon(
                parse_shape(SHAPES[platform_name]),
                closed=True,
                facecolor=PLATFORM,
                edgecolor="#4A6A7A",
                linewidth=1.2,
                zorder=2,
            )
        )

    for obstacle in OBSTACLES:
        ax.add_patch(
            Polygon(
                parse_shape(obstacle),
                closed=True,
                facecolor=OBSTACLE,
                edgecolor="#4A6070",
                linewidth=0.5,
                zorder=3,
            )
        )

    label_style = dict(
        fontsize=9,
        color="#1A3A4A",
        fontweight="bold",
        ha="center",
        va="center",
        fontfamily="DejaVu Sans",
        zorder=6,
    )
    ax.text(-41.0, 46.8, "Platform 3", **label_style)
    ax.text(-41.0, 35.1, "Platform 4", **label_style)
    ax.text(-20.9, -15.0, "Platform 2", rotation=90, **label_style)
    ax.text(-3.4, -18.0, "Platform 1", rotation=90, **label_style)

    ax.set_aspect("equal")
    ax.autoscale_view()

    x_limits = ax.get_xlim()
    y_limits = ax.get_ylim()

    ax.axis("off")
    plt.tight_layout(pad=0.1)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight", facecolor="none", transparent=True)
    plt.close(fig)

    return x_limits, y_limits


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a clean level -1 base map image for poster graphics.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("results/figures/base_map_level_minus_1.png"),
        help="Output PNG path.",
    )
    parser.add_argument("--dpi", type=int, default=300, help="Output image DPI.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    x_limits, y_limits = build_base_map(args.output, dpi=args.dpi)
    print(f"Saved base map to {args.output}")
    print(f"xlim: {x_limits}")
    print(f"ylim: {y_limits}")


if __name__ == "__main__":
    main()
