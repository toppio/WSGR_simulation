# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 布里斯托尔-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *
from AADG_common import *

"""全队舰船对空值增加30点。全队E国舰船火力值和命中值增加15点，因战斗造成的舰载机损失减少50%。
当伊丽莎白女王(CVA-01)存在于队伍中时，伊丽莎白女王(CVA-01)的舰载机威力提高25%，不会因战斗造成舰载机损失。
自身攻击时提升敌方50%命中值的额外伤害，攻击护卫舰时伤害和命中率提高25%。自身暴击时无视目标装甲。
全队每有1艘小型船，增加全队舰船4%暴击率和暴击伤害。自身装备的发射器会视为反潜装备，其索敌值视为对潜值。"""


class Skill_106561_1(Skill):
    """全队舰船对空值增加30点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = Target(side=1)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='antiair',
                phase=AllPhase,
                value=30,
                bias_or_weight=0
            )
        ]


class Skill_106561_2(Skill):
    """全队E国舰船火力值和命中值增加15点，因战斗造成的舰载机损失减少50%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = CountryTarget(side=1, country='E')
        self.buff = [
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=15,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=15,
                bias_or_weight=0
            ),
            CoeffBuff(
                timer=timer,
                name='fall_rest',
                phase=AirPhase,
                value=-0.5,
                bias_or_weight=1
            )
        ]


class Skill_106561_3(Skill):
    """当伊丽莎白女王(CVA-01)存在于队伍中时，伊丽莎白女王(CVA-01)的舰载机威力提高25%，
    不会因战斗造成舰载机损失。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = CidTarget(side=1, cid_list=['10644', '11644'])  # 伊丽莎白女王(CVA-01)
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='air_atk_buff',
                phase=AllPhase,
                value=0.25,
                bias_or_weight=2
            ),
            CoeffBuff(
                timer=timer,
                name='fall_rest',
                phase=AirPhase,
                value=-1,
                bias_or_weight=1
            )
        ]


class Skill_106561_4(Skill):
    """自身攻击时提升敌方50%命中值的额外伤害，攻击护卫舰时伤害和命中率提高25%。
    自身暴击时无视目标装甲。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            AccuracyExtraDamage(
                timer=timer,
                name='extra_damage',
                phase=AllPhase,
                value=0.5,
                bias_or_weight=0
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=AllPhase,
                value=0.25,
                atk_request=[ATKRequest_Cover]
            ),
            AtkBuff(
                timer=timer,
                name='hit_rate',
                phase=AllPhase,
                value=0.25,
                bias_or_weight=0,
                atk_request=[ATKRequest_Cover]
            ),
            AtkBuff(
                timer=timer,
                name='ignore_armor',
                phase=AllPhase,
                value=-1,
                bias_or_weight=1,
                atk_request=[ATKRequest_Crit]
            )
        ]


class AccuracyExtraDamage(AtkBuff):
    """提升敌方50%命中值的额外伤害"""
    def change_value(self, *args, **kwargs):
        try:
            atk = kwargs['atk']
        except:
            atk = args[0]
        self.value = np.ceil(atk.target.get_final_status('accuracy') * 0.5)


class ATKRequest_Cover(ATKRequest):
    """攻击护卫舰"""
    def __bool__(self):
        return isinstance(self.atk.target, CoverShip)


class ATKRequest_Crit(ATKRequest):
    """触发暴击"""
    def __bool__(self):
        return self.atk.get_coef('crit_flag')


class Skill_106561_5(Skill):
    """全队每有1艘小型船，增加全队舰船4%暴击率和暴击伤害。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = Target(side=1)
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='crit',
                phase=AllPhase,
                value=0.04,
                bias_or_weight=0
            ),
            CoeffBuff(
                timer=timer,
                name='crit_coef',
                phase=AllPhase,
                value=0.04,
                bias_or_weight=0
            )
        ]

    def activate(self, friend, enemy):
        num_small = len(TypeTarget(side=1, shiptype=SmallShip
                                   ).get_target(friend, enemy))
        target = self.target.get_target(friend, enemy)
        for tmp_target in target:
            for tmp_buff in self.buff[:]:
                tmp_buff = copy.copy(tmp_buff)
                tmp_buff.value *= num_small
                tmp_target.add_buff(tmp_buff)


name = '近卫骑士'
skill = [Skill_106561_1, Skill_106561_2, Skill_106561_3,
         Skill_106561_4, Skill_106561_5, AADGCommonSkill]
