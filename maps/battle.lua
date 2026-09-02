-- Opera Battles: engine-side battle script.
-- Shared across mods. config.lua (auto-generated per run) defines ArmyConfig.

ArmyConfig = ArmyConfig or {
	Attacker = { { type = "e1", count = 5 } },
	Defender = { { type = "e1", count = 5 } },
	GridCols = 4,
	Seed = 0,
}

AllUnits = {}
NextId = 1
StartTick = 0
SampleEvery = 5
BattleOver = false

function Emit(kind, kv)
	local parts = { "E|" .. kind }
	if kv then
		for k, v in pairs(kv) do
			parts[#parts + 1] = k .. "=" .. tostring(v)
		end
	end
	print(table.concat(parts, " "))
end

-- Park-Miller LCG: OpenRA's math.random is not reproducible across runs.
RandState = 1

function SeedRandom(s)
	RandState = math.floor(s) % 2147483647
	if RandState <= 0 then
		RandState = RandState + 2147483646
	end
end

function NextRandom(n)
	RandState = (RandState * 16807) % 2147483647
	return (RandState % n) + 1
end

function Remaining(side)
	local n = 0
	for _, u in ipairs(AllUnits) do
		if u.side == side and not u.actor.IsDead then
			n = n + 1
		end
	end
	return n
end

function SideCounts()
	local spawned = { Attacker = 0, Defender = 0 }
	local lost = { Attacker = 0, Defender = 0 }
	for _, u in ipairs(AllUnits) do
		spawned[u.side] = spawned[u.side] + 1
		if u.actor.IsDead then
			lost[u.side] = lost[u.side] + 1
		end
	end
	return spawned, lost
end

function SpawnArmy(sideName, player, spawnCell, dir)
	local order = {}
	for _, group in ipairs(ArmyConfig[sideName]) do
		for _ = 1, group.count do
			order[#order + 1] = group.type
		end
	end
	for k = #order, 2, -1 do
		local j = NextRandom(k)
		order[k], order[j] = order[j], order[k]
	end

	local cols = ArmyConfig.GridCols or 4
	local MaxRows = 48
	if math.ceil(#order / cols) > MaxRows then
		cols = math.ceil(#order / MaxRows)
	end
	local rows = math.min(math.ceil(#order / cols), MaxRows)

	for i = 0, #order - 1 do
		local col = i % cols
		local row = math.floor(i / cols)
		local cell = CPos.New(
			spawnCell.X - dir * col,
			spawnCell.Y - math.floor(rows / 2) + row)
		local unit = Actor.Create(order[i + 1], true, {
			Owner = player,
			Location = cell,
		})
		local id = NextId
		NextId = NextId + 1
		local unitType = order[i + 1]
		AllUnits[#AllUnits + 1] = { id = id, actor = unit, side = sideName, type = unitType }
		Emit("UNIT", { id = id, side = sideName, type = unitType })
		Trigger.OnKilled(unit, function(self, killer)
			local p = self.CenterPosition
			Emit("KILL", {
				id = id,
				side = sideName,
				unit = unitType,
				killer = killer and killer.Type or "none",
				x = math.floor(p.X * 10 / 1024),
				y = math.floor(p.Y * 10 / 1024),
				tick = StartTick,
				atk_left = Remaining("Attacker"),
				def_left = Remaining("Defender"),
			})
			CheckEnd()
		end)
	end
	Emit("SPAWN", { side = sideName, count = #order })
end

function SampleFrame()
	local parts = {}
	for _, u in ipairs(AllUnits) do
		local a = u.actor
		if a.IsInWorld and not a.IsDead then
			local p = a.CenterPosition
			local hp = 100
			if a.HasProperty("Health") and a.MaxHealth > 0 then
				hp = math.floor(a.Health * 100 / a.MaxHealth)
			end
			parts[#parts + 1] = string.format("%d,%d,%d,%d", u.id,
				math.floor(p.X * 10 / 1024), math.floor(p.Y * 10 / 1024), hp)
		end
	end
	print("F|" .. StartTick .. "|" .. table.concat(parts, ";"))
end

function TrackCamera()
	local sx, sy, n = 0, 0, 0
	for _, u in ipairs(AllUnits) do
		local a = u.actor
		if a.IsInWorld and not a.IsDead then
			local p = a.CenterPosition
			sx = sx + p.X
			sy = sy + p.Y
			n = n + 1
		end
	end
	if n == 0 then return end
	Camera.Position = WPos.New(math.floor(sx / n), math.floor(sy / n), 0)
end

-- Emit DONE synchronously: once a side dies, campaign rules stop the world and
-- deferred callbacks never run.
function CheckEnd()
	if BattleOver then return end
	local a, d = Remaining("Attacker"), Remaining("Defender")
	if a <= 0 or d <= 0 then
		SampleFrame()
		BattleOver = true
		local spawned, lost = SideCounts()
		local winner = "Draw"
		if a > 0 then winner = "Attacker"
		elseif d > 0 then winner = "Defender" end
		Emit("RESULT", {
			winner = winner,
			atk_spawned = spawned.Attacker,
			atk_lost = lost.Attacker,
			def_spawned = spawned.Defender,
			def_lost = lost.Defender,
		})
		Emit("DONE", {})
	end
end

function OrderHunt(sideName)
	for _, u in ipairs(AllUnits) do
		if u.side == sideName and u.actor.HasProperty("Hunt") then
			u.actor.Hunt()
		end
	end
end

WorldLoaded = function()
	local attacker = Player.GetPlayer("Attacker")
	local defender = Player.GetPlayer("Defender")

	Camera.Position = CameraPoint.CenterPosition

	Emit("BEGIN", { seed = ArmyConfig.Seed or 0 })
	SeedRandom((ArmyConfig.Seed or 0) + 1)

	SpawnArmy("Attacker", attacker, AttackerSpawn.Location, 1)
	SpawnArmy("Defender", defender, DefenderSpawn.Location, -1)

	CheckEnd()

	Trigger.AfterDelay(DateTime.Seconds(1), function()
		OrderHunt("Attacker")
		OrderHunt("Defender")
	end)

	Trigger.AfterDelay(DateTime.Minutes(5), function()
		if not BattleOver then
			SampleFrame()
			BattleOver = true
			Emit("RESULT", { winner = "Timeout" })
			Emit("DONE", {})
		end
	end)
end

Tick = function()
	StartTick = StartTick + 1
	if BattleOver then return end
	if StartTick % SampleEvery == 0 then
		SampleFrame()
	end
	if StartTick % 10 == 0 then
		TrackCamera()
	end
end
