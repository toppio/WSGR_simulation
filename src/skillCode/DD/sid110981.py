# -*- coding:utf-8 -*-
# Author:huan_yp
# Edited by: 银河远征(20260922)
# env:py38
# 沃克兰

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""自身回避值和索敌值增加35点。
自身和编队相邻的驱逐舰火力值、鱼雷值和命中值增加20点，
如果编队相邻的是F国驱逐舰，则额外提高其20%暴击率和暴击伤害。"""


class Skill_110981_1(CommonSkill):
    """自身回避值和索敌值增加35点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CommonBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=35,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='recon',
                phase=AllPhase,
                value=35,
                bias_or_weight=0
            )
        ]


class Skill_110981_2(Skill):
    """自身和编队相邻的驱逐舰火力值、鱼雷值和命中值增加20点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = NearestLocTarget(
            side=1,
            master=master,
            radius=1,
            direction='near',
            master_include=True,
            shiptype=DD
        )
        self.buff = [
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=20,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='torpedo',
                phase=AllPhase,
                value=20,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=20,
                bias_or_weight=0
            )
        ]


class Skill_110981_3(Skill):
    """如果编队相邻的是F国驱逐舰，则额外提高其20%暴击率和暴击伤害。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = CombinedTarget(
            side=1,
            target_list=[
                NearestLocTarget(
                    side=1,
                    master=master,
                    radius=1,
                    direction='near',
                    shiptype=DD
                ),
                CountryTarget(side=1, country='F')
            ]
        )
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='crit',
                phase=AllPhase,
                value=0.2,
                bias_or_weight=0
            ),
            CoeffBuff(
                timer=timer,
                name='crit_coef',
                phase=AllPhase,
                value=0.2,
                bias_or_weight=0
            )
        ]


name = '超级驱逐舰'
skill = [Skill_110981_1, Skill_110981_2, Skill_110981_3]
