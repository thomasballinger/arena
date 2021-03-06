
import json
import socket

def connect(host, port, game):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    params = {'game':game}
    sock.sendall(json.dumps(params).encode())

    # receive acknowledgment, do nothing with it for now
    _ = sock.recv(1000)

    return sock

def play(sock, move_function):

    print("Game started!")

    while True:
        
        msg = sock.recv(10000).decode()
        state = json.loads(msg)
        if state['result']:
            print("%s wins" % state['result'])
            sock.close()
            return

        else:
            move = {'token':state['token'], 'move':move_function(state)}
            move_json = json.dumps(move)
            sock.sendall(move_json.encode())

