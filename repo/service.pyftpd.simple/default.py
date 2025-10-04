import xbmc
import xbmcgui
import sys
import xbmcaddon

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

settings = xbmcaddon.Addon('service.system.pyftpd')

user1 = settings.getSettingString('user1')
user2 = settings.getSettingString('user2')
user3 = settings.getSettingString('user3')
user4 = settings.getSettingString('user4')
user5 = settings.getSettingString('user5')

password1 = settings.getSettingString('password1')
password2 = settings.getSettingString('password2')
password3 = settings.getSettingString('password3')
password4 = settings.getSettingString('password4')
password5 = settings.getSettingString('password5')

user1_enabled = settings.getSettingBool('user1_enabled')
user2_enabled = settings.getSettingBool('user2_enabled')
user3_enabled = settings.getSettingBool('user3_enabled')
user4_enabled = settings.getSettingBool('user4_enabled')
user5_enabled = settings.getSettingBool('user5_enabled')

path1 = settings.getSettingString('path1')
path2 = settings.getSettingString('path2')
path3 = settings.getSettingString('path3')
path4 = settings.getSettingString('path4')
path5 = settings.getSettingString('path5')

port = settings.getSettingInt('port')

anonymous_enabled = settings.getSettingBool('anonymous_enabled')
anonymous_path = settings.getSettingString('anonymous_path')

ip = xbmc.getIPAddress()
authorizer = DummyAuthorizer()

if(port > 0) :
    if(user1_enabled == True and user1 != '' and password1 != ''):
        authorizer.add_user(user1, password1, path1, perm="elradfmwMT")

    if(user2_enabled == True and user2 != '' and password2 != ''):
        authorizer.add_user(user2, password2, path2, perm="elradfmwMT")

    if(user3_enabled == True and user3 != '' and password3 != ''):
        authorizer.add_user(user3, password3, path3, perm="elradfmwMT")

    if(user4_enabled == True and user4 != '' and password4 != ''):
        authorizer.add_user(user4, password4, path4, perm="elradfmwMT")

    if(user5_enabled == True and user5 != '' and password5 != ''):
        authorizer.add_user(user5, password5, path5, perm="elradfmwMT")

    if(anonymous_enabled == True and anonymous_path != ''):
        authorizer.add_anonymous(anonymous_path)

    handler = FTPHandler
    handler.authorizer = authorizer

    server = FTPServer((ip, port), handler)
    server.serve_forever()

