# -*- coding:utf-8 -*-
# Author:huan_yp
# env:py38
# 布雷恩改-1、基林改-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""增加 8 点索敌值，60% 的索敌视为火力和对空。"""


class Skill_110921_1(CommonSkill):
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CommonBuff(
                timer=timer,
                name='recon',
                phase=AllPhase,
                value=8,
                bias_or_weight=0
            ),
        ]


class Skill_110921_2(Skill):
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            StatusBasedBuff(
                timer=timer,
                name='antiair',
                base='recon',
                phase=AllPhase,
                value=.6,
                bias_or_weight=0
            ),
            StatusBasedBuff(
                timer=timer,
                name='fire',
                base='recon',
                phase=AllPhase,
                value=.6,
                bias_or_weight=0
            ),
        ]


name = '冷战先锋'
skill = [Skill_110921_1, Skill_110921_2]
