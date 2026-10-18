#include "arcade.h"
#include <stdlib.h>
#include <string.h>

static void snake_food(snake_t *g)
{
    int empty[SNAKE_MAX], count = 0;
    for (int p = 0; p < SNAKE_MAX; ++p) {
        bool occupied = false;
        for (int i = 0; i < g->length; ++i) if (g->body[i] == p) { occupied = true; break; }
        if (!occupied) empty[count++] = p;
    }
    if (count) g->food = empty[rand() % count];
    else { g->over = true; g->won = true; }
}

void snake_init(snake_t *g)
{
    memset(g, 0, sizeof(*g));
    g->length = 3;
    g->direction = g->pending = 3;
    for (int i = 0; i < 3; ++i) g->body[i] = 6 * SNAKE_COLS + 10 - i;
    snake_food(g);
}

void snake_turn(snake_t *g, int direction)
{
    if (direction >= 0 && direction < 4 && direction != (g->direction ^ 1)) g->pending = direction;
}

void snake_step(snake_t *g)
{
    if (g->over) return;
    g->direction = g->pending;
    int x = g->body[0] % SNAKE_COLS, y = g->body[0] / SNAKE_COLS;
    x += g->direction == 3 ? 1 : g->direction == 2 ? -1 : 0;
    y += g->direction == 1 ? 1 : g->direction == 0 ? -1 : 0;
    if (x < 0 || x >= SNAKE_COLS || y < 0 || y >= SNAKE_ROWS) { g->over = true; return; }
    int next = y * SNAKE_COLS + x;
    bool eat = next == g->food;
    for (int i = 0; i < g->length - (eat ? 0 : 1); ++i)
        if (g->body[i] == next) { g->over = true; return; }
    if (eat && g->length < SNAKE_MAX) { g->length++; g->score += 10; }
    memmove(g->body + 1, g->body, (g->length - 1) * sizeof(g->body[0]));
    g->body[0] = next;
    if (eat) snake_food(g);
}

static void serve(breakout_t *g)
{
    g->x = g->paddle; g->y = 126; g->vx = 2.2f; g->vy = -2.8f; g->started = false;
}

void breakout_init(breakout_t *g)
{
    memset(g, 0, sizeof(*g));
    for (int y = 0; y < BRICK_ROWS; ++y) for (int x = 0; x < BRICK_COLS; ++x) g->bricks[y][x] = true;
    g->paddle = 150; g->lives = 3;
    serve(g);
}

void breakout_paddle(breakout_t *g, int x)
{
    g->paddle = x < 24 ? 24 : x > 276 ? 276 : x;
    if (!g->started) g->x = g->paddle;
}

void breakout_step(breakout_t *g)
{
    if (!g->started || g->over) return;
    float old_y = g->y;
    g->x += g->vx; g->y += g->vy;
    if (g->x < 4) { g->x = 4; g->vx = -g->vx; }
    if (g->x > 296) { g->x = 296; g->vx = -g->vx; }
    if (g->y < 4) { g->y = 4; g->vy = -g->vy; }
    if (g->vy > 0 && old_y < 134 && g->y >= 130 && g->x >= g->paddle - 27 && g->x <= g->paddle + 27) {
        g->y = 130; g->vy = -2.8f; g->vx = (g->x - g->paddle) / 8.f;
    }
    if (g->y > 158) {
        if (--g->lives == 0) g->over = true;
        else serve(g);
        return;
    }
    for (int row = 0; row < BRICK_ROWS; ++row) for (int col = 0; col < BRICK_COLS; ++col) {
        int left = 6 + col * 36, top = 12 + row * 17;
        if (g->bricks[row][col] && g->x + 4 >= left && g->x - 4 <= left + 33 && g->y + 4 >= top && g->y - 4 <= top + 13) {
            g->bricks[row][col] = false; g->score += 10;
            if (old_y + 4 <= top || old_y - 4 >= top + 13) g->vy = -g->vy;
            else g->vx = -g->vx;
            if (g->score == BRICK_COLS * BRICK_ROWS * 10) { g->over = true; g->won = true; }
            return;
        }
    }
}
