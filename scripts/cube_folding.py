"""Independent exact quarter-turn folding of six unit-square cells.

Each face frame has two tangent unit vectors (u,v), an outward normal n,
and a centre in doubled half-edge units. A neighbour is rotated 90 degrees
about the shared edge; no floating-point angles or answer-key lookup is used.
Coincident centres/normals mean two squares occupy the same cube face.
"""
from collections import deque


def neg(a):
    return tuple(-x for x in a)


def add(*vectors):
    return tuple(sum(parts) for parts in zip(*vectors))


def fold_cube_net(cells):
    cells = frozenset(tuple(p) for p in cells)
    if len(cells) != 6:
        return {'folds': False, 'reason': 'a cube requires exactly six square faces', 'faces': []}
    start = min(cells)
    # Frame = (right tangent, down tangent, normal, doubled centre).
    frames = {start: ((1, 0, 0), (0, 1, 0), (0, 0, 1), (0, 0, 1))}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        u, v, n, centre = frames[(x, y)]
        # Move to an adjacent cell by rotating its frame around the common edge.
        neighbours = (
            ((x+1, y), (neg(n), v, u, add(centre, u, neg(n)))),
            ((x-1, y), (n, v, neg(u), add(centre, neg(u), neg(n)))),
            ((x, y+1), (u, neg(n), v, add(centre, v, neg(n)))),
            ((x, y-1), (u, n, neg(v), add(centre, neg(v), neg(n)))),
        )
        for position, frame in neighbours:
            if position not in cells:
                continue
            if position in frames:
                if frames[position] != frame:
                    return {'folds': False, 'reason': 'inconsistent rotations around an adjacency cycle', 'faces': []}
            else:
                frames[position] = frame
                queue.append(position)
    if len(frames) != 6:
        return {'folds': False, 'reason': 'disconnected square cells', 'faces': []}
    faces = [{'cell': p, 'normal': frame[2], 'centre': frame[3]} for p, frame in sorted(frames.items())]
    seen = {}
    for face in faces:
        key = (face['normal'], face['centre'])
        if key in seen:
            return {'folds': False, 'reason': f'faces {seen[key]} and {face["cell"]} overlap after folding', 'faces': faces}
        seen[key] = face['cell']
    # There must be all six distinct outward normals, not repeated face planes.
    if len({face['normal'] for face in faces}) != 6:
        return {'folds': False, 'reason': 'repeated face normal', 'faces': faces}
    return {'folds': True, 'reason': 'six distinct non-overlapping cube faces', 'faces': faces}


def canonical(cells):
    """Identify translations, quarter turns and mirror images of a planar net."""
    images = []
    for swap in (False, True):
        for sx in (-1, 1):
            for sy in (-1, 1):
                transformed = [(sx*(y if swap else x), sy*(x if swap else y)) for x, y in cells]
                low_x = min(x for x, _ in transformed)
                low_y = min(y for _, y in transformed)
                images.append(tuple(sorted((x-low_x, y-low_y) for x, y in transformed)))
    return min(images)


def free_polyominoes(size):
    shapes = {((0, 0),)}
    for _ in range(1, size):
        grown = set()
        for shape in shapes:
            cells = set(shape)
            for x, y in shape:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    neighbour = (x+dx, y+dy)
                    if neighbour not in cells:
                        grown.add(canonical(cells | {neighbour}))
        shapes = grown
    return shapes
