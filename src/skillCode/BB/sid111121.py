# -*- coding:utf-8 -*-
# Author:stars
# Edited by: 银河远征(20260922)
# env:py38
# 维内托-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""自身火力值、装甲值和回避值增加20点。
全阶段自身可免疫1次伤害, 暴击率和暴击伤害提高38.1%。
炮击战阶段被攻击命中后对攻击的敌人发动反击, 该次反击的攻击威力不会因耐久损伤而降低且必定命中, 造成的伤害提高38.1%（大破无法发动）。"""


class Skill_111121_1(CommonSkill):
    """自身火力值、装甲值和回避值增加20点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CommonBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=20,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='armor',
                phase=AllPhase,
                value=20,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=20,
                bias_or_weight=0
            ),
        ]


class Skill_111121_2(Skill):
    """全阶段自身可免疫1次伤害, 暴击率和暴击伤害提高38.1%。
    炮击战阶段被攻击命中后对攻击的敌人发动反击,
    该次反击的攻击威力不会因耐久损伤而降低且必定命中,
    造成的伤害提高38.1%（大破无法发动）。"""

    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            DamageShield(
                timer=timer,
                phase=AllPhase,
            ),
            CoeffBuff(
                timer=timer,
                name='crit',
                phase=AllPhase,
                value=.381,
                bias_or_weight=0
            ),
            CoeffBuff(
                timer=timer,
                name='crit_coef',
                phase=AllPhase,
                value=.381,
                bias_or_weight=0
            ),
            HitBack(
                timer=timer,
                phase=ShellingPhase,
                exhaust=None,
                coef={'ignore_damaged': True,
                      'final_damage_buff': .381}
            )
        ]


name = '意式设计'
skill = [Skill_111121_1, Skill_111121_2]
