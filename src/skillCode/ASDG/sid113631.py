# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 炽热-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *
from AADG_common import *

"""全队航速增加3点。
自身装备的发射器会视为反潜装备，其索敌值视为对潜值。
自身反潜值视为火力值，攻击潜艇时命中率和伤害提高25%。"""


class Skill_113631_1(PrepSkill):
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = Target(side=1)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='speed',
                phase=AllPhase,
                value=3,
                bias_or_weight=0
            )
        ]


class Skill_113631_2(Skill):
    """自身反潜值视为火力值，攻击潜艇时命中率和伤害提高25%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            StatusBasedBuff(
                timer=timer,
                name='fire',
                base='antisub',
                phase=AllPhase,
                value=1,
                bias_or_weight=0
            ),
            AtkBuff(
                timer=timer,
                name='hit_rate',
                phase=AllPhase,
                value=.25,
                bias_or_weight=0,
                atk_request=[ATKRequest_1]
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=AllPhase,
                value=.25,
                atk_request=[ATKRequest_1]
            )
        ]


class ATKRequest_1(ATKRequest):
    def __bool__(self):
        return isinstance(self.atk.target, SS)


name = '胜利巡游'
skill = [Skill_113631_1, Skill_113631_2, AADGCommonSkill]
