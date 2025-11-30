import socket
import threading
import sys

# Send one line to server
def send_line(sock, text):
    try:
        sock.sendall((text + "\n").encode("utf-8"))
    except OSError:
        pass


# Receive one line from socket, return None if disconnected
def recv_line(sock):
    data = []
    try:
        while True:
            ch = sock.recv(1)
            if not ch:
                return None
            ch = ch.decode("utf-8")
            if ch == "\n":
                break
            data.append(ch)
    except OSError:
        return None
    return "".join(data)


# Print the 3x3 tic-tac-toe board
def print_board(board_state):
    # board_state: 'XOX---O--'
    if len(board_state) != 9:
        print("BOARD:", board_state)
        return
    print("\nCurrent board:")
    for r in range(3):
        row = board_state[r*3:(r+1)*3]
        # replace '-' with blank so it looks nicer
        display = " | ".join(ch if ch != "-" else " " for ch in row)
        print(" " + display)
        if r < 2:
            print("---+---+---")
    print()


# Thread keeps reading messages from server
def reader_thread(sock):
    while True:
        line = recv_line(sock)
        if line is None:
            print("\n[Disconnected from server]")
            try:
                sock.close()
            except OSError:
                pass
            # Exit entire program
            sys.exit(0)
        
        line = line.strip()
        if not line:
            continue

        parts = line.split(" ", 1)
        cmd = parts[0]
        rest = parts[1] if len(parts) > 1 else ""

        if cmd == "BOARD":
            print_board(rest)
        elif cmd == "TURN":
            print(f"[Turn] Current player: {rest}")
        elif cmd == "INFO":
            print(f"[Info] {rest}")
        elif cmd == "MSG":
            print(f"[Chat] {rest}")
        elif cmd == "START":
            # e.g. START X opponentName
            tokens = rest.split()
            if len(tokens) >= 2:
                my_mark = tokens[0]
                opp = " ".join(tokens[1:])
                print(f"[Game] You are {my_mark}. Opponent: {opp}")
            else:
                print(f"[Game] {rest}")
        elif cmd == "STATS":
            tokens = rest.split()
            if len(tokens) == 3:
                wins, losses, draws = tokens
                print(f"[Stats] Wins: {wins}, Losses: {losses}, Draws: {draws}")
            else:
                print(f"[Stats] {rest}")
        elif cmd == "RESULT":
            print(f"[Result] {rest}")
        else:
            # Unknown or raw
            print(line)


# Connect, start reader thread, handle user input
def main():
    if len(sys.argv) != 4:
        print("Usage: python client.py <server_host> <server_port> <username>")
        return

    host = sys.argv[1]
    port = int(sys.argv[2])
    username = sys.argv[3]

    # Create TCP socket and connect to server
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))

    # Start reader thread
    t = threading.Thread(target=reader_thread, args=(sock,), daemon=True)
    t.start()

    # Send username
    send_line(sock, f"USER {username}")

    print("Type commands:")
    print("  move r c     -> make a move at row r, col c (0-2)")
    print("  chat message -> send chat message to opponent")
    print("  quit         -> quit game\n")

    # Read commands from keyboard and send to server
    while True:
        try:
            user_input = input("> ")
        except EOFError:
            break
        user_input = user_input.strip()
        if not user_input:
            continue
        
        tokens = user_input.split(" ", 1)
        cmd = tokens[0].lower()

        # MOVE command: need row and col
        if cmd == "move":
            if len(tokens) < 2:
                print("Usage: move row col")
                continue
            args = tokens[1].split()
            if len(args) != 2:
                print("Usage: move row col")
                continue
            send_line(sock, f"MOVE {args[0]} {args[1]}")
        
        # CHAT command: send the rest of the line as message
        elif cmd == "chat":
            if len(tokens) < 2:
                print("Usage: chat your message")
                continue
            send_line(sock, f"CHAT {tokens[1]}")
        
        # Tell server to quit, then close socket and exit
        elif cmd == "quit":
            send_line(sock, "QUIT")
            print("Quitting...")
            try:
                sock.close()
            except OSError:
                pass
            break
        else:
            print("Unknown command. Use move/chat/quit.")

    print("Client exited.")


if __name__ == "__main__":
    main()
