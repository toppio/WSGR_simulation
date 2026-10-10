# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# harushima(test)

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""与雾岛一同展开克莱因力场，积蓄力量准备极其强力的超重力炮攻击。
在次轮炮击阶段前，无法攻击，减少50%自身受到的所有伤害，并且不会被暴击。
若次轮炮击战阶段开始时自身非中破、大破，次轮炮击阶段免疫一次受到的伤害，同时攻击所有目标，该次攻击必中且无视目标装甲。
若在次轮炮击战开始前自身中破，蓄力将被阻止：装甲-150，次轮炮击阶段无法攻击。"""


class Skill_030131_1(Skill):
    """在次轮炮击阶段前，无法攻击，减少50%自身受到的所有伤害，并且不会被暴击。"""

    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)

        self.buff = [
            ActPhaseBuff(
                timer=timer,
                name='no_normal_atk',
                phase=FirstShellingPhase
            ),
            DuringAtkBuff(
                        timer=timer,
                        name='final_damage_debuff',
                        phase=(LongMissilePhase, AirPhase, FirstMissilePhase, FirstTorpedoPhase, FirstShellingPhase),
                        value=-0.5,
                        bias_or_weight=2
           ),
            DuringSpecialBuff(
                        timer=timer,
                        name='must_not_be_crit',
                        phase=(FirstMissilePhase, SecondMissilePhase, AirPhase),
                        bias_or_weight=3
            ),
        ]

class Skill_030131_2(Skill):
    """若次轮炮击战阶段开始时自身非中破、大破，次轮炮击阶段免疫一次受到的伤害，该次攻击必中且无视目标装甲"""

    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)

        self.buff = [
            DamageShield(
                timer=timer,
                phase=SecondShellingPhase,
            ),
            MultipleAtkBuff(
                timer=timer,
                name='multi_attack',
                phase=SecondShellingPhase,
                num=6,
                rate=1,
                during_buff=[
                    DuringAtkBuff(
                        timer=timer,
                        name='must_hit',
                        phase=SecondShellingPhase
                    ),
                    DuringAtkBuff(
                        timer=timer,
                        name='ignore_armor',
                        phase=SecondShellingPhase,
                        value=-1,
                        bias_or_weight=1,
                    ),
                ]
            )
        ]

    def is_active(self, friend, enemy):
        if self.master.damaged == 1:
            return super().is_active(*args, **kwargs)
        else:
            return False

class Skill_030131_3(Skill):
    """若在次轮炮击战开始前自身中破，蓄力将被阻止：装甲-150，次轮炮击阶段无法攻击。"""

    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)

        self.buff = [
            StatusBuff_realTime(
                timer=timer,
                name='armor',
                phase=AllPhase,
                value=-150,
                bias_or_weight=0
            ),
            ActPhaseBuff_realTime(
                timer=timer,
                name='not_act_phase',
                phase=SecondShellingPhase
            )
        ]

class ActPhaseBuff_realTime(ActPhaseBuff):
    def __init__(self, timer, phase, *args, **kwargs):
        super().__init__(timer, phase, *args, **kwargs)
        self.master_damaged = None

    def set_master(self, master):
        self.master_damaged = master.damaged  # 战损状态缓存(受伤前状态)
        super().set_master(master)

    def is_active(self, atk, *args, **kwargs):

        # 如果战损状态缓存是中破，技能发动
        if self.master_damaged == 1 and self.master.damaged == 2 :
            return True
        # 否则更新战损状态缓存，技能不发动
        self.master_damaged = self.master.damaged
        return False

class StatusBuff_realTime(StatusBuff):
    def __init__(self, timer, phase, *args, **kwargs):
        super().__init__(timer, phase, *args, **kwargs)
        self.master_damaged = None

    def set_master(self, master):
        self.master_damaged = master.damaged  # 战损状态缓存(受伤前状态)
        super().set_master(master)

    def is_active(self, atk, *args, **kwargs):

        # 如果战损状态缓存是中破，技能发动
        if self.master_damaged == 1 and self.master.damaged == 2 :
            return True
        # 否则更新战损状态缓存，技能不发动
        self.master_damaged = self.master.damaged
        return False


name = '海军法典的试炼'
skill = [Skill_030131_1,Skill_030131_2,Skill_030131_3]

