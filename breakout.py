import tkinter as tk
import random

WIDTH, HEIGHT = 600, 500
PADDLE_W, PADDLE_H = 90, 12
BALL_R = 8
ROWS, COLS = 6, 10
BRICK_W = WIDTH // COLS
BRICK_H = 22
TOP_OFFSET = 50
COLORS = ["#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#3498db", "#9b59b6"]


class Breakout:
    def __init__(self, root):
        self.root = root
        root.title("블럭깨기")
        root.resizable(False, False)
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="black",
                                highlightthickness=0)
        self.canvas.pack()
        self.left = self.right = False
        root.bind("<KeyPress-Left>", lambda e: setattr(self, "left", True))
        root.bind("<KeyRelease-Left>", lambda e: setattr(self, "left", False))
        root.bind("<KeyPress-Right>", lambda e: setattr(self, "right", True))
        root.bind("<KeyRelease-Right>", lambda e: setattr(self, "right", False))
        root.bind("<space>", self.on_space)
        root.bind("<Motion>", self.on_mouse)
        self.new_game()
        self.loop()

    def new_game(self):
        self.canvas.delete("all")
        self.score = 0
        self.lives = 3
        self.level = 1
        self.speed = 5
        self.running = False
        self.over = False
        self.build_level()

    def build_level(self):
        self.canvas.delete("brick")
        self.bricks = {}
        for r in range(ROWS):
            for c in range(COLS):
                x = c * BRICK_W
                y = TOP_OFFSET + r * BRICK_H
                item = self.canvas.create_rectangle(
                    x + 1, y + 1, x + BRICK_W - 1, y + BRICK_H - 1,
                    fill=COLORS[r % len(COLORS)], outline="", tags="brick")
                self.bricks[item] = True
        self.canvas.delete("paddle", "ball", "hud", "msg")
        px = (WIDTH - PADDLE_W) / 2
        self.paddle = self.canvas.create_rectangle(
            px, HEIGHT - 40, px + PADDLE_W, HEIGHT - 40 + PADDLE_H,
            fill="white", tags="paddle")
        self.ball = self.canvas.create_oval(0, 0, BALL_R * 2, BALL_R * 2,
                                            fill="white", tags="ball")
        self.hud = self.canvas.create_text(10, 20, anchor="w", fill="white",
                                           font=("Arial", 14), tags="hud")
        self.reset_ball()
        self.update_hud()
        self.message("스페이스바를 눌러 시작\n← → 키 또는 마우스로 패들 이동")

    def reset_ball(self):
        self.running = False
        px1, py1, px2, _ = self.canvas.coords(self.paddle)
        cx = (px1 + px2) / 2
        self.canvas.coords(self.ball, cx - BALL_R, py1 - BALL_R * 2,
                           cx + BALL_R, py1)
        self.dx = random.choice([-1, 1]) * self.speed * 0.7
        self.dy = -self.speed

    def update_hud(self):
        self.canvas.itemconfig(
            self.hud, text=f"점수: {self.score}   목숨: {self.lives}   레벨: {self.level}")

    def message(self, text):
        self.canvas.delete("msg")
        if text:
            self.canvas.create_text(WIDTH / 2, HEIGHT / 2, text=text, fill="white",
                                    font=("Arial", 18), justify="center", tags="msg")

    def on_space(self, _):
        if self.over:
            self.new_game()
        elif not self.running:
            self.running = True
            self.message("")

    def on_mouse(self, e):
        self.move_paddle_to(e.x)

    def move_paddle_to(self, cx):
        x1, y1, x2, y2 = self.canvas.coords(self.paddle)
        nx = max(0, min(WIDTH - PADDLE_W, cx - PADDLE_W / 2))
        self.canvas.move(self.paddle, nx - x1, 0)
        if not self.running and not self.over:
            self.canvas.move(self.ball, nx - x1, 0)

    def loop(self):
        if self.left:
            self.move_paddle_to(self.canvas.coords(self.paddle)[0] + PADDLE_W / 2 - 10)
        if self.right:
            self.move_paddle_to(self.canvas.coords(self.paddle)[0] + PADDLE_W / 2 + 10)
        if self.running:
            self.step()
        self.root.after(16, self.loop)

    def step(self):
        self.canvas.move(self.ball, self.dx, self.dy)
        x1, y1, x2, y2 = self.canvas.coords(self.ball)

        # 벽 충돌
        if x1 <= 0:
            self.canvas.move(self.ball, -x1, 0)
            self.dx = abs(self.dx)
        elif x2 >= WIDTH:
            self.canvas.move(self.ball, WIDTH - x2, 0)
            self.dx = -abs(self.dx)
        if y1 <= 0:
            self.canvas.move(self.ball, 0, -y1)
            self.dy = abs(self.dy)

        # 패들 충돌
        px1, py1, px2, py2 = self.canvas.coords(self.paddle)
        if self.dy > 0 and x2 >= px1 and x1 <= px2 and y2 >= py1 and y1 < py2:
            offset = ((x1 + x2) / 2 - (px1 + px2) / 2) / (PADDLE_W / 2)
            self.dx = offset * self.speed * 1.2
            self.dy = -abs(self.dy)
            self.canvas.move(self.ball, 0, py1 - y2)

        # 블럭 충돌
        overlap = self.canvas.find_overlapping(x1, y1, x2, y2)
        hit = [i for i in overlap if i in self.bricks]
        if hit:
            brick = hit[0]
            bx1, by1, bx2, by2 = self.canvas.coords(brick)
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            if bx1 <= cx <= bx2:
                self.dy = -self.dy
            else:
                self.dx = -self.dx
            for b in hit:
                self.canvas.delete(b)
                del self.bricks[b]
                self.score += 10
            self.update_hud()
            if not self.bricks:
                self.next_level()
                return

        # 바닥
        if y1 >= HEIGHT:
            self.lives -= 1
            self.update_hud()
            if self.lives <= 0:
                self.over = True
                self.running = False
                self.message(f"게임 오버!\n점수: {self.score}\n스페이스바로 다시 시작")
            else:
                self.reset_ball()
                self.message("스페이스바를 눌러 계속")

    def next_level(self):
        self.level += 1
        self.speed = min(self.speed + 1, 11)
        self.build_level()
        self.update_hud()


if __name__ == "__main__":
    root = tk.Tk()
    Breakout(root)
    root.mainloop()
