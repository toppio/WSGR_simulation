# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 弗莱彻

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *
from src.skillCode.collection import FLETCHER_COUNT

"""根据图鉴中开启的弗莱彻级舰船数量，
每有一艘自身火力、装甲、鱼雷、命中、回避、对空、对潜、索敌、幸运增加1点，暴击率提高1%。
(现版本总计29)"""


class Skill_110891_1(CommonSkill):
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CommonBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=FLETCHER_COUNT,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='armor',
                phase=AllPhase,
                value=FLETCHER_COUNT,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='torpedo',
                phase=AllPhase,
                value=FLETCHER_COUNT,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=FLETCHER_COUNT,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=FLETCHER_COUNT,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='antiair',
                phase=AllPhase,
                value=FLETCHER_COUNT,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='antisub',
                phase=AllPhase,
                value=FLETCHER_COUNT,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='recon',
                phase=AllPhase,
                value=FLETCHER_COUNT,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='luck',
                phase=AllPhase,
                value=FLETCHER_COUNT,
                bias_or_weight=0
            ),
        ]


class Skill_110891_2(Skill):
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='crit',
                phase=AllPhase,
                value=FLETCHER_COUNT * 0.01,
                bias_or_weight=0
            )
        ]


name = '最优驱逐舰'
skill = [Skill_110891_1, Skill_110891_2]
