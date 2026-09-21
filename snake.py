import random
import tkinter as tk
from collections import deque

CELL = 20
COLS = 30
ROWS = 20
DELAY = 110  # ms

DIRS = {
    "Up": (0, -1),
    "Down": (0, 1),
    "Left": (-1, 0),
    "Right": (1, 0),
}
OPPOSITE = {"Up": "Down", "Down": "Up", "Left": "Right", "Right": "Left"}


def in_bounds(p):
    return 0 <= p[0] < COLS and 0 <= p[1] < ROWS


def neighbors(p):
    for d, (dx, dy) in DIRS.items():
        n = (p[0] + dx, p[1] + dy)
        if in_bounds(n):
            yield d, n


def bfs_first_step(start, goal, blocked):
    """start에서 goal까지 최단 경로의 첫 방향을 반환. 경로가 없으면 None."""
    queue = deque([start])
    first = {start: None}
    while queue:
        cur = queue.popleft()
        if cur == goal:
            return first[cur]
        for d, n in neighbors(cur):
            if n in first or n in blocked:
                continue
            first[n] = first[cur] or d
            queue.append(n)
    return None


def reachable_area(start, blocked):
    seen = {start}
    queue = deque([start])
    while queue:
        cur = queue.popleft()
        for _, n in neighbors(cur):
            if n not in seen and n not in blocked:
                seen.add(n)
                queue.append(n)
    return len(seen)


class Snake:
    def __init__(self, body, direction):
        self.body = body
        self.direction = direction
        self.next_direction = direction
        self.score = 0
        self.alive = True

    @property
    def head(self):
        return self.body[0]


class SnakeGame:
    def __init__(self, root):
        self.root = root
        root.title("사람 vs AI 뱀 게임")
        root.resizable(False, False)
        self.score_var = tk.StringVar()
        tk.Label(root, textvariable=self.score_var, font=("Arial", 14)).pack()
        self.canvas = tk.Canvas(
            root, width=COLS * CELL, height=ROWS * CELL, bg="black", highlightthickness=0
        )
        self.canvas.pack()
        root.bind("<Key>", self.on_key)
        self.reset()

    def reset(self):
        mid = ROWS // 2
        self.player = Snake([(5, mid + 3), (4, mid + 3), (3, mid + 3)], "Right")
        self.ai = Snake([(COLS - 6, mid - 3), (COLS - 5, mid - 3), (COLS - 4, mid - 3)], "Left")
        self.game_over = False
        self.result = ""
        self.place_food()
        self.update_score()
        self.tick()

    def update_score(self):
        self.score_var.set(f"나(초록): {self.player.score}    AI(파랑): {self.ai.score}")

    def place_food(self):
        taken = set(self.player.body) | set(self.ai.body)
        free = [(x, y) for x in range(COLS) for y in range(ROWS) if (x, y) not in taken]
        self.food = random.choice(free)

    def on_key(self, event):
        key = event.keysym
        if key in DIRS and key != OPPOSITE[self.player.direction]:
            self.player.next_direction = key
        elif key in ("r", "R", "space") and self.game_over:
            self.reset()

    # ---------- AI ----------
    def choose_ai_direction(self):
        ai, player = self.ai, self.player
        # 꼬리는 다음 턴에 빠지므로 통과 가능하다고 본다.
        blocked = set(ai.body[:-1]) | set(player.body[:-1])
        # 사람이 다음에 이동할 수 있는 칸은 충돌 위험이 있으므로 피한다.
        danger = {n for _, n in neighbors(player.head)}
        safe_blocked = blocked | danger

        for block in (safe_blocked, blocked):
            d = bfs_first_step(ai.head, self.food, block - {ai.head})
            if d and d != OPPOSITE[ai.direction]:
                dx, dy = DIRS[d]
                nxt = (ai.head[0] + dx, ai.head[1] + dy)
                # 먹이를 먹고도 갇히지 않는지 확인
                if reachable_area(nxt, block | {ai.head}) >= len(ai.body):
                    return d

        # 경로가 없거나 위험하면 가장 넓은 공간이 남는 방향을 선택
        best, best_area = ai.direction, -1
        for d, n in neighbors(ai.head):
            if d == OPPOSITE[ai.direction] or n in blocked:
                continue
            area = reachable_area(n, blocked | {ai.head})
            if n in danger:
                area -= 1000
            if area > best_area:
                best, best_area = d, area
        return best

    # ---------- 게임 진행 ----------
    def tick(self):
        if self.game_over:
            return
        p, a = self.player, self.ai
        a.next_direction = self.choose_ai_direction()

        new_heads = {}
        for s in (p, a):
            s.direction = s.next_direction
            dx, dy = DIRS[s.direction]
            new_heads[s] = (s.head[0] + dx, s.head[1] + dy)

        new_bodies = {}
        ate = {}
        for s in (p, a):
            ate[s] = new_heads[s] == self.food
            body = [new_heads[s]] + s.body
            if not ate[s]:
                body.pop()
            new_bodies[s] = body

        dead = {}
        for s, other in ((p, a), (a, p)):
            h = new_heads[s]
            dead[s] = (
                not in_bounds(h)
                or h in new_bodies[s][1:]
                or h in new_bodies[other]
            )

        for s in (p, a):
            s.body = new_bodies[s]
            if ate[s] and not dead[s]:
                s.score += 10
        self.update_score()

        if dead[p] or dead[a]:
            self.game_over = True
            p.alive, a.alive = not dead[p], not dead[a]
            if dead[p] and not dead[a]:
                self.result = "AI 승리!"
            elif dead[a] and not dead[p]:
                self.result = "당신의 승리!"
            elif p.score > a.score:
                self.result = "당신의 승리!"
            elif a.score > p.score:
                self.result = "AI 승리!"
            else:
                self.result = "무승부"
            self.draw()
            return

        if ate[p] or ate[a]:
            self.place_food()

        self.draw()
        self.root.after(DELAY, self.tick)

    def draw(self):
        c = self.canvas
        c.delete("all")
        fx, fy = self.food
        c.create_oval(fx * CELL + 2, fy * CELL + 2, (fx + 1) * CELL - 2, (fy + 1) * CELL - 2, fill="red")
        for snake, head_color, body_color in (
            (self.player, "lime", "green"),
            (self.ai, "deep sky blue", "royal blue"),
        ):
            for i, (x, y) in enumerate(snake.body):
                color = head_color if i == 0 else body_color
                if not snake.alive:
                    color = "gray"
                c.create_rectangle(x * CELL + 1, y * CELL + 1, (x + 1) * CELL - 1, (y + 1) * CELL - 1,
                                   fill=color, outline="")
        if self.game_over:
            c.create_text(COLS * CELL // 2, ROWS * CELL // 2 - 15, text=self.result,
                          fill="white", font=("Arial", 28, "bold"))
            c.create_text(COLS * CELL // 2, ROWS * CELL // 2 + 20, text="R 또는 스페이스: 다시 시작",
                          fill="white", font=("Arial", 14))


if __name__ == "__main__":
    root = tk.Tk()
    SnakeGame(root)
    root.mainloop()
