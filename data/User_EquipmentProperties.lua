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
  [20260617001] = {
    Type = "armor",
    Stat = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0 },
        SubSpellCastTime(((get(35)+get(33))/50)*4)
        AddSkillMDamage(10, (get(35)+get(33))/50)
        SubSpellDelay((get(36)+get(37))/50)
        AddSkillMDamage(10, (get(36)+get(37))/50)
        Combiitem = {2026061700001}
  },
  [20260617002] = {
    Type = "armor",
    Stat = { 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0 },
        temp2 = get(36)+get(37)
        SubSpellCastTime(((get(35)+get(33))/40)*5)
        AddExtParam(1, 140, ((get(35)+get(33))/40)*2)
        AddExtParam(1, 167, (temp2/40)*3)
        AddExtParam(1, 140, (get(36)+get(37))/40)
        Combiitem = {2026061700001}
  }
}
Combiitem = {
  [2026061700001] = {
    Item = {20260617001, 20260617002},
    AddExtParam(1, 237, 5)
    AddExtParam(1, 238, 5)
    AddMDamage_Property(1, 10, 10)
  },
}

