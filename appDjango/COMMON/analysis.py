
class LoginOutMsg:
    def __int__(self):
        self.station  = ""
        self.user = ""
        self.pwd = ""
    def analysis(self, msg):
        msg = str(msg)
        self.station = msg.split(';')[2].split(':')[1]
        self.user = msg.split(';')[3].split(':')[1].split(',')[0].split('=')[1]
        self.pwd = msg.split(';')[3].split(':')[1].split(',')[1].split('=')[1]

class CheckSnOutMsg:
    def __int__(self):
        self.station = ""
        self.sn = ""
        self.model = ""
    def analysis(self, msg):
        self.station = msg.split(';')[2].split(':')[1]
        self.sn = msg.split(';')[3].split(':')[1].split(',')[0].split('=')[1]
        self.model = msg.split(';')[3].split(':')[1].split(',')[1].split('=')[1]