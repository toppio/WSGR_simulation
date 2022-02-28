# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38

import xml.dom.minidom

from .. import battleUtil
from ..wsgr.ship import *
from ..wsgr import ship as rship
from ..wsgr import equipment as requip
from .. import skillCode


def load_config(config, dataset):
    """加载配置文件"""
    dom = xml.dom.minidom.parse(config)
    root = dom.documentElement

    friend_root = root.getElementsByTagName('Fleet')[0]
    friend = load_fleet(friend_root, dataset)

    enemy_root = root.getElementsByTagName('Fleet')[1]
    enemy = load_fleet(enemy_root, dataset)

    # 根据战斗类型调用不同流程类
    battle_type = root.getAttribute('type')
    battle = getattr(battleUtil, battle_type)

    return battle(friend, enemy)


def load_fleet(node, dataset):
    fleet = Fleet()
    fleet.set_form(int(node.getAttribute('form')))

    shiplist = []
    for i in range(len(node.getElementsByTagName('Ship'))):
        s_node = node.getElementsByTagName('Ship')[i]
        ship = load_ship(s_node, dataset)
        shiplist.append(ship)

    fleet.set_ship(shiplist)
    fleet.set_side(int(node.getAttribute('side')))
    return fleet


def load_ship(node, dataset):
    cid = node.getAttribute('cid')
    if cid[0] == '1':
        return load_friend_ship(node, dataset)
    else:
        return load_enemy_ship(node, dataset)


def load_friend_ship(node, dataset):
    # 读取舰船属性
    cid = node.getAttribute('cid')
    status = dataset.get_friend_ship_status(cid)

    # 舰船对象实例化
    ship_type = status.pop('type')
    ship = getattr(rship, ship_type)()  # 根据船型获取类，并实例化
    ship.set_cid(cid)

    # 写入节点属性
    ship.set_loc(int(node.getAttribute('loc')))
    ship.set_level(int(node.getAttribute('level')))
    ship.set_affection(int(node.getAttribute('affection')))

    if isinstance(ship, Aircraft):
        assert status['capacity'] != 0
        load = status.pop('load')
        ship.set_load(load)
    equip_num = status.pop('equipnum')
    skill_list = status.pop('skill')

    if ship.affection >= 100:  # 婚舰幸运+5
        status['luck'] += 5

    # 写入舰船属性
    ship.set_status(status=status)

    # 调用技能并写入
    skill_num = int(node.getAttribute('skill')) - 1
    sid = skill_list[skill_num]
    if sid != '':
        sid = 'sid' + sid
        skill = getattr(skillCode, sid).skill  # 根据技能设置获取技能列表，未实例化
        ship.add_skill(skill)

    # 读取装备属性并写入
    enodes = node.getElementsByTagName('Equipment')
    eskill_list = []
    for i in range(len(enodes)):
        e_node = enodes[i]
        enum = int(e_node.getAttribute('loc'))
        if enum > equip_num:  # 装备所在栏位超出舰船装备限制
            continue

        e_skill, equip = load_equip(e_node, dataset, ship)
        ship.set_equipment(equip)
        eskill_list.append(e_skill)

    # todo 同类装备效果不叠加

    return ship


def load_enemy_ship(node, dataset):
    pass


def load_equip(node, dataset, master):
    # 读取装备属性
    eid = node.getAttribute('eid')
    status = dataset.get_equip_status(eid)

    # 装备对象实例化
    equip_type = status.pop('type')
    enum = int(node.getAttribute('loc'))
    equip = getattr(requip, equip_type)(master, enum)  # 根据装备类型获取类，并实例化

    # 如果装备也存在特殊效果，当作技能写入舰船skill内
    skill = []
    # esid = status.pop('skill')
    # if esid != '':
    #     esid = 'eid' + esid
    #     skill = getattr(skillCode, esid).skill  # 根据技能设置获取技能列表，未实例化

    # 写入装备属性
    equip.set_status(status=status)

    return skill, equip
