# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 菜谱、藏品、工程局

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

# 菜谱技能（一个舰队只生效一种）
class FoodSkill(Skill):
    """S国舰船炮击战造成的伤害增加10%"""
    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = CountryTarget(side=1, country='S')
        self.buff = [
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=ShellingPhase,
                value=0.1,
            )
        ]

# 藏品加成-1
class CollectionSkill_1(Skill):
    """所有驱逐舰鱼雷+3"""
    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = TypeTarget(side=1, shiptype=DD)
        self.buff = [
            CommonBuff(
                timer=timer,
                name='torpedo',
                phase=AllPhase,
                value=3,
                bias_or_weight=0
            )
        ]

# 藏品加成-2
class CollectionSkill_2(Skill):
    """所有战列火力+2"""
    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = TypeTarget(side=1, shiptype=BB)
        self.buff = [
            CommonBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=2,
                bias_or_weight=0
            )
        ]

# 藏品加成-3
class CollectionSkill_3(Skill):
    """S火力+2"""
    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = CountryTarget(side=1, country='S')
        self.buff = [
            CommonBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=2,
                bias_or_weight=0
            )
        ]

# 工程局加成 战列公共
class EngineeringBureau_BB(Skill):
    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = TypeTarget(side=1, shiptype=BB)
        self.buff = [
            CommonBuff(
                timer=timer,
                name='armor',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CoeffBuff(
                timer=timer,
                name='crit',
                phase=AllPhase,
                value=0.03,
                bias_or_weight=0
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_debuff',
                phase=AirPhase,
                value=-0.1,
            )
        ]

# 工程局加成 驱逐公共
class EngineeringBureau_DD(Skill):
    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = TypeTarget(side=1, shiptype=BB)
        self.buff = [
            CommonBuff(
                timer=timer,
                name='torpedo',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='antisub',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='antiair',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='luck',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=TorpedoPhase,
                value=0.05
            )
        ]

# 工程局加成 导战公共
class EngineeringBureau_BBG(Skill):
    def __init__(self, timer):
        super().__init__(timer, master=None)
        self.target = TypeTarget(side=1, shiptype=BBG)
        self.buff = [
            CommonBuff(
                timer=timer,
                name='antiair',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CommonBuff(
                timer=timer,
                name='recon',
                phase=AllPhase,
                value=5,
                bias_or_weight=0
            ),
            CoeffBuff(
                timer=timer,
                name='crit',
                phase=AllPhase,
                value=0.03,
                bias_or_weight=0
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=FirstMissilePhase,
                value=0.05
            )
        ]

Other = [CollectionSkill_1,CollectionSkill_2,CollectionSkill_3,EngineeringBureau_BB,EngineeringBureau_DD]
# Other = []
