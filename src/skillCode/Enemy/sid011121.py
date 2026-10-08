# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# # 深海大凤(晴空万里)

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *
from src.wsgr.formulas import AirAtk

"""降低对方舰载机威力40%，自身受到的航空伤害降低40%"""


class Skill_011121_1(Skill):
    """降低对方舰载机威力40%"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = Target(side=0)
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='air_atk_buff',
                phase=AllPhase,
                value=-0.4,
                bias_or_weight=2
            )
        ]


class Skill_011121_2(Skill):
    """自身受到的航空伤害降低40%"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master=master)
        self.buff = [
            FinalDamageBuff(
                timer=timer,
                name='final_damage_debuff',
                phase=AllPhase,
                value=-0.4,
                bias_or_weight=2
            )
        ]


class ATKRequest_1(ATKRequest):
    def __bool__(self):
        return isinstance(self.atk, AirAtk)


name = '晴空万里'
skill = [Skill_011121_1, Skill_011121_2]