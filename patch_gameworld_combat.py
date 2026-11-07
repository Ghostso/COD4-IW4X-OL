with open("CODOL-Combat-Server-v0.1/src/Engine/GameWorld.cs", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update PlayerState
old_player_state = """        public uint LastCommandTime;
        public int InputsProcessed;
        public bool OnGround;

        public PlayerState(double[] spawn)
        {
            X = spawn[0]; Y = spawn[1]; Z = spawn[2];
            OnGround = true;
        }

        /// <summary>玩家状态快照用明文坐标（x=右, y=前, z=上，与参考实现的字段顺序一致）。</summary>
        public void CopyTo(out double x, out double y, out double z, out double vx, out double vy)
        {
            x = X; y = Y; z = Z; vx = VX; vy = VY;
        }
    }"""

new_player_state = """        public uint LastCommandTime;
        public int InputsProcessed;
        public bool OnGround;

        // --- 权威战斗与伤害属性 ---
        public const int DefaultMaxHealth = 100;
        public int Health = DefaultMaxHealth;
        public int MaxHealth = DefaultMaxHealth;
        public bool IsDead = false;
        public int Kills = 0;
        public int Deaths = 0;
        public double RespawnTimer = 0.0;
        public const double DefaultRespawnDelay = 3.0;

        public PlayerState(double[] spawn)
        {
            X = spawn[0]; Y = spawn[1]; Z = spawn[2];
            OnGround = true;
            Health = DefaultMaxHealth;
            MaxHealth = DefaultMaxHealth;
            IsDead = false;
        }

        /// <summary>结算伤害，生命值归零时置阵亡并安排重生。</summary>
        public bool TakeDamage(int damage, PlayerState attacker)
        {
            if (IsDead || !Connected) return false;
            Health -= damage;
            if (Health <= 0)
            {
                Health = 0;
                IsDead = true;
                Deaths++;
                RespawnTimer = DefaultRespawnDelay;
                if (attacker != null && !ReferenceEquals(attacker, this))
                {
                    attacker.Kills++;
                }
                return true;
            }
            return false;
        }

        /// <summary>在指定出生点复活玩家，重置生命值与速度。</summary>
        public void Respawn(double[] spawn)
        {
            Health = MaxHealth;
            IsDead = false;
            RespawnTimer = 0.0;
            X = spawn[0]; Y = spawn[1]; Z = spawn[2];
            VX = 0; VY = 0; VZ = 0;
            Move = 0; Buttons = 0;
            OnGround = true;
        }

        /// <summary>玩家状态快照用明文坐标（x=右, y=前, z=上，与参考实现的字段顺序一致）。</summary>
        public void CopyTo(out double x, out double y, out double z, out double vx, out double vy)
        {
            x = X; y = Y; z = Z; vx = VX; vy = VY;
        }
    }"""

assert old_player_state in content, "old_player_state not found"
content = content.replace(old_player_state, new_player_state, 1)

# 2. Update Frame and add RayIntersectsPlayer / ProcessWeaponFire
old_frame = """            for (int slot = 0; slot < n; slot++)
            {
                PlayerState p;
                if (!_entities.TryGetValue(slot, out p)) continue;
                if (p == null || !p.Connected) continue;
                IntegratePlayer(p, dt);
            }
        }"""

new_frame = """            for (int slot = 0; slot < n; slot++)
            {
                PlayerState p;
                if (!_entities.TryGetValue(slot, out p)) continue;
                if (p == null || !p.Connected) continue;

                if (p.IsDead)
                {
                    p.RespawnTimer -= dt;
                    if (p.RespawnTimer <= 0.0)
                    {
                        p.Respawn(_cfg.Spawn);
                        _log.Info("COMBAT", "玩家重生 slot=" + p.Slot + " entityId=" + p.EntityId);
                    }
                    continue;
                }

                IntegratePlayer(p, dt);
            }
        }

        /// <summary>
        /// 射线命中判定（CODOL 碰撞胶囊体相交）：
        /// 检查从视线起点 (ox, oy, oz) 沿方向 (dirX, dirY, dirZ) 是否命中 target 的碰撞体。
        /// </summary>
        public static bool RayIntersectsPlayer(
            double ox, double oy, double oz,
            double dirX, double dirY, double dirZ,
            double maxRange,
            PlayerState target,
            out double hitDist)
        {
            hitDist = -1.0;
            if (target == null || target.IsDead || !target.Connected) return false;

            const double radius = 15.0;
            const double height = 72.0;

            double dx = ox - target.X;
            double dy = oy - target.Y;

            double a = dirX * dirX + dirY * dirY;
            if (a < 1e-6) return false;

            double b = 2.0 * (dx * dirX + dy * dirY);
            double c = dx * dx + dy * dy - radius * radius;

            double disc = b * b - 4.0 * a * c;
            if (disc < 0) return false;

            double sqrtDisc = Math.Sqrt(disc);
            double t = (-b - sqrtDisc) / (2.0 * a);
            if (t < 0) t = (-b + sqrtDisc) / (2.0 * a);

            if (t < 0 || t > maxRange) return false;

            double hitZ = oz + dirZ * t;
            if (hitZ >= target.Z && hitZ <= target.Z + height)
            {
                hitDist = t;
                return true;
            }
            return false;
        }

        public PlayerState FindTargetInLineOfSight(PlayerState shooter, double maxRange, out double hitDist)
        {
            hitDist = -1.0;
            if (shooter == null || shooter.IsDead) return null;

            double yawRad = shooter.Yaw * (2.0 * Math.PI / 65536.0);
            double pitchRad = shooter.Pitch * (2.0 * Math.PI / 65536.0);

            double cosPitch = Math.Cos(pitchRad);
            double dirX = Math.Cos(yawRad) * cosPitch;
            double dirY = Math.Sin(yawRad) * cosPitch;
            double dirZ = -Math.Sin(pitchRad);

            const double eyeHeight = 60.0;
            double ox = shooter.X;
            double oy = shooter.Y;
            double oz = shooter.Z + eyeHeight;

            PlayerState bestTarget = null;
            double closestDist = double.MaxValue;

            foreach (PlayerState other in _entities.Values)
            {
                if (other == null || ReferenceEquals(other, shooter)) continue;
                double dist;
                if (RayIntersectsPlayer(ox, oy, oz, dirX, dirY, dirZ, maxRange, other, out dist))
                {
                    if (dist < closestDist)
                    {
                        closestDist = dist;
                        bestTarget = other;
                    }
                }
            }

            if (bestTarget != null)
            {
                hitDist = closestDist;
                return bestTarget;
            }
            return null;
        }

        /// <summary>
        /// 权威射击结算：扣除生命值并判定击杀。
        /// </summary>
        public bool ProcessWeaponFire(PlayerState shooter, int baseDamage, double range = 8192.0)
        {
            if (shooter == null || shooter.IsDead) return false;
            double dist;
            PlayerState victim = FindTargetInLineOfSight(shooter, range, out dist);
            if (victim != null)
            {
                bool lethal = victim.TakeDamage(baseDamage, shooter);
                _log.Info("COMBAT", "命中结算: 射手 slot=" + shooter.Slot + " -> 目标 slot=" + victim.Slot +
                                    " 伤害=" + baseDamage + " 剩余生命=" + victim.Health +
                                    " 距离=" + dist.ToString("0.0", System.Globalization.CultureInfo.InvariantCulture) +
                                    (lethal ? " [击杀!]" : ""));
                return true;
            }
            return false;
        }"""

assert old_frame in content, "old_frame not found"
content = content.replace(old_frame, new_frame, 1)

with open("CODOL-Combat-Server-v0.1/src/Engine/GameWorld.cs", "w", encoding="utf-8") as f:
    f.write(content)

print("GameWorld.cs combat mechanics patched successfully!")
