import socket
import threading
import json
import os
import logging
import select

# Server config
HOST = "0.0.0.0"
PORT = 5500

# Files for stats and logs
STATS_FILE = "stats.json"
LOG_FILE = "server.log"

# Logging setup
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


# Stats are kept in memory + a lock to be safe
stats_lock = threading.Lock()
stats = {}


# Load stats from json file if it exists
def load_stats():
    global stats
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except Exception:
            stats = {}
    else:
        stats = {}


# Save stats back to json file
def save_stats():
    with stats_lock:
        try:
            with open(STATS_FILE, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logging.error("Error saving stats: %s", e)


# Update winner/loser stats or draw result
def update_stats(winner_name, loser_name, draw=False):
    with stats_lock:
        # Make sure both players have an entry
        for name in [winner_name, loser_name]:
            if name not in stats:
                stats[name] = {"wins": 0, "losses": 0, "draws": 0}
        
        if draw:
            stats[winner_name]["draws"] += 1
            stats[loser_name]["draws"] += 1
        else:
            stats[winner_name]["wins"] += 1
            stats[loser_name]["losses"] += 1
    save_stats()


# Get a single player's stats
def get_stats(name):
    with stats_lock:
        if name not in stats:
            stats[name] = {"wins": 0, "losses": 0, "draws": 0}
        return stats[name]


# Send one line to a socket
def send_line(sock, text):
    try:
        sock.sendall((text + "\n").encode("utf-8"))
    except OSError:
        pass


# Receive one line from socket, return None on disconnect
def recv_line(sock):
    data = []
    try:
        while True:
            ch = sock.recv(1)
            # remote side closed
            if not ch:
                return None
            ch = ch.decode("utf-8")
            if ch == "\n":
                break
            data.append(ch)
    except OSError:
        return None
    return "".join(data)


# Check 3x3 board winner / draw / ongoing
def check_winner(board):
    # Board is list of 9 chars: 'X', 'O', or '-'
    lines = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    ]
    for a, b, c in lines:
        if board[a] != "-" and board[a] == board[b] == board[c]:
            return board[a]
    if "-" not in board:
        return "DRAW"
    return None


# Convert board list into 9-char string
def board_to_string(board):
    return "".join(board)


# Send current board + whose turn to both players
def send_board(p1_sock, p2_sock, board, current_mark):
    state = board_to_string(board)
    for s in (p1_sock, p2_sock):
        send_line(s, f"BOARD {state}")
        send_line(s, f"TURN {current_mark}")


# Send INFO message to both players
def send_info_to_both(p1_sock, p2_sock, msg):
    for s in (p1_sock, p2_sock):
        send_line(s, f"INFO {msg}")


# Broadcast chat message from one player to both
def broadcast_chat(p1_sock, p2_sock, sender_name, text):
    line = f"MSG {sender_name}: {text}"
    for s in (p1_sock, p2_sock):
        send_line(s, line)


# Handle a single tic-tac-toe game between two players
def handle_game(p1_sock, p1_name, p2_sock, p2_name):
    logging.info("Starting game between %s and %s", p1_name, p2_name)

    # Player1 is X, player2 is O
    p1_mark = "X"
    p2_mark = "O"

    # Tell each player their mark and opponent name
    send_line(p1_sock, f"START {p1_mark} {p2_name}")
    send_line(p2_sock, f"START {p2_mark} {p1_name}")

    # Send stats to both players
    stats1 = get_stats(p1_name)
    stats2 = get_stats(p2_name)
    send_line(p1_sock, f"STATS {stats1['wins']} {stats1['losses']} {stats1['draws']}")
    send_line(p2_sock, f"STATS {stats2['wins']} {stats2['losses']} {stats2['draws']}")

    # Init empty board
    board = ["-"] * 9
    current_mark = "X"  # X moves first

    # Broadcast initial board state
    send_board(p1_sock, p2_sock, board, current_mark)
    send_info_to_both(p1_sock, p2_sock, "Game started! X goes first.")

    # Flag helps to only print "your turn" when turn actually changes
    turn_just_changed = True

    while True:
        # Send turn info if needed
        if turn_just_changed:
            if current_mark == "X":
                send_line(p1_sock, "INFO Your turn. Use: MOVE row col (0-2) or CHAT message")
                send_line(p2_sock, "INFO Waiting for opponent...")
            else:
                send_line(p2_sock, "INFO Your turn. Use: MOVE row col (0-2) or CHAT message")
                send_line(p1_sock, "INFO Waiting for opponent...")
            turn_just_changed = False

        # Wait for input from either player (move / chat / quit)
        try:
            readable, _, _ = select.select([p1_sock, p2_sock], [], [])
        except Exception as e:
            logging.error("select error: %s", e)
            p1_sock.close()
            p2_sock.close()
            return

        for s in readable:
            # Map socket to player info
            if s is p1_sock:
                name, opp_name = p1_name, p2_name
                mark = "X"
                opp_sock = p2_sock
            else:
                name, opp_name = p2_name, p1_name
                mark = "O"
                opp_sock = p1_sock

            line = recv_line(s)
            if line is None:
                # If one player disconnects, the opponent wins by default
                logging.info("Player %s disconnected, %s wins by default", name, opp_name)
                send_line(opp_sock, "INFO Opponent disconnected. You win by default.")
                send_line(opp_sock, "RESULT WIN")
                update_stats(opp_name, name, draw=False)
                p1_sock.close()
                p2_sock.close()
                return

            line = line.strip()
            if not line:
                continue

            parts = line.split(" ", 1)
            cmd = parts[0].upper()

            # CHAT: any time, any player
            if cmd == "CHAT":
                if len(parts) < 2 or not parts[1].strip():
                    send_line(s, "INFO Usage: CHAT your message")
                    continue
                text = parts[1]
                broadcast_chat(p1_sock, p2_sock, name, text)
                continue

            # QUIT: current player gives up, opponent wins
            if cmd == "QUIT":
                logging.info("Player %s quit, %s wins by default", name, opp_name)
                send_line(opp_sock, "INFO Opponent quit. You win by default.")
                send_line(opp_sock, "RESULT WIN")
                update_stats(opp_name, name, draw=False)
                p1_sock.close()
                p2_sock.close()
                return

            # MOVE: only for current player
            if cmd == "MOVE":
                # Wrong player tries to move
                if mark != current_mark:
                    send_line(s, "INFO It's not your turn.")
                    continue

                if len(parts) < 2:
                    send_line(s, "INFO Usage: MOVE row col")
                    continue
                args = parts[1].split()
                if len(args) != 2:
                    send_line(s, "INFO Usage: MOVE row col")
                    continue

                # Parse row/col
                try:
                    r = int(args[0])
                    c = int(args[1])
                except ValueError:
                    send_line(s, "INFO Row and col must be integers 0-2")
                    continue
                if not (0 <= r <= 2 and 0 <= c <= 2):
                    send_line(s, "INFO Row and col must be between 0 and 2")
                    continue

                idx = r * 3 + c
                if board[idx] != "-":
                    send_line(s, "INFO That cell is already taken.")
                    continue

                board[idx] = mark

                # Check result
                winner = check_winner(board)
                next_mark = "O" if current_mark == "X" else "X"

                # Broadcast new board and whose turn is next
                send_board(p1_sock, p2_sock, board, next_mark)

                # Handle win/draw
                if winner == "DRAW":
                    send_info_to_both(p1_sock, p2_sock, "Game is a draw.")
                    send_line(p1_sock, "RESULT DRAW")
                    send_line(p2_sock, "RESULT DRAW")
                    update_stats(p1_name, p2_name, draw=True)
                    p1_sock.close()
                    p2_sock.close()
                    return
                elif winner == "X":
                    msg = f"Player {p1_name} (X) wins!"
                    send_info_to_both(p1_sock, p2_sock, msg)
                    send_line(p1_sock, "RESULT WIN")
                    send_line(p2_sock, "RESULT LOSE")
                    update_stats(p1_name, p2_name, draw=False)
                    p1_sock.close()
                    p2_sock.close()
                    return
                elif winner == "O":
                    msg = f"Player {p2_name} (O) wins!"
                    send_info_to_both(p1_sock, p2_sock, msg)
                    send_line(p2_sock, "RESULT WIN")
                    send_line(p1_sock, "RESULT LOSE")
                    update_stats(p2_name, p1_name, draw=False)
                    p1_sock.close()
                    p2_sock.close()
                    return

                # If no winner yet, switch turns and continue
                current_mark = next_mark
                turn_just_changed = True

                break

            # Unknown commands
            send_line(s, "INFO Unknown command. Use MOVE or CHAT or QUIT.")


def main():
    load_stats()
    print(f"Server listening on {HOST}:{PORT}")
    logging.info("Server starting on %s:%d", HOST, PORT)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind((HOST, PORT))
        server_sock.listen(2)  # only one game at a time

        # Accept player 1
        p1_sock, p1_addr = server_sock.accept()
        print("Player 1 connected from", p1_addr)
        logging.info("Player 1 connected from %s", p1_addr)
        send_line(p1_sock, "INFO Welcome to Network Tic-Tac-Toe!")
        send_line(p1_sock, "INFO Please enter your username using: USER your_name")

        # Read username
        while True:
            line = recv_line(p1_sock)
            if line is None:
                print("Player 1 disconnected before providing username.")
                p1_sock.close()
                return
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            if parts[0].upper() == "USER" and len(parts) == 2:
                p1_name = parts[1].strip()
                if not p1_name:
                    send_line(p1_sock, "INFO Username cannot be empty.")
                    continue
                break
            else:
                send_line(p1_sock, "INFO Please use: USER your_name")

        send_line(p1_sock, f"INFO Hi {p1_name}, waiting for an opponent to join...")

        # Accept player 2
        p2_sock, p2_addr = server_sock.accept()
        print("Player 2 connected from", p2_addr)
        logging.info("Player 2 connected from %s", p2_addr)
        send_line(p2_sock, "INFO Welcome to Network Tic-Tac-Toe!")
        send_line(p2_sock, "INFO Please enter your username using: USER your_name")

        # read username
        while True:
            line = recv_line(p2_sock)
            if line is None:
                print("Player 2 disconnected before providing username.")
                p2_sock.close()
                send_line(p1_sock, "INFO Opponent disconnected before game start.")
                p1_sock.close()
                return
            line = line.strip()
            if not line:
                continue
            parts = line.split(" ", 1)
            if parts[0].upper() == "USER" and len(parts) == 2:
                p2_name = parts[1].strip()
                if not p2_name:
                    send_line(p2_sock, "INFO Username cannot be empty.")
                    continue
                break
            else:
                send_line(p2_sock, "INFO Please use: USER your_name")

        # Notify both players that the game is starting
        send_line(p1_sock, f"INFO Opponent {p2_name} joined. Starting game...")
        send_line(p2_sock, f"INFO You are matched with {p1_name}. Starting game...")

        # Run the actual game loop
        handle_game(p1_sock, p1_name, p2_sock, p2_name)


if __name__ == "__main__":
    main()
