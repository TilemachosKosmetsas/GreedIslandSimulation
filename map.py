# map.py
import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter
from skimage.draw import polygon
import random
from matplotlib.lines import Line2D
import yaml
import os

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

with open(CONFIG_PATH, "r") as config_file:
    config = yaml.safe_load(config_file)

# ===============================
# Configuration Parameters
# ===============================

# Map Configuration
MAP_HEIGHT_KM = config["map"]["dimensions"]["height_km"]  # Map height in kilometers
MAP_WIDTH_KM = config["map"]["dimensions"]["width_km"]  # Map width in kilometers
CELL_SIZE_M = config["map"]["dimensions"]["cell_size_m"]  # Cell size in meters

# Visibility Modifiers
SEA_VISIBILITY = config["map"]["visibility"]["sea"]  # Visibility modifier for sea
LAND_DEFAULT_VISIBILITY = config["map"]["visibility"][
    "land_default"
]  # Default visibility modifier on land

# Island Parameters
ISLAND_CENTER1_X_RATIO = config["map"]["island"]["center1"]["x_ratio"]
ISLAND_CENTER1_Y_RATIO = config["map"]["island"]["center1"]["y_ratio"]
ISLAND_RADIUS1_RATIO = config["map"]["island"]["radius1_ratio"]

ISLAND_CENTER2_X_RATIO = config["map"]["island"]["center2"]["x_ratio"]
ISLAND_CENTER2_Y_RATIO = config["map"]["island"]["center2"]["y_ratio"]
ISLAND_RADIUS2_RATIO = config["map"]["island"]["radius2_ratio"]

# Lake Parameters
LAKE_NUM_POINTS = config["map"]["lake"]["num_points"]
LAKE_RADIUS_RATIO = config["map"]["lake"]["radius_ratio"]
LAKE_RADIUS_VARIATION = config["map"]["lake"]["radius_variation"]
LAKE_CENTER_X_RATIO = config["map"]["lake"]["center_x_ratio"]
LAKE_CENTER_Y_RATIO = config["map"]["lake"]["center_y_ratio"]

# Walls Parameters
WALLS_NUM_WALLS = config["map"]["walls"]["num_walls"]
WALLS_LENGTH_RATIO_MIN = config["map"]["walls"]["length_ratio_min"]
WALLS_LENGTH_RATIO_MAX = config["map"]["walls"]["length_ratio_max"]
WALLS_THICKNESS_MIN = config["map"]["walls"]["thickness_min"]
WALLS_THICKNESS_MAX = config["map"]["walls"]["thickness_max"]
WALLS_BREAK_PROBABILITY = config["map"]["walls"]["break_probability"]

# Forests Parameters
FORESTS_NUM_FORESTS = config["map"]["forests"]["num_forests"]
FORESTS_RADIUS_RATIO_MIN = config["map"]["forests"]["radius_ratio_min"]
FORESTS_RADIUS_RATIO_MAX = config["map"]["forests"]["radius_ratio_max"]
FORESTS_NUM_POINTS_MIN = config["map"]["forests"]["num_points_min"]
FORESTS_NUM_POINTS_MAX = config["map"]["forests"]["num_points_max"]
FORESTS_VISIBILITY_INCREMENT = config["map"]["forests"]["visibility_increment"]
FORESTS_VISIBILITY_DECAY = config["map"]["forests"]["visibility_decay"]

# ===============================
# Map Initialization
# ===============================

# Convert dimensions to meters
MAP_HEIGHT_M = MAP_HEIGHT_KM * 1000
MAP_WIDTH_M = MAP_WIDTH_KM * 1000

# Calculate grid dimensions
GRID_HEIGHT = int(MAP_HEIGHT_M / CELL_SIZE_M)
GRID_WIDTH = int(MAP_WIDTH_M / CELL_SIZE_M)

# Initialize the map grid
# Each cell will have 'accessible' and 'visibility' attributes
map_grid = np.zeros(
    (GRID_HEIGHT, GRID_WIDTH), dtype=[("accessible", "i4"), ("visibility", "f4")]
)

# Initialize all cells as inaccessible (sea)
map_grid["accessible"] = 0
map_grid["visibility"] = SEA_VISIBILITY  # Sea has low visibility for hiding


def create_island():
    """
    Creates an island by defining two overlapping circles and updating the map grid accordingly.
    """
    center1 = (
        GRID_WIDTH * ISLAND_CENTER1_X_RATIO,
        GRID_HEIGHT * ISLAND_CENTER1_Y_RATIO,
    )
    radius1 = GRID_HEIGHT * ISLAND_RADIUS1_RATIO  # Left circle with smaller radius

    center2 = (
        GRID_WIDTH * ISLAND_CENTER2_X_RATIO,
        GRID_HEIGHT * ISLAND_CENTER2_Y_RATIO,
    )
    radius2 = GRID_HEIGHT * ISLAND_RADIUS2_RATIO  # Right circle with larger radius

    Y, X = np.ogrid[:GRID_HEIGHT, :GRID_WIDTH]
    distance1 = (X - center1[0]) ** 2 + (Y - center1[1]) ** 2
    distance2 = (X - center2[0]) ** 2 + (Y - center2[1]) ** 2

    mask1 = distance1 <= radius1**2
    mask2 = distance2 <= radius2**2

    island_mask = mask1 | mask2  # Union of the two circles

    # Update accessibility for the island area
    map_grid["accessible"][island_mask] = 1
    # Default visibility on land
    map_grid["visibility"][island_mask] = LAND_DEFAULT_VISIBILITY


def create_irregular_lake():
    """
    Creates an irregularly shaped lake within the island and updates the map grid.
    """
    num_points = LAKE_NUM_POINTS
    angle = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
    radius = (
        GRID_HEIGHT
        * LAKE_RADIUS_RATIO
        * (1 + LAKE_RADIUS_VARIATION * np.random.rand(num_points))
    )  # Larger lake

    x_center = GRID_WIDTH * LAKE_CENTER_X_RATIO
    y_center = GRID_HEIGHT * LAKE_CENTER_Y_RATIO

    x = x_center + radius * np.cos(angle)
    y = y_center + radius * np.sin(angle)

    # Convert coordinates to integer indices
    x = x.astype(int)
    y = y.astype(int)

    # Ensure indices are within bounds
    x = np.clip(x, 0, GRID_WIDTH - 1)
    y = np.clip(y, 0, GRID_HEIGHT - 1)

    # Use integer indices in the correct order
    rr, cc = polygon(y, x, map_grid.shape)

    # Update accessibility and visibility for the lake area
    map_grid["accessible"][rr, cc] = 0  # Non-accessible (lake)
    map_grid["visibility"][rr, cc] = SEA_VISIBILITY  # Open area over water


def create_walls():
    """
    Creates walls with varying shapes and thicknesses on the map.
    """
    num_walls = WALLS_NUM_WALLS
    for wall_index in range(num_walls):
        # Random starting point within the island
        attempts = 0
        max_attempts = 1000
        while attempts < max_attempts:
            start_x = random.randint(0, GRID_WIDTH - 1)
            start_y = random.randint(0, GRID_HEIGHT - 1)
            if map_grid["accessible"][start_y, start_x] == 1:
                break
            attempts += 1
        else:
            # If no valid starting point is found, skip this wall
            continue

        # Random direction and length
        length = random.randint(
            int(GRID_HEIGHT * WALLS_LENGTH_RATIO_MIN),
            int(GRID_HEIGHT * WALLS_LENGTH_RATIO_MAX),
        )  # Longer walls
        thickness = random.randint(
            WALLS_THICKNESS_MIN, WALLS_THICKNESS_MAX
        )  # Thicker walls

        angle = random.uniform(0, 2 * np.pi)

        # Create a break in one of the walls based on probability
        if wall_index == 0 and random.random() <= WALLS_BREAK_PROBABILITY:
            # Wall with a break
            break_point = random.uniform(0.3, 0.7)  # Break somewhere in the middle

            # First segment
            num_points1 = int(length * break_point)
            x_end1 = start_x + num_points1 * np.cos(angle)
            y_end1 = start_y + num_points1 * np.sin(angle)

            x_coords1 = np.linspace(start_x, x_end1, num=num_points1)
            y_coords1 = np.linspace(start_y, y_end1, num=num_points1)

            # Second segment (after the break)
            num_points2 = length - num_points1
            x_start2 = x_end1 + (thickness + 2) * np.cos(angle)
            y_start2 = y_end1 + (thickness + 2) * np.sin(angle)
            x_end2 = x_start2 + num_points2 * np.cos(angle)
            y_end2 = y_start2 + num_points2 * np.sin(angle)

            x_coords2 = np.linspace(x_start2, x_end2, num=num_points2 + 10)
            y_coords2 = np.linspace(y_start2, y_end2, num=num_points2 + 10)

            # Combine coordinates
            x_coords = np.concatenate([x_coords1, x_coords2])
            y_coords = np.concatenate([y_coords1, y_coords2])
        else:
            # Continuous wall
            x_end = start_x + length * np.cos(angle)
            y_end = start_y + length * np.sin(angle)

            x_coords = np.linspace(start_x, x_end, num=length * 2)
            y_coords = np.linspace(start_y, y_end, num=length * 2)

        # Create thickness around the line
        for offset in np.linspace(-thickness, thickness, int(thickness * 3)):
            rr = np.clip(
                np.round(y_coords + offset * np.cos(angle + np.pi / 2)).astype(int),
                0,
                GRID_HEIGHT - 1,
            )
            cc = np.clip(
                np.round(x_coords + offset * np.sin(angle + np.pi / 2)).astype(int),
                0,
                GRID_WIDTH - 1,
            )

            # Only update cells within the island
            valid_indices = map_grid["accessible"][rr, cc] == 1
            map_grid["accessible"][
                rr[valid_indices], cc[valid_indices]
            ] = 0  # Wall is non-accessible
            map_grid["visibility"][
                rr[valid_indices], cc[valid_indices]
            ] = SEA_VISIBILITY  # Open area along the wall


def create_forest_clusters():
    """
    Creates forest clusters with irregular shapes and updates the map grid.
    """
    num_forests = FORESTS_NUM_FORESTS
    for _ in range(num_forests):
        # Random center within the island
        attempts = 0
        max_attempts = 1000
        while attempts < max_attempts:
            center_x = random.uniform(0, GRID_WIDTH - 1)
            center_y = random.uniform(0, GRID_HEIGHT - 1)
            if map_grid["accessible"][int(center_y), int(center_x)] == 1:
                break
            attempts += 1
        else:
            # If no valid center is found, skip this forest cluster
            continue

        radius = (
            random.uniform(FORESTS_RADIUS_RATIO_MIN, FORESTS_RADIUS_RATIO_MAX)
            * GRID_HEIGHT
        )

        num_points = random.randint(FORESTS_NUM_POINTS_MIN, FORESTS_NUM_POINTS_MAX)
        angle = np.linspace(0, 2 * np.pi, num_points, endpoint=False)
        radius_variation = radius * (
            1 + 0.6 * np.random.rand(num_points) - 0.3
        )  # Increased variation

        x = center_x + radius_variation * np.cos(angle)
        y = center_y + radius_variation * np.sin(angle)

        # Create a mask for the forest area
        rr, cc = polygon(y, x, map_grid.shape)

        # Assign high visibility modifiers (for hiding) to the forest area
        distances = np.sqrt((rr - center_y) ** 2 + (cc - center_x) ** 2)
        visibility_values = np.maximum(
            FORESTS_VISIBILITY_INCREMENT
            - (distances / radius) * FORESTS_VISIBILITY_DECAY,
            0,
        )

        # Smooth the visibility values
        visibility_patch = np.zeros(map_grid.shape)
        visibility_patch[rr, cc] = visibility_values
        visibility_patch = gaussian_filter(visibility_patch, sigma=2)

        # Update the map grid with the visibility modifiers, only on accessible land
        valid_indices = map_grid["accessible"] == 1
        map_grid["visibility"][valid_indices] += visibility_patch[valid_indices]


def visualize_map(hunters=None):
    """
    Visualizes the map's accessibility and visibility modifiers. Optionally overlays hunters on the map.
    """
    accessible = map_grid["accessible"]
    visibility = map_grid["visibility"]

    # Define legend elements for hunters
    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="Aggressive",
            markerfacecolor=config["visualization"]["hunter_markers"]["aggressive"][
                "color"
            ],
            markersize=config["visualization"]["hunter_markers"]["aggressive"]["size"],
            markeredgecolor=config["visualization"]["hunter_markers"]["aggressive"][
                "edgecolor"
            ],
        ),
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="Defensive",
            markerfacecolor=config["visualization"]["hunter_markers"]["defensive"][
                "color"
            ],
            markersize=config["visualization"]["hunter_markers"]["defensive"]["size"],
            markeredgecolor=config["visualization"]["hunter_markers"]["defensive"][
                "edgecolor"
            ],
        ),
    ]

    # First Figure: Map Accessibility
    plt.figure(figsize=tuple(config["visualization"]["figure_size"]))
    plt.title("Map Accessibility")
    plt.imshow(
        accessible,
        cmap=config["visualization"]["map_accessibility_cmap"],
        origin="lower",
    )
    plt.xlabel("X coordinate")
    plt.ylabel("Y coordinate")

    # Overlay hunters on the accessibility map if they exist
    if hunters:
        for hunter in hunters:
            x, y = hunter.position
            color = (
                config["visualization"]["hunter_markers"]["aggressive"]["color"]
                if hunter.strategy >= 10
                else config["visualization"]["hunter_markers"]["defensive"]["color"]
            )
            plt.scatter(
                x,
                y,
                c=color,
                marker=config["visualization"]["hunter_markers"]["aggressive"][
                    "marker"
                ],
                edgecolors=config["visualization"]["hunter_markers"]["aggressive"][
                    "edgecolor"
                ],
                s=config["visualization"]["hunter_markers"]["aggressive"]["size"],
            )
            plt.text(
                x + 1,
                y + 1,
                f"ID:{hunter.unique_id}",
                fontsize=config["visualization"]["hunter_labels"]["fontsize"],
                color=config["visualization"]["hunter_labels"]["color"],
            )
        plt.legend(handles=legend_elements, loc="upper right")

    plt.colorbar(label="Accessible (1) or Not (0)")
    plt.show()

    # Second Figure: Map Visibility Modifiers
    plt.figure(figsize=tuple(config["visualization"]["figure_size"]))
    plt.title("Map Visibility Modifiers")
    plt.imshow(
        visibility,
        cmap=config["visualization"]["map_visibility_cmap"],
        origin="lower",
        vmin=-5,
        vmax=5,
    )
    plt.xlabel("X coordinate")
    plt.ylabel("Y coordinate")

    # Overlay hunters on the visibility map if they exist
    if hunters:
        for hunter in hunters:
            x, y = hunter.position
            color = (
                config["visualization"]["hunter_markers"]["aggressive"]["color"]
                if hunter.strategy >= 10
                else config["visualization"]["hunter_markers"]["defensive"]["color"]
            )
            plt.scatter(
                x,
                y,
                c=color,
                marker=config["visualization"]["hunter_markers"]["aggressive"][
                    "marker"
                ],
                edgecolors=config["visualization"]["hunter_markers"]["aggressive"][
                    "edgecolor"
                ],
                s=config["visualization"]["hunter_markers"]["aggressive"]["size"],
            )
            plt.text(
                x + 1,
                y + 1,
                f"ID:{hunter.unique_id}",
                fontsize=config["visualization"]["hunter_labels"]["fontsize"],
                color=config["visualization"]["hunter_labels"]["color"],
            )
        plt.legend(handles=legend_elements, loc="upper right")

    plt.colorbar(label="Visibility Modifier (-5 to +5)")
    plt.show()


# Run the functions to create the map
create_island()
create_irregular_lake()
create_walls()
create_forest_clusters()

# Only execute the visualization if this script is run directly
if __name__ == "__main__":
    # Call the visualization function
    visualize_map()
