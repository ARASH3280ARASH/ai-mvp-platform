"""
Whilber-AI — Robot Store Manager
==================================
Manage trading robots: upload, list, download, admin CRUD.
Storage: robots.json + files in robots/ directory.
"""

import json
import os
import shutil
import hashlib
import base64
from datetime import datetime, timezone
from threading import Lock

PROJECT_DIR = r"C:\Users\Administrator\Desktop\mvp"
ROBOTS_FILE = os.path.join(PROJECT_DIR, "robots.json")
ROBOTS_DIR = os.path.join(PROJECT_DIR, "robots")
IMAGES_DIR = os.path.join(PROJECT_DIR, "robots", "images")
FILES_DIR = os.path.join(PROJECT_DIR, "robots", "files")
ADMIN_PASSWORD = "whilber2024"

_lock = Lock()

# Ensure directories
for d in [ROBOTS_DIR, IMAGES_DIR, FILES_DIR]:
    os.makedirs(d, exist_ok=True)


def _load():
    try:
        if os.path.exists(ROBOTS_FILE):
            with open(ROBOTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "reviews" not in data:
                data["reviews"] = []
            return data
    except Exception:
        pass
    return {"robots": [], "categories": [
        {"id": "scalper", "name_fa": "اسکالپر"},
        {"id": "trend", "name_fa": "روندی"},
        {"id": "grid", "name_fa": "گرید"},
        {"id": "hedge", "name_fa": "هج"},
        {"id": "news", "name_fa": "خبری"},
        {"id": "indicator", "name_fa": "اندیکاتور"},
        {"id": "utility", "name_fa": "ابزار"},
        {"id": "other", "name_fa": "سایر"},
    ], "reviews": []}


def _save(data):
    with _lock:
        with open(ROBOTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def verify_admin(password):
    return password == ADMIN_PASSWORD


def get_categories():
    data = _load()
    return data.get("categories", [])


# ── Robot CRUD ──────────────────────────────────────

def add_robot(
    name_fa,
    description_fa,
    category,
    version="1.0",
    platform="MT5",
    price_type="free",
    price_amount=0,
    symbols_fa="",
    timeframes_fa="",
    min_balance="",
    features_fa="",
    tags="",
    image_data=None,
    image_ext="png",
    file_data=None,
    file_name="robot.ex5",
):
    data = _load()
    rid = hashlib.md5(f"{name_fa}{datetime.now().isoformat()}".encode()).hexdigest()[:8]

    # Save image
    image_path = ""
    if image_data:
        image_path = f"images/{rid}.{image_ext}"
        full_img = os.path.join(ROBOTS_DIR, image_path)
        try:
            img_bytes = base64.b64decode(image_data)
            with open(full_img, "wb") as f:
                f.write(img_bytes)
        except Exception:
            image_path = ""

    # Save robot file
    file_path = ""
    file_size = 0
    if file_data:
        safe_name = f"{rid}_{file_name}"
        file_path = f"files/{safe_name}"
        full_file = os.path.join(ROBOTS_DIR, file_path)
        try:
            file_bytes = base64.b64decode(file_data)
            with open(full_file, "wb") as f:
                f.write(file_bytes)
            file_size = len(file_bytes)
        except Exception:
            file_path = ""

    robot = {
        "id": rid,
        "name_fa": name_fa,
        "description_fa": description_fa,
        "category": category,
        "version": version,
        "platform": platform,
        "price_type": price_type,
        "price_amount": price_amount,
        "symbols_fa": symbols_fa,
        "timeframes_fa": timeframes_fa,
        "min_balance": min_balance,
        "features_fa": features_fa,
        "tags": tags,
        "image_path": image_path,
        "file_path": file_path,
        "file_name": file_name,
        "file_size": file_size,
        "downloads": 0,
        "views": 0,
        "rating_avg": 0,
        "rating_count": 0,
        "active": True,
        "featured": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    data["robots"].insert(0, robot)
    _save(data)
    return {"success": True, "robot_id": rid, "robot": robot}


def update_robot(rid, updates, image_data=None, image_ext="png", file_data=None, file_name=None):
    data = _load()
    for r in data["robots"]:
        if r["id"] == rid:
            for k, v in updates.items():
                if k in r and k not in ("id", "created_at", "downloads"):
                    r[k] = v
            r["updated_at"] = datetime.now(timezone.utc).isoformat()

            if image_data:
                img_path = f"images/{rid}.{image_ext}"
                full_img = os.path.join(ROBOTS_DIR, img_path)
                try:
                    with open(full_img, "wb") as f:
                        f.write(base64.b64decode(image_data))
                    r["image_path"] = img_path
                except Exception:
                    pass

            if file_data and file_name:
                safe_name = f"{rid}_{file_name}"
                fpath = f"files/{safe_name}"
                full_file = os.path.join(ROBOTS_DIR, fpath)
                try:
                    fbytes = base64.b64decode(file_data)
                    with open(full_file, "wb") as f:
                        f.write(fbytes)
                    r["file_path"] = fpath
                    r["file_name"] = file_name
                    r["file_size"] = len(fbytes)
                except Exception:
                    pass

            _save(data)
            return {"success": True, "robot": r}

    return {"success": False, "error": "Robot not found"}


def delete_robot(rid):
    data = _load()
    robot = None
    for r in data["robots"]:
        if r["id"] == rid:
            robot = r
            break

    if not robot:
        return {"success": False, "error": "Not found"}

    # Delete files
    if robot.get("image_path"):
        fp = os.path.join(ROBOTS_DIR, robot["image_path"])
        if os.path.exists(fp):
            os.remove(fp)
    if robot.get("file_path"):
        fp = os.path.join(ROBOTS_DIR, robot["file_path"])
        if os.path.exists(fp):
            os.remove(fp)

    data["robots"] = [r for r in data["robots"] if r["id"] != rid]
    _save(data)
    return {"success": True}


def get_robots(category=None, active_only=True):
    data = _load()
    robots = data.get("robots", [])
    if active_only:
        robots = [r for r in robots if r.get("active", True)]
    if category:
        robots = [r for r in robots if r.get("category") == category]
    return robots


def get_robot(rid):
    data = _load()
    for r in data["robots"]:
        if r["id"] == rid:
            return r
    return None


def increment_download(rid):
    data = _load()
    for r in data["robots"]:
        if r["id"] == rid:
            r["downloads"] = r.get("downloads", 0) + 1
            _save(data)
            return r["downloads"]
    return 0


def toggle_featured(rid):
    data = _load()
    for r in data["robots"]:
        if r["id"] == rid:
            r["featured"] = not r.get("featured", False)
            _save(data)
            return {"success": True, "featured": r["featured"]}
    return {"success": False}


def toggle_active(rid):
    data = _load()
    for r in data["robots"]:
        if r["id"] == rid:
            r["active"] = not r.get("active", True)
            _save(data)
            return {"success": True, "active": r["active"]}
    return {"success": False}


def get_stats():
    data = _load()
    robots = data.get("robots", [])
    total = len(robots)
    active = sum(1 for r in robots if r.get("active", True))
    total_downloads = sum(r.get("downloads", 0) for r in robots)
    total_views = sum(r.get("views", 0) for r in robots)
    total_reviews = len(data.get("reviews", []))
    return {"total": total, "active": active, "downloads": total_downloads, "views": total_views, "reviews": total_reviews}


# ── Reviews & Ratings ─────────────────────────────────

def _recalc_rating(data, robot_id):
    """Recalculate cached rating_avg and rating_count for a robot from reviews."""
    reviews = [rv for rv in data.get("reviews", []) if rv["robot_id"] == robot_id]
    count = len(reviews)
    avg = round(sum(rv["rating"] for rv in reviews) / count, 1) if count else 0
    for r in data["robots"]:
        if r["id"] == robot_id:
            r["rating_avg"] = avg
            r["rating_count"] = count
            break


def add_review(robot_id, author, rating, text):
    if not author or not author.strip():
        return {"success": False, "error": "author required"}
    if not text or not text.strip():
        return {"success": False, "error": "text required"}
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return {"success": False, "error": "rating must be 1-5"}

    data = _load()
    # Verify robot exists
    found = False
    for r in data["robots"]:
        if r["id"] == robot_id:
            found = True
            break
    if not found:
        return {"success": False, "error": "robot not found"}

    rev_id = hashlib.md5(f"{robot_id}{author}{datetime.now().isoformat()}".encode()).hexdigest()[:10]
    review = {
        "id": rev_id,
        "robot_id": robot_id,
        "author": author.strip(),
        "rating": rating,
        "text": text.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    data.setdefault("reviews", []).insert(0, review)
    _recalc_rating(data, robot_id)
    _save(data)
    return {"success": True, "review": review}


def get_reviews(robot_id):
    data = _load()
    reviews = [rv for rv in data.get("reviews", []) if rv["robot_id"] == robot_id]
    reviews.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return reviews


def delete_review(review_id, password):
    if not verify_admin(password):
        return {"success": False, "error": "forbidden"}
    data = _load()
    robot_id = None
    for rv in data.get("reviews", []):
        if rv["id"] == review_id:
            robot_id = rv["robot_id"]
            break
    if not robot_id:
        return {"success": False, "error": "review not found"}

    data["reviews"] = [rv for rv in data["reviews"] if rv["id"] != review_id]
    _recalc_rating(data, robot_id)
    _save(data)
    return {"success": True}


# ── Views ─────────────────────────────────────────────

def increment_views(robot_id):
    data = _load()
    for r in data["robots"]:
        if r["id"] == robot_id:
            r["views"] = r.get("views", 0) + 1
            _save(data)
            return r["views"]
    return 0


# ── Search & Sort ─────────────────────────────────────

def search_robots(query):
    if not query or not query.strip():
        return []
    q = query.strip().lower()
    data = _load()
    results = []
    for r in data.get("robots", []):
        if not r.get("active", True):
            continue
        searchable = " ".join([
            r.get("name_fa", ""),
            r.get("description_fa", ""),
            r.get("tags", ""),
            r.get("symbols_fa", ""),
            r.get("features_fa", ""),
        ]).lower()
        if q in searchable:
            results.append(r)
    return results


def get_robots_sorted(sort_by="newest", category=None):
    data = _load()
    robots = [r for r in data.get("robots", []) if r.get("active", True)]
    if category:
        robots = [r for r in robots if r.get("category") == category]

    if sort_by == "popular":
        robots.sort(key=lambda x: x.get("downloads", 0), reverse=True)
    elif sort_by == "rating":
        robots.sort(key=lambda x: x.get("rating_avg", 0), reverse=True)
    elif sort_by == "views":
        robots.sort(key=lambda x: x.get("views", 0), reverse=True)
    else:  # newest
        robots.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    return robots
