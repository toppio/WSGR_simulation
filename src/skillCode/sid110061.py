# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 俾斯麦-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""旗舰杀手(3级)：当俾斯麦作为旗舰时，40%概率发动，攻击对方舰队旗舰并+20%穿甲，增加30点固定伤害且必定命中。
"""


class Skill_110061(Skill):
    def __init__(self, master, timer):
        super().__init__(master, timer)
        self.target = SelfTarget(master)
        self.buff = [
            SpecialAtkBuff_1(
                timer=timer,
                name='special_attack',
                phase=ShellingPhase,
                num=1,
                rate=0.4,
                during_buff=[
                    CoeffBuff(
                        timer=timer,
                        name='pierce_coef',
                        phase=ShellingPhase,
                        value=0.2,
                        bias_or_weight=0
                    ),
                    CoeffBuff(
                        timer=timer,
                        name='extra_damage',
                        phase=ShellingPhase,
                        value=30,
                        bias_or_weight=0
                    )
                ],
                coef={'must_hit': True}
            )
        ]

    def is_active(self, friend, enemy):
        return self.master.loc == 1


class SpecialAtkBuff_1(ActiveBuff):
    def is_active(self, atk, enemy, *args, **kwargs):
        # 对方旗舰不存活，不发动技能
        if enemy.ship[0].damaged == 4:
            return False
        elif not enemy.ship[0].can_be_atk(atk):
            return False
        else:
            return self.rate_verify() and \
                   isinstance(self.timer.phase, self.phase)

    def active_start(self, atk, enemy, *args, **kwargs):
        assert self.master is not None
        self.add_during_buff()  # 攻击时效果
        spetial_atk = atk(
            timer=self.timer,
            atk_body=self.master,
            def_list=[enemy.ship[0]],
            coef=self.coef,
            target=enemy.ship[0],
        )
        yield spetial_atk

        self.remove_during_buff()  # 去除攻击时效果
        self.add_end_buff()  # 攻击结束效果


skill = [Skill_110061]
