# Network Tic-Tac-Toe Game

A real-time multiplayer Tic-Tac-Toe game implementation over TCP/IP networks. This application demonstrates network programming concepts including socket communication, multi-threading, and real-time data synchronization.

## Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Network Protocol](#network-protocol)
- [Game Features](#game-features)
- [Logging and Statistics](#logging-and-statistics)
- [Future Improvements](#future-improvements)

## Features

The application implements all required features for Project 2:

1. **Real-time Turn-based Gameplay**: Players take turns with moves updating instantly across both clients
2. **Player Matching**: Users can join and wait for an opponent to connect
3. **Synchronized Game State**: Both players see the same board state in real-time
4. **In-game Chat**: Players can message each other while playing
5. **Statistics Tracking**: System tracks wins, losses, and draws for each player
6. **Connection Activity Logging**: Server logs all connection events and game activities
7. **Command-line Interface**: Intuitive text-based user interface
8. **Graphical User Interface (GUI)**: Optional Tkinter-based interface with clickable board and chat display
9. **Web Dashboard**: A Flask-based leaderboard that displays player statistics in real time

## System Architecture

The application follows a **client-server architecture**:

```
┌─────────────┐         TCP/IP          ┌─────────────┐
│   Client 1  │◄───────────────────────►│             │
│  (Player X) │                         │   Server    │
└─────────────┘                         │  (Game      │
                                        │   Logic)    │
┌─────────────┐         TCP/IP          │             │
│   Client 2  │◄───────────────────────►│             │
│  (Player O) │                         └─────────────┘
└─────────────┘
```
- **GUI Client (`gui_client.py`)**:
  - Optional Tkinter-based graphical interface
  - Provides clickable board, real-time updates, and integrated chat display

- **Web Dashboard (`dashboard.py`)**:
  - Simple Flask server displaying player statistics from stats.json
  - Shows wins, losses, and draws in a leaderboard format

### Components

- **Server (`server.py`)**: 
  - Manages game sessions between two players
  - Handles game logic and state synchronization
  - Maintains player statistics and connection logs
  - Uses `select.select()` for efficient I/O multiplexing

- **Client (`client.py`)**:
  - Connects to server via TCP socket
  - Uses separate thread for receiving server messages
  - Provides interactive command-line interface
  - Displays game board and handles user input

## Technology Stack

- **Language**: Python 3.x
- **Networking**: 
  - `socket` module for TCP/IP communication
  - `select` module for I/O multiplexing
- **Concurrency**: 
  - `threading` for multi-threaded client message handling
- **Data Persistence**: 
  - `json` for statistics storage
- **Logging**: 
  - `logging` module for server activity tracking
- **GUI**:
  - Tkinter for graphical game interface and chat display
- **Web Dashboard**:
  - Flask (Python micro-framework) for rendering player statistics

## Prerequisites

- Python 3.6 or higher
- Network connectivity between server and clients
- The core game (server + CLI client + GUI client) uses only Python standard libraries.
- The optional dashboard requires one external dependency: Flask.

## Installation

1. Clone or download the project repository
2. Ensure Python 3.6+ is installed on your system
3. Create Virtual Environment (recommended)
4. Install Flask (optional, required for the dashboard)

## Usage

### Starting the Server

```bash
python server.py
```

The server will start listening on `0.0.0.0:5500` by default. You should see:
```
Server listening on 0.0.0.0:5500
```

### Starting Clients

### Starting the GUI Client

The GUI client provides a Tkinter-based interface with a clickable board and integrated chat.

```bash
python gui_client.py <server_host> <server_port> <username>
```

Open two terminal windows and run the client in each:

**Example:**
```bash
python gui_client.py localhost 5500 Alice
python gui_client.py localhost 5500 Bob
```

### Client Commands

Once connected, players can use the following commands:

- `move <row> <col>` - Make a move at the specified position (row and col are 0-2)
  - Example: `move 1 1` places a mark at the center
- `chat <message>` - Send a message to the opponent
  - Example: `chat Good move!`
- `quit` - Quit the current game

### Game Flow

1. **Player 1 connects** and enters username
2. **Player 1 waits** for an opponent
3. **Player 2 connects** and enters username
4. **Game starts** automatically:
   - Player 1 (X) goes first
   - Both players see the initial empty board
5. **Players take turns** making moves
6. **Game ends** when:
   - A player wins (three in a row)
   - The board is full (draw)
   - A player quits or disconnects

## Project Structure

```
cs5700-tictactoe/
├── server.py # Game server
├── client.py # CLI client
├── gui_client.py # Tkinter-based GUI client
├── dashboard.py # Web dashboard for statistics display
├── stats.json # Persistent player statistics
├── server.log # Server activity log
├── venv/ # Optional virtual environment
└── README.md
```

## Network Protocol

The application uses a simple text-based protocol over TCP:

### Client to Server Messages

- `USER <username>` - Register username
- `MOVE <row> <col>` - Make a move (row, col: 0-2)
- `CHAT <message>` - Send chat message
- `QUIT` - Quit the game

### Server to Client Messages

- `INFO <message>` - Informational message
- `BOARD <state>` - Board state (9-character string: X, O, or -)
- `TURN <mark>` - Current player's turn (X or O)
- `START <mark> <opponent>` - Game start notification
- `MSG <sender>: <message>` - Chat message from opponent
- `STATS <wins> <losses> <draws>` - Player statistics
- `RESULT <outcome>` - Game result (WIN, LOSE, or DRAW)

## Game Features

### Turn Management
- Server enforces turn order (X moves first, then O)
- Players cannot move out of turn
- Invalid moves are rejected with error messages

### Board Synchronization
- After each move, both players receive the updated board state
- Board is represented as a 9-character string (row-major order)
- Visual representation displayed on client side

### Win Detection
The server checks for wins in 8 possible configurations:
- 3 horizontal lines
- 3 vertical lines
- 2 diagonal lines

### Statistics Tracking
- Statistics are persisted in `stats.json`
- Each player's record includes:
  - Wins
  - Losses
  - Draws
- Statistics are updated after each game

### Error Handling
- Invalid moves (out of bounds, occupied cells)
- Connection loss detection
- Graceful handling of player disconnections

## Logging and Statistics

### Server Logging
- All connection events logged to `server.log`
- Log format: `%(asctime)s [%(levelname)s] %(message)s`
- Logged events include:
  - Server startup
  - Player connections
  - Game starts
  - Player disconnections

### Statistics File
- Player statistics stored in `stats.json`
- Format:
```json
{
  "PlayerName": {
    "wins": 0,
    "losses": 0,
    "draws": 0
  }
}
```

## Future Improvements

Potential enhancements for future versions:

1. Support for multiple concurrent games (server currently supports one game at a time)
2. Improved GUI responsiveness and smoother animations
3. Automatic reconnection or game recovery after a player disconnects
4. Authentication system and persistent player accounts
5. Multi-game tournament mode

## Authors

Minyi Zhu, Dixuan Zhao, Yuanyuan Wu