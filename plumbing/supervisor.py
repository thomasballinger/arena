
import json
import select
import socket

from .match import Match

def send_json(sock, data):
    sock.sendall((json.dumps(data)+'\n').encode())


class Supervisor():

    def handle_new_connection(self):

        player_sock, _ = self.listen_sock.accept()

        # Receive play request
        request = player_sock.recv(1028).decode()
        request_json = json.loads(request)
        game_string = request_json['game']

        eligible_matches = [e for e in self.active_matches.values() if e.is_waiting_for_player() and e.gname == game_string]
        if eligible_matches:
            match = eligible_matches[0]
        else:
            match = Match(game_string, self.known_games[game_string]())

        self.active_matches[player_sock] = match
        player_number = match.add_player(player_sock)

        # build and send acknowledgment
        acknowledgment = {
            'name': game_string,
            'timelimit': 5,
            'player': player_number,
            }
        send_json(player_sock, acknowledgment)

        if match.is_ready():
            send_json(match.players[0], match.build_state())
            match.set_last_move_time()

    def handle_match_message(self, sock):
        match = self.active_matches[sock]

        move_msg = sock.recv(1028).decode()

        try:
            move = json.loads(move_msg)
            match.make_move(move)
        except ValueError:
            match.log("Player %s submitted ill-formed json" % match.game.current_player)
            match.result = 3 - match.game.current_player

        match.game.draw_board()

        if match.get_result() != 0:
            self.complete_matches.add(match)
            for i, player in enumerate(match.players, start=1):
                send_json(player, match.build_state(player=i))
        else:
            send_json(match.get_current_socket(), match.build_state())


    def __init__(self, host, port, known_games):
        # Set up supervisor.
        self.known_games = known_games
        self.active_matches = {} # dict mapping socket => game object
        self.complete_matches = set()

        self.listen_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listen_sock.bind((host, port))
        self.listen_sock.listen(100)

    def supervise(self):
        while True:
            self.loop(5)

    def loop(self, timeout):
        # Iterate active matches.
        current_sockets = [e.get_current_socket() for e in set(self.active_matches.values())]
        readable_sockets, _, _ = select.select(current_sockets + [self.listen_sock], [], [], timeout)

        for sock in readable_sockets:
            if sock == self.listen_sock:
                # New connection.
                self.handle_new_connection()
            else:
                self.handle_match_message(sock)

        # Clean up.
        self.active_matches = {s:g for (s, g) in self.active_matches.items() if g not in self.complete_matches}
        self.complete_matches = set()

