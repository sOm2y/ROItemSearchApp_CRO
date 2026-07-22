Item = {
  [18000] = {
    Type = "Cannonball",
    Stat = {0, 100}
  },
  [18001] = {
    Type = "Cannonball",
    Stat = {6, 120}
  },
  [18002] = {
    Type = "Cannonball",
    Stat = {7, 120}
  },
  [18003] = {
    Type = "Cannonball",
    Stat = {8, 120}
  },
  [18004] = {
    Type = "Cannonball",
    Stat = {0, 250}
  },
  [18005] = {
    Type = "Cannonball",
    Stat = {1, 120}
  },
  [18006] = {
    Type = "Cannonball",
    Stat = {4, 120}
  },
  [18007] = {
    Type = "Cannonball",
    Stat = {2, 120}
  },
  [18008] = {
    Type = "Cannonball",
    Stat = {3, 120}
  },
  [18009] = {
    Type = "Cannonball",
    Stat = {5, 120}
  },
  [19393] = {
    Type = "armor",
    Stat = { 20, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0 },
    OnStartEquip = function()
      local temp1 = 0
      local temp2 = 0
      local temp3 = 0
      local temp4 = 0
      local temp5 = 0
      local temp6 = 0
      temp1 = get(32)
      temp2 = get(33)
      temp3 = get(35)
      temp4 = get(34)
      temp5 = get(36)
      temp6 = get(37)
      SubSpellCastTime(5)
      AddSkillMDamage(0, math.floor(temp1 / 12) * 2)
      AddSkillMDamage(4, math.floor(temp2 / 12) * 2)
      AddSkillMDamage(1, math.floor(temp4 / 12) * 2)
      AddSkillMDamage(3, math.floor(temp3 / 12) * 2)
      AddSkillMDamage(2, math.floor(temp5 / 12) * 2)
      AddSkillMDamage(6, math.floor(temp6 / 12) * 2)
    end,
    Combiitem = {2000001020, 2000002303}
  },
  [490384] = {
    Type = "armor",
    Stat = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0 },
    OnStartEquip = function()
      AddExtParam(0, 41, 50)
      AddExtParam(0, 200, 50)
      RaceAddDamage(9999, 10)
      AddMdamage_Race(9999, 10)
      AddExtParam(0, 111, 10)
    end
  },
  [491073] = {
    Type = "armor",
    Stat = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0 },
    OnStartEquip = function()
      local temp = 0
      local temp2 = 0
      local tempGrade = 0
      temp = GetRefineLevel(GetLocation())
      temp2 = math.floor(temp / 4)
      tempGrade = GetEquipGradeLevel(GetLocation())
      AddExtParam(0, 207, 10)
      AddExtParam(0, 140, 6)
      AddExtParam(0, 111, 10)
      AddMeleeAttackDamage(1, temp2 * 5)
      AddRangeAttackDamage(1, temp2 * 5)
      AddSkillMDamage(10, temp2 * 5)
      if 8 < temp then
        RaceAddDamage(9999, 15)
        AddMdamage_Race(9999, 15)
      end
      if 11 < temp then
        AddDamage_SKID(1, 2006, 40)
        AddDamage_SKID(1, 5004, 40)
        AddDamage_SKID(1, 2008, 40)
        AddDamage_SKID(1, 2261, 40)
        AddDamage_SKID(1, 2321, 40)
        AddDamage_SKID(1, 2330, 40)
        AddDamage_SKID(1, 2332, 40)
        AddDamage_SKID(1, 2040, 40)
        AddDamage_SKID(1, 2477, 40)
        AddDamage_SKID(1, 2481, 40)
        AddDamage_SKID(1, 2280, 40)
        AddDamage_SKID(1, 2215, 40)
        AddDamage_SKID(1, 2202, 40)
        AddDamage_SKID(1, 2213, 40)
        AddDamage_SKID(1, 2447, 40)
        AddDamage_SKID(1, 2446, 40)
        AddDamage_SKID(1, 2449, 30)
        AddDamage_SKID(1, 2233, 40)
        AddDamage_SKID(1, 382, 40)
        AddDamage_SKID(1, 2236, 40)
        AddDamage_SKID(1, 2418, 40)
        AddDamage_SKID(1, 2414, 40)
        AddDamage_SKID(1, 2036, 40)
        AddDamage_SKID(1, 2029, 40)
        AddDamage_SKID(1, 2022, 40)
        AddDamage_SKID(1, 2284, 40)
        AddDamage_SKID(1, 2288, 40)
        AddDamage_SKID(1, 2579, 40)
        AddDamage_SKID(1, 2576, 40)
        AddDamage_SKID(1, 2602, 40)
        AddDamage_SKID(1, 2600, 40)
        AddDamage_SKID(1, 3004, 40)
        AddDamage_SKID(1, 3009, 40)
        AddDamage_SKID(1, 5033, 40)
        AddDamage_SKID(1, 5026, 40)
        AddDamage_SKID(1, 2571, 40)
        AddDamage_SKID(1, 2565, 40)
      end
      if 0 < tempGrade then
        AddExtParam(0, 41, 100)
        AddExtParam(0, 200, 100)
      end
      if 1 < tempGrade then
        SubSpellDelay(5)
      end
      if 2 < tempGrade and 199 < get(11) then
        AddDamage_SKID(1, 6001, 25)
        AddDamage_SKID(1, 5208, 25)
        AddDamage_SKID(1, 5213, 25)
        AddDamage_SKID(1, 5266, 25)
        AddDamage_SKID(1, 5267, 25)
        AddDamage_SKID(1, 5265, 25)
        AddDamage_SKID(1, 5252, 25)
        AddDamage_SKID(1, 5244, 25)
        AddDamage_SKID(1, 5284, 25)
        AddDamage_SKID(1, 5273, 25)
        AddDamage_SKID(1, 5283, 25)
        AddDamage_SKID(1, 6005, 25)
        AddDamage_SKID(1, 6006, 25)
        AddDamage_SKID(1, 6004, 25)
        AddDamage_SKID(1, 6003, 25)
        AddDamage_SKID(1, 6002, 25)
        AddDamage_SKID(1, 5220, 25)
        AddDamage_SKID(1, 5235, 25)
        AddDamage_SKID(1, 5217, 25)
        AddDamage_SKID(1, 5369, 25)
        AddDamage_SKID(1, 5373, 25)
        AddDamage_SKID(1, 5371, 25)
        AddDamage_SKID(1, 5370, 25)
        AddDamage_SKID(1, 5328, 30)
        AddDamage_SKID(1, 5329, 30)
        AddDamage_SKID(1, 5334, 25)
        AddDamage_SKID(1, 5353, 25)
        AddDamage_SKID(1, 5355, 25)
        AddDamage_SKID(1, 5356, 25)
        AddDamage_SKID(1, 5292, 25)
        AddDamage_SKID(1, 5289, 25)
        AddDamage_SKID(1, 5287, 25)
        AddDamage_SKID(1, 5294, 25)
        AddDamage_SKID(1, 5320, 25)
        AddDamage_SKID(1, 5322, 25)
        AddDamage_SKID(1, 5317, 25)
        AddDamage_SKID(1, 5466, 25)
        AddDamage_SKID(1, 5469, 25)
        AddDamage_SKID(1, 5472, 25)
        AddDamage_SKID(1, 5474, 25)
        AddDamage_SKID(1, 5427, 25)
        AddDamage_SKID(1, 5429, 25)
        AddDamage_SKID(1, 5431, 25)
        AddDamage_SKID(1, 5425, 25)
        AddDamage_SKID(1, 5483, 25)
        AddDamage_SKID(1, 5482, 25)
        AddDamage_SKID(1, 5488, 25)
        AddDamage_SKID(1, 5489, 25)
        AddDamage_SKID(1, 5490, 25)
        AddDamage_SKID(1, 5491, 25)
        AddDamage_SKID(1, 5492, 25)
        AddDamage_SKID(1, 5435, 25)
        AddDamage_SKID(1, 5437, 25)
        AddDamage_SKID(1, 5445, 25)
        AddDamage_SKID(1, 5446, 25)
        AddDamage_SKID(1, 5452, 25)
        AddDamage_SKID(1, 5460, 25)
        AddDamage_SKID(1, 5456, 25)
        AddDamage_SKID(1, 5451, 25)
        AddDamage_SKID(1, 5407, 25)
        AddDamage_SKID(1, 5408, 25)
        AddDamage_SKID(1, 5409, 25)
      end
      if 3 < tempGrade then
        AddDamage_Property(1, 10, 15)
        AddMDamage_Property(1, 10, 15)
      end
    end
  },
  [410211] = {
    Type = "armor",
    Stat = { 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0 },
    OnStartEquip = function()
      temp = get(11)
      AddExtParam(0, 41, temp)
      AddExtParam(0, 200, temp)
    end,
    Combiitem = {2000004910, 2000004913}
  }
}
Combiitem = {
}
