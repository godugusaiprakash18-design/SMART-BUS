from flask import Flask, render_template, request, jsonify, send_file
import sqlite3
from datetime import datetime
from io import BytesIO

try:
    import qrcode
except ImportError:
    qrcode = None


app = Flask(__name__, static_folder="static", static_url_path="/static")

DATABASE = "smartbus_app.db"
BUS_TYPES = ("AC", "NON-AC")
ALLOWED_DISTANCES = (300, 400, 500, 600, 700, 800, 900, 1000)
MAX_TICKETS = 6
SEAT_CODES = [f"S{i:02d}" for i in range(1, 21)]

FOOD_MENU = {
    "Chicken Dum Biryani": 200,
    "Sambar Rice": 100,
    "Paneer Rice": 150,
    "Diet Coke": 60,
    "Monster": 150,
    "Coffee": 70,
    "Water Bottle": 30,
    "Milk (Children)": 40,
}


def get_db():
    conn = sqlite3.connect(DATABASE, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def get_ac_price(distance):
    return 1000 + ((distance - 300) // 200) * 500


def get_seat_price(distance, bus_type):
    price = get_ac_price(distance)
    return price if bus_type == "AC" else price - 150


def get_rest_stops(distance):
    return [f"Rest Stop {i} - 30 min" for i in range(1, distance // 200 + 1)]


def seat_location(code):
    idx = SEAT_CODES.index(code)
    return idx // 4, idx % 4


def init_db():
    conn = get_db()

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            passenger TEXT NOT NULL,
            phone TEXT NOT NULL,
            bus_type TEXT NOT NULL,
            distance INTEGER NOT NULL,
            seat_fare INTEGER NOT NULL,
            food_total INTEGER NOT NULL DEFAULT 0,
            grand_total INTEGER NOT NULL,
            rest_stops TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'CONFIRMED',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bus_type TEXT NOT NULL,
            seat_code TEXT NOT NULL,
            UNIQUE(bus_type, seat_code)
        );

        CREATE TABLE IF NOT EXISTS booking_seats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            seat_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'CONFIRMED',
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE,
            FOREIGN KEY (seat_id) REFERENCES seats(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS booking_food (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price INTEGER NOT NULL,
            total_price INTEGER NOT NULL,
            FOREIGN KEY (booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        );

        CREATE UNIQUE INDEX IF NOT EXISTS unique_active_seat_booking
        ON booking_seats(seat_id)
        WHERE status = 'CONFIRMED';
        """
    )

    for bus_type in BUS_TYPES:
        for code in SEAT_CODES:
            conn.execute(
                "INSERT OR IGNORE INTO seats(bus_type, seat_code) VALUES (?, ?)",
                (bus_type, code),
            )

    conn.commit()
    conn.close()


def parse_food(raw_food):
    if raw_food is None:
        return []

    if isinstance(raw_food, dict):
        items = list(raw_food.items())
    elif isinstance(raw_food, list):
        items = [
            (x.get("name"), x.get("quantity"))
            for x in raw_food
            if isinstance(x, dict)
        ]
    else:
        raise ValueError("Invalid food format.")

    result = []

    for name, raw_qty in items:
        if name not in FOOD_MENU:
            raise ValueError(f"Invalid food item: {name}")

        try:
            qty = int(raw_qty)
        except (TypeError, ValueError):
            raise ValueError(f"Invalid quantity for {name}.")

        if qty < 0 or qty > 10:
            raise ValueError(f"Quantity for {name} must be between 0 and 10.")

        if qty > 0:
            result.append((name, qty))

    return result


def fetch_booking(conn, booking_id):
    booking = conn.execute(
        "SELECT * FROM bookings WHERE id = ?",
        (booking_id,),
    ).fetchone()

    if not booking:
        return None

    seat_rows = conn.execute(
        """
        SELECT s.seat_code
        FROM booking_seats bs
        JOIN seats s ON s.id = bs.seat_id
        WHERE bs.booking_id = ?
        ORDER BY s.id
        """,
        (booking_id,),
    ).fetchall()

    food_rows = conn.execute(
        """
        SELECT item_name, quantity, unit_price, total_price
        FROM booking_food
        WHERE booking_id = ?
        ORDER BY id
        """,
        (booking_id,),
    ).fetchall()

    return {
        "id": booking["id"],
        "passenger": booking["passenger"],
        "phone": booking["phone"],
        "bus": booking["bus_type"],
        "bus_type": booking["bus_type"],
        "distance": booking["distance"],
        "seats": [r["seat_code"] for r in seat_rows],
        "seatCount": len(seat_rows),
        "seatFare": booking["seat_fare"],
        "food": [dict(r) for r in food_rows],
        "foodTotal": booking["food_total"],
        "total": booking["grand_total"],
        "grandTotal": booking["grand_total"],
        "restStops": (
            booking["rest_stops"].split("|")
            if booking["rest_stops"]
            else []
        ),
        "status": booking["status"],
        "date": booking["created_at"],
    }


@app.after_request
def no_cache(response):
    response.headers["Cache-Control"] = (
        "no-store, no-cache, must-revalidate, max-age=0"
    )
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/health")
def health():
    return jsonify(
        status="OK",
        backend="Python Flask",
        database="SQLite",
        message="SmartBus backend is running.",
    )


@app.route("/api/seats")
def seats():
    bus_type = request.args.get("bus_type", "AC").upper()

    if bus_type not in BUS_TYPES:
        return jsonify(error="Invalid bus type."), 400

    conn = get_db()

    rows = conn.execute(
        """
        SELECT s.seat_code
        FROM seats s
        JOIN booking_seats bs ON bs.seat_id = s.id
        WHERE s.bus_type = ? AND bs.status = 'CONFIRMED'
        ORDER BY s.id
        """,
        (bus_type,),
    ).fetchall()

    conn.close()

    booked = [r["seat_code"] for r in rows]
    booked_set = set(booked)
    available = [
        code for code in SEAT_CODES
        if code not in booked_set
    ]

    return jsonify(
        bus_type=bus_type,
        total=len(SEAT_CODES),
        booked=booked,
        available=available,
    )


@app.route("/api/food")
def food():
    return jsonify(
        [
            {"name": name, "price": price}
            for name, price in FOOD_MENU.items()
        ]
    )


@app.route("/api/suggest", methods=["POST"])
def suggest():
    data = request.get_json(silent=True) or {}

    bus_type = str(
        data.get("bus_type", "AC")
    ).upper()

    try:
        count = int(data.get("count", 1))
    except (TypeError, ValueError):
        return jsonify(error="Invalid ticket count."), 400

    if bus_type not in BUS_TYPES:
        return jsonify(error="Invalid bus type."), 400

    if not 1 <= count <= MAX_TICKETS:
        return jsonify(
            error="Ticket count must be between 1 and 6."
        ), 400

    conn = get_db()

    rows = conn.execute(
        """
        SELECT s.seat_code
        FROM seats s
        LEFT JOIN booking_seats bs
          ON bs.seat_id = s.id
         AND bs.status = 'CONFIRMED'
        WHERE s.bus_type = ? AND bs.id IS NULL
        ORDER BY s.id
        """,
        (bus_type,),
    ).fetchall()

    conn.close()

    available = [r["seat_code"] for r in rows]

    if len(available) < count:
        return jsonify(
            error=f"Only {len(available)} seat(s) are available."
        ), 409

    available_set = set(available)

    best_group = None
    best_score = None

    # Priority-Based Greedy Scoring
    # Priority:
    # 1. Adjacent seats
    # 2. Same row
    # 3. Lower/front seat index
    for start in range(len(SEAT_CODES) - count + 1):

        group = SEAT_CODES[start:start + count]

        if not all(
            code in available_set
            for code in group
        ):
            continue

        rows_used = [
            seat_location(code)[0]
            for code in group
        ]

        adjacent = 0

        for a, b in zip(group, group[1:]):
            ra, ca = seat_location(a)
            rb, cb = seat_location(b)

            # Do not treat B/C across the aisle as adjacent.
            crosses_aisle = (
                ra == rb
                and {ca, cb} == {1, 2}
            )

            if (
                ra == rb
                and abs(ca - cb) == 1
                and not crosses_aisle
            ):
                adjacent += 1

        same_row = (
            1
            if len(set(rows_used)) == 1
            else 0
        )

        front_bonus = -sum(
            SEAT_CODES.index(code)
            for code in group
        )

        score = (
            adjacent * 100
            + same_row * 50
            + front_bonus
        )

        if best_score is None or score > best_score:
            best_score = score
            best_group = group

    if best_group is None:
        best_group = available[:count]

    return jsonify(
        seats=best_group,
        algorithm="Priority-Based Greedy Scoring",
        message=(
            "Seats suggested using the "
            "priority-based greedy scoring algorithm."
        ),
    )


@app.route("/api/bookings", methods=["POST"])
def create_booking():
    data = request.get_json(silent=True) or {}

    passenger = str(
        data.get("passenger", "")
    ).strip()

    phone = str(
        data.get("phone", "")
    ).strip()

    bus_type = str(
        data.get("bus_type", "")
    ).upper()

    distance = data.get("distance")
    raw_seats = data.get("seats")

    if not passenger:
        return jsonify(
            error="Enter passenger name."
        ), 400

    if not phone.isdigit() or len(phone) != 10:
        return jsonify(
            error="Phone number must contain exactly 10 digits."
        ), 400

    if bus_type not in BUS_TYPES:
        return jsonify(
            error="Invalid bus type."
        ), 400

    try:
        distance = int(distance)
    except (TypeError, ValueError):
        return jsonify(
            error="Invalid journey distance."
        ), 400

    if distance not in ALLOWED_DISTANCES:
        return jsonify(
            error="Distance must be between 300 and 1000 KM."
        ), 400

    if not isinstance(raw_seats, list) or not raw_seats:
        return jsonify(
            error="Select at least one seat."
        ), 400

    if len(raw_seats) > MAX_TICKETS:
        return jsonify(
            error="Maximum 6 tickets per booking."
        ), 400

    seats = [
        str(x).upper()
        for x in raw_seats
    ]

    if len(set(seats)) != len(seats):
        return jsonify(
            error="Duplicate seats are not allowed."
        ), 400

    if any(
        x not in SEAT_CODES
        for x in seats
    ):
        return jsonify(
            error="Invalid seat selection."
        ), 400

    try:
        food_items = parse_food(
            data.get("food", {})
        )
    except ValueError as exc:
        return jsonify(error=str(exc)), 400

    fare_each = get_seat_price(
        distance,
        bus_type,
    )

    seat_fare = (
        fare_each * len(seats)
    )

    food_total = sum(
        FOOD_MENU[name] * qty
        for name, qty in food_items
    )

    grand_total = (
        seat_fare + food_total
    )

    stops = get_rest_stops(
        distance
    )

    created_at = (
        datetime.now()
        .astimezone()
        .strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    conn = get_db()

    try:
        conn.execute(
            "BEGIN IMMEDIATE"
        )

        placeholders = ",".join(
            "?" for _ in seats
        )

        occupied_rows = conn.execute(
            f"""
            SELECT s.seat_code
            FROM seats s
            JOIN booking_seats bs
              ON bs.seat_id = s.id
            WHERE s.bus_type = ?
              AND s.seat_code IN ({placeholders})
              AND bs.status = 'CONFIRMED'
            """,
            [bus_type, *seats],
        ).fetchall()

        occupied = [
            r["seat_code"]
            for r in occupied_rows
        ]

        if occupied:
            conn.rollback()

            return jsonify(
                error=(
                    "Seat(s) already booked: "
                    + ", ".join(occupied)
                )
            ), 409

        cur = conn.execute(
            """
            INSERT INTO bookings(
                passenger,
                phone,
                bus_type,
                distance,
                seat_fare,
                food_total,
                grand_total,
                rest_stops,
                status,
                created_at
            )
            VALUES(
                ?, ?, ?, ?, ?, ?,
                ?, ?, 'CONFIRMED', ?
            )
            """,
            (
                passenger,
                phone,
                bus_type,
                distance,
                seat_fare,
                food_total,
                grand_total,
                "|".join(stops),
                created_at,
            ),
        )

        booking_id = cur.lastrowid

        for code in seats:

            seat_row = conn.execute(
                """
                SELECT id
                FROM seats
                WHERE bus_type = ?
                  AND seat_code = ?
                """,
                (
                    bus_type,
                    code,
                ),
            ).fetchone()

            conn.execute(
                """
                INSERT INTO booking_seats(
                    booking_id,
                    seat_id,
                    status
                )
                VALUES(
                    ?, ?, 'CONFIRMED'
                )
                """,
                (
                    booking_id,
                    seat_row["id"],
                ),
            )

        for name, qty in food_items:

            unit_price = FOOD_MENU[name]

            conn.execute(
                """
                INSERT INTO booking_food(
                    booking_id,
                    item_name,
                    quantity,
                    unit_price,
                    total_price
                )
                VALUES(
                    ?, ?, ?, ?, ?
                )
                """,
                (
                    booking_id,
                    name,
                    qty,
                    unit_price,
                    unit_price * qty,
                ),
            )

        conn.commit()

        booking = fetch_booking(
            conn,
            booking_id,
        )

        return jsonify(
            message="Booking confirmed.",
            booking=booking,
        ), 201

    except sqlite3.IntegrityError:
        conn.rollback()

        return jsonify(
            error=(
                "Booking conflict. "
                "Refresh the seat map and try again."
            )
        ), 409

    except sqlite3.Error as exc:
        conn.rollback()

        return jsonify(
            error=f"SQLite database error: {exc}"
        ), 500

    finally:
        conn.close()


@app.route("/api/bookings", methods=["GET"])
def get_bookings():
    phone = str(
        request.args.get(
            "phone",
            "",
        )
    ).strip()

    conn = get_db()

    if phone:
        rows = conn.execute(
            """
            SELECT id
            FROM bookings
            WHERE phone = ?
            ORDER BY id DESC
            """,
            (phone,),
        ).fetchall()

    else:
        rows = conn.execute(
            """
            SELECT id
            FROM bookings
            ORDER BY id DESC
            """
        ).fetchall()

    result = []

    for row in rows:

        booking = fetch_booking(
            conn,
            row["id"],
        )

        if booking:
            result.append(
                booking
            )

    conn.close()

    return jsonify(result)


@app.route("/api/bookings/<int:booking_id>")
def get_booking(booking_id):
    conn = get_db()

    booking = fetch_booking(
        conn,
        booking_id,
    )

    conn.close()

    if not booking:
        return jsonify(
            error="Booking not found."
        ), 404

    return jsonify(
        booking=booking
    )


@app.route(
    "/api/bookings/<int:booking_id>/cancel",
    methods=["POST"],
)
def cancel_booking(booking_id):
    conn = get_db()

    try:
        conn.execute(
            "BEGIN IMMEDIATE"
        )

        row = conn.execute(
            """
            SELECT status
            FROM bookings
            WHERE id = ?
            """,
            (booking_id,),
        ).fetchone()

        if not row:
            conn.rollback()

            return jsonify(
                error="Booking not found."
            ), 404

        if row["status"] == "CANCELLED":
            conn.rollback()

            return jsonify(
                error="Booking is already cancelled."
            ), 400

        conn.execute(
            """
            UPDATE bookings
            SET status = 'CANCELLED'
            WHERE id = ?
            """,
            (booking_id,),
        )

        conn.execute(
            """
            UPDATE booking_seats
            SET status = 'RELEASED'
            WHERE booking_id = ?
            """,
            (booking_id,),
        )

        conn.commit()

        booking = fetch_booking(
            conn,
            booking_id,
        )

        return jsonify(
            message="Booking cancelled.",
            booking=booking,
        )

    except sqlite3.Error as exc:
        conn.rollback()

        return jsonify(
            error=f"Could not cancel booking: {exc}"
        ), 500

    finally:
        conn.close()


@app.route(
    "/api/reset-demo",
    methods=["POST"],
)
def reset_demo():
    conn = get_db()

    try:
        conn.execute(
            "BEGIN IMMEDIATE"
        )

        conn.execute(
            "DELETE FROM booking_food"
        )

        conn.execute(
            "DELETE FROM booking_seats"
        )

        conn.execute(
            "DELETE FROM bookings"
        )

        conn.commit()

        return jsonify(
            message="All demo bookings cleared."
        )

    except sqlite3.Error as exc:
        conn.rollback()

        return jsonify(
            error=f"Could not reset demo bookings: {exc}"
        ), 500

    finally:
        conn.close()


@app.route(
    "/api/bookings/<int:booking_id>/qr"
)
def booking_qr(booking_id):

    if qrcode is None:
        return jsonify(
            error=(
                "QR package missing. "
                "Run: pip install qrcode pillow"
            )
        ), 500

    conn = get_db()

    booking = fetch_booking(
        conn,
        booking_id,
    )

    conn.close()

    if not booking:
        return jsonify(
            error="Booking not found."
        ), 404

    food_text = ", ".join(
        (
            f"{item['item_name']} "
            f"x{item['quantity']}"
        )
        for item in booking["food"]
    ) or "None"

    qr_text = (
        f"SmartBus Booking #{booking['id']}\n"
        f"Passenger: {booking['passenger']}\n"
        f"Phone: {booking['phone']}\n"
        f"Bus: {booking['bus_type']}\n"
        f"Distance: {booking['distance']} KM\n"
        f"Seats: {', '.join(booking['seats'])}\n"
        f"Food: {food_text}\n"
        f"Seat Fare: Rs.{booking['seatFare']}\n"
        f"Food Total: Rs.{booking['foodTotal']}\n"
        f"Grand Total: Rs.{booking['grandTotal']}\n"
        f"Status: {booking['status']}\n"
        f"Booked: {booking['date']}"
    )

    qr = qrcode.QRCode(
        version=1,
        box_size=8,
        border=4,
    )

    qr.add_data(qr_text)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    return send_file(
        buffer,
        mimetype="image/png",
        max_age=0,
    )


init_db()


if __name__ == "__main__":

    print("=" * 42)
    print("          SMARTBUS FLASK BACKEND")
    print("=" * 42)
    print("Frontend : HTML + CSS + JavaScript")
    print("Backend  : Python Flask")
    print("Database : SQLite")
    print("QR       : Python qrcode")
    print("URL      : http://127.0.0.1:5000")
    print("=" * 42)

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False,
    )