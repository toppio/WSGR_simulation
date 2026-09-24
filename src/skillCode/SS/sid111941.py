# -*- coding:utf-8 -*-
# Author:huan_yp
# Edited by: 银河远征(20260922)
# env:py38
# 大青花鱼

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""增加自身鱼雷值和命中值20点，暴击率和暴击伤害20%。
被自身攻击命中的敌人受到的伤害提高50%。"""


class Skill_111941_1(CommonSkill):
    """增加自身鱼雷值和命中值20点"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CommonBuff(
                timer=timer,
                name='torpedo',
                phase=AllPhase,
                value=20,
                bias_or_weight=0,
            ),
            CommonBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=20,
                bias_or_weight=0,
            )
        ]


class Skill_111941_2(Skill):
    """增加自身暴击率和暴击伤害20%"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='crit',
                phase=AllPhase,
                value=.2,
                bias_or_weight=0,
            ),
            CoeffBuff(
                timer=timer,
                name='crit_coef',
                phase=AllPhase,
                value=.2,
                bias_or_weight=0,
            )
        ]


class Skill_111941_3(Skill):
    """被自身攻击命中的敌人受到的伤害提高50%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            AtkHitBuff(
                timer=timer,
                name='atk_hit',
                phase=AllPhase,
                buff=[
                    FinalDamageBuff(
                        timer=timer,
                        name='final_damage_debuff',
                        phase=AllPhase,
                        value=.5
                    )
                ],
                side=0
            )
        ]


name = '王牌潜艇'
skill = [Skill_111941_1, Skill_111941_2, Skill_111941_3]
