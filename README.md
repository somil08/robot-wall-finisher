# Robot Wall Finisher

## Overview

This project simulates a robot that paints a wall while avoiding obstacles such as windows, sockets, and doors.  
It has two main parts:
1. A **FastAPI backend** that manages wall data, trajectories, and obstacles.
2. A **Pygame frontend** that visualizes the robot’s painting path in real time.

The goal was to design a system that can automatically plan and display a robot’s movement over a wall, ensuring it covers all paintable regions while avoiding obstacle areas.

---

## Approach

### 1. Problem Understanding

The robot must move in a systematic path to paint the wall while avoiding defined obstacles.  
The simulation needed to visually show:
- The wall boundary  
- Obstacles that cannot be painted  
- The robot’s path as it paints the rest of the wall  

### 2. Backend Design

The backend was built using **FastAPI** for creating RESTful APIs.  
It handles:
- Creating walls with dimensions and obstacles  
- Storing robot trajectories  
- Retrieving trajectory and obstacle data for visualization  

**SQLite** is used as the database because it is lightweight and easy to integrate.  
**SQLAlchemy** manages database models and queries.  
Logging is included to track API usage and performance.

---

### 3. Visualization (Frontend)

The visualization uses **Pygame** to show the wall, obstacles, and robot path:
- The wall is drawn as a rectangular canvas.  
- Obstacles are displayed in red.  
- The robot follows a blue zig-zag trajectory, covering the wall area.  
- The robot’s position is marked by a moving green dot.

The trajectory avoids all obstacle regions. The robot moves in a back-and-forth pattern similar to how a wall-painting robot would move in real life.

---

### 4. Handling Obstacles

One of the main challenges was ensuring that the robot never moves over an obstacle.  
The system:
- Detects if a path crosses an obstacle area.  
- Skips drawing lines inside those areas.  
- Generates alternate paths around the obstacle so that the wall area next to the obstacle is still covered.  

This gives the appearance that the robot paints the wall completely while neatly avoiding windows and sockets.

---

## How It Works

1. Run the Pygame visualization using:  
   ```bash
   python gui/visualize.py <trajectory_id>
