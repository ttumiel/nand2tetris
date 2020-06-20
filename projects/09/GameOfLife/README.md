# Conway's Game Of Life

Implemented in Jack.

## Rules

1. Any live cell with two or three live neighbours survives.
2. Any dead cell with three live neighbours becomes a live cell.
3. All other live cells die in the next generation. Similarly, all other dead cells stay dead.

## Implementation

A `Grid` of squares. Each square checks if it lives or dies in the next timestep. Outer loop `GameRunner` controls timesteps.
