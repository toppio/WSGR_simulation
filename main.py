# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38

import os
import sys
import copy
import numpy as np

curDir = os.path.dirname(__file__)
srcDir = os.path.join(curDir, 'src')
sys.path.append(srcDir)

from src.utils.loadConfig import load_xml, load_yaml, load_config
from src.utils.loadDataset import Dataset
from src.utils.runUtil import *
from src.wsgr.wsgrTimer import timer
from src.wsgr.formulas import *

configDir = os.path.join(os.path.dirname(srcDir), 'config')
dependDir = os.path.join(os.path.dirname(srcDir), 'depend')
data_file = os.path.join(dependDir, r'ship/database.xlsx')
mapDir = os.path.join(dependDir, r'map')
ds = None  # 舰船数据；首次使用时加载


def get_dataset():
    """延迟加载 database.xlsx。

    spawn 平台（Windows）启动子进程时会重新执行本模块的顶层代码，若在这里
    直接 Dataset(...)，每个子进程都要白白解析一次 Excel（1-2 秒）。
    """
    global ds
    if ds is None:
        ds = Dataset(data_file)
    return ds


def main(infile, epoch, battle_num, fun, worker=1, **kwargs):
    """worker: 并行进程数。1 表示串行；>=2 且 epoch >= 1000 时切分给多个进程"""
    dataset = get_dataset()
    timer_init = timer()  # 创建时钟
    if infile.endswith('.xml'):
        battleConfig = load_xml(infile, mapDir)
    elif infile.endswith('.yaml'):
        battleConfig = load_yaml(infile, mapDir)
    else:
        raise Exception(f"未许可的文件后缀'{os.path.splitext(infile)[1]}'")
    battle = load_config(battleConfig, mapDir, dataset, timer_init)  # 加载战斗配置
    # for ship in battle.enemy.ship:  # 属性修改
    #     ship.status['armor'] = 180
    #     ship.status['fire'] = 200
    #     ship.status['accuracy'] = 120
    #     ship.status['total_health'] = 450
    #     ship.status['antiair'] = 100
    #     ship.status['recon'] = 100
    # fire = kwargs.pop('fire') if 'fire' in kwargs else 0
    # battle.friend.ship[4].status['fire'] += fire
    set_supply(battle, battle_num)
    prebattle_info(battle)
    fun(battle, epoch, worker=worker,
        battle_source=(battleConfig, mapDir, dataset, battle_num), **kwargs)


if __name__ == '__main__':
    epoch = 10000
    worker = 1  # 并行进程数
    battle_num = 1  # 战斗轮次
    supportFlag = False  # todo 是否使用支援攻击
    fun = run_victory
    configFile = os.path.join(configDir, r'config_map_test.yaml')
    # configFile = os.path.join(configDir, r'event/config_1_2.xml')
    # configFile = os.path.join(configDir, r'config.xml')
    main(configFile, epoch, battle_num, fun, worker=worker)

    # for fire in range(10, 40, 10):
    #     main(configFile, epoch, battle_num, fun, fire=fire)
    #     print('\n')
