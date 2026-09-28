# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 埃塞克斯改-2

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *
from src.skillCode.collection import ESSEX_COUNT

"""根据图鉴中开启的埃塞克斯级舰船数量，每有一艘自身舰载机威力提高9%。
全队埃塞克斯级舰船舰载机威力提高5%。"""


class Skill_112262_1(Skill):
    """根据图鉴中开启的埃塞克斯级舰船数量，每有一艘自身舰载机威力提高9%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='air_atk_buff',
                phase=AllPhase,
                value=ESSEX_COUNT * 0.09,
                bias_or_weight=2
            )
        ]


class Skill_112262_2(Skill):
    """全队埃塞克斯级舰船舰载机威力提高5%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = TagTarget(side=1, tag='essex')
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='air_atk_buff',
                phase=AllPhase,
                value=0.05,
                bias_or_weight=2
            )
        ]


name = '埃塞克斯'
skill = [Skill_112262_1, Skill_112262_2]
