# -*- coding:utf-8 -*-
# Author:银河远征
# env:py38

from .Equipment import *  # 装备特效
from .Strategy import *  # 战术效果

from .AV import *
from .CV import *
from .CVL import *
from .DD import *

from .Other import *  # 其他舰种，包含航战、航巡、雷巡、补给

# 未改BB
from . import sid102001  # 兴登堡-1
from . import sid102051  # 约克公爵-1
from . import sid102081  # 马萨诸塞-1
from . import sid102091  # 密苏里-1
from . import sid102101  # 衣阿华-1
from . import sid102131  # 罗马-1
from . import sid102141  # 苏联-1
from . import sid102991  # 让巴尔-1
from . import sid103051  # 英王乔治五世-1
from . import sid103451  # 威斯康星-1
from . import sid103671  # 乌尔里希·冯·胡滕-1
from . import sid103811  # 印第安纳-1
from . import sid104091  # 新泽西-1
from . import sid104181  # 阿金库尔-1
from . import sid104421  # 里昂-1
from . import sid104481  # 弗兰德尔-1
from . import sid104501  # L20-1
from . import sid104541  # 征服者-1
from . import sid104601  # 宾夕法尼亚-1
from . import sid104641  # 南达科他(1920)-1
from . import sid104681  # 猎户座-1
from . import sid104991  # 克里蒙梭-1

# 改造BB
from . import sid110061  # 俾斯麦-1
from . import sid110062  # 俾斯麦-2
from . import sid110071  # 提尔比茨-1
from . import sid110081  # BIG SEVEN
from . import sid110092  # 罗德尼-2
from . import sid110101  # 威尔士亲王-1
from . import sid110102  # 威尔士亲王-2
from . import sid110111  # 重点防御：内华达-1、俄克拉荷马-1
from . import sid110131  # 安德烈亚多里亚-1
from . import sid110141  # 金刚-1
from . import sid111001  # 狮-1
from . import sid111002  # 狮-2
from . import sid111022  # 陆奥-2
from . import sid111051  # 前卫-1
from . import sid111052  # 前卫-2
from . import sid111061  # 田纳西-1
from . import sid111071  # 加利福尼亚-1
from . import sid111091  # 马里兰-1
from . import sid111101  # 西弗吉尼亚-1
from . import sid111102  # 西弗吉尼亚-2
from . import sid111111  # 华盛顿-1
from . import sid111112  # 华盛顿-2
from . import sid111121  # 维内托-1
from . import sid111131  # 黎塞留-1
from . import sid111132  # 黎塞留-2
from . import sid112061  # 北卡罗来纳-1
from . import sid112062  # 北卡罗来纳-2
from . import sid112071  # 南达科他-1
from . import sid112072  # 南达科他-2
from . import sid112111  # 卡约•杜伊里奥-1
from . import sid113801  # 圣乔治-1
from . import sid113802  # 圣乔治-2

# 未改BC
from . import sid103311  # 无比-1
from . import sid103971  # 斯大林格勒-1
from . import sid104351  # B65-1
from . import sid104361  # 十三号战舰-1
from . import sid104461  # 狮(战巡)-1
from . import sid104611  # 无敌-1
from . import sid104841  # 安森-1
from . import sid104901  # 克劳塞维茨-1

# 改造BC
from . import sid110011  # 胡德-1
from . import sid110012  # 胡德-2
from . import sid110181  # 声望-1
from . import sid110182  # 声望-2
from . import sid110191  # 反击-1
from . import sid111301  # 斯佩伯爵海军上将-1
from . import sid111302  # 斯佩伯爵海军上将-2
from . import sid113621  # 星座-1
from . import sid113622  # 星座-2

# 未改CACL
from . import sid102431  # 得梅因-1
from . import sid103521  # 莫斯科-1
from . import sid103571  # 羽黑-1
from . import sid103881  # 纽波特纽斯-1
from . import sid104101  # 萨勒姆-1
from . import sid104381  # 梅肯-1
from . import sid104511  # 伊吹-1
# from . import sid104201  # 亚尔古水手-1
from . import sid104221  # 凤凰城-1
from . import sid104821  # 大淀(苍青)-1

# 改造CACL
from . import sid110581  # 高速射击
from . import sid110321  # 高雄-1
from . import sid110331  # 爱宕-1
from . import sid110341  # 摩耶-1
from . import sid110351  # 鸟海-1
from . import sid110361  # 希佩尔海军上将-1
from . import sid110371  # 布吕歇尔-1
from . import sid110381  # 欧根亲王改-1
from . import sid110382  # 欧根亲王改-2
from . import sid110391  # 威奇塔改-1
from . import sid110402  # 昆西-2
from . import sid111311  # 古鹰-1
from . import sid111321  # 加古-1
from . import sid111331  # 青叶-1
from . import sid111351  # 过度击穿: 伦敦-1、肯特-1
from . import sid111371  # 波特兰改-1
from . import sid111391  # 彭萨科拉改-1
from . import sid111411  # 北安普顿-1
from . import sid111431  # 新奥尔良改-1
from . import sid112401  # 旧金山改-1
from . import sid112411  # 巴尔的摩改-1
from . import sid112412  # 巴尔的摩改-2
from . import sid114311  # 什罗普郡-1
# from . import sid110461  # 夕张改-1
from . import sid110501  # 天狼星改-1
from . import sid110541  # 重庆-1
from . import sid110571  # 朱诺改-1
from . import sid110591  # 海伦娜改-1
from . import sid110592  # 海伦娜改-2
from . import sid111601  # 摩尔曼斯克改-1
from . import sid111621  # 逸仙改-1
from . import sid114561  # 塔林-1

# 导弹
from . import sid104671  # 鞍山-1
from . import sid110201  # 阿拉斯加改-1
from . import sid110211  # 关岛改-1
from . import sid110941  # 基阿特改-1
from . import sid110971  # 长春改-1
from . import sid112092  # 密苏里改-2
from . import sid112992  # 让巴尔改-2
from . import sid114131  # 加里波第改-1

# SSSC
from . import sid103661  # 鹦鹉螺
from . import sid104581  # U-14
from . import sid111941  # 大青花鱼
from . import sid111951  # 射水鱼
from . import sid111971  # U-47改-1
from . import sid111972  # U-47改-2
from . import sid111991  # 絮库夫
from . import sid112891  # U-81
from . import sid112901  # U-96
from . import sid112931  # U-1206
from . import sid113511  # U-1405
from . import sid114081  # 鲃鱼
