# animate_simulation_pickled.py
import pickle
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import logging
import yaml
import os
from matplotlib.lines import Line2D
from savemp4 import save_animation_with_opencv

# ===============================
# Configuration Loading
# ===============================


def load_config():
    """
    Loads the configuration from config.yaml.

    Returns:
        dict: Parsed configuration dictionary.
    """
    CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(CONFIG_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)
    return config


# ===============================
# Main Execution
# ===============================


def main():
    # Load configuration
    config = load_config()

    # Validate configuration (optional, can implement a validation function)

    # ===============================
    # Logging Configuration
    # ===============================

    # Set up logging based on configuration
    logging_level_str = config["logging"]["animation"]["level"]
    try:
        logging_level = getattr(logging, logging_level_str.upper())
    except AttributeError:
        logging_level = logging.WARNING
        logging.warning(
            f"Invalid logging level '{logging_level_str}'. Defaulting to WARNING."
        )

    logging.basicConfig(
        filename=config["general"]["logging"]["filename"],
        filemode=config["general"]["logging"]["filemode"],
        level=logging_level,
        format=config["general"]["logging"]["format"],
    )

    # ===============================
    # Load Simulation Data and Map Grid
    # ===============================

    SIMULATION_DATA_FILE = config["simulation"]["data_storage"]["simulation_data_file"]
    MAP_GRID_FILE = config["simulation"]["data_storage"]["map_grid_file"]

    try:
        with open(SIMULATION_DATA_FILE, "rb") as f:
            hunters_over_time = pickle.load(f)
        logging.info(f"Loaded simulation data from {SIMULATION_DATA_FILE}.")
    except FileNotFoundError:
        logging.error(f"Simulation data file '{SIMULATION_DATA_FILE}' not found.")
        return
    except Exception as e:
        logging.error(f"Error loading simulation data: {e}")
        return

    try:
        with open(MAP_GRID_FILE, "rb") as f:
            map_grid = pickle.load(f)
        logging.info(f"Loaded map grid from {MAP_GRID_FILE}.")
    except FileNotFoundError:
        logging.error(f"Map grid file '{MAP_GRID_FILE}' not found.")
        return
    except Exception as e:
        logging.error(f"Error loading map grid: {e}")
        return

    # ===============================
    # Visualization Configuration
    # ===============================

    VISUALIZATION = config["visualization"]
    MAP_VISIBILITY_CMAP = VISUALIZATION["map_visibility_cmap"]
    FIGURE_SIZE = tuple(VISUALIZATION["figure_size"])
    HUNTER_MARKERS = VISUALIZATION["hunter_markers"]
    HUNTER_LABELS = VISUALIZATION["hunter_labels"]

    # ===============================
    # Animation Configuration
    # ===============================

    ANIMATION = config["animation"]
    FRAME_INTERVAL_MS = ANIMATION["frame_interval_ms"]
    SAVE_ANIMATION = ANIMATION["save_animation"]
    ANIMATION_FILE = ANIMATION["animation_file"]

    # ===============================
    # Setup Matplotlib Figure
    # ===============================

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    # ===============================
    # Define Update Function
    # ===============================

    def update(frame):
        """
        Updates the plot for each frame in the animation.

        Args:
            frame (int): The current frame number.

        Returns:
            tuple: A tuple containing the scatter plot object.
        """
        ax.clear()
        # Redraw the map
        visibility = map_grid["visibility"]
        ax.imshow(visibility, cmap=MAP_VISIBILITY_CMAP, origin="lower")
        ax.set_title(f"Hunter Simulation - Step {frame + 1}")
        ax.set_xlabel("X coordinate")
        ax.set_ylabel("Y coordinate")

        # Get the hunters at this time step
        hunters = hunters_over_time[frame]

        # Extract positions and colors based on strategy
        x_positions = [hunter.position[0] for hunter in hunters]
        y_positions = [hunter.position[1] for hunter in hunters]
        colors = [
            (
                HUNTER_MARKERS["aggressive"]["color"]
                if hunter.strategy >= 10
                else HUNTER_MARKERS["defensive"]["color"]
            )
            for hunter in hunters
        ]

        # Plot the hunters
        scatter = ax.scatter(
            x_positions,
            y_positions,
            c=colors,
            marker=HUNTER_MARKERS["aggressive"][
                "marker"
            ],  # Assuming same marker for both
            edgecolors=HUNTER_MARKERS["aggressive"][
                "edgecolor"
            ],  # Assuming same edge color for both
            s=HUNTER_MARKERS["aggressive"]["size"],  # Assuming same size for both
            alpha=0.7,  # Optional: add some transparency
        )

        # Annotate hunters with their IDs
        for hunter in hunters:
            x, y = hunter.position
            ax.text(
                x + 1,
                y + 1,
                f"ID:{hunter.unique_id}",
                fontsize=HUNTER_LABELS["fontsize"],
                color=HUNTER_LABELS["color"],
            )

        # Legend
        legend_elements = [
            Line2D(
                [0],
                [0],
                marker=HUNTER_MARKERS["aggressive"]["marker"],
                color="w",
                label="Aggressive",
                markerfacecolor=HUNTER_MARKERS["aggressive"]["color"],
                markersize=HUNTER_MARKERS["aggressive"]["size"],
                markeredgecolor=HUNTER_MARKERS["aggressive"]["edgecolor"],
            ),
            Line2D(
                [0],
                [0],
                marker=HUNTER_MARKERS["defensive"]["marker"],
                color="w",
                label="Defensive",
                markerfacecolor=HUNTER_MARKERS["defensive"]["color"],
                markersize=HUNTER_MARKERS["defensive"]["size"],
                markeredgecolor=HUNTER_MARKERS["defensive"]["edgecolor"],
            ),
        ]
        ax.legend(handles=legend_elements, loc="upper right")

        return (scatter,)

    # ===============================
    # Create Animation
    # ===============================

    ani = animation.FuncAnimation(
        fig,
        update,
        frames=len(hunters_over_time),
        blit=False,
        interval=FRAME_INTERVAL_MS,
        repeat=False,
    )

    # ===============================
    # Save Animation (Optional)
    # ===============================

    if SAVE_ANIMATION:
        try:
            save_animation_with_opencv(hunters_over_time, map_grid, config)
        except Exception as e:
            logging.error(f"Failed to save animation: {e}")

    # ===============================
    # Display Animation
    # ===============================

    else:
        plt.show()


# Run the animation
if __name__ == "__main__":
    main()
