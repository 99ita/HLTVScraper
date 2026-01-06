class Player():
    def __init__(self, nickname, nationality):
        self.nickname = nickname
        self.nationality = nationality

    def is_pt(self):
        return self.nationality == 'Portugal'

    def to_json(self):
        return {
            "nickname": self.nickname,
            "nationality": self.nationality
        }

    def to_csv(self):
        return [self.nickname, self.nationality]