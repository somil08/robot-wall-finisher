import sqlite3
from datetime import datetime
from sqlalchemy import select
from app.db.models import obstacles, trajectories, trajectory_points
from app.db.database import engine, SessionLocal


# ===============================================================
#  OBSTACLE FUNCTIONS
# ===============================================================

def insert_obstacle_sqlite(obs: dict):
    """
    obs = {"trajectory_id": int or None, "name": str, "x": float, "y": float, "w": float, "h": float}
    Stores in obstacles table and into obstacle_rtree.
    """
    conn = sqlite3.connect("robot.db")
    cur = conn.cursor()

    # Insert into obstacles table
    cur.execute("""
        INSERT INTO obstacles (trajectory_id, name, x, y, w, h)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (obs.get("trajectory_id"), obs.get("name"), obs["x"], obs["y"], obs["w"], obs["h"]))
    obstacle_id = cur.lastrowid

    # Compute bounding box for spatial index
    minX = obs["x"] - obs["w"]/2
    maxX = obs["x"] + obs["w"]/2
    minY = obs["y"] - obs["h"]/2
    maxY = obs["y"] + obs["h"]/2

    # Insert into R-Tree index
    cur.execute("""
        INSERT INTO obstacle_rtree (id, minX, maxX, minY, maxY)
        VALUES (?, ?, ?, ?, ?)
    """, (obstacle_id, minX, maxX, minY, maxY))

    conn.commit()
    conn.close()
    return obstacle_id


def list_obstacles_for_wall(trajectory_id: int):
    conn = sqlite3.connect("robot.db")
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, x, y, w, h FROM obstacles WHERE trajectory_id = ?",
        (trajectory_id,)
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "x": r[2], "y": r[3], "w": r[4], "h": r[5]}
        for r in rows
    ]


def list_all_obstacles():
    conn = sqlite3.connect("robot.db")
    cur = conn.cursor()
    cur.execute("SELECT id, name, x, y, w, h, trajectory_id FROM obstacles")
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "name": r[1], "x": r[2], "y": r[3], "w": r[4], "h": r[5], "trajectory_id": r[6]}
        for r in rows
    ]


# ===============================================================
#  TRAJECTORY FUNCTIONS
# ===============================================================

def create_trajectory(name: str, width: float, height: float) -> int:
    """
    Creates a new trajectory record (i.e., a wall definition).
    Returns the new trajectory_id.
    """
    conn = sqlite3.connect("robot.db")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO trajectories (name, width, height, created_at)
        VALUES (?, ?, ?, ?)
    """, (name, width, height, datetime.utcnow().isoformat()))
    traj_id = cur.lastrowid
    conn.commit()
    conn.close()
    return traj_id


def insert_points(trajectory_id: int, waypoints: list[tuple[float, float]]):
    """
    Inserts generated trajectory waypoints (x, y) into trajectory_points table.
    """
    if not waypoints:
        return

    conn = sqlite3.connect("robot.db")
    cur = conn.cursor()
    data = [(trajectory_id, i, float(x), float(y)) for i, (x, y) in enumerate(waypoints)]
    cur.executemany("""
        INSERT INTO trajectory_points (trajectory_id, ord, x, y)
        VALUES (?, ?, ?, ?)
    """, data)
    conn.commit()
    conn.close()


def get_trajectory(traj_id: int):
    """
    Retrieve trajectory metadata and points for visualization.
    """
    conn = sqlite3.connect("robot.db")
    cur = conn.cursor()

    # Get metadata
    cur.execute("SELECT id, name, width, height, created_at FROM trajectories WHERE id = ?", (traj_id,))
    meta = cur.fetchone()
    if not meta:
        conn.close()
        return None

    # Get points
    cur.execute("SELECT x, y, ord FROM trajectory_points WHERE trajectory_id = ? ORDER BY ord ASC", (traj_id,))
    points = [{"x": r[0], "y": r[1], "ord": r[2]} for r in cur.fetchall()]
    conn.close()

    return {
        "id": meta[0],
        "name": meta[1],
        "width": meta[2],
        "height": meta[3],
        "created_at": meta[4],
        "points": points
    }
