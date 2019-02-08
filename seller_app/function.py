from django.db import connection
import common.settings as my_settings


#real recv
def base_bill_app(shop_id):
    sql = "SELECT TD.trade_price, TP.pay_type FROM common_trade AS T " \
        "LEFT JOIN common_tradediscountprofile AS TD ON T.id = TD.trade_id " \
        "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id " \
        "WHERE to_days(T.trade_time)=to_days(now()-1) AND TD.`status` = 'pay' AND T.shop_id = {0} AND T.settle_type != 'nothing' " \
        "UNION ALL " \
        "SELECT TT.trade_price, TP.pay_type FROM common_trade AS T " \
        "RIGHT JOIN common_tradeticketprofile AS TT ON T.id = TT.trade_id " \
        "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id " \
        "WHERE to_days(TT.confirm_time)=to_days(now()-1) AND TT.`status` = 'confirm' AND T.shop_id = {0} AND T.settle_type != 'nothing' " \
        "UNION ALL " \
        "SELECT TM.trade_price, TP.pay_type FROM common_trade AS T " \
        "LEFT JOIN common_tradememberprofile AS TM ON T.id = TM.trade_id " \
        "LEFT JOIN common_tradepay AS TP ON T.id = TP.trade_id " \
        "WHERE to_days(T.trade_time)=to_days(now()-1) AND TM.`status` = 'pay' AND T.shop_id = {0} AND T.settle_type != 'nothing'".format(shop_id)

    cursor = connection.cursor()
    cursor.execute(sql)
    fetchall = cursor.fetchall()

    sale_day = sale_day_wx = sale_day_ali = 0
    for obj in fetchall:
        sale_day += obj[0]
        if obj[1] in my_settings.pay_type_reversal['微信']:
            sale_day_wx += obj[0]
        elif obj[1] in my_settings.pay_type_reversal['支付宝']:
            sale_day_ali += obj[0]

    sql = "SELECT * FROM " \
      "(SELECT SUM(trade_price) FROM ( " \
      "SELECT SUM(B.trade_price) AS trade_price FROM common_trade AS A LEFT JOIN common_tradediscountprofile AS B ON A.id = B.trade_id " \
      "WHERE DATE_FORMAT(A.trade_time,'%Y%m')= date_format(now(),'%Y%m') AND B.`status` = 'confirm' AND A.shop_id = {0} AND A.settle_type != 'nothing' " \
      "UNION ALL " \
      "SELECT SUM(B.trade_price) AS trade_price FROM common_trade AS A RIGHT JOIN common_tradeticketprofile AS B ON A.id = B.trade_id " \
      " WHERE DATE_FORMAT(A.trade_time,'%Y%m')= date_format(now(),'%Y%m') AND B.`status` = 'confirm' AND A.shop_id = {0} AND A.settle_type != 'nothing' " \
      "UNION ALL " \
      "SELECT SUM(B.trade_price) AS trade_price FROM common_trade AS A LEFT JOIN common_tradememberprofile AS B ON A.id = B.trade_id " \
      "WHERE DATE_FORMAT(A.trade_time,'%Y%m')= date_format(now(),'%Y%m') AND B.`status` = 'confirm' AND A.shop_id = {0} AND A.settle_type != 'nothing' " \
      ") AS tmp) AS T1, " \
      "(SELECT SUM(trade_price) FROM ( " \
      "SELECT SUM(B.trade_price) AS trade_price " \
      " FROM common_trade AS A LEFT JOIN common_tradediscountprofile AS B ON A.id = B.trade_id " \
      "WHERE to_days(now()) - to_days(A.trade_time) = 1 AND B.`status` = 'confirm' AND A.shop_id = {0} AND A.settle_type != 'nothing' " \
      "UNION ALL " \
      "SELECT SUM(B.trade_price) AS trade_price " \
      " FROM common_trade AS A RIGHT JOIN common_tradeticketprofile AS B ON A.id = B.trade_id " \
      "WHERE to_days(now()) - to_days(A.trade_time) = 1 AND B.`status` = 'confirm' AND A.shop_id = {0} AND A.settle_type != 'nothing' " \
      "UNION ALL " \
      "SELECT SUM(B.trade_price) AS trade_price " \
      "FROM common_trade AS A LEFT JOIN common_tradememberprofile AS B ON A.id = B.trade_id " \
      " WHERE to_days(now()) - to_days(A.trade_time) = 1 AND B.`status` = 'confirm' AND A.shop_id = {0} AND A.settle_type != 'nothing' " \
      ") AS tmp) AS T3".format(shop_id)

    cursor = connection.cursor()
    cursor.execute(sql)
    fetchall = cursor.fetchall()

    obj = fetchall[0]
    sale_month = obj[0] if obj[0] else 0
    sale_month += sale_day
    sale_yesterday = obj[1] if obj[1] else 0

    return sale_month, sale_day, sale_day_wx, sale_day_ali, sale_yesterday
