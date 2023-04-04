# -*- coding:utf-8 -*-
# Author:KS Mist*
# env:py38
# 阿贝克隆比&罗伯茨

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""增加火力值15%/20%/25%，命中值5/8/10点，航速越低增加幅度越高，最多增加火力值30%/40%/50%，命中值10/15/20点。"""


class Skill_110621_1(Skill):
    """增加火力值15%/20%/25%，命中值5/8/10点，航速越低增加幅度越高，最多增加火力值30%/40%/50%，命中值10/15/20点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        now_speed = self.master.get_final_status('speed')
        speed = self.master.status['speed']
        d_speed = max(0, speed - now_speed)
        fire_val = 0.25 + d_speed / speed * 0.25
        accu_val = 10 + d_speed / speed + 10
        self.buff = [
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=fire_val,
                bias_or_weight=2
            ),
            StatusBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=accu_val,
                bias_or_weight=0
            )
        ]

name = '火力支援'
skill = [Skill_110621_1]
