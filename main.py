import sys
from pathlib import Path
import os
import argparse
import csv
import numpy as np
import numpy.typing as npt
from scipy.interpolate import interp1d
import cv2
from itertools import combinations
from src.plots import (
    plot_signal_function,
    plot_signal_functions_on_whole_image,
    plot_images,
    plot_plots_areas_in_parts,
)

from src.types import PlotArea, SignalFunction

IMAGES_DIR = Path("images")
TEMPLATES_DIR = Path("templates")
REPORT_IMAGES_DIR = Path("report", "images")

TEMPLATES = {
    "III": Path(TEMPLATES_DIR, "III.png"),
    "II": Path(TEMPLATES_DIR, "II.png"),
    "aVL": Path(TEMPLATES_DIR, "aVL.png"),
    "aVF": Path(TEMPLATES_DIR, "aVF.png"),
    "aVR": Path(TEMPLATES_DIR, "aVR.png"),
    "V2": Path(TEMPLATES_DIR, "V2.png"),
    "V4": Path(TEMPLATES_DIR, "V4.png"),
    "V6": Path(TEMPLATES_DIR, "V6.png"),
    "V3": Path(TEMPLATES_DIR, "V3.png"),
    "V5": Path(TEMPLATES_DIR, "V5.png"),
    "V1": Path(TEMPLATES_DIR, "V1.png"),
    "I": Path(TEMPLATES_DIR, "I.png"),
}


LABELS = ["I", "II", "III", "aVR", "aVL", "aVF", "V1", "V2", "V3", "V4", "V5", "V6"]

assert set(TEMPLATES.keys()) == set(LABELS)


def save_signal_functions_to_csv(
    signal_functions: list[SignalFunction], output_path: Path
):

    assert all(
        (x1 == x2).all()
        for x1, x2 in combinations([sf.x for sf in signal_functions], 2)
    )

    with open(output_path, mode="w", newline="") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(
            [
                "time_ms",
                "I",
                "II",
                "III",
                "aVR",
                "aVL",
                "aVF",
                "V1",
                "V2",
                "V3",
                "V4",
                "V5",
                "V6",
            ]
        )

        for i in range(len(signal_functions[0].x)):
            row = [signal_functions[0].x[i]]
            for sf in signal_functions:
                row.append(sf.y[i])
            writer.writerow(row)


def contour_to_signal_function(
    contour: npt.NDArray, label: str, pixels_per_200ms: int
) -> SignalFunction:
    assert contour.ndim == 3 and contour.shape[1] == 1 and contour.shape[2] == 2
    points = contour.reshape(-1, 2)

    x = points[:, 0]
    y = points[:, 1]

    y_sum = np.bincount(x, weights=y, minlength=pixels_per_200ms)
    x_counts = np.bincount(x, minlength=pixels_per_200ms)

    valid_x = np.where(x_counts > 0)[0]

    averaged_y = y_sum[valid_x] / x_counts[valid_x]

    base_line = np.median(averaged_y)

    averaged_y = averaged_y - base_line

    pixels_per_ms = pixels_per_200ms / 200.0
    time_ms = valid_x / pixels_per_ms

    new_time_ms = np.arange(0, time_ms.max(), 1.0)

    interpolator = interp1d(
        time_ms, averaged_y, kind="linear", fill_value="extrapolate"
    )
    resampled_y = interpolator(new_time_ms)

    assert new_time_ms.min() == 0.0
    assert new_time_ms.max() == 199.0, (
        f"Expected x to be in range [0, 199], but got min {x.min()} and max {x.max()}"
    )

    return SignalFunction(
        label=label,
        x=new_time_ms,
        y=resampled_y,
        base_line=base_line,
        pixels_per_ms=pixels_per_ms,
    )


def get_signal_function_by_contour(plot_area: PlotArea) -> SignalFunction:
    height, width = plot_area.image.shape
    img_binary = plot_area.image

    contours, _ = cv2.findContours(img_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)

    valid_contours = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)

        if w < 0.8 * width:
            continue

        valid_contours.append(contour)

    label_center = plot_area.label_center
    distances_to_label_center = []
    for contour in valid_contours:
        distances = np.linalg.norm(contour.squeeze() - label_center, axis=1)
        distances_to_label_center.append(np.min(distances))

    closest_contour_idx = np.argmin(distances_to_label_center)

    selected_contour = valid_contours[closest_contour_idx]

    signal_function = contour_to_signal_function(
        selected_contour, plot_area.label, pixels_per_200ms=width
    )

    return signal_function


def remove_label_by_template(
    img_gray: npt.NDArray, template: npt.NDArray, template_left_upper: tuple
) -> npt.NDArray[np.uint8]:
    assert img_gray.ndim == 2
    assert template.ndim == 2

    template_on_image = np.zeros_like(img_gray, dtype=np.uint8)

    h, w = template.shape
    x, y = template_left_upper
    template_on_image[y : y + h, x : x + w] = template
    # template_on_image = cv2.morphologyEx(
    #     template_on_image, cv2.MORPH_DILATE, np.ones((3, 3), dtype=np.uint8)
    # )

    diff = cv2.subtract(img_gray, template_on_image).astype(np.uint8)

    return diff


def get_plots_roi(
    img_gray, found_labels_coords: list[tuple[str, tuple[int, int], tuple[int, int]]]
) -> list[PlotArea]:
    height, width = img_gray.shape

    labels = [label for label, _, _ in found_labels_coords]

    assert set(labels) == set(LABELS), f"Expected labels {LABELS}, but found {labels}"

    avg_label_height = int(
        np.mean([br_y - tl_y for _, (tl_x, tl_y), (br_x, br_y) in found_labels_coords])
    )

    padding_top = 6 * avg_label_height
    padding_bottom = 7 * avg_label_height
    padding_left = int(0 * avg_label_height)
    crop_right = 7

    plots_areas = []
    for label, (tl_x, tl_y), (br_x, br_y) in found_labels_coords:
        image = img_gray[
            tl_y - padding_top : br_y + padding_bottom,
            tl_x - padding_left : width - crop_right,
        ]

        label_center_absolute = (tl_x + (br_x - tl_x) // 2, tl_y + (br_y - tl_y) // 2)
        label_center = (
            label_center_absolute[0] - (tl_x - padding_left),
            label_center_absolute[1] - (tl_y - padding_top),
        )

        plots_areas.append(
            PlotArea(
                label,
                label_center=label_center,
                top_left_absolute=(tl_x - padding_left, tl_y - padding_top),
                bottom_right_absolute=(br_x, br_y + padding_bottom),
                image=image,
            )
        )

    return plots_areas


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--input_dir", type=str, help="Directory with input images")
    argparser.add_argument(
        "--output_dir", type=str, help="Directory to save output CSV files"
    )
    argparser.add_argument(
        "--debug_dir",
        type=str,
        default="debug_dir",
        help="Directory to save debug images",
    )

    args = argparser.parse_args()

    if not args.input_dir:
        raise ValueError(f"Provided images_dir {args.images_dir} is not a directory")

    input_dir = Path(args.input_dir)

    csv_output_dir = Path(args.output_dir)
    os.makedirs(csv_output_dir, exist_ok=True)

    plot_output_dir = Path(args.debug_dir)
    os.makedirs(plot_output_dir, exist_ok=True)

    images_filenames = [filename for filename in os.listdir(input_dir)]

    for filename in images_filenames:
        image_path = IMAGES_DIR.joinpath(filename)
        assert image_path.exists(), f"Image {filename} not found at {image_path}"

    for name, path in TEMPLATES.items():
        assert path.exists(), f"Pattern {name} not found at {path}"

    loaded_templates = {}
    for name, path in TEMPLATES.items():
        template = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        assert template is not None, f"Failed to load template {name} from {path}"

        loaded_templates[name] = template

    images_with_labels_marked = []
    images_with_labels_removed = []
    images_binary = []

    for image_idx, filename in enumerate(images_filenames):
        image_path = IMAGES_DIR.joinpath(filename)
        img_color = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        assert img_color is not None, (
            f"Failed to load image {filename} from {image_path}"
        )

        img_gray = cv2.cvtColor(img_color, cv2.COLOR_BGR2GRAY)

        img_gray_no_labels = img_gray.copy()
        img_for_templates = img_gray.copy()

        img_display = img_color.copy()

        found_labels_coords = []
        for template_name, template in loaded_templates.items():
            res = cv2.matchTemplate(img_for_templates, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)

            h, w = template.shape
            top_left = max_loc
            bottom_right = (top_left[0] + w, top_left[1] + h)

            found_labels_coords.append((template_name, top_left, bottom_right))

            img_gray_no_labels = remove_label_by_template(
                img_gray_no_labels, template, tuple(top_left)
            )

            cv2.rectangle(img_for_templates, top_left, bottom_right, 0, -1)

            bbox_color = (0, 255, 0)
            cv2.rectangle(img_display, top_left, bottom_right, bbox_color, 4)

            label_position = (top_left[0], top_left[1] - 10)

            cv2.putText(
                img_display,
                f"{template_name}",
                label_position,
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                bbox_color,
                2,
            )
        img_display_rgb = cv2.cvtColor(img_display, cv2.COLOR_BGR2RGB)

        images_with_labels_marked.append(img_display_rgb.copy())
        images_with_labels_removed.append(img_gray_no_labels.copy())

        _, img_binary = cv2.threshold(img_gray_no_labels, 127, 255, cv2.THRESH_BINARY)
        images_binary.append(img_binary.copy())

        plot_areas = get_plots_roi(img_binary, found_labels_coords)
        plot_areas.sort(key=lambda x: LABELS.index(x.label))

        signal_functions = []
        for plot_area in plot_areas:
            signal_function = get_signal_function_by_contour(plot_area)
            signal_functions.append(signal_function)

            if image_idx == 1 and plot_area.label == "V2":
                plot_signal_function(plot_area, signal_function, display=False)

        plot_plots_areas_in_parts(
            plot_areas,
            save_dir=plot_output_dir,
            save_path_prefix=filename.replace(".png", "_"),
            display=False,
        )

        filename_base = Path(filename).stem
        csv_output_path = csv_output_dir.joinpath(f"{filename_base}.csv")

        save_signal_functions_to_csv(signal_functions, csv_output_path)

        plot_signal_functions_on_whole_image(
            img_color,
            signal_functions,
            plot_areas,
            save_path=plot_output_dir.joinpath(
                f"{filename_base}_signal_functions.png"
            ),
            display=False,
        )

    plot_images(
        images_with_labels_marked,
        save_path=plot_output_dir.joinpath("images_marked_templates.png"),
        display=False,
    )
    plot_images(
        images_with_labels_removed,
        save_path=plot_output_dir.joinpath("images_removed_labels.png"),
        display=False,
    )
    plot_images(
        images_binary,
        display=False,
        save_path=plot_output_dir.joinpath("images_binary.png"),
    )


if __name__ == "__main__":
    main()
