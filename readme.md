# Hunter Simulation Project

This project simulates a dynamic hunter environment on a generated map. Hunters navigate a terrain composed of islands, lakes, walls, and forests while engaging in combat and gathering statistics over multiple simulation steps. The simulation can be run interactively via a Streamlit web app.

## Table of Contents

- [Overview](#overview)
- [File Overview](#file-overview)
  - [map.py](#mappy)
  - [hunters.py](#hunterspy)
  - [simulation.py](#simulationpy)
  - [animate_simulation_pickled.py](#animate_simulation_pickledpy)
  - [savemp4.py](#savemp4py)
  - [config.yaml](#configyaml)
  - [app.py](#apppy)
- [Installation & Running Locally](#installation--running-locally)

## Overview

The simulation creates a grid-based map that includes an island with a lake, walls, and forest clusters. Hunters are spawned on the map and interact based on a set of configurable attributes (such as strength, hiding skills, and Elo ratings for combat). The simulation runs for a number of steps, and results (including statistics and a video animation) are generated and can be downloaded via a user-friendly Streamlit interface.

## File Overview

### map.py

- **Purpose:** Generates the simulation map and sets up the terrain.
- **Key Functions:**
  - `create_island()`: Combines two circles to form an island.
  - `create_irregular_lake()`: Uses a polygon to create an irregularly shaped lake.
  - `create_walls()`: Generates walls with random orientations, lengths, and breaks.
  - `create_forest_clusters()`: Creates forest areas with varied visibility modifiers.
  - `visualize_map()`: Provides matplotlib-based visualization of map accessibility and visibility.

### hunters.py

- **Purpose:** Defines the `Hunter` class and manages hunter behavior.
- **Key Methods in `Hunter` Class:**
  - `sense_nearby_hunters()`: Allows a hunter to detect nearby opponents.
  - `decide_combat()` and `engage_combat()`: Handle combat decisions and outcomes using an Elo-based system.
  - `update_aggression()`: Adjusts hunter aggression based on interactions.
  - `move_towards()` and `move_away_from()`: Control hunter movement and pathfinding.
- **Other Functions:**
  - `remove_hunter_from_game()`: Handles hunter removal after combat.

### simulation.py

- **Purpose:** Runs the overall simulation.
- **Key Functions:**
  - `initialize_hunters()`: Creates a list of `Hunter` instances with randomized attributes.
  - `run_simulation()`: Executes simulation steps, updates hunter states, logs events, and saves simulation snapshots using pickle.
  - `calculate_statistics()`: Computes key metrics such as alive/winning hunters and average scores.

### animate_simulation_pickled.py

- **Purpose:** Animates the simulation by loading saved pickle data.
- **Key Features:**
  - Loads simulation snapshots and the map grid.
  - Creates an animation using Matplotlib’s animation module.
  - Optionally saves the animation as an MP4 using OpenCV via the function in `savemp4.py`.

### savemp4.py

- **Purpose:** Provides functionality to save the simulation animation as an MP4 file.
- **Key Function:**
  - `save_animation_with_opencv()`: Takes simulation data, map grid, and config to generate and save a video.

### config.yaml

- **Purpose:** Stores all configurable parameters.
- **Highlights:**
  - **Map Settings:** Dimensions, visibility modifiers, island, lake, walls, and forest parameters.
  - **Hunters Settings:** Attributes ranges, combat, movement, and sensing parameters.
  - **Simulation Settings:** Number of hunters, steps, death chance, and data storage files.
  - **Animation & Visualization:** Frame intervals, file names, colormaps, and marker styles.
  - **Logging:** Levels and formats for different parts of the simulation.

### app.py

- **Purpose:** The Streamlit front-end that allows users to interact with the simulation.
- **Key Features:**
  - Sidebar sliders let users adjust simulation parameters (map size, number of walls/forests, combat settings, etc.).
  - A top row with a **Run Simulation** button and progress bar.
  - Simulation progress is displayed in four steps: spawning hunters, running simulation steps, saving the animation, and finalizing.
  - Once complete, the app shows:
    - A download button for the generated MP4 video (centered at the bottom).
    - Simulation statistics and a histogram of Elo ratings displayed side by side.
- **Major Functions Used:**
  - `initialize_hunters()`, `run_simulation()`, and `save_animation_with_opencv()` are called to generate simulation results.
  - A custom `compute_statistics()` function computes KPIs from the final hunter data.

## Installation & Running Locally

1. **Clone the Repository:**

```
git clone https://github.com/yourusername/hunter-simulation.git
cd hunter-simulation

```

2. **Install Dependencies: Ensure you have Python 3.7+ installed. Then run:**

```
pip install -r requirements.txt

```

3. **Run the App:**

```
streamlit run app.py
```
