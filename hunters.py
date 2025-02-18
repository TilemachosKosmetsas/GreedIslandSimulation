# hunters.py
import random
import numpy as np
from map import GRID_WIDTH, GRID_HEIGHT, map_grid
import logging
import yaml
import os

# Load configuration
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.yaml")

with open(CONFIG_PATH, "r") as config_file:
    config = yaml.safe_load(config_file)

# ===============================
# Configuration Parameters
# ===============================


# Precompute the list of all accessible positions once
ALL_ACCESSIBLE_POSITIONS = [
    tuple(pos[::-1]) for pos in np.argwhere(map_grid["accessible"] == 1)
]
ALL_ACCESSIBLE_POSITIONS_SET = set(ALL_ACCESSIBLE_POSITIONS)

# Hunters Configuration
GRID_CELL_SIZE = config["hunters"]["grid_cell_size"]

# Attributes Ranges
STRENGTH_MIN, STRENGTH_MAX = config["hunters"]["attributes"]["strength_range"]
HIDING_SKILL_MIN, HIDING_SKILL_MAX = config["hunters"]["attributes"][
    "hiding_skill_range"
]
STRATEGY_MIN, STRATEGY_MAX = config["hunters"]["attributes"]["strategy_range"]
SENSING_MIN, SENSING_MAX = config["hunters"]["attributes"]["sensing_range"]

# Combat Parameters (Note: now using Elo, so strength comparison is replaced)
ESCAPE_BASE_CHANCE = config["hunters"]["combat"]["escape_base_chance"]
ESCAPE_DISTANCE_THRESHOLD_CLOSE = config["hunters"]["combat"][
    "escape_distance_threshold_close"
]
ESCAPE_DISTANCE_THRESHOLD_FAR = config["hunters"]["combat"][
    "escape_distance_threshold_far"
]
ESCAPE_CHANCE_MODIFIER_CLOSE = config["hunters"]["combat"][
    "escape_chance_modifier_close"
]
ESCAPE_CHANCE_MODIFIER_FAR = config["hunters"]["combat"]["escape_chance_modifier_far"]

# Movement Parameters
EXPLORATION_VISIBILITY_THRESHOLD = config["hunters"]["movement"][
    "exploration_visibility_threshold"
]
CONSECUTIVE_FIGHT_RESET_CHANCE = config["hunters"]["movement"][
    "consecutive_fight_reset_chance"
]
AGGRESSION_FACTOR_MAX = config["hunters"]["movement"]["aggression_factor_max"]
AGGRESSION_FACTOR_MIN = config["hunters"]["movement"]["aggression_factor_min"]

# Sensing Parameters
D_MAX = config["hunters"]["sensing"]["D_max"]
K_BASE = config["hunters"]["sensing"]["k_base"]
K = config["hunters"]["sensing"]["k"]
D0_CLOSE = config["hunters"]["sensing"]["d0_close"]

# Logging Configuration
logging_level = getattr(logging, config["logging"]["hunters"]["level"])
logging.basicConfig(
    filename=config["general"]["logging"]["filename"],  # Log file name
    filemode=config["general"]["logging"][
        "filemode"
    ],  # 'w' to overwrite, 'a' to append
    level=logging_level,  # Logging level
    format=config["general"]["logging"]["format"],  # Log format
)

# Define grid cell size for spatial partitioning
# Initialize the grid index using sets
grid_index = {}
for x in range(0, GRID_WIDTH, GRID_CELL_SIZE):
    for y in range(0, GRID_HEIGHT, GRID_CELL_SIZE):
        grid_index[(x // GRID_CELL_SIZE, y // GRID_CELL_SIZE)] = set()


def get_grid_cell(position):
    x_cell = position[0] // GRID_CELL_SIZE
    y_cell = position[1] // GRID_CELL_SIZE
    return (x_cell, y_cell)


def remove_hunter_from_game(hunter, hunters_list):
    # Check if the hunter is still in the list before attempting to remove
    if hunter in hunters_list:
        # Remove hunter from grid index
        grid_index[hunter.grid_cell].discard(hunter)
        # Remove hunter from the list of hunters
        hunters_list.remove(hunter)
        # Decrease total hunters count
        Hunter.total_hunters -= 1
        logging.info(f"Hunter {hunter.unique_id} has been removed from the game.")
    else:
        logging.warning(f"Hunter {hunter.unique_id} was already removed from the list.")


class Hunter:
    total_hunters = 0  # Class variable to keep track of the total number of hunters

    def __init__(
        self,
        strength,
        hiding_skill,
        unique_id,
        knows_their_enemy,
        enemy_id,
        strategy,
        sensing,
        location=None,
    ):
        self.strength = strength  # Hunter's strength (int)
        self.hiding_skill = hiding_skill  # Hunter's hiding ability (int)
        self.unique_id = unique_id  # Unique identifier for the hunter (int)
        self.knows_their_enemy = knows_their_enemy  # Boolean flag
        self.enemy_id = enemy_id  # Enemy's unique ID (int)
        self.card_score = 3  # Starts with their own card worth 3 points
        self.strategy = strategy  # Aggression level (int between 0 and 20)
        self.sensing = sensing  # Sensing ability (max 10) (int)
        self.cards = [
            unique_id
        ]  # List of card IDs the hunter holds (starts with their own card)
        self.holds_his_own_card = True  # Initially holds their own card
        self.holds_his_specific_opponents_card = (
            False  # Initially does not hold their enemy's card
        )
        self.last_opponent_id = None  # Initialize last opponent ID
        self.consecutive_fight_count = 0  # Initialize consecutive fight count
        self.last_fight_outcome = None  # Initialize last fight outcome
        self.move_away_steps = 0
        self.last_group_position = None
        self.visited_positions = set()
        self.explore_target = None
        self.direction = random.choice(
            [-1, 1]
        )  # Randomly choose clockwise or counterclockwise
        self.following_boundary = False  # Track if the hunter is following a boundary
        self.boundary_following_direction = random.choice(
            [-1, 1]
        )  # Clockwise or counterclockwise
        self.boundary_following_steps = (
            0  # Track how many steps they've been following the boundary
        )
        self.last_movement_vector = (
            0,
            0,
        )  # To remember last direction for smooth boundary following

        if location is not None:
            self.position = location
        else:
            self.position = self.get_random_accessible_position()

        self.visited_positions.add(self.position)

        # Assign grid cell
        self.grid_cell = get_grid_cell(self.position)
        grid_index[self.grid_cell].add(self)

        # Increment the total number of hunters upon instantiation
        Hunter.total_hunters += 1

        # -------------------------------
        # Elo-based Combat System Change:
        # -------------------------------
        # Assign an Elo rating sampled from a normal distribution with mean 1700 and std 400.
        # If the sampled value is less than 1700, reflect it to the right side of the bell curve.
        raw_elo = np.random.normal(1700, 400)
        if raw_elo < 1700:
            self.elo = 1700 + (1700 - raw_elo)
        else:
            self.elo = raw_elo

        # Optional: log the assigned Elo rating
        logging.info(f"Hunter {self.unique_id} assigned Elo rating: {self.elo:.1f}")

    def get_random_accessible_position(self):
        accessible_cells = np.argwhere(map_grid["accessible"] == 1)
        if accessible_cells.size == 0:
            raise ValueError(
                "No accessible cells available on the map for hunters to spawn."
            )
        idx = random.choice(range(len(accessible_cells)))
        y, x = accessible_cells[idx]
        return (x, y)

    def __repr__(self):
        return (
            f"Hunter(ID={self.unique_id}, Strength={self.strength}, Hiding={self.hiding_skill}, "
            f"Sensing={self.sensing}, Card_Score={self.card_score}, Strategy={self.strategy}, "
            f"Position={self.position}, Elo={self.elo:.1f})"
        )

    def __str__(self):  # Overrides repr; use print(repr(hunter)) to use __repr__
        return f"Hunter {self.unique_id} at position {self.position} with card score {self.card_score} and Elo {self.elo:.1f}"

    """SENSING"""

    def sensing_probability(
        self,
        distance,
        sensing,
        terrain_modifier_self,
        target_hiding,
        terrain_modifier_target,
    ):
        if distance > D_MAX:
            return 0.0

        # Adjust sensing and hiding abilities with terrain modifiers
        effective_sensing = sensing + terrain_modifier_self
        effective_hiding = target_hiding + terrain_modifier_target

        # Normalize to [0, 10] range
        effective_sensing = max(0, min(effective_sensing, 10))
        effective_hiding = max(0, min(effective_hiding, 10))

        # Normalize to [0, 1]
        sensing_normalized = effective_sensing / 10
        hiding_normalized = (
            effective_hiding / 14
        )  # Assuming max hiding skill + terrain_modifier_target is 14

        # Net sensing ability
        net_sensing = sensing_normalized - hiding_normalized

        net_sensing = max(
            0, max(0.01, min(net_sensing, 1.99))
        )  # Avoid zero or negative values

        # Effective distance at which probability is 50%
        d0 = D_MAX * net_sensing

        # Steepness parameter
        k = K_BASE

        # Calculate probability using the logistic function
        probability = 1 / (1 + np.exp(k * (distance - d0)))
        return probability

    def sense_nearby_hunters(self):

        # Get adjacent grid cells
        x_cell, y_cell = self.grid_cell
        adjacent_cells = [
            (x_cell + dx, y_cell + dy)
            for dx in (-1, 0, 1)
            for dy in (-1, 0, 1)
            if (x_cell + dx, y_cell + dy) in grid_index
        ]

        # Collect hunters in adjacent cells
        potential_targets = []
        for cell in adjacent_cells:
            potential_targets.extend(grid_index[cell])

        sensed_hunters = []
        x_self, y_self = self.position
        terrain_modifier_self = map_grid["visibility"][y_self, x_self]
        sensing = self.sensing

        for other in potential_targets:
            if other.unique_id == self.unique_id:
                continue  # Skip self
            x_other, y_other = other.position
            distance = np.hypot(x_other - x_self, y_other - y_self)
            terrain_modifier_target = map_grid["visibility"][y_other, x_other]
            target_hiding = other.hiding_skill
            probability = self.sensing_probability(
                distance,
                sensing,
                terrain_modifier_self,
                target_hiding,
                terrain_modifier_target,
            )
            if random.random() <= probability:
                sensed_hunters.append((other, distance))
        return sensed_hunters

    """AGGRESSION AND FIGHT"""

    def update_aggression(self):
        max_aggression = AGGRESSION_FACTOR_MAX
        min_aggression = AGGRESSION_FACTOR_MIN

        if not hasattr(self, "initial_strategy"):
            self.initial_strategy = self.strategy

        if self.initial_strategy <= 5:
            self.strategy = 5

            if not self.holds_his_own_card:
                self.strategy = max(min_aggression, self.strategy - 1)
                logging.info(
                    f"Hunter {self.unique_id} lost their own card. Aggression decreased to {self.strategy}."
                )

            other_cards = [
                card
                for card in self.cards
                if card != self.unique_id and card != self.enemy_id
            ]
            aggression_adjustment = len(other_cards)
            self.strategy = min(max_aggression, self.strategy + aggression_adjustment)

            if aggression_adjustment > 0:
                logging.info(
                    f"Hunter {self.unique_id} increased aggression by +{aggression_adjustment} for holding non-enemy cards. Aggression is now {self.strategy}."
                )

            if self.strategy < 5 and self.holds_his_own_card:
                self.strategy = 5

            if self.card_score >= 6:
                self.strategy = max(min_aggression, self.strategy - 5)
                logging.info(
                    f"Hunter {self.unique_id}'s card score is {self.card_score} (≥6). Aggression decreased by 5 to {self.strategy}."
                )

        else:
            self.strategy = self.initial_strategy

            if self.card_score > 3:
                extra_points = self.card_score - 3
                aggression_increase = extra_points // 2
                self.strategy = min(max_aggression, self.strategy + aggression_increase)
                if aggression_increase > 0:
                    logging.info(
                        f"Hunter {self.unique_id} increased aggression by {aggression_increase} based on card score. Aggression is now {self.strategy}."
                    )

            threshold = (Hunter.total_hunters + 4) // 5 + 1
            if self.card_score >= threshold:
                self.strategy = max(min_aggression, self.strategy - 10)
                logging.info(
                    f"Hunter {self.unique_id}'s card score reached threshold {threshold}. Aggression decreased by 10 to {self.strategy}."
                )

            if not self.holds_his_own_card:
                self.strategy = min(max_aggression, self.strategy + 5)
                logging.info(
                    f"Hunter {self.unique_id} lost their own card. Aggression increased by 5 to {self.strategy}."
                )

        self.strategy = min(max_aggression, max(min_aggression, self.strategy))

    def update_fight_history(self, opponent, won):
        if self.last_opponent_id == opponent.unique_id:
            if self.last_fight_outcome == won:
                self.consecutive_fight_count += 1
            else:
                self.consecutive_fight_count = 1  # Outcome changed, reset count
        else:
            if random.random() < CONSECUTIVE_FIGHT_RESET_CHANCE:
                self.consecutive_fight_count = 1  # New opponent, reset count

        self.last_opponent_id = opponent.unique_id
        self.last_fight_outcome = won

    def gain_cards(self, cards_gained):
        for card in cards_gained:
            if card not in self.cards:
                self.cards.append(card)
                if card == self.unique_id:
                    self.card_score += 3
                    self.holds_his_own_card = True
                    logging.info(f"Hunter {self.unique_id} regained their own card.")
                elif card == self.enemy_id:
                    self.card_score += 3
                    self.holds_his_specific_opponents_card = True
                    logging.info(
                        f"Hunter {self.unique_id} now holds their specific opponent's card."
                    )
                else:
                    self.card_score += 1

    def lose_cards(self, cards_lost):
        for card in cards_lost:
            if card in self.cards:
                self.cards.remove(card)
                if card == self.unique_id:
                    self.card_score -= 3
                    self.holds_his_own_card = False
                    logging.info(f"Hunter {self.unique_id} lost their own card.")
                elif card == self.enemy_id:
                    self.card_score -= 3
                    self.holds_his_specific_opponents_card = False
                    logging.info(
                        f"Hunter {self.unique_id} no longer holds their specific opponent's card."
                    )
                else:
                    self.card_score -= 1

    def decide_combat(self, other, distance):
        if distance <= 50:
            probability = 1 / (1 + np.exp(K * (distance - D0_CLOSE)))
            return random.random() <= probability
        else:
            return False  # Too far to fight

    def engage_combat(self, opponent, hunters_list):
        """Decides the outcome of combat using Elo-based probabilities."""
        # Ensure both self and opponent are still in the list before proceeding
        if self not in hunters_list or opponent not in hunters_list:
            return False

        # Calculate win probability for self based on Elo ratings
        prob_self = 1 / (1 + 10 ** ((opponent.elo - self.elo) / 400))
        if random.random() < prob_self:
            winner, loser = self, opponent
        else:
            winner, loser = opponent, self

        # Winner gains cards from loser
        winner.gain_cards(loser.cards)
        loser.lose_cards(loser.cards.copy())

        # Chance of death for the loser
        if random.random() < config["simulation"]["combat"]["death_chance"]:
            logging.info(f"Hunter {loser.unique_id} has died.")
            remove_hunter_from_game(loser, hunters_list)
        else:
            # Update fight history if loser survives
            self.update_fight_history(opponent, winner == self)
            opponent.update_fight_history(self, winner == opponent)

        # Chance for hunters to learn their enemy
        if not self.knows_their_enemy and random.random() <= 0.2:
            self.knows_their_enemy = True
            logging.info(
                f"Hunter {self.unique_id} has learned their special enemy is Hunter {self.enemy_id}."
            )
        if not opponent.knows_their_enemy and random.random() <= 0.2:
            opponent.knows_their_enemy = True
            logging.info(
                f"Hunter {opponent.unique_id} has learned their special enemy is Hunter {opponent.enemy_id}."
            )

        return winner == self

    """MOVEMENTS AND COMBAT DECISIONS"""

    def decide_movement(self, sensed_hunters):
        if self.move_away_steps > 0:
            if self.last_group_position:
                self.move_away_from(self.last_group_position)
                logging.info(
                    f"Hunter {self.unique_id} continues to move away from the group for {self.move_away_steps} more steps."
                )
            else:
                self.explore()
            self.move_away_steps -= 1
            return

        if not sensed_hunters:
            self.explore()
            return

        enemy_in_sensed = None
        for hunter, dist in sensed_hunters:
            if hunter.unique_id == self.enemy_id:
                enemy_in_sensed = (hunter, dist)
                break

        if self.knows_their_enemy and enemy_in_sensed:
            enemy_hunter, distance = enemy_in_sensed
            if not self.holds_his_specific_opponents_card:
                action_choice = random.random()
                if action_choice <= 0.9:
                    self.move_towards(enemy_hunter.position)
                    logging.info(
                        f"Hunter {self.unique_id} moves aggressively towards their enemy Hunter {enemy_hunter.unique_id}."
                    )
                else:
                    self.move_away_from(enemy_hunter.position)
                    logging.info(
                        f"Hunter {self.unique_id} moves away from their enemy Hunter {enemy_hunter.unique_id}."
                    )
            else:
                action_choice = random.random()
                if action_choice <= 0.9:
                    self.move_away_from(enemy_hunter.position)
                    logging.info(
                        f"Hunter {self.unique_id} moves away from their enemy Hunter {enemy_hunter.unique_id}."
                    )
                else:
                    self.explore()
                    logging.info(
                        f"Hunter {self.unique_id} decides to explore instead of moving away from Hunter {enemy_hunter.unique_id}."
                    )
            return

        if len(sensed_hunters) >= 2 and (self.strategy / 15) <= 1:
            avg_x = sum(hunter.position[0] for hunter, _ in sensed_hunters) / len(
                sensed_hunters
            )
            avg_y = sum(hunter.position[1] for hunter, _ in sensed_hunters) / len(
                sensed_hunters
            )
            avg_position = (avg_x, avg_y)
            self.move_away_steps = int((120 - self.strategy) / 2)
            self.last_group_position = avg_position
            self.move_away_from(avg_position)
            logging.info(
                f"Hunter {self.unique_id} starts moving away from the group for {self.move_away_steps} steps."
            )
            return

        sensed_hunters.sort(key=lambda x: x[1])
        closest_hunter, distance = sensed_hunters[0]

        if (
            self.last_opponent_id == closest_hunter.unique_id
            and self.consecutive_fight_count >= 2
        ):
            self.move_away_from(closest_hunter.position)
            logging.info(
                f"Hunter {self.unique_id} avoids Hunter {closest_hunter.unique_id} after repeated fights."
            )
            return

        aggression_factor = self.strategy / 20  # Adjusted to max aggression 20
        action_choice = random.random()

        if action_choice <= aggression_factor:
            self.move_towards(closest_hunter.position)
            logging.info(
                f"Hunter {self.unique_id} (Aggression: {self.strategy}) moves towards Hunter {closest_hunter.unique_id}."
            )
        else:
            self.move_away_from(closest_hunter.position)
            logging.info(
                f"Hunter {self.unique_id} (Aggression: {self.strategy}) moves away from Hunter {closest_hunter.unique_id}."
            )

    def move_towards(self, target_position):
        x_self, y_self = self.position
        x_target, y_target = target_position
        dx = x_target - x_self
        dy = y_target - y_self
        distance = np.hypot(dx, dy)
        if distance == 0:
            return
        dx /= distance
        dy /= distance
        movement_vector = (
            self.last_movement_vector if self.following_boundary else (dx, dy)
        )
        new_x = int(round(x_self + movement_vector[0]))
        new_y = int(round(y_self + movement_vector[1]))
        if (
            0 <= new_x < GRID_WIDTH
            and 0 <= new_y < GRID_HEIGHT
            and map_grid["accessible"][new_y, new_x] == 1
        ):
            self.position = (new_x, new_y)
            self.visited_positions.add(self.position)
            self.following_boundary = False
            self.boundary_following_steps = 0
            self.last_movement_vector = (dx, dy)
        else:
            if not self.following_boundary:
                self.following_boundary = True
                self.boundary_following_direction = random.choice([-1, 1])
            self.boundary_following_steps += 1
            angle_offset = np.pi / 4 * self.boundary_following_direction
            new_dx = movement_vector[0] * np.cos(angle_offset) - movement_vector[
                1
            ] * np.sin(angle_offset)
            new_dy = movement_vector[0] * np.sin(angle_offset) + movement_vector[
                1
            ] * np.cos(angle_offset)
            self.last_movement_vector = (new_dx, new_dy)
            new_x = int(round(x_self + new_dx))
            new_y = int(round(y_self + new_dy))
            if (
                0 <= new_x < GRID_WIDTH
                and 0 <= new_y < GRID_HEIGHT
                and map_grid["accessible"][new_y, new_x] == 1
            ):
                self.position = (new_x, new_y)
                self.visited_positions.add(self.position)
            else:
                if self.boundary_following_steps > 10:
                    self.move_randomly()
                    self.following_boundary = False
                    self.boundary_following_steps = 0
                else:
                    self.last_movement_vector = (new_dx, new_dy)

    def move_away_from(self, target_position):
        x_self, y_self = self.position
        x_target, y_target = target_position
        dx = x_self - x_target
        dy = y_self - y_target
        distance = np.hypot(dx, dy)
        if distance == 0:
            self.move_randomly()
            return
        dx /= distance
        dy /= distance
        new_x = int(round(x_self + dx))
        new_y = int(round(y_self + dy))
        if (
            0 <= new_x < GRID_WIDTH
            and 0 <= new_y < GRID_HEIGHT
            and map_grid["accessible"][new_y, new_x] == 1
        ):
            self.position = (new_x, new_y)
            self.visited_positions.add(self.position)
            new_grid_cell = get_grid_cell(self.position)
            if new_grid_cell != self.grid_cell:
                grid_index[self.grid_cell].discard(self)
                self.grid_cell = new_grid_cell
                grid_index[self.grid_cell].add(self)
        else:
            logging.info(
                f"Hunter {self.unique_id} cannot move to inaccessible position {(new_x, new_y)}. Moving randomly instead."
            )
            self.move_randomly()

    def _explore(self):
        if not self.explore_target or self.position == self.explore_target:
            accessible_positions = np.argwhere(map_grid["accessible"] == 1)
            unvisited_positions = [
                tuple(pos[::-1])
                for pos in accessible_positions
                if tuple(pos[::-1]) not in self.visited_positions
            ]
            if not unvisited_positions:
                unvisited_positions = [tuple(pos[::-1]) for pos in accessible_positions]
            if self.hiding_skill > 5:
                positions_with_visibility = [
                    (pos, map_grid["visibility"][pos[1], pos[0]])
                    for pos in unvisited_positions
                ]
                positions_with_visibility.sort(key=lambda x: -x[1])
                top_positions = positions_with_visibility[
                    : max(1, len(positions_with_visibility) // 10)
                ]
                self.explore_target = random.choice([pos for pos, vis in top_positions])
            else:
                self.explore_target = random.choice(unvisited_positions)
        self.move_towards(self.explore_target)

    def explore(self):
        if not self.explore_target or self.position == self.explore_target:
            # Compute unvisited positions using the precomputed set
            unvisited_positions = list(
                ALL_ACCESSIBLE_POSITIONS_SET - self.visited_positions
            )
            if not unvisited_positions:
                unvisited_positions = ALL_ACCESSIBLE_POSITIONS

            # Get the maximum exploration range from the configuration (default to 10 if not set)
            max_range = config["hunters"]["movement"].get("explore_max_range", 10)

            # Filter candidate positions to those within the maximum allowed Manhattan distance
            unvisited_positions = [
                pos
                for pos in unvisited_positions
                if abs(pos[0] - self.position[0]) + abs(pos[1] - self.position[1])
                <= max_range
            ]
            # If no positions within the range, fall back to all accessible positions
            if not unvisited_positions:
                unvisited_positions = ALL_ACCESSIBLE_POSITIONS

            # Choose target based on hiding skill
            if self.hiding_skill > 5:
                # Get visibility for each candidate position
                positions_with_visibility = [
                    (pos, map_grid["visibility"][pos[1], pos[0]])
                    for pos in unvisited_positions
                ]
                # Sort candidates in descending order of visibility
                positions_with_visibility.sort(key=lambda x: -x[1])
                # Choose from the top 10% (at least one candidate)
                top_count = max(1, len(positions_with_visibility) // 10)
                top_positions = [
                    pos for pos, _ in positions_with_visibility[:top_count]
                ]
                self.explore_target = random.choice(top_positions)
            else:
                self.explore_target = random.choice(unvisited_positions)
        self.move_towards(self.explore_target)

    def move_randomly(self):
        x_self, y_self = self.position
        possible_moves = [
            (-1, -1),
            (-1, 0),
            (-1, 1),
            (0, -1),
            (0, 1),
            (1, -1),
            (1, 0),
            (1, 1),
        ]
        random.shuffle(possible_moves)
        for dx, dy in possible_moves:
            new_x = x_self + dx
            new_y = y_self + dy
            if (
                0 <= new_x < GRID_WIDTH
                and 0 <= new_y < GRID_HEIGHT
                and map_grid["accessible"][new_y, new_x] == 1
            ):
                self.position = (new_x, new_y)
                self.visited_positions.add(self.position)
                new_grid_cell = get_grid_cell(self.position)
                if new_grid_cell != self.grid_cell:
                    grid_index[self.grid_cell].discard(self)
                    self.grid_cell = new_grid_cell
                    grid_index[self.grid_cell].add(self)
                logging.info(
                    f"Hunter {self.unique_id} moves randomly to position {self.position}."
                )
                return
        logging.info(f"Hunter {self.unique_id} stays in place at {self.position}.")
