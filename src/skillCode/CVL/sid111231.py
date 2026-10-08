# -*- coding:utf-8 -*-
# Author:zzhh225
# Edited by: 银河远征(20260923)
# env:py38
# 博格改-1、追赶者改-1

from src.wsgr.skill import *
from src.wsgr.ship import *
from src.wsgr.phase import *

"""敌方潜艇命中值和回避值降低20点。
自身攻击威力提高15%，自身中破和大破时可以进行反潜攻击，对潜艇造成的伤害提高100%。"""


class Skill_111231_1(Skill):
    """敌方潜艇命中值和回避值降低20点。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = TypeTarget(side=0, shiptype=(SS, SC))
        self.buff = [
            StatusBuff(
                timer=timer,
                name='accuracy',
                phase=AllPhase,
                value=-20,
                bias_or_weight=0
            ),
            StatusBuff(
                timer=timer,
                name='evasion',
                phase=AllPhase,
                value=-20,
                bias_or_weight=0
            )
        ]


class Skill_111231_2(Skill):
    """自身攻击威力提高15%，对潜艇造成的伤害提高100%。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = [
            CoeffBuff(
                timer=timer,
                name='power_buff',
                phase=AllPhase,
                value=0.15,
                bias_or_weight=2
            ),
            FinalDamageBuff(
                timer=timer,
                name='final_damage_buff',
                phase=AllPhase,
                value=1,
                atk_request=[ATKRequest_1]
            )
        ]


class ATKRequest_1(ATKRequest):
    def __bool__(self):
        return isinstance(self.atk.target, (SS, SC))


class Skill_111231_3(CommonSkill):
    """自身中破和大破时可以进行反潜攻击。"""
    def __init__(self, timer, master):
        super().__init__(timer, master)
        self.target = SelfTarget(master)
        self.buff = []

    def activate(self, friend, enemy):
        """重构 CVL.get_act_indicator 和 CVL.act_phase_indicator
        让反潜相关的阶段行动判定放宽到 damaged < 4
        重构 CVL.raise_atk 和 CVL.raise_night_atk
        当 damaged = 2 or 3 时只执行反潜"""
        from types import MethodType

        def get_act_indicator(ship):
            from src.wsgr.phase import AntiSubPhase
            # 跳过阶段，优先级最高
            for tmp_buff in ship.temper_buff:
                if tmp_buff.name == 'not_act_phase' and tmp_buff.is_active():
                    return False

            # 可参与阶段
            for tmp_buff in ship.temper_buff:
                if tmp_buff.name == 'act_phase' and tmp_buff.is_active():
                    if isinstance(ship.timer.phase, AntiSubPhase):
                        return (ship.damaged < 4) and (ship.check_atk_plane())
                    else:
                        return (ship.damaged < 4) and (ship.check_atk_plane_load())

            # 默认行动模式
            phase_name = type(ship.timer.phase).__name__
            return ship.act_phase_indicator[phase_name](ship)

        def raise_atk(ship, target_fleet):
            # 中破/大破时只能反潜
            if ship.damaged in (2, 3):
                def_list = target_fleet.get_atk_target(atk_type=ship.anti_sub_atk)
                if len(def_list):
                    yield ship.anti_sub_atk(
                        timer=ship.timer,
                        source=ship,
                        def_list=def_list,
                    )
                return
            yield from type(ship).raise_atk(ship, target_fleet)

        def raise_night_atk(ship, target_fleet):
            # 夜战预留，与白天一致，中破/大破只进行夜战反潜
            if ship.damaged in (2, 3):
                night_anti_sub_atk = ship.night_anti_sub_atk
                if night_anti_sub_atk is not None:
                    def_list = target_fleet.get_atk_target(atk_type=night_anti_sub_atk)
                    if len(def_list):
                        yield night_anti_sub_atk(
                            timer=ship.timer,
                            source=ship,
                            def_list=def_list,
                        )
                return
            yield from type(ship).raise_night_atk(ship, target_fleet)

        self.master.act_phase_indicator.update({
            'AntiSubPhase': lambda x:
                (x.damaged < 4) and (x.check_atk_plane()) and (x.get_form() == 5),
            'FirstShellingPhase': lambda x:
                (x.damaged < 4) and (x.check_atk_plane_load()),
            'SecondShellingPhase': lambda x:
                (x.damaged < 4) and (x.check_atk_plane_load()) and (x.get_range() >= 3),
            'NightPhase': lambda x:
                (x.damaged < 4) and (x.check_atk_plane_load()),
        })
        self.master.get_act_indicator = MethodType(get_act_indicator, self.master)
        self.master.raise_atk         = MethodType(raise_atk, self.master)
        self.master.raise_night_atk   = MethodType(raise_night_atk, self.master)


name = '反潜护航'
skill = [Skill_111231_1, Skill_111231_2, Skill_111231_3]
