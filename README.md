# SMART-BUS http://127.0.0.1:5000/
# 🚌 SmartBus — Smart Bus Seat Allocation System

A web-based **Smart Bus Seat Allocation System** that uses a **Priority-Based Greedy Scoring algorithm** to recommend available seats for passengers.

The project combines a premium **Navy Ocean** frontend with a **Python Flask** backend and **SQLite** database.

---

## 🌊 Project Overview

SmartBus is designed to make bus seat selection simple, fast, and intelligent.

Instead of making passengers choose seats completely at random, the **Smart Arrange** feature evaluates available seat groups using defined priorities:

1. **Adjacent seats**
2. **Same-row seats**
3. **Lower/front seat index**

The highest-scoring available group is recommended to the passenger.

---

## ✨ Features

- 🎟️ Select **1–6 tickets** per booking
- 🚌 Separate **AC / Non-AC** seat allocation
- 💺 20 seats per bus type
- ✦ **Smart Arrange** using a greedy scoring algorithm
- 🌊 Premium **Dark Navy Ocean** UI
- 💠 Clearly highlighted selected/allotted seats
- 🔴 Visual booked-seat state
- 🥘 Food and beverage add-ons with quantity controls
- 💰 Dynamic fare calculation based on distance and bus type
- 🛑 Rest-stop information for long journeys
- 🧾 Detailed final bill
- 🎫 Digital booking ticket
- 🔳 QR-code ticket generation
- 📜 Booking history
- ❌ Booking cancellation with seat release
- 📊 Live bus occupancy
- 🧠 Greedy algorithm score explanation
- 🔄 Reset Demo for hackathon testing
- 💾 SQLite database persistence

---

## 🧠 DAA Algorithm

### Priority-Based Greedy Scoring

The Smart Arrange module follows a greedy strategy.

For each possible available group of seats, the system calculates a score based on:

### 1. Adjacency
Adjacent seats receive the highest priority because passengers travelling together generally prefer seats next to each other.

### 2. Same Row
A group where all requested seats belong to the same row receives additional priority.

### 3. Front / Lower Seat Index
When other priorities are comparable, seats with lower/front indices receive preference.

### Greedy Process

```text
Input:
    Number of tickets
    Available seats

For each possible seat group:
    Check whether all seats are available
    Calculate adjacency score
    Calculate same-row score
    Calculate front-seat priority
    Calculate total score

Choose the available group with the highest score
Return the recommended seats
```

This approach makes a local best choice among the currently available groups.

---

## ⏱️ Complexity

For the implementation used in this project:

- **Time Complexity:** `O(n × k)`
- **Space Complexity:** `O(n)`

Where:

- `n` = number of seats considered
- `k` = number of tickets requested

For this demo, there are **20 seats per bus** and a maximum of **6 tickets per booking**, so the search space is small.

---

## 💰 Fare Structure

### AC

| Distance | Fare / Seat |
|---|---:|
| 300–400 KM | ₹1,000 |
| 500–600 KM | ₹1,500 |
| 700–800 KM | ₹2,000 |
| 900–1000 KM | ₹2,500 |

### Non-AC

Non-AC fare is **₹150 less per seat** than the corresponding AC fare.

| Distance | Fare / Seat |
|---|---:|
| 300–400 KM | ₹850 |
| 500–600 KM | ₹1,350 |
| 700–800 KM | ₹1,850 |
| 900–1000 KM | ₹2,350 |

---

## 🍱 Food Menu

| Item | Price |
|---|---:|
| Chicken Dum Biryani | ₹200 |
| Sambar Rice | ₹100 |
| Paneer Rice | ₹150 |
| Diet Coke | ₹60 |
| Monster | ₹150 |
| Coffee | ₹70 |
| Water Bottle | ₹30 |
| Milk (Children) | ₹40 |

---

## 🛠️ Technology Stack

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Flask

### Database
- SQLite

### QR Generation
- Python `qrcode`
- Pillow

---

## 📁 Project Structure

```text
Smart allocation/
│
├── app.py
├── requirements.txt
├── README.md
│
├── templates/
│   └── index.html
│
├── static/
│   └── css/
│       └── smartbus-theme.css
│
└── smartbus_app.db
```

> The current frontend contains the main styling directly inside `index.html`, so the application does not depend on the external CSS file to render the main UI.

---

## 🚀 How to Run

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd SmartBus-Seat-Allocation-System
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Flask server

```bash
python app.py
```

### 4. Open the application

Visit:

```text
http://127.0.0.1:5000
```

---

## 🔌 Main API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | SmartBus frontend |
| GET | `/api/health` | Backend health check |
| GET | `/api/seats?bus_type=AC` | Get seat availability |
| GET | `/api/food` | Get food menu |
| POST | `/api/suggest` | Smart Arrange seat recommendation |
| POST | `/api/bookings` | Create a booking |
| GET | `/api/bookings` | Booking history |
| GET | `/api/bookings/<id>` | Get one booking |
| POST | `/api/bookings/<id>/cancel` | Cancel booking |
| GET | `/api/bookings/<id>/qr` | Generate QR ticket |
| POST | `/api/reset-demo` | Clear demo bookings |

---

## 🧪 Testing Performed

The system was tested for:

- Manual seat selection
- Smart Arrange
- AC / Non-AC switching
- 1–6 ticket selection
- Food quantity updates
- Fare and bill calculation
- Booking confirmation
- SQLite persistence
- QR-ticket generation
- Booking history
- Booking cancellation
- Seat release after cancellation
- Reset Demo
- Live seat availability updates
- Algorithm score display

---

## 🎬 Hackathon Demo Flow

```text
Enter passenger details
        ↓
Select distance
        ↓
Choose ticket count
        ↓
Choose AC / Non-AC
        ↓
Click Smart Arrange
        ↓
Show selected seats + algorithm score
        ↓
Add food
        ↓
Confirm Booking
        ↓
Show digital ticket + QR
        ↓
Open Booking History
        ↓
Cancel booking
        ↓
Show seats released
        ↓
Reset Demo
```

---

## 🔮 Future Improvements

Possible extensions include:

- Multiple bus routes and destinations
- Multiple buses per route
- User login and registration
- Online payment integration
- Real-time seat synchronization for multiple users
- Advanced optimization for larger buses
- Passenger preference profiles
- Accessibility-aware allocation
- Admin dashboard and analytics
- Cloud database deployment
- Deployment to a public web server

---

## 🎓 Academic / DAA Relevance

This project demonstrates practical application of:

- Greedy algorithm design
- Search over feasible seat groups
- Constraint handling
- Time and space complexity analysis
- Database-backed state management
- Frontend-backend integration

The main DAA component is the **Priority-Based Greedy Scoring algorithm** used by **Smart Arrange**.

---

## 👥 Project

**SmartBus — Smart Bus Seat Allocation System**

Built with:

`HTML + CSS + JavaScript + Python Flask + SQLite`

---

## 📌 Note

This project is designed as a **class/hackathon demonstration system**. The fare rules, seat capacity, rest-stop timing, and allocation priorities are project-defined rules.
