from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Database Setup ---
def get_db():
    """Opens a connection to the SQLite database file."""
    conn = sqlite3.connect("swim.db")
    conn.row_factory = sqlite3.Row  # lets us access columns by name
    return conn


def init_db():
    """
    
    """

    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS meets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            saved INTEGER DEFAULT 0       
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            meet_id INTEGER,
            name TEXT NOT NULL,
            heat INTEGER NOT NULL,
            gender TEXT NOT NULL,
            FOREIGN KEY (meet_id) REFERENCES meets(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS event_swimmers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            gender TEXT NOT NULL,
            lane INTEGER NOT NULL,
            team TEXT,
            seed_time TEXT,
            actual_time TEXT,
            relay_order INTEGER DEFAULT NULL,
            FOREIGN KEY (event_id) REFERENCES events(id)
        )
    """)

    conn.commit()
    conn.close()

init_db()  # run this when the server starts


# --- Data Model ---
class Meet(BaseModel):
    name: Optional[str] = None
    saved: int = 0

class Event(BaseModel):
    meet_id: int
    name: str
    heat: int
    gender: str


class Swimmer(BaseModel):
    event_id: int
    name: str
    gender: str
    lane: int
    team: Optional[str] = None
    seed_time: Optional[str] = None
    actual_time: Optional[str] = None
    relay_order: Optional[int] = None


# --- Serve the Frontend ---
@app.get("/")
def serve_frontend():
    return FileResponse("index.html")


# --- API Routes ---

@app.get("/meets")
def get_meets():
    conn = get_db()

    meets = conn.execute(
        "SELECT * FROM meets WHERE saved = 1 ORDER BY id DESC"    
    ).fetchall()

    conn.close()
    return [dict(m) for m in meets]


@app.post("/meets")
def create_meet():
    conn = get_db()

    cursor = conn.execute(
        "INSERT INTO meets (name, saved) VALUES (?, 0)",
        (None,)
    )

    conn.commit()

    new_id = cursor.lastrowid

    conn.close()

    return {"id" : new_id, "name" : None, "saved" : 0}


@app.put("/meets/{meet_id}")
def save_meet(meet_id: int, meet: Meet):

    conn = get_db()

    result = conn.execute(
        "UPDATE meets SET name = ?, saved = 1 WHERE id = ?",
        (meet.name, meet_id)
    )

    conn.commit()
    conn.close()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Meet not found")
    return {"id": meet_id, "name": meet.name, "saved": 1}


@app.delete("/meets/{meet_id}")
def delete_meet(meet_id: int):

    conn = get_db()

    # cascade delete events and their swimmers
    events = conn.execute(
        "SELECT id FROM events WHERE meet_id = ?", (meet_id,)
    ).fetchall()

    for event in events:
        conn.execute(
            "DELETE FROM event_swimmers WHERE event_id = ?", (event["id"],)
        )

    conn.execute("DELETE FROM events WHERE meet_id = ?", (meet_id,))
    conn.execute("DELETE FROM meets WHERE id = ?", (meet_id,))

    conn.commit()
    conn.close()

    return {"message": "Meet deleted"}


@app.get("/events")
def get_events(meet_id: int = Query(None)):

    conn = get_db()

    if meet_id:
        events = conn.execute(
            "SELECT * FROM events WHERE meet_id = ? ORDER BY heat",
            (meet_id,)
        ).fetchall()

    else:
        events = conn.execute(
            "SELECT * FROM events ORDER BY heat"
        ).fetchall()

    conn.close()

    return [dict(e) for e in events]


@app.post("/events")
def create_event(event: Event):
    """
    
    """

    conn = get_db()

    cursor = conn.execute(
        "INSERT INTO events (meet_id, name, heat, gender) VALUES (?, ?, ?, ?)",
        (event.meet_id, event.name, event.heat, event.gender)
    )

    conn.commit()
    new_id = cursor.lastrowid

    conn.close()
    return {"id": new_id, **event.dict()}


@app.put("/events/{event_id}")
def update_event(event_id: int, event: Event):
    """
    
    """

    conn = get_db()

    result = conn.execute(
        "UPDATE events SET name = ?, heat = ?, gender = ? WHERE id = ?",
        (event.name, event.heat, event.gender, event_id)
    )

    conn.commit()
    conn.close()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"id": event_id, **event.dict()}


@app.delete("/events/{event_id}")
def delete_event(event_id: int):
    """
    
    """

    conn = get_db()

    conn.execute("DELETE FROM event_swimmers WHERE event_id = ?", (event_id,))
    result = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))

    conn.commit()
    conn.close()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    return {"message": "Event deleted"}


# --- Swimmer Routes ---
@app.get("/events/{event_id}/swimmers")
def get_swimmers(event_id: int):
    """
    
    """
    
    conn = get_db()
    
    swimmers = conn.execute(
        "SELECT * FROM event_swimmers WHERE event_id = ? ORDER BY lane",
        (event_id,)
    ).fetchall()

    conn.close()
    return [dict(s) for s in swimmers]


@app.post("/swimmers")
def create_swimmer(swimmer: Swimmer):
    """
    
    """
    conn = get_db()
    
    cursor = conn.execute(
        "INSERT INTO event_swimmers (event_id, name, gender, lane, team, seed_time, actual_time, relay_order) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (swimmer.event_id, swimmer.name, swimmer.gender, swimmer.lane, swimmer.team, swimmer.seed_time, swimmer.actual_time, swimmer.relay_order)
    )

    conn.commit()
    new_id = cursor.lastrowid

    conn.close()
    return {"id": new_id, **swimmer.dict()}


@app.put("/swimmers/{swimmer_id}")
def update_swimmer(swimmer_id: int, swimmer: Swimmer):
    """
    
    """

    conn = get_db()

    result = conn.execute(
        "UPDATE event_swimmers SET name = ?, gender = ?, lane = ?, team = ?, seed_time = ?, actual_time = ?, relay_order = ? WHERE id = ?",
        (swimmer.name, swimmer.gender, swimmer.lane, swimmer.team, swimmer.seed_time, swimmer.actual_time, swimmer.relay_order, swimmer_id)
    )

    conn.commit()
    conn.close()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Swimmer not found")
    return {"id": swimmer_id, **swimmer.dict()}


@app.delete("/swimmers/{swimmer_id}")
def delete_swimmer(swimmer_id: int):
    """
    
    """
    
    conn = get_db()
    
    result = conn.execute("DELETE FROM event_swimmers WHERE id = ?", (swimmer_id,))
    
    conn.commit()
    conn.close()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Swimmer not found")
    return {"message": "Swimmer deleted"}