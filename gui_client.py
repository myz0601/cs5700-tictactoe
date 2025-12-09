import socket
import threading
import queue
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext

# ---------- Network Utility Functions ----------

def send_line(sock, text):
    """Send a UTF-8 encoded line (ending with newline) to the server."""
    try:
        print(f"[DEBUG] send_line -> {text}")
        sock.sendall((text + "\n").encode("utf-8"))
    except OSError as e:
        print(f"[ERROR] send_line failed: {e}")

def recv_line(sock):
    """Receive a newline-terminated UTF-8 string from the server, one byte at a time."""
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

# ---------- GUI Client ----------

class TicTacToeGUI:
    def __init__(self, root, sock, username):
        self.root = root
        self.sock = sock
        self.username = username

        self.root.title(f"Tic-Tac-Toe - {username}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Queue used to pass messages from the network thread to the GUI thread
        self.msg_queue = queue.Queue()

        # Game state
        self.board_state = ["-"] * 9
        self.my_mark = "?"
        self.opponent = "?"
        self.current_turn = "?"

        # ---------- UI Layout ----------
        top_frame = tk.Frame(root)
        top_frame.pack(pady=5, fill="x")

        self.info_label = tk.Label(top_frame, text="Connecting...", anchor="w")
        self.info_label.pack(fill="x")

        # 3x3 board
        board_frame = tk.Frame(root)
        board_frame.pack(pady=5)

        self.buttons = []
        for r in range(3):
            for c in range(3):
                idx = r * 3 + c
                btn = tk.Button(
                    board_frame,
                    text=" ",
                    width=5,
                    height=2,
                    command=lambda r=r, c=c: self.on_cell_click(r, c),
                )
                btn.grid(row=r, column=c, padx=2, pady=2)
                self.buttons.append(btn)

        # Chat window
        chat_frame = tk.Frame(root)
        chat_frame.pack(pady=5, fill="both", expand=True)

        self.chat_box = scrolledtext.ScrolledText(
            chat_frame, width=40, height=10, state="disabled"
        )
        self.chat_box.pack(fill="both", expand=True)

        # Input box + send button
        input_frame = tk.Frame(root)
        input_frame.pack(pady=5, fill="x")

        self.chat_entry = tk.Entry(input_frame)
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.chat_entry.bind("<Return>", self.on_send_chat)

        send_btn = tk.Button(input_frame, text="Send", command=self.on_send_chat)
        send_btn.pack(side="right")

        # Status bar
        self.status_label = tk.Label(root, text="Waiting...", anchor="w")
        self.status_label.pack(fill="x")

        # Periodically poll the message queue
        self.root.after(100, self.process_queue)

    # ---------- UI Event Handlers ----------

    def on_cell_click(self, r, c):
        """Handle clicks on board cells."""
        idx = r * 3 + c
        print(f"[DEBUG] cell clicked r={r}, c={c}, idx={idx}, val={self.board_state[idx]}")

        # Ignore if the cell is not empty
        if self.board_state[idx] != "-":
            return

        # Send MOVE request; server will validate turn ownership
        send_line(self.sock, f"MOVE {r} {c}")

    def on_send_chat(self, event=None):
        """Send chat text to the server."""
        text = self.chat_entry.get().strip()
        if not text:
            return
        send_line(self.sock, f"CHAT {text}")
        self.chat_entry.delete(0, tk.END)

    def on_close(self):
        """Gracefully close the connection and exit."""
        try:
            send_line(self.sock, "QUIT")
            self.sock.close()
        except OSError:
            pass
        self.root.destroy()

    # ---------- UI Update Utilities ----------

    def append_chat(self, line):
        """Append a line to the chat box."""
        self.chat_box.config(state="normal")
        self.chat_box.insert(tk.END, line + "\n")
        self.chat_box.see(tk.END)
        self.chat_box.config(state="disabled")

    def update_board(self, board_string):
        """Update board buttons based on a 9-character board string."""
        print(f"[DEBUG] update_board -> {board_string}")
        if len(board_string) != 9:
            return
        self.board_state = list(board_string)
        for i, ch in enumerate(self.board_state):
            text = ch if ch != "-" else " "
            self.buttons[i].config(text=text)

    # ---------- Incoming Message Processing (from network thread) ----------

    def process_queue(self):
        """Process queued server messages in the GUI thread."""
        try:
            while not self.msg_queue.empty():
                cmd, rest = self.msg_queue.get()
                print(f"[DEBUG] process_queue cmd={cmd}, rest={rest}")

                if cmd == "BOARD":
                    self.update_board(rest)

                elif cmd == "TURN":
                    self.current_turn = rest
                    self.status_label.config(text=f"Current turn: {self.current_turn}")

                elif cmd == "INFO":
                    self.append_chat(f"[Info] {rest}")
                    self.info_label.config(text=rest)

                elif cmd == "MSG":
                    self.append_chat(f"[Chat] {rest}")

                elif cmd == "START":
                    tokens = rest.split()
                    if len(tokens) >= 2:
                        self.my_mark = tokens[0]
                        self.opponent = " ".join(tokens[1:])
                        self.append_chat(
                            f"[Game] You are {self.my_mark}. Opponent: {self.opponent}"
                        )
                    else:
                        self.append_chat(f"[Game] {rest}")

                elif cmd == "STATS":
                    tokens = rest.split()
                    if len(tokens) == 3:
                        wins, losses, draws = tokens
                        self.append_chat(
                            f"[Stats] Wins: {wins}, Losses: {losses}, Draws: {draws}"
                        )

                elif cmd == "RESULT":
                    self.append_chat(f"[Result] {rest}")
                    self.status_label.config(text=f"Game result: {rest}")

                elif cmd == "DISCONNECT":
                    messagebox.showinfo("Disconnected", "Disconnected from server.")
                    try:
                        self.sock.close()
                    except OSError:
                        pass
                    self.root.destroy()
                    return

        except Exception as e:
            print(f"[ERROR] process_queue exception: {e}")

        # Schedule next queue check after 100 ms
        self.root.after(100, self.process_queue)

    # ---------- Message Handler Called by Network Thread ----------

    def handle_server_line(self, line):
        """Parse a raw server line and push it into the GUI queue."""
        print(f"[DEBUG] handle_server_line raw={line!r}")
        line = line.strip()
        if not line:
            return
        parts = line.split(" ", 1)
        cmd = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        # Put into queue for GUI thread to handle
        self.msg_queue.put((cmd, rest))

# ---------- Network Reader Thread ----------

def reader_thread(sock, gui: TicTacToeGUI):
    """Continuously read lines from server and deliver them to the GUI."""
    while True:
        line = recv_line(sock)
        if line is None:
            gui.msg_queue.put(("DISCONNECT", ""))
            break
        gui.handle_server_line(line)

# ---------- main ----------

def main():
    import sys

    if len(sys.argv) != 4:
        print("Usage: python gui_client.py <server_host> <server_port> <username>")
        return

    host = sys.argv[1]
    try:
        port = int(sys.argv[2])
    except ValueError:
        print("Port must be an integer.")
        return
    username = sys.argv[3]

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
    except OSError as e:
        print(f"Could not connect to server: {e}")
        return

    root = tk.Tk()
    gui = TicTacToeGUI(root, sock, username)

    send_line(sock, f"USER {username}")

    t = threading.Thread(target=reader_thread, args=(sock, gui), daemon=True)
    t.start()

    root.mainloop()


if __name__ == "__main__":
    main()
