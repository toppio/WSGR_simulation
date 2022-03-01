# -*- coding:utf-8 -*-
# Author:zzhh225
# env:py38
# 伊势改-1
from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *
from src.wsgr.equipment import *


class Skill_110041(Skill):
    """机群驱散B(3级)：降低航空战时对方轰炸机20%的命中率。"""
    def __init__(self, master):
        super().__init__(master)
        self.target = EquipTarget(side=0,
                                  target=Target(side=0),
                                  equiptype=(Bomber,))
        self.buff = [CoeffBuff(
            name='hit_rate',
            phase=(AirPhase,),
            value=-0.2,
            bias_or_weight=0
        )]


skill = [Skill_110041]
