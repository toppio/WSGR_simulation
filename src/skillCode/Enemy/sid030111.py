# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 雾岛

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""自身射程增加2档。展开克莱因力场：免疫1次伤害。炮击战阶段使用超重力炮作战：同时攻击3个目标。"""


class Skill_030111_1(Skill):
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            MultipleAtkBuff(
                timer=timer,
                name='multi_attack',
                phase=ShellingPhase,
                num=3,
                rate=1
            )
        ]

class Skill_030111_2(Skill):
    """自身射程增加2档"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='range_buff',
                phase=AllPhase,
                value=2,
                bias_or_weight=0
            ),
        ]

class Skill_030111_3(Skill):
    """免疫1次伤害"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            DamageShield(
                timer=timer,
                phase=AllPhase,
            ),
        ]


name = '海军法典的试炼-翠'
skill = [Skill_030111_1,Skill_030111_2,Skill_030111_3]

