# simulation.py
import random
import copy
import pickle
import logging
import yaml
import os
from hunters import Hunter, remove_hunter_from_game, grid_index
from map import GRID_WIDTH, GRID_HEIGHT, map_grid, visualize_map

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

with open(CONFIG_PATH, "r") as config_file:
    config = yaml.safe_load(config_file)

# ===============================
# Configuration Parameters
# ===============================

# Simulation Configuration
NUM_HUNTERS = config["simulation"]["num_hunters"]
STEPS = config["simulation"]["steps"]
SIMULATION_DATA_FILE = config["simulation"]["data_storage"]["simulation_data_file"]
MAP_GRID_FILE = config["simulation"]["data_storage"]["map_grid_file"]
DEATH_CHANCE = config["simulation"]["combat"]["death_chance"]

# Logging Configuration
logging_level = getattr(logging, config["logging"]["simulation"]["level"])
logging.basicConfig(
    filename=config["general"]["logging"]["filename"],  # Log file name
    filemode=config["general"]["logging"][
        "filemode"
    ],  # 'w' to overwrite, 'a' to append
    level=logging_level,  # Logging level
    format=config["general"]["logging"]["format"],  # Log format
)

# ===============================
# Function Definitions
# ===============================


def initialize_hunters(num_hunters):
    """
    Initializes a list of Hunter instances based on the configuration parameters.

    Args:
        num_hunters (int): The number of hunters to initialize.

    Returns:
        list: A list of initialized Hunter instances.
    """
    hunters_list = []
    for i in range(num_hunters):
        strength = random.randint(
            config["hunters"]["attributes"]["strength_range"][0],
            config["hunters"]["attributes"]["strength_range"][1],
        )
        hiding_skill = random.randint(
            config["hunters"]["attributes"]["hiding_skill_range"][0],
            config["hunters"]["attributes"]["hiding_skill_range"][1],
        )
        unique_id = i
        knows_their_enemy = random.choice([True, False])
        enemy_id = random.randint(0, num_hunters - 1)
        while enemy_id == unique_id:
            enemy_id = random.randint(0, num_hunters - 1)
        strategy = random.randint(
            config["hunters"]["attributes"]["strategy_range"][0],
            config["hunters"]["attributes"]["strategy_range"][1],
        )
        sensing = random.randint(
            config["hunters"]["attributes"]["sensing_range"][0],
            config["hunters"]["attributes"]["sensing_range"][1],
        )
        hunter = Hunter(
            strength,
            hiding_skill,
            unique_id,
            knows_their_enemy,
            enemy_id,
            strategy,
            sensing,
        )
        hunters_list.append(hunter)
    return hunters_list


def attempt_escape(defender, attacker, distance):
    """
    Determines whether the defender successfully escapes from the attacker based on escape chances.

    Args:
        defender (Hunter): The defending hunter attempting to escape.
        attacker (Hunter): The attacking hunter.
        distance (float): The distance between the defender and attacker.

    Returns:
        bool: True if escape is successful, False otherwise.
    """
    # Base escape chance from configuration
    base_escape_chance = config["hunters"]["combat"]["escape_base_chance"]

    # Modify escape chance based on distance
    if distance < config["hunters"]["combat"]["escape_distance_threshold_close"]:
        escape_chance = (
            base_escape_chance
            * config["hunters"]["combat"]["escape_chance_modifier_close"]
        )
    elif distance > config["hunters"]["combat"]["escape_distance_threshold_far"]:
        escape_chance = (
            base_escape_chance
            * config["hunters"]["combat"]["escape_chance_modifier_far"]
        )
    else:
        escape_chance = base_escape_chance

    # Ensure escape chance is within [0,1]
    escape_chance = max(0, min(escape_chance, 1))

    # Random chance to determine if escape is successful
    return random.random() < escape_chance


def process_hunter(hunter, hunters_list):
    """
    Processes a single hunter's actions for the current simulation step.

    Args:
        hunter (Hunter): The hunter to process.
        hunters_list (list): The current list of active hunters.
    """
    sensed_hunters = hunter.sense_nearby_hunters()
    hunter.decide_movement(sensed_hunters)

    # Engage in combat with sensed hunters
    for other, distance in sensed_hunters:
        if hunter.decide_combat(other, distance):
            # Check if the other hunter also wants to fight
            if other.decide_combat(hunter, distance):
                # Both hunters want to fight
                combat_result = hunter.engage_combat(other, hunters_list)
                break  # Only one combat per turn
            else:
                # Defender does not want to fight
                if attempt_escape(defender=other, attacker=hunter, distance=distance):
                    # Defender successfully escapes
                    logging.info(
                        f"Hunter {other.unique_id} escapes from Hunter {hunter.unique_id}"
                    )
                    other.move_away_from(hunter.position)
                else:
                    # Defender fails to escape; combat occurs
                    combat_result = hunter.engage_combat(other, hunters_list)
                break  # Only one combat per turn


def run_simulation(hunters_list, steps):
    """
    Runs the simulation for a specified number of steps.

    Args:
        hunters_list (list): The initial list of hunters.
        steps (int): The number of simulation steps to run.

    Returns:
        list: A list containing snapshots of hunters at each simulation step.
    """
    hunters_over_time = []
    for step in range(steps):
        logging.info(f"--- Step {step + 1} ---")

        # # Update aggression for each hunter
        # for hunter in hunters_list.copy():
        #     hunter.update_aggression()

        # Each hunter senses and decides movement
        for hunter in hunters_list.copy():
            hunter.update_aggression()
            process_hunter(hunter, hunters_list)

        # Collect data for animation
        # Deep copy the hunters_list to capture their states at this time step
        hunters_snapshot = copy.deepcopy(hunters_list)
        hunters_over_time.append(hunters_snapshot)

        # Optionally visualize the map at certain steps (e.g., every 100 steps)
        # if (step + 1) % 100 == 0:
        #     visualize_map(hunters_list)

    # Save the simulation data
    with open(SIMULATION_DATA_FILE, "wb") as f:
        pickle.dump(hunters_over_time, f)

    # Save the map grid
    with open(MAP_GRID_FILE, "wb") as f:
        pickle.dump(map_grid, f)

    return hunters_over_time


def calculate_statistics(hunters_list, total_initial_hunters):
    """
    Calculates and logs various statistics after the simulation.

    Args:
        hunters_list (list): The final list of active hunters.
        total_initial_hunters (int): The initial number of hunters at simulation start.
    """
    alive_hunters = [hunter for hunter in hunters_list]
    num_alive = len(alive_hunters)

    if num_alive > 0:
        avg_score_alive = sum(h.card_score for h in alive_hunters) / num_alive
        max_score_alive = max(h.card_score for h in alive_hunters)
        min_score_alive = min(h.card_score for h in alive_hunters)
    else:
        avg_score_alive = max_score_alive = min_score_alive = 0

    # Including dead hunters
    avg_score_total = sum(h.card_score for h in hunters_list) / total_initial_hunters

    # Winners
    winning_hunters = len([hunter for hunter in hunters_list if hunter.card_score >= 6])

    logging.info(f"Number of alive hunters: {num_alive}")
    logging.info(f"Number of winning hunters: {winning_hunters}")
    logging.info(f"Average score of alive hunters: {avg_score_alive:.2f}")
    logging.info(f"Max score of alive hunters: {max_score_alive}")
    logging.info(f"Min score of alive hunters: {min_score_alive}")
    logging.info(f"Average score including dead hunters: {avg_score_total:.2f}")

    if num_alive > 0:
        ratio = winning_hunters / num_alive
    else:
        ratio = 0
    logging.info(f"Winning to alive ratio: {ratio:.2f}")


# ===============================
# Main Execution
# ===============================

if __name__ == "__main__":
    # Initialize hunters based on configuration
    hunters_list = initialize_hunters(NUM_HUNTERS)
    logging.info(f"Initialized {NUM_HUNTERS} hunters.")

    # Run the simulation
    hunters_over_time = run_simulation(hunters_list, STEPS)
    logging.info(f"Simulation completed after {STEPS} steps.")

    # Calculate and log statistics
    calculate_statistics(hunters_list, NUM_HUNTERS)
