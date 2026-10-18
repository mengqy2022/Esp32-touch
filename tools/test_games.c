#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "arcade.h"
#include "game2048.h"
#include "flappy.h"
#include "sudoku.h"

int main(void)
{
    snake_t snake;
    snake_init(&snake);
    int head = snake.body[0];
    snake_turn(&snake, 2); snake_step(&snake);
    assert(snake.body[0] == head + 1);
    snake.food = snake.body[0] + 1; snake_step(&snake);
    assert(snake.length == 4 && snake.score == 10);
    for (int i = 0; i < 30; ++i) snake_step(&snake);
    assert(snake.over);
    snake_init(&snake);
    snake.body[0] = 25; snake.body[1] = 26; snake.body[2] = 50; snake.body[3] = 49;
    snake.length = 4; snake.direction = snake.pending = 3; snake_step(&snake);
    assert(snake.over);
    breakout_t breakout;
    breakout_init(&breakout);
    breakout_paddle(&breakout, -100); assert(breakout.paddle == 24);
    breakout_paddle(&breakout, 900); assert(breakout.paddle == 276);
    breakout.started = true; breakout.x = 20; breakout.y = 10; breakout.vx = 0; breakout.vy = 3;
    breakout_step(&breakout); assert(!breakout.bricks[0][0] && breakout.score == 10);
    breakout.paddle = 150; breakout.x = 150; breakout.y = 129; breakout.vy = 3;
    breakout_step(&breakout); assert(breakout.vy < 0);
    for (int i = 0; i < 3; ++i) {
        breakout.started = true; breakout.y = 159; breakout.vy = 3;
        breakout_step(&breakout);
    }
    assert(breakout.over && breakout.lives == 0);
    breakout_init(&breakout);
    memset(breakout.bricks, 0, sizeof(breakout.bricks));
    breakout.bricks[0][0] = true; breakout.score = 310; breakout.started = true;
    breakout.x = 20; breakout.y = 10; breakout.vx = 0; breakout.vy = 3;
    breakout_step(&breakout); assert(breakout.won && breakout.over);
    game2048_t tiles = {0};
    tiles.tile[0][0] = tiles.tile[0][1] = tiles.tile[0][2] = tiles.tile[0][3] = 2;
    assert(game2048_move(&tiles, 2));
    assert(tiles.tile[0][0] == 4 && tiles.tile[0][1] == 4 && tiles.score == 8);
    for (int y = 0; y < 4; ++y) for (int x = 0; x < 4; ++x) tiles.tile[y][x] = (x + y) % 2 ? 2 : 4;
    assert(game2048_over(&tiles));
    tiles.tile[0][0] = 2; assert(!game2048_over(&tiles));
    flappy_game_t bird; flappy_init(&bird);
    int initial_y = bird.bird_y; flappy_step(&bird); assert(bird.bird_y == initial_y);
    flappy_flap(&bird); flappy_step(&bird); assert(bird.bird_y < initial_y);
    for (int i = 0; i < 100; ++i) flappy_step(&bird);
    assert(bird.game_over);
    sudoku_t sudoku; sudoku_new(&sudoku, 0);
    for (int y = 0; y < 9; ++y) for (int x = 0; x < 9; ++x) if (sudoku.given[y][x]) {
        int value = sudoku.grid[y][x]; sudoku_set(&sudoku, x, y, 9); sudoku_clear(&sudoku, x, y);
        assert(sudoku.grid[y][x] == value);
    }
    puts("Snake, Breakout, 2048, Flappy and Sudoku checks: PASS");
    return 0;
}
