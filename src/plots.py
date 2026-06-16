import matplotlib.pyplot as plt
from math import ceil
import numpy as np
import numpy.typing as npt
from dataclasses import dataclass
from pathlib import Path
from src.types import PlotArea, SignalFunction


def plot_images(
    images: list[npt.NDArray[np.uint8]],
    save_path: Path | None = None,
    display: bool = True,
):
    ncols = 2
    nrows = ceil(len(images) / ncols)
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(12, 3 * nrows))
    axes = axes.flatten()

    cmap = "gray" if images[0].ndim == 2 else None
    for i, img in enumerate(images):
        axes[i].imshow(img, cmap=cmap)
        axes[i].axis("off")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300)
    if display:
        plt.show()
    else:
        plt.close(fig)


def plot_plots_areas_in_parts(
    plots_areas: list[PlotArea],
    images_per_plot: int = 5,
    save_dir: Path | None = None,
    save_path_prefix: str | None = None,
    display: bool = True,
):

    num_plots = len(plots_areas)
    for i in range(0, num_plots, images_per_plot):
        plots_part = plots_areas[i : i + images_per_plot]

        if save_dir:
            assert save_path_prefix is not None, (
                "save_path_prefix must be provided if save_dir is specified"
            )

            save_path = save_dir.joinpath(
                f"{save_path_prefix}_{i // images_per_plot + 1}.png"
            )
        else:
            save_path = None

        plot_plots_areas(plots_part, save_path=save_path, display=display)


def plot_plots_areas(
    plots_areas: list[PlotArea], save_path: Path | None = None, display: bool = True
):
    num_plots = len(plots_areas)

    fig, axes = plt.subplots(num_plots, 1, figsize=(12, 4 * num_plots))

    for i, plot_area in enumerate(plots_areas):
        axes[i].imshow(plot_area.image, cmap="gray")

        label_center = plot_area.label_center
        # mark the label center on the image with x
        axes[i].plot(
            label_center[0], label_center[1], "rx", markersize=10, label="Label Center"
        )

        axes[i].set_title(f"Plot {plot_area.label}")
        axes[i].axis("off")

    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300)
    if display:
        plt.show()
    else:
        plt.close(fig)


def plot_signal_function(
    plot_area: PlotArea,
    signal_function: SignalFunction,
    save_path: Path | None = None,
    display: bool = True,
):
    assert plot_area.label == signal_function.label

    fig, axs = plt.subplots(nrows=2, ncols=1, figsize=(12, 8))

    axs[0].set_title(f"{plot_area.label}")
    axs[0].imshow(plot_area.image, cmap="gray")

    _, img_width = plot_area.image.shape
    scaled_x = signal_function.x * signal_function.pixels_per_ms
    axs[1].imshow(plot_area.image, cmap="gray")
    axs[1].plot(
        scaled_x,
        signal_function.y + signal_function.base_line,
        "b-",
        label="Signal Function",
    )
    axs[1].axhline(
        signal_function.base_line,
        color="r",
        linestyle="--",
        label="Base Line",
        linewidth=1,
    )
    axs[1].plot(
        plot_area.label_center[0],
        plot_area.label_center[1],
        "rx",
        markersize=11,
        label="Label Center",
    )

    axs[0].axis("off")
    axs[1].axis("off")

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300)
    if display:
        plt.show()
    else:
        plt.close(fig)


def plot_signal_functions_on_whole_image(
    img: npt.NDArray,
    signal_functions: list[SignalFunction],
    plot_areas: list[PlotArea],
    save_path: Path | None = None,
    display: bool = True,
):
    assert img.ndim == 3
    assert len(signal_functions) == len(plot_areas)

    fig, ax = plt.subplots(figsize=(12, 8))
    ax.imshow(img)
    for signal_function, plot_area in zip(signal_functions, plot_areas):
        assert signal_function.label == plot_area.label

        scaled_x = signal_function.x * signal_function.pixels_per_ms
        ax.plot(
            scaled_x + plot_area.top_left_absolute[0],
            signal_function.y
            + signal_function.base_line
            + plot_area.top_left_absolute[1],
            label=f"Signal {signal_function.label}",
        )
        ax.axhline(
            signal_function.base_line + plot_area.top_left_absolute[1],
            color="r",
            linestyle="--",
            label=f"Base Line {signal_function.label}",
            linewidth=1,
        )

    ax.axis("off")
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path, dpi=300)
    if display:
        plt.show()
    else:
        plt.close(fig)
