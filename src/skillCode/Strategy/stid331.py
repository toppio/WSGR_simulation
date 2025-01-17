# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 改良被帽弹

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""自身位于队伍中时，炮击战阶段，我方队伍中的战列巡洋舰炮击附带2%/5%/7%/10%护甲穿透效果。"""


class Strategy_331(FleetStrategy):
    def __init__(self, timer, master, level=3):
        super().__init__(timer, master, level)
        value = [0.02, 0.05, 0.07, 0.1]
        self.stid = '331'
        self.target = TypeTarget(side=1, shiptype=BC)
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='pierce_coef',
                phase=ShellingPhase,
                value=value[self.level],
                bias_or_weight=0
            )
        ]


skill = [Strategy_331]
