# gui_client.py
import socket
import threading
import queue
import tkinter as tk
from tkinter import simpledialog, messagebox, scrolledtext

# ---------- 网络工具函数 ----------

def send_line(sock, text):
    try:
        print(f"[DEBUG] send_line -> {text}")
        sock.sendall((text + "\n").encode("utf-8"))
    except OSError as e:
        print(f"[ERROR] send_line failed: {e}")

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

# ---------- GUI 客户端 ----------

class TicTacToeGUI:
    def __init__(self, root, sock, username):
        self.root = root
        self.sock = sock
        self.username = username

        self.root.title(f"Tic-Tac-Toe - {username}")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # 用来从网络线程传消息到主线程
        self.msg_queue = queue.Queue()

        # 当前棋盘状态
        self.board_state = ["-"] * 9
        self.my_mark = "?"
        self.opponent = "?"
        self.current_turn = "?"

        # ---------- UI 布局 ----------
        top_frame = tk.Frame(root)
        top_frame.pack(pady=5, fill="x")

        self.info_label = tk.Label(top_frame, text="Connecting...", anchor="w")
        self.info_label.pack(fill="x")

        # 棋盘 3x3
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

        # 聊天窗口
        chat_frame = tk.Frame(root)
        chat_frame.pack(pady=5, fill="both", expand=True)

        self.chat_box = scrolledtext.ScrolledText(
            chat_frame, width=40, height=10, state="disabled"
        )
        self.chat_box.pack(fill="both", expand=True)

        # 输入框 + 按钮
        input_frame = tk.Frame(root)
        input_frame.pack(pady=5, fill="x")

        self.chat_entry = tk.Entry(input_frame)
        self.chat_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.chat_entry.bind("<Return>", self.on_send_chat)

        send_btn = tk.Button(input_frame, text="Send", command=self.on_send_chat)
        send_btn.pack(side="right")

        # 状态栏
        self.status_label = tk.Label(root, text="Waiting...", anchor="w")
        self.status_label.pack(fill="x")

        # 启动一个定时器轮询消息队列
        self.root.after(100, self.process_queue)

    # ---------- UI 事件 ----------

    def on_cell_click(self, r, c):
        idx = r * 3 + c
        print(f"[DEBUG] cell clicked r={r}, c={c}, idx={idx}, val={self.board_state[idx]}")
        # 如果格子不是空的，就不要再点
        if self.board_state[idx] != "-":
            return
        # 直接发 MOVE 交给服务器检查是否轮到我
        send_line(self.sock, f"MOVE {r} {c}")

    def on_send_chat(self, event=None):
        text = self.chat_entry.get().strip()
        if not text:
            return
        send_line(self.sock, f"CHAT {text}")
        self.chat_entry.delete(0, tk.END)

    def on_close(self):
        try:
            send_line(self.sock, "QUIT")
            self.sock.close()
        except OSError:
            pass
        self.root.destroy()

    # ---------- UI 更新工具 ----------

    def append_chat(self, line):
        self.chat_box.config(state="normal")
        self.chat_box.insert(tk.END, line + "\n")
        self.chat_box.see(tk.END)
        self.chat_box.config(state="disabled")

    def update_board(self, board_string):
        print(f"[DEBUG] update_board -> {board_string}")
        if len(board_string) != 9:
            return
        self.board_state = list(board_string)
        for i, ch in enumerate(self.board_state):
            text = ch if ch != "-" else " "
            self.buttons[i].config(text=text)

    # ---------- 从网络线程来的消息处理 ----------

    def process_queue(self):
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

        # 再次安排自己 100 ms 后检查队列
        self.root.after(100, self.process_queue)

    # ---------- 从网络读消息的入口（由线程调用） ----------

    def handle_server_line(self, line):
        print(f"[DEBUG] handle_server_line raw={line!r}")
        line = line.strip()
        if not line:
            return
        parts = line.split(" ", 1)
        cmd = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        # 把消息丢到队列，主线程再处理
        self.msg_queue.put((cmd, rest))

# ---------- 网络读线程 ----------

def reader_thread(sock, gui: TicTacToeGUI):
    while True:
        line = recv_line(sock)
        if line is None:
            gui.msg_queue.put(("DISCONNECT", ""))
            break
        gui.handle_server_line(line)

# ---------- main ----------

def main():
    root = tk.Tk()
    root.withdraw()  # 先隐藏主窗口

    host = simpledialog.askstring("Server Host", "Enter server host:", initialvalue="127.0.0.1")
    if host is None:
        return
    port_str = simpledialog.askstring("Server Port", "Enter server port:", initialvalue="5500")
    if port_str is None:
        return
    try:
        port = int(port_str)
    except ValueError:
        messagebox.showerror("Error", "Port must be an integer.")
        return

    username = simpledialog.askstring("Username", "Enter your username:")
    if not username:
        messagebox.showerror("Error", "Username cannot be empty.")
        return

    # 创建 socket 并连接
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
    except OSError as e:
        messagebox.showerror("Error", f"Could not connect to server:\n{e}")
        return

    # 连接 OK，创建 GUI
    root.deiconify()
    gui = TicTacToeGUI(root, sock, username)

    # 发送用户名
    send_line(sock, f"USER {username}")

    # 启动读线程
    t = threading.Thread(target=reader_thread, args=(sock, gui), daemon=True)
    t.start()

    root.mainloop()

if __name__ == "__main__":
    main()
