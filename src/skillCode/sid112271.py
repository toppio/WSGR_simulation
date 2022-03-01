# -*- coding:utf-8 -*-
# Author:zzhh225
# env:py38
# 飞鹰改-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *


class Skill_112271(Skill):
    """特设空母(3级)：炮击战阶段造成的最终伤害增加30%。"""

    def __init__(self, master):
        super().__init__(master)
        self.target = SelfTarget(master)
        self.buff = [
            FinalDamageBuff(
                name='final_damage_buff',
                phase=(ShellingPhase,),
                value=0.3,
            )
        ]


skill = [Skill_112271]
