# -*- coding:utf-8 -*-
# Author:zzhh225
# env:py38
# 大凤改-1

from ..wsgr.skill import *
from ..wsgr.ship import *
from ..wsgr.phase import *


class Skill_111171(Skill):
    """队伍中该舰下方位置的3艘航母（轻航，正规航母，装甲航母）增加回避6点
    todo 并且炮击战可进行二次攻击，但二次攻击的伤害减低50%。"""
    def __init__(self, master):
        super().__init__(master)
        self.target = NearestLocTarget(
            side=1,
            master=master,
            radius=3,
            direction='down',
            expand=True,
            shiptype=(CVL, CV, AV)
        )

        self.buff = [StatusBuff(
            name='accuracy',
            phase=(AllPhase,),
            value=6,
            bias_or_weight=0
        ),
        ]


skill = [Skill_111171]