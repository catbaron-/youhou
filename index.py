# -*- coding: utf-8 -*-  
import sae
import web
import urllib,urllib2
import re
import hashlib
import time
import xml.dom.minidom
import datetime
import MySQLdb
from sae.const import *
from math import sin,cos,asin,acos,sqrt,pi

web.config.debug = True
urls = (
        '/svr','SVR',
        '/location','Location',
        '/test','Test',
        '/home','Home',
        )


DB = web.database(dbn='mysql',host=MYSQL_HOST,user=MYSQL_USER,pw=MYSQL_PASS,db=MYSQL_DB,port=int(MYSQL_PORT))
RENDER = web.template.render('templates/', cache=False)

#用来查询二维码
HEADERS = {'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/31.0.1650.63 Safari/537.36'} 
#二维码的查询地址
QRSITE = "http://www.2and1.cn/Default.aspx"

XML_STRING = """这里是测试用的XML内容，Location类会读取这个XML生成XML对象"""
DIS_LIMIT = 5    #距离限制，在此范围内的群才会显示
FROMNAME = "gh_a68996c55d03"    #公共账号ID

#回复的文字信息
MSG = {
           "welcome":u"""yoooo，你终于来了，正找你打球呢。回复1查找附近的篮球群，回复2创建自己的篮球群，回复数字0查看此消息。""",
           "create_start": u"勇士啊，现在开始建群的冒险旅程。你需要集齐‘群描述’，‘群地址’和‘群二维码名片’三种神器来建立冒险的队伍。首先回复给我你的群描述：",
           "create_url": u"上传群二维码让别人加入",
           "create_loc": u"上传你的位置作为群的位置",
           "create_info": u"输入群描述，最好标注出你的位置",
           "create_fin": u"NB，建群完成了！",
           "search_start": u"上传你的位置，看看附近有哪些队伍",
           "search_failed":u"卧槽你附近没有群，赶紧的回复2创建一个去",
           }

#功能字符，切换用户状态
USER_STAT = {"search":'1',"create":'2',"close":'3',"created":'100'}
#用来匹配各种信息类型的字符串
MSGTYPE = {"text":"text","image":"image","location":"location"}
#图文消息首条记录
NEWS_TITLE = {"title":u"输入0查看帮助","url":"http://youhou.sinaapp.com/home","img":"http://youhou.sinaapp.com/static/title.jpg","dis":-1}

LOC_FLAG = 4    #用户上传群地理位置的标记
INFO_FLAG = 2   #用户更新群信息的标记
URL_FLAG = 1    #用户上传群二维码的标记

app = web.application(urls, globals())

#测试用类
class Location:
    def POST(self):
        MsgType = web.input().MsgType
        return MsgType
    def GET(self):
        string = XML_STRING
        data = xml.dom.minidom.parseString(string)
        MsgType = data.getElementsByTagName("MsgType")[0].childNodes[0].data
        tname = xmlData(data,"FromUserName")
        if MsgType == "image":
            url = xmlData(data, 'PicUrl')
            return newsResponse(data)
        if MsgType == "event":
            e = xmlData(data,"Event")
            print e
            if "subscribe" == e:
                web.header('Content-Type', 'text/xml')
                return textResponse(tname,MSG["welcome"])
        return data

# 将度表示转化为π表示
def rad(d):
    return (float(d)*pi)/180.0
# 根据经纬度计算实际距离，结果单位为km，经度为0.001
def loc2dis(lat1,lng1,lat2,lng2):
    radlat1 = rad(lat1)
    radlat2 = rad(lat2)
    a = rad(lat1) - rad(lat2)
    b = rad(lng1) - rad(lng2)
    EARTH_RADIUS = 6378.137
    dis = 2 * asin(sqrt((sin(a/2)**2) + cos(radlat1)*cos(radlat2)*(sin(b/2)**2)))
    dis = dis * EARTH_RADIUS
    return round(dis*1000)/1000.0

# 获得XML指定TAG的值
def xmlData(xmldata,tag):
    return xmldata.getElementsByTagName(tag)[0].childNodes[0].data

# 回复文字消息
# tname: 目标用户id
# ctnt: 消息内容字符串
# 返回: 渲染好的xml模板对象
# Debug: 会打印返回的内容和返回的时间
def textResponse(tname,ctnt):
    fname = FROMNAME
    tname = tname
    ctime = int(time.time())
    ctnt = ctnt
    r = RENDER.text(tname,fname,ctime,ctnt)
    print "WXLOG--",r
    print "WXLOG--RETURN MSG",datetime.datetime.now()
    return r

# 回复图文消息
# tname：目标用户ID
# items：每条图文记录
# 返回: 渲染好的news.xml对象
# Debug: 打印返回的xml内容和返回的时间
def newsResponse(tname,items):
    fname = FROMNAME
    ctime = int(time.time())
    r = RENDER.news(tname,fname,ctime,items)
    print "WXLOG--",r
    print "WXLOG--RETURN NEWS",datetime.datetime.now()
    return r

# 模拟post请求，用来请求二维码解析结果
# 返回: 拿到的html
def post(url,data):
    req = urllib2.Request(url,headers = HEADERS)
    postdata = urllib.urlencode(data)
    opener = urllib2.build_opener()
    res = opener.open(req,postdata)
    return res.read()

# 从2and1网站拿到二维码信息
# img_url: 二维码的图片地址
# 返回: 如果是微信群/成员的二维码，则返回url；
#       否则返回空字符串
def readQrcode(img_url):
    posturl = QRSITE
    #Post数据
    data = {
    "txtUrl":"",
    ### ↓↓↓这两个不知道干啥的↓↓↓ ###
    "__VIEWSTATE":"/wEPDwUKLTMzMTkzNzMwNQ9kFgICAw8WAh4HZW5jdHlwZQUTbXVsdGlwYXJ0L2Zvcm0tZGF0YWRkA6XqfNFAPcVg3WiVKKi7AncYYjI=",
    "__EVENTVALIDATION":"/wEWBwLT+pq2CgLq9o7AAgKa+/bVAgLH4MTHAQL6g4f3AwKShuTABQLI9t6sBcwfGz4tzMTBDCJbXL8TKWYDaTBS",
    ### ↑↑↑这两个不知道干啥的↑↑↑ ###
    "bntMUrl":"解析二维码"
    }
    data["txtUrl"] = img_url
    html = post(posturl,data)
    url_re = re.compile(r"http://weixin.qq.com/g/\w+")
    url_reg = url_re.findall(html)
    if len(url_reg) > 0:
        return url_reg[0]
    else:
        return ""

# 更新群信息
def groupInfo(tname,info):
    selvar = dict(user=tname,flag=7)
    #在群表中找该用户未完成的群，
    res_list = list(DB.select('groups',vars = selvar, where='g_user=$user and g_flag!=$flag'))
    if 0 < len(res_list):
        #如果找到了说明用户正在建群，对此群信息进行更新
        g_id = res_list[0]["g_id"]
        g_flag = res_list[0]["g_flag"]|INFO_FLAG #更新群信息标记
        DB.update('groups',vars = dict(g_id=g_id), where="g_id=$g_id",g_info=info,g_flag=g_flag)
        return g_flag
    else:
        #如果没找到说明建过完整的群或者未建过群，插入新纪录
        DB.insert('groups',g_flag=INFO_FLAG,g_user=tname,g_info=info)
        g_flag = INFO_FLAG #更新群信息标记
        return g_flag

# 更新群名片
def groupUrl(tname,url):
    selvar = dict(user=tname,flag=7)
    #在群表中找该用户未完成的群，
    res_list = list(DB.select('groups',vars = selvar, where='g_user=$user and g_flag!=$flag'))
    if 0 < len(res_list):
        #如果找到了说明用户正在建群，对此群URL进行更新
        g_id = res_list[0]["g_id"]
        g_flag = res_list[0]["g_flag"]|URL_FLAG
        DB.update('groups',vars = dict(g_id=g_id), where="g_id=$g_id",g_url=url,g_flag=g_flag)
        return g_flag
    else:
        #如果没找到说明建过完整的群或者未建过群，插入新纪录
        DB.insert('groups',g_flag=URL_FLAG,g_user=tname,g_url=url)
        g_flag = URL_FLAG
        return g_flag
# 更新群位置
def groupLoc(tname,loc):
    selvar = dict(user=tname,flag=7)
    #在群表中找该用户未完成的群，
    res_list = list(DB.select('groups',vars = selvar, where='g_user=$user and g_flag!=$flag'))
    if 0 < len(res_list):
        #如果找到了说明用户正在建群，对此群信息进行更新
        g_id = res_list[0]["g_id"]
        g_flag = res_list[0]["g_flag"]|LOC_FLAG
        DB.update('groups',vars = dict(g_id=g_id), where="g_id=$g_id",g_loc_x=loc[0],g_loc_y=loc[1],g_flag=g_flag)
        return g_flag
    else:
        #如果没找到说明建过完整的群或者未建过群，插入新纪录
        DB.insert('groups',g_flag=LOC_FLAG,g_loc_x=loc[0],g_loc_y=loc[1],g_user=tname)
        g_flag = LOC_FLAG
        return g_flag

# 创建群的过程回复的引导信息
def returnByFlag(tname,g_flag):
    if g_flag & LOC_FLAG == 0:
        str_res = MSG["create_loc"]
    if g_flag & INFO_FLAG == 0:
        str_res = MSG["create_info"]
    if g_flag & URL_FLAG == 0:
        str_res = MSG["create_url"]
    if g_flag == 7:
        DB.update('user',vars = dict(user=tname),where="u_user=$user",u_stat=USER_STAT["search"])
        str_res = MSG["create_fin"]
    return textResponse(tname,str_res)

# 对数据库中的群和用户的距离快速排序，最小的排在前面
# g_list: {"g_info":群描述，"g_url":群url,"g_dis":群和用户的距离,"g_title":显示的信息（群描述+距离描述）}
# left，right: 递归排序需要的上下界标
def qsort(g_list,left,right):
    lp = left
    rp = right
    key = g_list[right]["dis"]
    if lp == rp:
        return
    while True:
        while (g_list[lp]["dis"] <= key) and (lp < rp):
            lp = lp+1
        while g_list[rp]["dis"] >= key and lp < rp:
            rp = rp -1
        g_list[lp],g_list[rp] = g_list[rp],g_list[lp]
        if lp >= rp:
            break
    g_list[right],g_list[rp] = g_list[rp],g_list[right]
    if lp > left:
        qsort(g_list,left,lp-1)
    qsort(g_list,lp,right)

# 从数据库中查询出所有的群，然后和用户计算距离，排列出最近的8个群返回
# tname: 目标用户ID
# loc: [lat,lng]，用户的纬度和经度
def findGroup(fname,loc):
    g = {}
    #查找创建状态为7的群，表示群信息已经更新完成
    res_list = list(DB.select('groups',where='g_flag=7'))
    g_list = [NEWS_TITLE]
    if len(res_list) > 0:
        for group in res_list:
            #计算群和用户的距离
            g_dis= loc2dis(loc[0],loc[1],group["g_loc_x"],group["g_loc_y"])
            #距离比较小的才返回
            if g_dis <= DIS_LIMIT:
                g_url = group["g_url"]
                g_title = group["g_info"]+"("+str(g_dis)+"km)"
                g_list.append({"title":g_title,"url":g_url,"dis":g_dis,"img":""})
        #对符合要求的所有群进行排序
        qsort(g_list,0,len(g_list)-1)
    return g_list


# 处理群相关请求，包括创建和查找
# tname: 用户ID
# msgtype: 用户发来的消息类型
# ctnt: 封装用户发来的消息内容的字典。
def dealWithGroup(tname,msgtype,ctnt):
    selvar = dict(user=tname,flag=7)
    #现获取用户状态，用来判断指令是否合法
    res_list = list(DB.select('user',vars = selvar, where='u_user=$user'))
    if 1 == res_list[0]["u_stat"] and msgtype == MSGTYPE["location"]:
        #状态为1，表示在查找群。上传地理位置查找群的情况，返回查找结果
        g_list = findGroup(tname,ctnt["loc"])
        if len(g_list)>8:#找到8个以上，只取前八
            return newsResponse(tname,g_list[0:9])
        if 1 == len(g_list):#一个没找到，返回失败消息
            return textResponse(tname,MSG["search_failed"])
        else:#找到8个以内（包括8个），全部返回
            return newsResponse(tname,g_list)

    if 2 != res_list[0]["u_stat"]:
        #状态不是查找也不是创建的情况，直接返回欢迎信息
        return textResponse(tname, MSG["welcome"])
    #状态是2的情况，开始创建群，根据图片/位置/文字 分别更新群的url/坐标/描述信息
    if msgtype == MSGTYPE["text"]:
        g_flag = groupInfo(tname,ctnt["ctnt"])
        return returnByFlag(tname,int(g_flag))
    if msgtype == MSGTYPE["image"]:
        g_flag = groupUrl(tname,ctnt["url"])
        return returnByFlag(tname,int(g_flag))
    if msgtype == MSGTYPE["location"]:
        g_flag = groupLoc(tname,ctnt["loc"])
        return returnByFlag(tname,int(g_flag))

# 文字信息处理，命令数字进行状态转化，普通文字则认为是更新群信息
# xmldata: xml对象
# tname: 用户ID
# msgtype: 消息类型
# 返回：最后返回的是各个流程处理后得出的xml渲染对象
def dealWithText(xmldata,tname):
    selvar = dict(user=tname)
    ctnt = xmlData(xmldata,"Content")
    if USER_STAT["search"] == ctnt:
        #查找群
        DB.update('user',vars = selvar,where="u_user=$user",u_stat=ctnt)
        return textResponse(tname,MSG["search_start"])
    if USER_STAT["create"] == ctnt:
        #建立群  
        DB.update('user',vars = selvar,where="u_user=$user",u_stat = ctnt)
        str_res = MSG["create_start"]
        return textResponse(tname,str_res)
    if USER_STAT["close"] == ctnt:
        #关闭建群过程
        res_list = list(DB.select('user',vars = selvar, where='u_user=$user'))
        if len(res_list) > 0:
            u_id = res_list[0]["u_id"]
            if res_list[0]["u_stat"] == USER_STAT["created"]:
                #建群完成，重置为search状态
                DB.update('user',where="u_id="+str(u_id),u_stat = USER_STAT["search"])
    else:
        return dealWithGroup(tname,MSGTYPE["text"],{"ctnt":ctnt})

#上传图片认为是上传二维码，更新群状态
def dealWithImg(xmldata,tname,msgtype):
    img_url = xmlData(xmldata,"PicUrl")
    g_url = readQrcode(img_url)
    if len(g_url) > 0:
        #找到群信息，开始简历群
        return dealWithGroup(tname,msgtype,{"url":g_url})
    else:
        res_str = "卧槽二维码好像不对头，我读书少你别骗我……"
        return textResponse(tname,res_str)

#处理上传位置
def dealWithLoc(xmldata,tname,msgtype):
    lat = xmlData(xmldata,"Location_X")
    lng = xmlData(xmldata,"Location_Y")
    g_loc = [lat,lng]
    try:
        DB.update('user',vars = {"user":tname},where="u_user=$user",u_loc_x=lat, u_loc_y=lng)
    except Exception,e:
        print "WXLOG-- Update User Loc Err:",e
    return dealWithGroup(tname,msgtype,{"loc":g_loc})

class Home:
    def GET(self):
        return RENDER.home()

class SVR:
    def GET(self):
        #GET 请求用来处理开发人员认证
        str_in = web.input()
        s = ""
        token = "catbaron"
        nonce = str_in.nonce
        timestamp = str_in.timestamp
        signature = str_in.signature
        echostr = str_in.echostr
        l = [token,nonce,timestamp]
        l.sort()

        for w in l:
            s = s+w
        sha = hashlib.sha1(s)
        tmpstr = sha.hexdigest()

        if tmpstr == signature:
            return echostr
        else:
            return u"我擦搞错了"+echostr+"-"+tmpstr
    def POST(self):
        print "WXLOG--GET POST", datetime.datetime.now()
        data = xml.dom.minidom.parseString(web.data())
        msgtype = xmlData(data, "MsgType")
        user = xmlData(data, "FromUserName")
        selvar = dict(user=user)
        res_list = list(DB.select('user',vars = selvar, where='u_user=$user'))
        if len(res_list) == 0:
            u_id = DB.insert('user',u_user=user,u_stat=1)
        if msgtype == "text":
            web.header('Content-Type', 'text/xml')
            return dealWithText(data,user)
        if msgtype == "location":
            web.header('Content-Type','text/xml')
            return dealWithLoc(data,user,msgtype)
        if msgtype == "image":
            web.header('Content-Type', 'text/xml')
            return dealWithImg(data,user,msgtype)
        if msgtype == "event":
            #第一次的关注信息
            event = xmlData(data,"Event")
            if "subscribe" == event:
                web.header('Content-Type', 'text/xml')
                return textResponse(user,MSG["welcome"])
        return msgtype

application = sae.create_wsgi_app(app.wsgifunc())
