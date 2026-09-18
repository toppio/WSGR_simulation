# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 反潜航母

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""所有可参与先制反潜阶段的我方舰船，在非单横阵时亦可以进行先制反潜。"""


class Skill_030051_1(Skill):
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = TypeTarget(side=1,shiptype=AntiSubShip)
        self.buff = [
            ActPhaseBuff(
                timer=timer,
                name='act_phase',
                phase=AntiSubPhase
            )
        ]


name = '反潜平台'
skill = [Skill_030051_1]

