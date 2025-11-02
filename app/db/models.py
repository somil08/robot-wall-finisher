from sqlalchemy import Table, Column, Integer, Float, String, ForeignKey, MetaData

metadata = MetaData()

# ===============================================================
#  TRAJECTORIES TABLE
# ===============================================================
trajectories = Table(
    "trajectories",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, nullable=False),
    Column("width", Float, nullable=False),
    Column("height", Float, nullable=False),
    Column("created_at", String)  # ✅ Added this
)


# ===============================================================
#  TRAJECTORY POINTS TABLE
# ===============================================================
trajectory_points = Table(
    "trajectory_points",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("trajectory_id", Integer, ForeignKey("trajectories.id")),
    Column("ord", Integer),
    Column("x", Float),
    Column("y", Float),
)


# ===============================================================
#  OBSTACLES TABLE
# ===============================================================
obstacles = Table(
    "obstacles",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("trajectory_id", Integer, ForeignKey("trajectories.id"), nullable=True),
    Column("name", String),
    Column("x", Float),
    Column("y", Float),
    Column("w", Float),
    Column("h", Float),
)
