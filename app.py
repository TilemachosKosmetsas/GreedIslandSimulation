import streamlit as st
import yaml
import os
import time
import pickle
import matplotlib.pyplot as plt

# Initialize a session state flag for simulation run status
if "simulation_run" not in st.session_state:
    st.session_state.simulation_run = False

# Import your simulation functions
from simulation import initialize_hunters, run_simulation
from savemp4 import (
    save_animation_with_opencv,
)  # Ensure this file exists in your project

# Load the pre-generated map grid
with open("map_grid.pkl", "rb") as f:
    map_grid = pickle.load(f)


# Load the base configuration
@st.cache_data
def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)


config = load_config()

st.title("Hunter Simulation")
st.write(
    """
                Adjust the parameters on the sidebar (to the left) & press **Run Simulation** to generate the simulation. 
                
                When simulation processing is over, download the MP4 video file.
    """
)

# -------------------------
# DISPLAY TOP-CENTERED IMAGE
# -------------------------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image("pix.png", use_container_width=True)

# -------------------------
# PLACEHOLDER FOR PROGRAM DESCRIPTION
# (Only appears on the initial page, before simulation starts)
# -------------------------
if not st.session_state.simulation_run:
    st.markdown(
        """
        **What is this?**

    Inspired by the Greed Island arc from Hunter x Hunter,
    I created this simulation to play out the three-day trial all cadet hunters pass. 
    
    Each hunter spawned on our map initially holds a unique card worth 3 points. 
    For player X, all other players' cards are valued at 1 point for, except for a special enemy of X whose
    card which is worth 3 points to X only.

    Some hunters (cadets) know which enemy holds their uniquely valued enemy card and they are actively seeking to find them.
    Some do not know, but have a chance to obtain this information after battling enemies here and there.

    To escape the Greed Island, one must survive first, but to win it X must collect cards
    totaling 6 points by the end of the challenge, no matter how they do it.

    So for example, X may hold their initial card and their special enemy's card -> 6 points or 
    they may lose their card, win over 6 totally random enemies' cards and still have 6 points worth 
    of cards.


        Why did I do it?
    
    I wondered if it is possible to know how many would survive a game like that.
    I also wondered how likely it is to survive but not make it to the next round.

        Is it parametrized and what are the parameters & assumptions?
    The code is modular enough to allow for crazy parametrization (ergo a different expected value at the end), but you have
    to copy the code and run it locally. For computational reasons I have only added a few sliders here and restricted the use of many steps & hunters.
    After cloning the code, go to config.yaml and break the simulation at your own pace.

    1) Map is created & inspired from the anime. A two-joint circles form an island with a lake in the middle. I have added 
    a number of walls as physical obstacles.

    2) Hunters are objects of the Hunters class. Each hunter has:
        * a unique ability to hide (the terrain also enhances or blocks this ability),
        * a unique ability to sense enemies nearby with a sensing_probability function which uses a logistic function to increase
        sensing as the distance gets smaller.
        * Their own strength value (which determines battle outcomes). This is ELO based and I have only allowed players of ELO greater than 1700
        (assuming only strong fighters have a chance of even entering this trial).
        * A strategy (passive or aggressive). Everyone is a little more aggressive when they need to survive and make it to the next round, but some players tend to get
        more bloodthirsty after a few kills, while others tend to hide once they reached their target.


    3) At every step of the simulation every hunter decides what to do next. E.g some passive hunter who holds 6 points
    wants to avoid battle, perhaps this hunter senses 5 enemies around them and decides to avoid them all,
    the program sends the player to the opposite direction of the average vector location of the 5 enemies sensed. But
    the hunter may have not been able to sense every nearby enemy, thus may fall straight into an unavoidable battle.

    4) There are two visualization options, one layer is for accessible and non-accessible blocks of the map,
    and the second layer is based on a palette of green color (which is the one currently used).
    The Greener a spot appears on the map, the easier it is for hunters to hide there.



        Facts:
    Two hunters may also choose not to fight.

    The probability of dying at the end of a battle is 0.25 but you can change it as well!

    There is no code integration that allows some hunters to form a group and operate as one. Humans tend to 
    form pacts and this would be a great addition.

        Enjoy!

        """,
        unsafe_allow_html=True,
    )

# -------------------------
# SIDEBAR SLIDERS
# -------------------------
st.sidebar.header("Simulation Settings")

# Number of Hunters
num_hunters = st.sidebar.slider(
    "Number of Hunters",
    min_value=10,
    max_value=50,
    value=config["simulation"]["num_hunters"],
    step=5,
)

# Number of Steps
steps = st.sidebar.slider(
    "Number of Steps",
    min_value=100,
    max_value=500,
    value=config["simulation"]["steps"],
    step=10,
)

# Map Dimensions
map_height_km = st.sidebar.slider(
    "Map Height (km)",
    min_value=1.0,
    max_value=10.0,
    value=float(config["map"]["dimensions"]["height_km"]),
    step=0.5,
)
map_width_km = st.sidebar.slider(
    "Map Width (km)",
    min_value=1.0,
    max_value=10.0,
    value=float(config["map"]["dimensions"]["width_km"]),
    step=0.5,
)

# Number of Walls
num_walls = st.sidebar.slider(
    "Number of Walls",
    min_value=0,
    max_value=10,
    value=config["map"]["walls"]["num_walls"],
    step=1,
)

# Number of Forest Clusters
num_forests = st.sidebar.slider(
    "Number of Forest Clusters",
    min_value=0,
    max_value=30,
    value=config["map"]["forests"]["num_forests"],
    step=1,
)

# Base Chance to Escape Combat
escape_base_chance = st.sidebar.slider(
    "Base Chance to Escape Combat",
    min_value=0.0,
    max_value=1.0,
    value=float(config["hunters"]["combat"]["escape_base_chance"]),
    step=0.05,
)

# Maximum Sensing Range
d_max = st.sidebar.slider(
    "Maximum Sensing Range (D_max)",
    min_value=0,
    max_value=200,
    value=config["hunters"]["sensing"]["D_max"],
    step=5,
)

# Death Chance
death_chance = st.sidebar.slider(
    "Death Chance",
    min_value=0.0,
    max_value=1.0,
    value=float(config["simulation"]["combat"]["death_chance"]),
    step=0.05,
)

# -------------------------
# APPLY SLIDER VALUES TO CONFIG
# -------------------------
config["simulation"]["num_hunters"] = num_hunters
config["simulation"]["steps"] = steps

config["map"]["dimensions"]["height_km"] = map_height_km
config["map"]["dimensions"]["width_km"] = map_width_km

config["map"]["walls"]["num_walls"] = num_walls
config["map"]["forests"]["num_forests"] = num_forests

config["hunters"]["combat"]["escape_base_chance"] = escape_base_chance
config["hunters"]["sensing"]["D_max"] = d_max

config["simulation"]["combat"]["death_chance"] = death_chance

# -------------------------
# TOP ROW: RUN BUTTON & PROGRESS BAR
# -------------------------
col_run, col_progress = st.columns([1, 3])
with col_run:
    run_sim = st.button("Run Simulation")
with col_progress:
    progress_bar = st.progress(0)

progress_text = st.empty()


# Helper function to compute statistics from the final hunters list
def compute_statistics(hunters, total_initial_hunters):
    num_alive = len(hunters)
    if num_alive > 0:
        avg_score_alive = sum(h.card_score for h in hunters) / num_alive
        max_score_alive = max(h.card_score for h in hunters)
        min_score_alive = min(h.card_score for h in hunters)
    else:
        avg_score_alive = max_score_alive = min_score_alive = 0
    avg_score_total = sum(h.card_score for h in hunters) / total_initial_hunters
    winning_hunters = len([h for h in hunters if h.card_score >= 6])
    ratio = winning_hunters / num_alive if num_alive > 0 else 0
    # Additional KPI: Average Elo Rating
    avg_elo = sum(h.elo for h in hunters) / num_alive if num_alive > 0 else 0

    return {
        "Number of Alive Hunters": num_alive,
        "Number of Winning Hunters": winning_hunters,
        "Average Score (Alive)": avg_score_alive,
        "Max Score (Alive)": max_score_alive,
        "Min Score (Alive)": min_score_alive,
        "Average Score (All)": avg_score_total,
        "Winning to Alive Ratio": ratio,
        "Average Elo Rating": avg_elo,
    }


# -------------------------
# RUN SIMULATION WHEN BUTTON PRESSED
# -------------------------
if run_sim:
    # Set the flag so that the description placeholder is hidden in future reruns
    st.session_state.simulation_run = True

    total_steps = 4  # We'll track 4 major steps
    current_step = 0

    # Step 1: Hunter Spawning
    progress_text.text("Spawning hunters...")
    hunters_list = initialize_hunters(num_hunters)
    current_step += 1
    progress_bar.progress(int(current_step / total_steps * 100))
    time.sleep(0.5)

    # Step 2: Running Simulation Steps
    progress_text.text("Running simulation steps...")
    simulation_start = time.time()
    hunters_over_time = run_simulation(hunters_list, steps)
    simulation_duration = time.time() - simulation_start
    current_step += 1
    progress_bar.progress(int(current_step / total_steps * 100))
    time.sleep(0.5)

    # Step 3: Saving Animation to MP4
    progress_text.text("Saving simulation as MP4...")
    animation_file = config["animation"]["animation_file"]
    try:
        save_animation_with_opencv(hunters_over_time, map_grid, config)
    except Exception as e:
        st.error(f"Failed to create animation: {e}")
    current_step += 1
    progress_bar.progress(int(current_step / total_steps * 100))
    time.sleep(0.5)

    # Step 4: Finalizing
    progress_text.text("Finalizing simulation...")
    current_step += 1
    progress_bar.progress(100)
    st.success(f"Simulation completed in {simulation_duration:.2f} seconds.")

    # -------------------------
    # DISPLAY STATISTICS & HISTOGRAM SIDE-BY-SIDE
    # -------------------------
    stats = compute_statistics(hunters_list, num_hunters)
    final_elo = [h.elo for h in hunters_list]

    col_stats, col_hist = st.columns(2)
    with col_stats:
        st.subheader("Simulation Statistics")
        for key, value in stats.items():
            if isinstance(value, float):
                st.write(f"**{key}:** {value:.2f}")
            else:
                st.write(f"**{key}:** {value}")
    with col_hist:
        st.subheader("Distribution of Elo Ratings")
        fig, ax = plt.subplots()
        ax.hist(final_elo, bins=10, color="skyblue", edgecolor="black")
        ax.set_title("Distribution of Elo Ratings")
        ax.set_xlabel("Elo Rating")
        ax.set_ylabel("Number of Hunters")
        st.pyplot(fig)

    # -------------------------
    # DOWNLOAD BUTTON CENTERED AT THE BOTTOM
    # -------------------------
    cols = st.columns(3)
    with cols[1]:
        if os.path.exists(animation_file):
            with open(animation_file, "rb") as f:
                video_bytes = f.read()
            st.download_button(
                label="Download Simulation Video",
                data=video_bytes,
                file_name=animation_file,
                mime="video/mp4",
            )
        else:
            st.error("Animation file not found.")

    progress_text.text("Simulation complete!")

    # -------------------------
    # DISPLAY BOTTOM-CENTERED IMAGE AFTER SIMULATION
    # -------------------------
    col_bottom1, col_bottom2, col_bottom3 = st.columns([1, 2, 1])
    with col_bottom2:
        st.image("pix.png", use_container_width=True)
