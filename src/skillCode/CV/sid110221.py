# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 赤城改-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""旗舰技能，索敌成功时，敌方全体对空值降低30%"""


class Skill_110221(Skill):
    def __init__(self, timer, master):
        super().__init__(timer, master)

        self.target = Target(side=0)

        self.buff = [
            StatusBuff(
                timer=timer,
                name='antiair',
                phase=(AllPhase,),
                value=-0.3,
                bias_or_weight=1
            )
        ]

    def is_active(self, friend, enemy):
        return self.master.loc == 1 and \
               self.master.get_recon_flag()


name = '奇袭'
skill = [Skill_110221]
