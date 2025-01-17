# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 穿甲榴弹

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""在炮击战阶段，自身对战列巡洋舰造成的伤害增加2%/4%/6%/8%。"""


class Strategy_313(SelfStrategy):
    def __init__(self, timer, master, level=3):
        super().__init__(timer, master, level)
        value = [0.02, 0.04, 0.06, 0.08]
        self.stid = '313'
        self.buff = [
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=ShellingPhase,
                value=value[self.level],
                atk_request=[ATKRequest_1]
            )
        ]


class ATKRequest_1(ATKRequest):
    def __bool__(self):
        return isinstance(self.atk.target, BC)


skill = [Strategy_313]
