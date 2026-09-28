# -*- coding:utf-8 -*-
# Author:huan_yp
# env:py38
# U-14

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""增加自身 9 点闪避值，闪避值的 20% 同时视为鱼雷值。"""


class Skill_104581_1(CommonSkill):
    """增加自身 9 点闪避值"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CommonBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=9,
                bias_or_weight=0,
            )
        ]


class Skill_104581_2(Skill):
    """闪避值的 20% 同时视为鱼雷值。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            StatusBasedBuff(
                timer=timer,
                name='torpedo',
                base='evasion',
                phase=AllPhase,
                value=0.2,
                bias_or_weight=0
            )
        ]


name = '王牌'
skill = [Skill_104581_1, Skill_104581_2]
