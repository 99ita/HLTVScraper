class Stats:
    def __init__(self):
        # Structure:
        # {
        #   "total": { "FURIA": [PlayerStats], "G2": [PlayerStats] },
        #   "maps": {
        #       "Inferno": { ... },
        #       "Nuke": { ... }
        #    }
        # }
        self.total = {}
        self.maps = {}

    def add_total(self, team_name, player_stats):
        if team_name not in self.total:
            self.total[team_name] = []
        self.total[team_name].append(player_stats)

    def add_map(self, map_name, team_name, player_stats):
        if map_name not in self.maps:
            self.maps[map_name] = {}
        if team_name not in self.maps[map_name]:
            self.maps[map_name][team_name] = []
        self.maps[map_name][team_name].append(player_stats)

    def to_json(self):
        return {
            "total": {
                team: [p.to_json() for p in players]
                for team, players in self.total.items()
            },
            "maps": {
                map_name: {
                    team: [p.to_json() for p in players]
                    for team, players in teams.items()
                }
                for map_name, teams in self.maps.items()
            }
        }




class PlayerStats:
    def __init__(self, nickname, kills, deaths, kd, adr, kast, rating, swing):
        self.nickname = nickname
        self.kills = kills
        self.deaths = deaths
        self.kd = kd
        self.adr = adr
        self.kast = kast
        self.rating = rating
        self.swing = swing

    def to_json(self):
        return {
            "nickname": self.nickname,
            "kills": self.kills,
            "deaths": self.deaths,
            "kd": self.kd,
            "adr": self.adr,
            "kast": self.kast,
            "rating": self.rating,
            "swing": self.swing
        }
