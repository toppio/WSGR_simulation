# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38
# 舰船类

import numpy as np

from src.wsgr.wsgrTimer import Time
from src.wsgr.equipment import *


class Ship(Time):
    """舰船总类"""

    def __init__(self, timer):
        super().__init__(timer)
        self.master = None
        self.cid = '0'          # 编号
        self.type = None        # 船型
        self.size = None        # 量级，大中小型船
        self.function = None    # 功能，主力、护卫舰
        self.status = {
            'name': None,       # 船名
            'country': None,    # 国籍
            'total_health': 0,  # 总耐久
            'health': 0,        # 当前耐久
            'fire': 0,          # 火力
            'torpedo': 0,       # 鱼雷
            'armor': 0,         # 装甲
            'antiair': 0,       # 对空
            'antisub': 0,       # 对潜
            'accuracy': 0,      # 命中
            'evasion': 0,       # 回避
            'recon': 0,         # 索敌
            'speed': 0,         # 航速
            'range': 0,         # 射程, 1: 短; 2: 中; 3: 长; 4: 超长
            'luck': 0,          # 幸运
            'capacity': 0,      # 搭载
            'tag': '',          # 标签(特驱、z系等)
            'supply_oil': 0,    # 补给油耗
            'supply_ammo': 0,   # 补给弹耗
            'repair_oil': 0,    # 修理油耗
            'repair_steel': 0,  # 修理钢耗
        }

        self._skill = []        # 技能(未实例化)
        self.skill = []         # 技能
        self.equipment = []     # 装备
        self.load = []          # 搭载
        self.strategy = []      # 战术

        self.side = 0  # 敌我识别; 1: 友方; 0: 敌方
        self.loc = 0  # 站位, 1-6
        self.level = 110  # 等级
        self.affection = 50  # 好感

        self.created_damage = {}  # 造成伤害记录，分阶段，在下一点开始时重置
        self.got_damage = 0  # 受到伤害记录，只有总数，在下一点开始时重置
        self.damaged = 1  # 耐久状态, 1: 正常; 2: 中破; 3: 大破; 4: 撤退，修理后重置
        self.damage_protect = True  # 耐久保护，大破进击时消失，在所有战斗结束后重置
        self.supply_oil = 1.  # 燃料补给状态，在所有战斗结束后重置
        self.supply_ammo = 1.  # 弹药补给状态，在所有战斗结束后重置

        self.common_buff = []  # 永久面板加成
        self.temper_buff = []  # 临时buff
        self.active_buff = []  # 主动技能buff
        self.strategy_buff = {}  # 战术buff

        self.act_phase_flag = {
            'AirPhase': False,
            'FirstMissilePhase': False,
            'AntiSubPhase': False,
            'FirstTorpedoPhase': False,
            'FirstShellingPhase': True,
            'SecondShellingPhase': True,
            'SecondTorpedoPhase': True,
            'SecondMissilePhase': False,
            'NightPhase': True,
        }  # 可参与阶段

        self.act_phase_indicator = {
            'AirPhase': lambda x: False,
            'FirstMissilePhase': lambda x: False,
            'AntiSubPhase': lambda x: False,
            'FirstTorpedoPhase': lambda x:
                (x.level > 10) and (x.damaged < 3),
            'FirstShellingPhase': lambda x: x.damaged < 4,
            'SecondShellingPhase': lambda x:
                (x.get_range() >= 3) and (x.damaged < 4),
            'SecondTorpedoPhase': lambda x:
                (x.damaged < 3) and (x.get_final_status('torpedo') > 0),
            'SecondMissilePhase': lambda x: False,
            'NightPhase': lambda x: x.damaged < 3,
        }  # 可行动标准

        from src.wsgr.formulas import NormalAtk, NightNormalAtk
        self.normal_atk = NormalAtk  # 普通炮击
        self.anti_sub_atk = None  # 反潜攻击
        self.night_atk = NightNormalAtk  # 夜战普通炮击
        self.night_anti_sub_atk = None  # 夜战反潜攻击

    def __eq__(self, other):
        return self.cid == other.cid and \
               self.loc == other.loc and \
               self.side == other.side

    def __ne__(self, other):
        return self.cid != other.cid or \
               self.loc != other.loc or \
               self.side != other.side

    def __repr__(self):
        damage = ['未定义', '正常', '中破', '大破', '撤退']
        return f"{type(self).__name__}: {self.status['name']}, 状态: {damage[self.damaged]}"

    def set_master(self, master):
        self.master = master

    def get_form(self):
        """阵型
        1: 单纵; 2: 复纵; 3: 轮形; 4: 梯形; 5: 单横"""
        return self.master.form

    def get_recon_flag(self):
        """索敌"""
        if self.timer.recon_flag is None:
            raise ValueError('Recon flag not defined!')
        if self.side:
            return self.timer.recon_flag
        else:
            return False

    def get_dir_flag(self):
        """航向, 优同反劣分别为1-4"""
        if self.timer.direction_flag is None:
            raise ValueError('Direction flag not defined!')
        if self.side:
            return self.timer.direction_flag
        else:
            return 5 - self.timer.direction_flag

    def get_air_con_flag(self):
        """制空结果, 从空确到空丧分别为1-5"""
        if self.timer.air_con_flag is None:
            raise ValueError('Air control flag not defined!')
        if self.side:
            return self.timer.air_con_flag
        else:
            return 6 - self.timer.air_con_flag

    def set_cid(self, cid):
        """设置舰船编号"""
        self.cid = cid

    def set_side(self, side):
        """敌我判断"""
        self.side = side

    def set_loc(self, loc):
        """设置舰船站位"""
        self.loc = loc

    def set_level(self, level):
        """设置舰船等级"""
        self.level = level

    def set_affection(self, affection):
        """设置舰船好感度"""
        self.affection = affection

    def get_affection(self):
        """获取舰船好感度"""
        if self.side == 0:
            return 50
        if self.cid[0] != 1:
            return 50
        return self.affection

    def set_equipment(self, equipment):
        """设置舰船装备"""
        if isinstance(equipment, list):
            self.equipment = equipment
        else:
            self.equipment.append(equipment)

    def set_load(self, load):
        if isinstance(load, list):
            self.load = load
        else:
            raise AttributeError(f"'load' should be list, got {type(load)} instead.")

    def add_skill(self, skill):
        """设置舰船技能(未实例化)"""
        self._skill.extend(skill)

    def add_strategy(self, strategy):
        """增加战术技能(已实例化)"""
        self.strategy.append(strategy)

    def init_skill(self, friend, enemy):
        """舰船技能实例化，并结算常驻面板技能和战术"""
        self.skill = []
        for skill in self._skill[:]:
            tmp_skill = skill(self.timer, self)
            if tmp_skill.is_common():  # 常驻面板技能，仅初始化一次，后续不再处理
                tmp_skill.activate(friend, enemy)
                self._skill.remove(skill)
            elif tmp_skill.is_end_skill():
                self.timer.end_skill.append(tmp_skill)
            else:
                self.skill.append(tmp_skill)

        # 装备技能
        for tmp_equip in self.equipment:
            e_skill, e_value = tmp_equip.get_skill()
            if len(e_skill):
                # assert len(e_skill) == 1
                # tmp_skill = e_skill[0](self.timer, self, e_value)
                # self.skill.append(tmp_skill)
                for i in range(len(e_skill)):
                    tmp_skill = e_skill[i](self.timer, self, e_value)
                    self.skill.append(tmp_skill)

        # 战术
        self.strategy_buff = {}
        for tmp_strategy in self.strategy:
            tmp_strategy.activate(friend, enemy)

    def init_health(self):
        """初始化血量"""
        # standard_health 血量战损状态计算标准
        self.status['standard_health'] = self.status['total_health']
        for tmp_buff in self.common_buff:
            if tmp_buff.name == 'health':
                self.status['standard_health'] += tmp_buff.value
        self.status['standard_health'] += self.get_equip_status('health')
        self.status['health'] = self.status['standard_health']

    def init_supply(self):
        """初始化补给"""
        self.supply_ammo += self.get_strategy_value('strategy_ammo')

    def get_raw_skill(self):
        """获取技能，让巴尔可调用"""
        return self._skill[:]

    def run_prepare_skill(self, friend, enemy):
        """结算准备阶段技能，让巴尔技能可用"""
        for tmp_skill in self.skill:
            if tmp_skill.is_prep() and \
                    tmp_skill.is_active(friend, enemy):
                tmp_skill.activate(friend, enemy)

    def run_raw_prepare_skill(self, friend, enemy):
        """结算准备阶段技能，让巴尔技能不可用"""
        for tmp_skill in self.skill:
            # 跳过让巴尔偷取技能
            if tmp_skill.request is None and \
                    tmp_skill.target is None and \
                    tmp_skill.buff is None:
                continue

            if tmp_skill.is_prep() and \
                    tmp_skill.is_active(friend, enemy):
                tmp_skill.activate(friend, enemy)

    def run_normal_skill(self, friend, enemy):
        """结算普通技能"""
        for tmp_skill in self.skill:
            if not tmp_skill.is_prep() and \
                    tmp_skill.is_active(friend, enemy):
                tmp_skill.activate(friend, enemy)

    def run_strategy(self):
        """结算战术效果"""
        self.temper_buff.extend(list(self.strategy_buff.values()))

    def set_status(self, name=None, value=None, status=None):
        """根据属性名称设置本体属性"""
        if status is None:
            if (name is not None) and (value is not None):
                self.status[name] = value
            else:
                raise ValueError("'name', 'value' and 'status' should not be all None!")
        else:
            if isinstance(status, dict):
                self.status = status
            else:
                raise AttributeError(f"'status' should be dict, got {type(status)} instead.")

    def get_status(self, name):
        """根据属性名称获取本体属性，包含常驻面板加成"""
        status = self.status.get(name, 0)
        if isinstance(status, str):  # 国籍、名称、tag等，直接返回
            return status

        scale_add = 0
        scale_mult = 1
        bias = 0
        for tmp_buff in self.common_buff:
            if tmp_buff.name == name:
                if tmp_buff.bias_or_weight == 0:
                    bias += tmp_buff.value
                elif tmp_buff.bias_or_weight == 1:
                    scale_add += tmp_buff.value
                # elif tmp_buff.bias_or_weight == 2:
                #     scale_mult *= (1 + tmp_buff.value)
                # else:
                #     pass

        # 好感补正(重置后变更至命中率公式计算)
        # if name in ['accuracy', 'evasion'] and self.side == 1:
        #     scale_mult *= 1 + self.affection * 0.001

        status = status * (1 + scale_add) * scale_mult + bias
        return max(0, status)

    def get_equip_status(self, name, equiptype=None):
        """根据属性名称获取装备属性"""
        status = 0
        for tmp_equip in self.equipment:
            if (equiptype is None) or isinstance(tmp_equip, equiptype):
                status += tmp_equip.get_final_status(name)
        return status

    def get_final_status(self, name, equip=True):
        """根据属性名称获取属性总和"""
        buff_scale_1, buff_scale_2, buff_bias = self.get_buff(name)
        status = self.get_status(name) * (1 + buff_scale_1)

        if equip and name != 'speed':
            status += self.get_equip_status(name)

        status = status * buff_scale_2 + buff_bias

        return max(0, status)

    def get_range(self):
        """获取射程(本体、装备、buff中取最大值)"""
        ship_range = self.status['range']

        for tmp_buff in self.common_buff:
            if tmp_buff.name == 'range' and tmp_buff.is_active():
                tmp_range = tmp_buff.value
                ship_range = max(ship_range, tmp_range)
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'range' and tmp_buff.is_active():
                tmp_range = tmp_buff.value
                ship_range = max(ship_range, tmp_range)
        for tmp_equip in self.equipment:
            equip_range = tmp_equip.get_range()
            ship_range = max(ship_range, equip_range)

        return ship_range

    def add_buff(self, buff):
        """分类添加增益"""
        buff.set_master(self)
        if buff.is_common():
            self.common_buff.append(buff)

        elif buff.is_active_buff():
            self.active_buff.append(buff)

        elif buff.is_event():
            self.timer.queue_append(buff)

        elif buff.is_unique_effect():  # 唯一效果(技能不叠加效果、装备特效)
            buff_type = buff.effect_type

            # 2类不叠加(2类为舰船技能，标注为多个单位携带此技能不重复生效)
            # 注意2类每个buff标识数字各不相同
            if 2 <= buff_type < 3:
                type2 = self.get_unique_effect(effect_type=buff_type)
                if type2 is not None:  # 有相同特效，跳过
                    return

            # 3和4类不叠加
            elif buff_type in [3, 4]:
                type34 = self.get_unique_effect(effect_type=buff_type)

                # 特效类型相同，取最高值
                if type34 is not None:
                    value1 = buff.value
                    value2 = type34.value
                    type34.set_value(max(value1, value2))
                    return

            self.temper_buff.append(buff)

        else:
            self.temper_buff.append(buff)
            aaa = 1

    def add_strategy_buff(self, buff, stid):
        """增加战术效果"""
        if stid not in self.strategy_buff.keys():
            self.strategy_buff[stid] = buff

    def get_buff(self, name, *args, **kwargs):
        """根据增益名称获取全部属性增益(分别统计加法系数、乘法系数、数值增益)"""
        scale_add = 0
        scale_mult = 1
        bias = 0
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == name and tmp_buff.is_active(*args, **kwargs):
                if tmp_buff.bias_or_weight == 0:
                    bias += tmp_buff.value
                elif tmp_buff.bias_or_weight == 1:
                    scale_add += tmp_buff.value
                elif tmp_buff.bias_or_weight == 2:
                    scale_mult *= (1 + tmp_buff.value)

        for tmp_buff in self.common_buff:
            if tmp_buff.name == name and tmp_buff.bias_or_weight == 2:
                scale_mult *= (1 + tmp_buff.value)

        bias += self.get_strategy_value(name, *args, **kwargs)

        return scale_add, scale_mult, bias  # 先scale后bias

    def get_atk_buff(self, name, atk, *args, **kwargs):
        """根据增益名称获取全部攻击系数增益(含攻击判断)"""
        scale_add = 0
        scale_mult = 1
        bias = 0
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == name and tmp_buff.is_active(atk=atk, *args, **kwargs):
                if tmp_buff.bias_or_weight == 0:
                    bias += tmp_buff.value
                elif tmp_buff.bias_or_weight == 1:
                    scale_add += tmp_buff.value
                elif tmp_buff.bias_or_weight == 2:
                    scale_mult *= (1 + tmp_buff.value)

        bias += self.get_strategy_value(name, atk, *args, **kwargs)

        return (1 + scale_add) * scale_mult - 1, bias  # 先scale后bias

    def atk_coef_process(self, atk, *args, **kwargs):
        for tmp_buff in self.temper_buff:
            if not tmp_buff.is_coef_process():
                continue
            if tmp_buff.is_active(atk=atk, *args, **kwargs):
                atk.set_coef({tmp_buff.name: tmp_buff.value})

    def get_special_buff(self, name, *args, **kwargs):
        """查询机制增益"""
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == name:
                if tmp_buff.is_active(*args, **kwargs):
                    tmp_buff.activate(*args, **kwargs)
                    return True
        return False

    def get_strategy_buff(self, name, *args, **kwargs):
        """查询战术增益"""
        for tmp_buff in self.strategy_buff.values():
            if tmp_buff.name == name:
                if tmp_buff.is_active(*args, **kwargs):
                    return True
        return False

    def get_strategy_value(self, name, *args, **kwargs):
        """查询战术数值"""
        for tmp_buff in self.strategy_buff.values():
            if tmp_buff.name == name and tmp_buff.is_active(*args, **kwargs):
                return tmp_buff.value
        return 0

    def get_unique_effect(self, effect_type):
        if not isinstance(effect_type, list):
            effect_type = [effect_type]

        for tmp_buff in self.temper_buff:
            if tmp_buff.is_unique_effect():
                if tmp_buff.effect_type in effect_type:
                    return tmp_buff
        return None

    def get_final_damage_buff(self, atk):
        """根据攻击类型决定终伤加成"""
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'final_damage_buff' and \
                    tmp_buff.is_active(atk=atk):
                yield tmp_buff.value

    def get_final_damage_debuff(self, atk):
        """根据攻击类型决定终伤减伤加成"""
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'final_damage_debuff' and \
                    tmp_buff.is_active(atk=atk):
                yield tmp_buff.value

    def get_act_flag(self):
        # 可参与阶段，优先级最高
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'act_phase' and tmp_buff.is_active():
                return True

        # 默认行动模式
        phase_name = type(self.timer.phase).__name__
        return self.act_phase_flag[phase_name]

    def get_act_indicator(self):
        """判断舰船在指定阶段内能否行动"""
        # 跳过阶段，优先级最高
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'not_act_phase' and tmp_buff.is_active():
                return False

        # 可参与阶段(不用检测，如果判断条件与默认行动模式不同，则重新定义)
        # for tmp_buff in self.temper_buff:
        #     if tmp_buff.name == 'act_phase' and tmp_buff.is_active():
        #         return True

        # 默认行动模式
        phase_name = type(self.timer.phase).__name__
        return self.act_phase_indicator[phase_name](self)

    def raise_atk(self, target_fleet):
        """
        判断炮击战攻击类型
        :param target_fleet: Fleet
        """
        # 技能限制无法进行普通攻击
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'no_normal_atk' and tmp_buff.is_active():
                return []

        # 技能发动特殊攻击
        for tmp_buff in self.active_buff:
            if tmp_buff.is_active(atk=self.normal_atk, enemy=target_fleet):
                return tmp_buff.active_start(atk=self.normal_atk, enemy=target_fleet)

        # 技能优先攻击特定船型
        prior = self.get_prior_type_target(target_fleet)
        if prior is not None:
            atk = self.normal_atk(
                timer=self.timer,
                atk_body=self,
                def_list=prior,
            )
            return [atk]

        # 优先反潜
        if self.anti_sub_atk is not None:
            def_list = target_fleet.get_atk_target(atk_type=self.anti_sub_atk)
            if len(def_list):
                atk = self.anti_sub_atk(
                    timer=self.timer,
                    atk_body=self,
                    def_list=def_list,
                )
                return [atk]

        # 常规攻击模式
        def_list = target_fleet.get_atk_target(atk_type=self.normal_atk)
        if not len(def_list):
            return []

        atk = self.normal_atk(
            timer=self.timer,
            atk_body=self,
            def_list=def_list,
        )
        return [atk]

    def raise_night_atk(self, target_fleet):
        """
        夜间攻击模式
        :param target_fleet: Fleet"""
        # CA/CL/CAV确认火雷攻击方式
        # 夜战导弹舰攻击
        from src.wsgr.formulas import NightMissileAtk

        self.check_night_atk_type()

        # 技能发动特殊攻击
        for tmp_buff in self.active_buff:
            if tmp_buff.is_active(atk=self.night_atk, enemy=target_fleet):
                return tmp_buff.active_start(atk=self.night_atk, enemy=target_fleet)

        # 技能优先攻击特定船型
        prior = self.get_prior_type_target(target_fleet)
        if prior is not None:
            if issubclass(self.night_atk, NightMissileAtk):
                return self.raise_night_missile_atk(target_fleet)

            atk = self.night_atk(
                timer=self.timer,
                atk_body=self,
                def_list=prior,
            )
            return [atk]

        # 优先反潜
        if self.night_anti_sub_atk is not None:
            def_list = target_fleet.get_atk_target(atk_type=self.night_anti_sub_atk)
            if len(def_list):
                atk = self.night_anti_sub_atk(
                    timer=self.timer,
                    atk_body=self,
                    def_list=def_list,
                )
                return [atk]

        # 夜战导弹舰攻击
        if issubclass(self.night_atk, NightMissileAtk):
            return self.raise_night_missile_atk(target_fleet)

        # 常规攻击模式
        def_list = target_fleet.get_atk_target(atk_type=self.night_atk)
        if not len(def_list):
            return []

        atk = self.night_atk(
            timer=self.timer,
            atk_body=self,
            def_list=def_list,
        )
        return [atk]

    def raise_night_missile_atk(self, target_fleet):
        raise UserWarning(f'Wrong call of missile attack from {self.status["name"]}!')

    def check_night_atk_type(self):
        from src.wsgr.formulas import NightFirelAtk, NightFireTorpedolAtk
        if isinstance(self, (CA, CL, CAV)):
            if self.status['torpedo'] == 0:
                self.night_atk = NightFirelAtk
            else:
                self.night_atk = NightFireTorpedolAtk

    # def get_atk_type(self, target):  # 备用接口
    #     """判断攻击该对象时使用什么攻击类型"""
    #     pass

    def can_be_atk(self, atk):
        """判断舰船是否可被某攻击类型指定"""
        from src.wsgr.formulas import AntiSubAtk
        if issubclass(atk, AntiSubAtk):
            return False
        return self.damaged < 4

    def get_prior_type_target(self, fleet, *args, **kwargs):
        """获取指定列表可被自身优先攻击船型的目标"""
        if isinstance(fleet, Fleet):
            fleet = fleet.ship
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'prior_type_target' and \
                    tmp_buff.is_active(*args, **kwargs):
                return tmp_buff.activate(fleet)

    def get_prior_loc_target(self, fleet, *args, **kwargs):
        """获取指定列表可被自身优先攻击站位的目标"""
        if isinstance(fleet, Fleet):
            fleet = fleet.ship
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'prior_loc_target' and \
                    tmp_buff.is_active(*args, **kwargs):
                return tmp_buff.activate(fleet)

    def atk_hit(self, name, atk, *args, **kwargs):
        """处理命中后、被命中后添加buff效果（含反击）"""
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == name and \
                    tmp_buff.is_active(atk=atk, *args, **kwargs):
                tmp_buff.activate(atk=atk, *args, **kwargs)

        if name == 'atk_be_hit':
            for tmp_buff in self.temper_buff:
                if tmp_buff.name == 'hit_back' and \
                        tmp_buff.is_active(atk=atk, *args, **kwargs):
                    return tmp_buff.activate(atk=atk, *args, **kwargs)

            strategy_hit_back = self.strategy_buff.get('231')
            if strategy_hit_back is not None:
                if strategy_hit_back.is_active(atk=atk, *args, **kwargs):
                    return strategy_hit_back.activate(atk=atk, *args, **kwargs)

    def get_damage(self, damage):
        """受伤结算，过伤害保护，需要返回受伤与否"""
        from src.wsgr.phase import AntiSubPhase, ShellingPhase, NightPhase
        if isinstance(self.timer.phase, (AntiSubPhase, ShellingPhase, NightPhase)) \
                and self.damaged == 4:
            raise SyntaxError(f"{type(self.timer.phase).__name__}: 已击沉船只受到攻击! "
                              f"{self.timer.atk.atk_body.status['name']} -> "
                              f"{self.timer.atk.target.status['name']}")

        standard_health = self.status['standard_health']

        # 敌方没有伤害保护，大破进击没有伤害保护
        if self.side == 0 or \
                not self.damage_protect or \
                self.damaged == 4:
            pass

        # 友方大破时受伤, 非大破进击
        elif self.damaged == 3:
            if self.status['health'] == 1:  # 剩余血量为1，强制miss
                damage = 0
            else:
                damage = np.ceil(self.status['health'] * 0.1)

        # 如果血量刚好在中保线，变为大破保护
        elif self.status['health'] == standard_health * 0.25:
            if self.status['health'] == 1:  # 剩余血量为1，强制miss
                damage = 0
            else:
                damage = np.ceil(self.status['health'] * 0.1)

        # 友方非大破状态下，受到足以大破的伤害
        elif self.status['health'] - damage < standard_health * 0.25:
            # 满血保护
            if self.status['health'] == standard_health:
                damage = np.ceil(standard_health * np.random.uniform(0.5, 0.75))

            # 否则只有中破保护
            else:
                damage = np.ceil(self.status['health'] - standard_health * 0.25)

        self.status['health'] -= int(damage)
        self.got_damage += int(damage)

        # 受伤状态结算
        if self.status['health'] <= 0:
            if self.use_dcitem():  # 检测能否损管
                self.status['health'] = standard_health
            else:
                self.status['health'] = 0
                self.damaged = 4
        elif self.damaged < 3 and \
                self.status['health'] < standard_health * 0.25:
            self.damaged = 3
        elif self.damaged < 2 and \
                self.status['health'] < standard_health * 0.5:
            self.damaged = 2

        return damage

    def create_damage(self, damage):
        """造成伤害记录"""
        phase = type(self.timer.phase).__name__
        if phase in self.created_damage.keys():
            self.created_damage[phase] += damage
        else:
            self.created_damage[phase] = damage

    def use_dcitem(self):
        """检测能否损管"""
        if self.side == 1:  # 友方可损管
            self.timer.log['dcitem'] += 1
            return True

        elif self.get_special_buff('damage_control'):  # 深海需要检查技能
            return True

        else:
            return False

    def remove_during_buff(self):
        """去除攻击期间的临时buff"""
        # i = 0
        # while i < len(self.temper_buff):
        #     tmp_buff = self.temper_buff[i]
        #     if tmp_buff.is_during_buff():
        #         self.temper_buff.remove(tmp_buff)
        #         continue
        #     else:
        #         i += 1

        tmp_buff_list = [tmp_buff for tmp_buff in self.temper_buff
                         if not tmp_buff.is_during_buff()]
        self.temper_buff = tmp_buff_list

    def reinit_health(self):
        """战斗中更新血量状态"""
        # 大破进击取消保护
        if self.damaged >= 3:
            self.damage_protect = False
        self.got_damage = 0

    def clear_buff(self):
        """清空临时buff"""
        self.temper_buff = []
        self.active_buff = []
        for equip in self.equipment:
            equip.clear_buff()

    def reinit(self):
        """道中初始化舰船状态"""
        self.clear_buff()
        self.created_damage = {}
        self.reinit_health()

    def reset(self):
        """初始化当前舰船"""
        self.clear_buff()
        self.created_damage = {}
        supply = {'oil': 0, 'ammo': 0, 'steel': 0, 'almn': 0}

        # 统计补给耗油并补满
        supply['oil'] += np.ceil((1 - self.supply_oil) * self.status['supply_oil'])
        self.supply_oil = 1

        # 统计补给耗弹并补满
        strategy_ammo = self.get_strategy_value('strategy_ammo')
        supply['ammo'] += np.ceil((1 + strategy_ammo - self.supply_ammo) * self.status['supply_ammo'])
        self.supply_ammo = 1 + strategy_ammo

        # 统计修理费用并恢复血量
        got_damage = self.status['standard_health'] - self.status['health']
        supply['oil'] += np.ceil(got_damage * self.status['repair_oil'])
        supply['steel'] += np.ceil(got_damage * self.status['repair_steel'])
        self.status['health'] = self.status['standard_health']
        self.got_damage = 0
        self.damaged = 1
        self.damage_protect = True

        # 统计铝耗并补满
        if len(self.load):
            for i in range(len(self.equipment)):
                tmp_equip = self.equipment[i]
                if isinstance(tmp_equip, (Plane, Missile)):
                    supply_num = self.load[i] - tmp_equip.load
                    supply['almn'] += supply_num * tmp_equip.status['supply_almn']
                    tmp_equip.load = self.load[i]
        return supply


class LargeShip(Ship):
    """大型船总类"""

    def __init__(self, timer):
        super().__init__(timer)
        self.size = 3  # 船型


class MidShip(Ship):
    """中型船总类"""

    def __init__(self, timer):
        super().__init__(timer)
        self.size = 2  # 船型


class SmallShip(Ship):
    """小型船总类"""

    def __init__(self, timer):
        super().__init__(timer)
        self.size = 1  # 船型


class MainShip(Ship):
    """主力舰总类"""

    def __init__(self, timer):
        super().__init__(timer)
        self.function = 'main'


class CoverShip(Ship):
    """护卫舰总类"""

    def __init__(self, timer):
        super().__init__(timer)
        self.function = 'cover'


class Submarine(Ship):
    """水下单位"""
    def __init__(self, timer):
        super().__init__(timer)

        from src.wsgr.formulas import NightTorpedoAtk
        self.night_atk = NightTorpedoAtk  # 夜战普通炮击

    def can_be_atk(self, atk):
        from src.wsgr.formulas import AntiSubAtk
        if issubclass(atk, AntiSubAtk):
            return self.damaged < 4
        else:
            return False


class SS(Submarine, SmallShip, CoverShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'SS'

        self.act_phase_flag.update({
            'FirstTorpedoPhase': True,
            'FirstShellingPhase': False,
            'SecondShellingPhase': False,
        })


class SC(Submarine, SmallShip, CoverShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'SC'


class AntiSubShip(Ship):
    """反潜船"""
    def __init__(self, timer):
        super().__init__(timer)
        self.act_phase_flag.update({'AntiSubPhase': True})

        self.act_phase_indicator.update({
            'AntiSubPhase': lambda x:
                (x.get_form() == 5) and (x.damaged < 4),
        })

        from src.wsgr.formulas import AntiSubAtk, NightAntiSubAtk
        self.anti_sub_atk = AntiSubAtk  # 反潜攻击
        self.night_anti_sub_atk = NightAntiSubAtk  # 夜战反潜攻击


class Aircraft(Ship):
    """航系单位(所有可参与航空战攻击的单位)"""

    def __init__(self, timer):
        super().__init__(timer)
        self.flightparam = 0
        self.act_phase_flag.update({'AirPhase': True})
        self.act_phase_indicator.update({'AirPhase': lambda x: x.damaged < 3})

    def check_atk_plane(self):
        """检查攻击型飞机是否有载量"""
        for tmp_equip in self.equipment:
            if isinstance(tmp_equip, (Bomber, DiveBomber)):
                if tmp_equip.load > 0:
                    return True
        return False


class CV(Aircraft, LargeShip, MainShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'CV'
        self.flightparam = 5

        self.act_phase_flag.update({
            'AirPhase': True,
            'SecondTorpedoPhase': False,
            'NightPhase': False,
        })

        self.act_phase_indicator.update({
            'AirPhase': lambda x: x.damaged < 3,
            'FirstShellingPhase': lambda x:
                (x.damaged < 2) and (x.check_atk_plane()),
            'SecondShellingPhase': lambda x:
                (x.damaged < 2) and (x.check_atk_plane()) and (x.get_range() >= 3),
        })

        from src.wsgr.formulas import AirNormalAtk
        self.normal_atk = AirNormalAtk  # 炮击战航空攻击

    def get_act_indicator(self):
        # 跳过阶段，优先级最高
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'not_act_phase' and tmp_buff.is_active():
                return False

        # 可参与阶段
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'act_phase' and tmp_buff.is_active():
                return (self.damaged < 2) and (self.check_atk_plane())

        # 默认行动模式
        phase_name = type(self.timer.phase).__name__
        return self.act_phase_indicator[phase_name](self)


class CVL(Aircraft, AntiSubShip, MidShip, CoverShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'CVL'
        self.flightparam = 5

        self.act_phase_flag.update({
            'AirPhase': True,
            'AntiSubPhase': True,
            'SecondTorpedoPhase': False,
            'NightPhase': False,
        })

        self.act_phase_indicator.update({
            'AirPhase': lambda x: x.damaged < 3,
            'AntiSubPhase': lambda x:
                (x.damaged < 2) and (x.check_atk_plane()) and (x.get_form() == 5),
            'FirstShellingPhase': lambda x: x.damaged < 2,
            'SecondShellingPhase': lambda x:
                (x.damaged < 2) and (x.check_atk_plane()) and (x.get_range() >= 3),
        })

        from src.wsgr.formulas import AirNormalAtk, AirAntiSubAtk
        self.normal_atk = AirNormalAtk  # 炮击战航空攻击
        self.anti_sub_atk = AirAntiSubAtk  # 反潜攻击

    def get_act_indicator(self):
        # 跳过阶段，优先级最高
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'not_act_phase' and tmp_buff.is_active():
                return False

        # 可参与阶段
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'act_phase' and tmp_buff.is_active():
                return (self.damaged < 2) and (self.check_atk_plane())

        # 默认行动模式
        phase_name = type(self.timer.phase).__name__
        return self.act_phase_indicator[phase_name](self)


class AV(Aircraft, LargeShip, MainShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'AV'
        self.flightparam = 5

        self.act_phase_flag.update({
            'AirPhase': True,
            'SecondTorpedoPhase': False,
            'NightPhase': False,
        })

        self.act_phase_indicator.update({
            'AirPhase': lambda x: x.damaged < 3,
            'FirstShellingPhase': lambda x:
                (x.damaged < 3) and (x.check_atk_plane()),
            'SecondShellingPhase': lambda x:
                (x.damaged < 3) and (x.check_atk_plane()) and (x.get_range() >= 3),
        })

        from src.wsgr.formulas import AirNormalAtk
        self.normal_atk = AirNormalAtk  # 炮击战航空攻击

    def get_act_indicator(self):
        # 跳过阶段，优先级最高
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'not_act_phase' and tmp_buff.is_active():
                return False

        # 可参与阶段
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'act_phase' and tmp_buff.is_active():
                return (self.damaged < 3) and (self.check_atk_plane())

        # 默认行动模式
        phase_name = type(self.timer.phase).__name__
        return self.act_phase_indicator[phase_name](self)


class BB(LargeShip, MainShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'BB'


class BC(LargeShip, MainShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'BC'


class BBV(Aircraft, LargeShip, MainShip):
    """航战"""
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'BBV'
        self.flightparam = 10

        self.act_phase_flag.update({
            'SecondTorpedoPhase': False,
        })

        self.act_phase_indicator.update({
            'SecondShellingPhase': lambda x:
                (x.get_range() >= 3) and (x.damaged < 3),
        })

        from src.wsgr.formulas import AirAntiSubAtk
        self.anti_sub_atk = AirAntiSubAtk  # 反潜攻击

    def raise_atk(self, target_fleet):
        from src.wsgr.phase import SecondShellingPhase

        # 技能限制无法进行普通攻击
        for tmp_buff in self.temper_buff:
            if tmp_buff.name == 'no_normal_atk' and tmp_buff.is_active():
                return []

        # 技能发动特殊攻击
        for tmp_buff in self.active_buff:
            if tmp_buff.is_active(atk=self.normal_atk, enemy=target_fleet):
                return tmp_buff.active_start(atk=self.normal_atk, enemy=target_fleet)

        # 技能优先攻击特定船型
        prior = self.get_prior_type_target(target_fleet)
        if prior is not None:
            atk = self.normal_atk(
                timer=self.timer,
                atk_body=self,
                def_list=prior,
            )
            return [atk]

        # 次轮炮击优先反潜
        if isinstance(self.timer.phase, SecondShellingPhase) \
                and self.damaged == 1 \
                and self.check_antisub_plane():
            def_list = target_fleet.get_atk_target(atk_type=self.anti_sub_atk)
            if len(def_list):
                atk = self.anti_sub_atk(
                    timer=self.timer,
                    atk_body=self,
                    def_list=def_list,
                )
                return [atk]

        # 常规攻击模式
        def_list = target_fleet.get_atk_target(atk_type=self.normal_atk)
        if not len(def_list):
            return []

        atk = self.normal_atk(
            timer=self.timer,
            atk_body=self,
            def_list=def_list,
        )
        return [atk]

    def check_antisub_plane(self):
        """检查是否携带反潜飞机"""
        for tmp_equip in self.equipment:
            if isinstance(tmp_equip, (Plane, ScoutPlane)):
                if tmp_equip.get_final_status('antisub') > 0:
                    return True
        return False


class BBV0(BBV):
    """深海航战"""
    def __init__(self, timer):
        super().__init__(timer)
        from src.wsgr.formulas import NightFireTorpedolAtk
        self.night_atk = NightFireTorpedolAtk


class CAV(Aircraft, AntiSubShip, MidShip, CoverShip):
    """航巡"""
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'CAV'
        self.flightparam = 10


class CA(MidShip, CoverShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'CA'


class CL(AntiSubShip, MidShip, CoverShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'CL'


class CLT(MidShip, CoverShip):
    """雷巡"""
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'CLT'

        from src.wsgr.formulas import AntiSubAtk, NightTorpedoAtk, NightAntiSubAtk
        self.anti_sub_atk = AntiSubAtk  # 反潜攻击
        self.night_atk = NightTorpedoAtk  # 夜战普通炮击
        self.night_anti_sub_atk = NightAntiSubAtk  # 夜战反潜攻击


class CLT0(CLT):
    """深海雷巡"""
    def __init__(self, timer):
        super().__init__(timer)
        self.act_phase_flag.update({
            'FirstTorpedoPhase': True,
        })


class DD(AntiSubShip, SmallShip, CoverShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'DD'

        from src.wsgr.formulas import NightTorpedoAtk
        self.night_atk = NightTorpedoAtk  # 夜战普通炮击


class BM(SmallShip, CoverShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'BM'


class AP(SmallShip, CoverShip):
    """补给"""
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'AP'

        self.act_phase_flag.update({
            'NightPhase': False,
        })


class MissileShip(Ship):
    """导弹船"""
    def __init__(self, timer):
        super().__init__(timer)
        from src.wsgr.formulas import NightMissileAtk
        self.night_atk = NightMissileAtk

    def check_missile(self):
        """检查导弹装备是否有载量、是否有发射器"""

        # 检查是否有发射器
        launcher_flag = False
        for tmp_equip in self.equipment:
            if isinstance(tmp_equip, Launcher):
                launcher_flag = True
        if not launcher_flag:
            return False

        # 检查导弹装备是否有载量
        for tmp_equip in self.equipment:
            if isinstance(tmp_equip, Missile) and tmp_equip.load > 0:
                return True
        return False

    def raise_night_missile_atk(self, target_fleet):
        if self.check_missile():  # 可以发射导弹时，获取全部有存量的导弹，并排序
            msl_list = [equip for equip in self.equipment
                        if isinstance(equip, Missile) and equip.load > 0]
            msl_list.sort(key=lambda x: (x.get_final_status('missile_atk'), x.enum)
                          )  # 按照突防从小到大+顺位顺序排序

        else:  # 无法发射导弹时，生成一枚0火力导弹
            zero_missile = NormalMissile(timer=self.timer,
                                         master=self,
                                         enum=1)
            zero_missile.set_status('fire', 0)
            msl_list = [zero_missile]

        for tmp_msl in msl_list:
            def_enemy = target_fleet.get_atk_target(atk_type=self.night_atk)
            if not len(def_enemy):
                break

            atk = self.night_atk(
                timer=self.timer,
                atk_body=self,
                def_list=def_enemy,
                equip=tmp_msl
            )
            yield atk
            tmp_msl.load -= 1


class AtkMissileShip(MissileShip):
    """反舰导弹船"""

    def __init__(self, timer):
        super().__init__(timer)
        self.act_phase_flag.update({
            'FirstMissilePhase': True,
            'SecondTorpedoPhase': False,
        })

        self.act_phase_indicator.update({
            'FirstMissilePhase': lambda x:
                (x.damaged < 3) and x.check_missile(),
        })


class DefMissileShip(MissileShip):
    """防空导弹船"""

    def __init__(self, timer):
        super().__init__(timer)
        self.act_phase_flag.update({
            'SecondTorpedoPhase': False,  # 大巡可参与
            'SecondMissilePhase': True,
        })

        self.act_phase_indicator.update({
            'SecondMissilePhase': lambda x:
                (x.damaged < 3) and x.check_missile(),
        })


class ASDG(AtkMissileShip, SmallShip, MainShip):
    """导驱"""
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'ASDG'


class AADG(DefMissileShip, AntiSubShip, SmallShip, CoverShip):
    """防驱"""
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'AADG'


class KP(AtkMissileShip, MidShip, MainShip):
    """导巡"""
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'KP'


class CG(DefMissileShip, MidShip, CoverShip):
    """防巡"""
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'CG'


class BBG(AtkMissileShip, LargeShip, MainShip):
    """导战"""

    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'BBG'
        from src.wsgr.formulas import NightNormalAtk
        self.night_atk = NightNormalAtk  # 夜战普通炮击


class BG(DefMissileShip, LargeShip, MainShip):
    """大巡"""

    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'BG'
        self.act_phase_flag.update({
            'SecondTorpedoPhase': True,  # 大巡可参与
        })


class LandUnit(LargeShip, MainShip):
    """路基单位"""
    def can_be_atk(self, atk):
        from src.wsgr.formulas import TorpedoAtk, AntiSubAtk
        if issubclass(atk, TorpedoAtk):
            return False
        elif issubclass(atk, AntiSubAtk):
            return False
        else:
            return self.damaged < 4


class Elite(Aircraft, LargeShip, MainShip):
    """旗舰"""

    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'Elite'
        self.flightparam = 10

        self.act_phase_flag.update({
            'SecondTorpedoPhase': False,
        })


class Fortness(LandUnit, Aircraft):
    """要塞"""

    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'Fortness'
        self.flightparam = 10

        self.act_phase_flag.update({
            'SecondTorpedoPhase': False,
        })
        from src.wsgr.formulas import NightFireTorpedolAtk
        self.night_atk = NightFireTorpedolAtk


class Airfield(LandUnit, Aircraft):
    """机场"""

    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'Airfield'
        self.flightparam = 10

        self.act_phase_flag.update({
            'SecondTorpedoPhase': False,
            'NightPhase': False,
        })

        self.act_phase_indicator.update({
            'AirPhase': lambda x: x.damaged < 3,
            'FirstShellingPhase': lambda x:
                (x.damaged < 3) and (x.check_atk_plane()),
            'SecondShellingPhase': lambda x:
                (x.damaged < 3) and (x.check_atk_plane()) and (x.get_range() >= 3),
        })

        from src.wsgr.formulas import AirNormalAtk
        self.normal_atk = AirNormalAtk  # 炮击战航空攻击


class Port(LandUnit):
    """港口"""
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'Port'


class Tuning(SmallShip, CoverShip):
    """调谐"""
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'Tuning'

        self.act_phase_flag = {
            'AirPhase': True,
            'FirstMissilePhase': True,
            'AntiSubPhase': True,
            'FirstTorpedoPhase': True,
            'FirstShellingPhase': True,
            'SecondShellingPhase': True,
            'SecondTorpedoPhase': True,
            'SecondMissilePhase': True,
            'NightPhase': True,
        }  # 可参与阶段

        self.act_phase_indicator = {
            'AirPhase':
                lambda x: x.damaged < 3,
            'FirstMissilePhase':
                lambda x: (x.damaged < 3) and x.check_missile(),
            'AntiSubPhase':
                lambda x: (x.get_form() == 5) and (x.damaged < 4),
            'FirstTorpedoPhase':
                lambda x: (x.level > 10) and (x.damaged < 3),
            'FirstShellingPhase':
                lambda x: x.damaged < 4,
            'SecondShellingPhase':
                lambda x: (x.get_range() >= 3) and (x.damaged < 4),
            'SecondTorpedoPhase':
                lambda x: (x.damaged < 3) and (x.get_final_status('torpedo') > 0),
            'SecondMissilePhase':
                lambda x: (x.damaged < 3) and x.check_missile(),
            'NightPhase':
                lambda x: x.damaged < 3,
        }  # 可行动标准

        from src.wsgr.formulas import \
            NormalAtk, AntiSubAtk, NightFireTorpedolAtk, NightAntiSubAtk
        self.normal_atk = NormalAtk  # 普通炮击
        self.anti_sub_atk = AntiSubAtk  # 反潜攻击
        self.night_atk = NightFireTorpedolAtk  # 夜战普通炮击
        self.night_anti_sub_atk = NightAntiSubAtk  # 夜战反潜攻击


class SSV(Aircraft, Submarine, SmallShip, CoverShip):
    def __init__(self, timer):
        super().__init__(timer)
        self.type = 'SSV'
        self.flightparam = 10

        self.act_phase_flag.update({
            'AirPhase': True,
            'FirstTorpedoPhase': True,
            'FirstShellingPhase': False,
            'SecondShellingPhase': False,
        })

class Fleet(Time):
    def __init__(self, timer):
        super().__init__(timer)
        self.ship = []
        self.status = {}  # 舰队属性
        self.form = 0  # 阵型; 1: 单纵; 2: 复纵; 3: 轮形; 4: 梯形; 5: 单横
        self.side = 0  # 敌我识别; 1: 友方; 0: 敌方

    def __repr__(self):
        if self.side == 1:
            fleet_name = '友方舰队'
        else:
            fleet_name = '敌方舰队'
        form_list = ['单纵阵', '复纵阵', '轮形阵', '梯形阵', '单横阵']
        return f"{fleet_name}-{form_list[self.form - 1]}"

    def set_ship(self, shiplist: list):
        shiplist.sort(key=lambda x: x.loc)
        self.ship = shiplist

    def set_form(self, form):
        self.form = form

    def set_side(self, side):
        self.side = side
        for tmp_ship in self.ship:
            tmp_ship.set_side(side)

    def get_init_status(self, enemy):
        """计算带路相关属性"""
        # 结算影响队友航速、索敌的技能，不结算让巴尔
        for tmp_ship in self.ship:
            tmp_ship.run_raw_prepare_skill(self, enemy)

        low_speed, high_speed = self.get_low_high_status('speed')  # 舰队最低速、最高速

        self.status.update({
            'level': sum([ship.level for ship in self.ship]),
            'speed': self.get_fleet_speed(),
            'avg_speed': self.get_avg_status('speed'),
            'leader_speed': self.ship[0].get_final_status('speed'),
            'low_speed': low_speed,
            'high_speed': high_speed,
            'recon': self.get_total_status('recon'),
            'antisub_recon': self.get_antisub_recon(),
            'luck': self.get_total_status('luck'),
        })

        for tmp_ship in self.ship:
            tmp_ship.clear_buff()

    def get_avg_status(self, name):
        """获取平均数据"""
        if not len(self.ship):
            return 0

        status = 0
        for tmp_ship in self.ship:
            status += tmp_ship.get_final_status(name)
        status /= len(self.ship)
        return status

    def get_low_high_status(self, name):
        """获取最高、最低数据"""
        if not len(self.ship):
            return 0, 0

        low_status = np.inf
        high_status = -np.inf
        for tmp_ship in self.ship:
            status = tmp_ship.get_final_status(name)
            if status > high_status:
                high_status = status
            if status < low_status:
                low_status = status
        return low_status, high_status

    def get_total_status(self, name):
        """获取属性总和"""
        if not len(self.ship):
            return 0

        status = 0
        for tmp_ship in self.ship:
            status += tmp_ship.get_final_status(name)
        return status

    def get_fleet_speed(self):
        """计算舰队航速"""
        main_type = (CV, CVL, AV, BB, BC, BBV, ASDG, AADG, KP, CG, BBG, BG,
                         Elite, Fortness, Airfield, Port)
        cover_type = (CA, CAV, CL, CLT, DD, BM, AP, Tuning)

        # 存在水面舰
        if self.count(Submarine) != len(self.ship):
            main_speed = 0
            main_num = 0
            cover_speed = 0
            cover_num = 0
            for tmp_ship in self.ship:
                if isinstance(tmp_ship, main_type):
                    main_speed += tmp_ship.get_final_status('speed')
                    main_num += 1
                elif isinstance(tmp_ship, cover_type):
                    cover_speed += tmp_ship.get_final_status('speed')
                    cover_num += 1

            # debug
            if main_num + cover_num > 6:
                raise ValueError('Number of ship not consist')
            elif main_num == 0 and cover_num == 0:
                raise ValueError('Mainship and Covership are both 0')

            # 主力舰与护卫舰同时存在，航速向下取整并取较小值
            elif main_num != 0 and cover_num != 0:
                main_speed = np.floor(main_speed / main_num)
                cover_speed = np.floor(cover_speed / cover_num)
                return min(main_speed, cover_speed)

            # 否则不取整
            elif main_num != 0:
                return main_speed / main_num
            else:
                return cover_speed / cover_num

        # 只有水下舰
        else:
            speed = self.get_avg_status('speed')
            return np.floor(speed)

    def get_antisub_recon(self):
        """反潜船索敌"""
        antisub_recon = 0
        for tmp_ship in self.ship:
            if isinstance(tmp_ship, AntiSubShip):
                antisub_recon += tmp_ship.get_final_status('recon')
                antisub_recon += tmp_ship.get_final_status('antisub', equip=False)
        return antisub_recon

    def get_member_inphase(self):
        """确定舰队中参与当前阶段的成员(不论是否可以行动，以满足炮序计算需求)"""
        member = []
        for tmp_ship in self.ship:
            if tmp_ship.get_act_flag():
                member.append(tmp_ship)
        return member

    def get_act_member_inphase(self):
        """确定舰队中在当前阶段可行动的成员"""
        member = []
        for tmp_ship in self.ship:
            if tmp_ship.get_act_flag() and tmp_ship.get_act_indicator():
                member.append(tmp_ship)
        return member

    def get_atk_target(self, atk_type=None, atk_body=None):
        """确定舰队中可被指定攻击方式选中的成员"""
        target = []
        if atk_type is not None:
            for tmp_ship in self.ship:
                if tmp_ship.can_be_atk(atk_type):
                    target.append(tmp_ship)
        # elif atk_body is not None:
        #     for tmp_ship in self.ship:
        #         if tmp_ship in atk_body.get_target():
        #             target.append(tmp_ship)
        # else:
        #     raise ValueError('"atk_type" and "atk_body" should not be None at the same time!')
        return target

    def count(self, shiptype):
        c = 0
        for tmp_ship in self.ship:
            if isinstance(tmp_ship, shiptype):
                c += 1
        return c
