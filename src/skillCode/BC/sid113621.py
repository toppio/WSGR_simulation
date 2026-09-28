# -*- coding:utf-8 -*-
# Author:huan_yp
# Edited by: 银河远征(20260922)
# env:py38
# 星座-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""增加全队索敌值6点，增加全队大型船火力值、命中值和回避值12点。
自身优先攻击位置排在前方的敌方大型船。
首轮炮击阶段自身攻击大型船时无视目标装甲，伤害提高25%。
当列克星敦（CV-2）位于队伍中时，自身火力值、装甲值、命中值和回避值增加25点。"""


class Skill_113621_1(PrepSkill):
    """增加全队索敌值6点"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = Target(side=1)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='recon',
                phase=AllPhase,
                value=6,
                bias_or_weight=0,
            ),
        ]


class Skill_113621_2(Skill):
    """增加全队大型船火力值、命中值和回避值12点"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = TypeTarget(side=1, shiptype=LargeShip)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=12,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=12,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=12,
                bias_or_weight=0
            )
        ]


class Skill_113621_3(Skill):
    """自身优先攻击位置排在前方的敌方大型船。
    首轮炮击阶段自身攻击大型船时无视目标装甲，伤害提高25%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            PriorTargetBuff(
                timer=timer,
                name='prior_type_target',
                phase=AllPhase,
                target=TypeTarget(side=0, shiptype=LargeShip),
                ordered=True
            ),
            AtkBuff(
                timer=timer,
                name='ignore_armor',
                phase=FirstShellingPhase,
                value=-1,
                bias_or_weight=1,
                atk_request=[ATKRequest_1]
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=FirstShellingPhase,
                value=0.25,
                atk_request=[ATKRequest_1]
            )
        ]


class ATKRequest_1(ATKRequest):
    def __bool__(self):
        return isinstance(self.atk.target, LargeShip)


class Skill_113621_4(Skill):
    """当列克星敦（CV-2）位于队伍中时，自身火力值、装甲值、命中值和回避值增加25点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            StatusBuff(
                timer=timer,
                name='fire',
                phase=AllPhase,
                value=25,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='armor',
                phase=AllPhase,
                value=25,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=25,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=25,
                bias_or_weight=0
            )
        ]

    def is_active(self, friend, enemy):
        if isinstance(friend, Fleet):
            friend = friend.ship
        for tmp_ship in friend:
            # 列克星敦cv2 cid = 10029/11029
            if tmp_ship.cid == '10029' or tmp_ship.cid == '11029':
                return True
        return False


name = '特遣先锋'
skill = [Skill_113621_1, Skill_113621_2, Skill_113621_3, Skill_113621_4]
