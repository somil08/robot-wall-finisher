from fastapi import APIRouter
from app.schemas import WallIn, ObstacleIn
from app.db import crud
from app.core.planner import generate_lawnmower

router = APIRouter()

@router.post("/walls")
async def create_wall(payload: WallIn):
    data = payload.dict()
    name = data["name"]
    width = data["width"]
    height = data["height"]
    step = data["step"]
    obstacles = data.get("obstacles", [])

    # 1️⃣ Save wall / trajectory metadata
    traj_id = crud.create_trajectory(name, width, height)

    # 2️⃣ Save obstacles to DB
    for obs in obstacles:
        obs["trajectory_id"] = traj_id
        crud.insert_obstacle_sqlite(obs)

    # 3️⃣ Generate trajectory avoiding obstacles
    waypoints = generate_lawnmower(width, height, obstacles, step)

    # 4️⃣ Save trajectory points
    crud.insert_points(traj_id, waypoints)

    return {
        "trajectory_id": traj_id,
        "points_count": len(waypoints),
        "obstacles": obstacles
    }

@router.get("/obstacles")
async def get_obstacles():
    return crud.list_all_obstacles()

@router.get("/trajectories/{traj_id}")
def get_trajectory(traj_id: int):
    """
    Returns the trajectory metadata, points, and created_at time for visualization.
    """
    data = crud.get_trajectory(traj_id)
    if not data:
        raise HTTPException(status_code=404, detail="Trajectory not found")
    return data
