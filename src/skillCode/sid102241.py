# -*- coding:utf-8 -*-
# Author:zzhh225
# env:py38
# 可畏-1

from ..wsgr.skill import *
from ..wsgr.ship import *
from ..wsgr.phase import *


class Skill_102241(Skill):
    """马塔潘角之箭(3级)：航空战阶段提升自身15点命中，
    炮击战阶段自身攻击敌人时降低敌人30%的装甲。"""

    def __init__(self, master):
        super().__init__(master)
        self.target = SelfTarget(master)
        self.buff = [
            StatusBuff(
                name='accuracy',
                phase=(AirPhase,),
                value=15,
                bias_or_weight=0
            ),
            AtkBuff(
                name='ignore_armor',
                phase=(ShellingPhase,),
                value=-0.3,
                bias_or_weight=1,
            )
        ]


skill = [Skill_102241]
