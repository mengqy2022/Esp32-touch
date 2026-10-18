#pragma once
#include <stdbool.h>
#include <stdint.h>

#define SNAKE_COLS 24
#define SNAKE_ROWS 12
#define SNAKE_MAX (SNAKE_COLS * SNAKE_ROWS)
typedef struct {
    uint16_t body[SNAKE_MAX];
    int length, direction, pending, food, score;
    bool over, won;
} snake_t;
void snake_init(snake_t *g);
void snake_turn(snake_t *g, int direction);
void snake_step(snake_t *g);

#define BRICK_COLS 8
#define BRICK_ROWS 4
typedef struct {
    float x, y, vx, vy;
    int paddle, lives, score;
    bool bricks[BRICK_ROWS][BRICK_COLS];
    bool started, over, won;
} breakout_t;
void breakout_init(breakout_t *g);
void breakout_step(breakout_t *g);
void breakout_paddle(breakout_t *g, int x);
