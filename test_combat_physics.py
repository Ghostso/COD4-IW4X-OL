import math

class PlayerState:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.slot = 0
        self.entity_id = 1
        self.connected = True
        self.x, self.y, self.z = x, y, z
        self.vx, self.vy, self.vz = 0.0, 0.0, 0.0
        self.yaw, self.pitch, self.roll = 0, 0, 0
        self.health = 100
        self.max_health = 100
        self.is_dead = False
        self.kills = 0
        self.deaths = 0
        self.respawn_timer = 0.0

    def take_damage(self, damage, attacker):
        if self.is_dead or not self.connected:
            return False
        self.health -= damage
        if self.health <= 0:
            self.health = 0
            self.is_dead = True
            self.deaths += 1
            self.respawn_timer = 3.0
            if attacker and attacker != self:
                attacker.kills += 1
            return True
        return False

    def respawn(self, spawn):
        self.health = self.max_health
        self.is_dead = False
        self.respawn_timer = 0.0
        self.x, self.y, self.z = spawn
        self.vx, self.vy, self.vz = 0.0, 0.0, 0.0

def ray_intersects_player(ox, oy, oz, dirX, dirY, dirZ, max_range, target):
    if not target.connected or target.is_dead:
        return None
    radius = 15.0
    height = 72.0
    dx = ox - target.x
    dy = oy - target.y
    a = dirX * dirX + dirY * dirY
    if a < 1e-6:
        return None
    b = 2.0 * (dx * dirX + dy * dirY)
    c = dx * dx + dy * dy - radius * radius
    disc = b * b - 4.0 * a * c
    if disc < 0:
        return None
    sqrt_disc = math.sqrt(disc)
    t = (-b - sqrt_disc) / (2.0 * a)
    if t < 0:
        t = (-b + sqrt_disc) / (2.0 * a)
    if t < 0 or t > max_range:
        return None
    hit_z = oz + dirZ * t
    if target.z <= hit_z <= target.z + height:
        return t
    return None

# Test 1: Damage & Kill
p1 = PlayerState(0, 0, 0)
p2 = PlayerState(100, 0, 0)

assert not p2.take_damage(40, p1)
assert p2.health == 60 and not p2.is_dead
print("[Test 1.1] Take 40 damage: health=60 is_dead=False -> PASS")

assert p2.take_damage(70, p1) # lethal
assert p2.health == 0 and p2.is_dead and p2.deaths == 1 and p1.kills == 1
print("[Test 1.2] Take 70 damage (lethal): health=0 is_dead=True kills=1 deaths=1 -> PASS")

# Test 2: Respawn
p2.respawn((48.0, -572.0, -116.0))
assert p2.health == 100 and not p2.is_dead and p2.x == 48.0
print("[Test 2] Respawn: health=100 is_dead=False coords reset -> PASS")

# Test 3: Raycast Hit Detection
p1.x, p1.y, p1.z = 0, 0, 0
p2.x, p2.y, p2.z = 100, 0, 0
# Eye position: (0, 0, 60), Facing +X: dir = (1, 0, 0)
dist = ray_intersects_player(0, 0, 60, 1.0, 0.0, 0.0, 8192.0, p2)
assert dist is not None and abs(dist - 85.0) < 1e-4
print(f"[Test 3.1] Forward ray hit target at dist={dist:.1f} -> PASS")

# Ray facing backward: dir = (-1, 0, 0)
dist_back = ray_intersects_player(0, 0, 60, -1.0, 0.0, 0.0, 8192.0, p2)
assert dist_back is None
print("[Test 3.2] Backward ray missed target -> PASS")

# Ray facing 90 degrees right: dir = (0, 1, 0)
dist_right = ray_intersects_player(0, 0, 60, 0.0, 1.0, 0.0, 8192.0, p2)
assert dist_right is None
print("[Test 3.3] Orthogonal ray missed target -> PASS")

print("\nALL COMBAT MECHANICS & RAYCAST TESTS PASSED 100%!")
