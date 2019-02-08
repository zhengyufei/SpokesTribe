pay_type_reversal = {}
pay_type_reversal['微信'] = ('weixin', 'weixinjs', 'zb_wx', 'fy_wxjs')
pay_type_reversal['支付宝'] = ('ali', 'zb_ali', 'fy_alijs')
pay_type_reversal['会员'] = ('member',)
pay_type_reversal['手动'] = ('offline',)

PAY_TYPE = []
PAY_TYPE_DICT = {}
for key, item in pay_type_reversal.items():
    for item2 in item:
        PAY_TYPE.append((item2, key))
        PAY_TYPE_DICT[item2] = key

PAY_TYPE = tuple(PAY_TYPE)