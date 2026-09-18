# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 高雄

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""若敌方索敌失败，自身可发动远程打击。炮击战阶段使用超重力炮作战：同时攻击2个目标。"""


class Skill_030011_1(Skill):
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            MultipleAtkBuff(
                timer=timer,
                name='multi_attack',
                phase=ShellingPhase,
                num=2,
                rate=1
            )
        ]


name = '海军法典的试炼-赫'
skill = [Skill_030011_1]

