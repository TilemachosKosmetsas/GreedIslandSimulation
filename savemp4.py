import cv2
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def save_animation_with_opencv(hunters_over_time, map_grid, config):
    """
    Saves an animation as an MP4 file using OpenCV's VideoWriter.

    Args:
        hunters_over_time (list): List of hunter snapshots for each frame.
        map_grid (ndarray): The map grid data.
        config (dict): Configuration dictionary loaded from config.yaml.

    Returns:
        str: The filename of the saved MP4 video.
    """
    # Retrieve visualization settings from config
    viz = config["visualization"]
    figure_size = tuple(viz["figure_size"])  # in inches
    dpi = 100  # You can also make this configurable if desired
    width_px = int(figure_size[0] * dpi)
    height_px = int(figure_size[1] * dpi)

    # Retrieve animation settings from config
    anim_config = config["animation"]
    frame_interval_ms = anim_config["frame_interval_ms"]
    fps = 1000 / frame_interval_ms  # frames per second
    output_filename = anim_config["animation_file"]

    # Create an OpenCV VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")  # On Windows, 'mp4v' works well
    video_writer = cv2.VideoWriter(output_filename, fourcc, fps, (width_px, height_px))

    # Create a Matplotlib figure
    fig, ax = plt.subplots(figsize=figure_size, dpi=dpi)

    # Retrieve visualization details for hunters
    MAP_VISIBILITY_CMAP = viz["map_visibility_cmap"]
    hunter_markers = viz["hunter_markers"]
    hunter_labels = viz["hunter_labels"]

    # Loop over each frame (each snapshot in hunters_over_time)
    for frame in range(len(hunters_over_time)):
        ax.clear()
        # Draw the map background
        visibility = map_grid["visibility"]
        ax.imshow(visibility, cmap=MAP_VISIBILITY_CMAP, origin="lower")
        ax.set_title(f"Hunter Simulation - Step {frame + 1}")
        ax.set_xlabel("X coordinate")
        ax.set_ylabel("Y coordinate")

        # Plot the hunters for the current frame
        hunters = hunters_over_time[frame]
        x_positions = [hunter.position[0] for hunter in hunters]
        y_positions = [hunter.position[1] for hunter in hunters]
        colors = [
            (
                hunter_markers["aggressive"]["color"]
                if hunter.strategy >= 10
                else hunter_markers["defensive"]["color"]
            )
            for hunter in hunters
        ]

        ax.scatter(
            x_positions,
            y_positions,
            c=colors,
            marker=hunter_markers["aggressive"]["marker"],
            edgecolors=hunter_markers["aggressive"]["edgecolor"],
            s=hunter_markers["aggressive"]["size"],
            alpha=0.7,
        )

        for hunter in hunters:
            x, y = hunter.position
            ax.text(
                x + 1,
                y + 1,
                f"ID:{hunter.unique_id}",
                fontsize=hunter_labels["fontsize"],
                color=hunter_labels["color"],
            )

        # Add a legend
        legend_elements = [
            Line2D(
                [0],
                [0],
                marker=hunter_markers["aggressive"]["marker"],
                color="w",
                label="Aggressive",
                markerfacecolor=hunter_markers["aggressive"]["color"],
                markersize=hunter_markers["aggressive"]["size"],
                markeredgecolor=hunter_markers["aggressive"]["edgecolor"],
            ),
            Line2D(
                [0],
                [0],
                marker=hunter_markers["defensive"]["marker"],
                color="w",
                label="Defensive",
                markerfacecolor=hunter_markers["defensive"]["color"],
                markersize=hunter_markers["defensive"]["size"],
                markeredgecolor=hunter_markers["defensive"]["edgecolor"],
            ),
        ]
        ax.legend(handles=legend_elements, loc="upper right")

        # Render the figure to a canvas and convert to an image array
        fig.canvas.draw()
        img = np.frombuffer(fig.canvas.tostring_rgb(), dtype=np.uint8)
        img = img.reshape(fig.canvas.get_width_height()[::-1] + (3,))

        # Convert RGB to BGR (OpenCV expects BGR)
        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

        # Write the frame to the video
        video_writer.write(img_bgr)

    # Release the VideoWriter and close the figure
    video_writer.release()
    plt.close(fig)

    return output_filename
