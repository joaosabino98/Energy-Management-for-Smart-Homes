import zmq

context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

def parse_request(message):
    parsed_message = message.split(" ")
    match parsed_message:
        case 'choose':
            pass
        case 'start':
            pass
        case 'finish':
            pass        

while True:
    message = socket.recv().decode('utf-8')
    print("Received request: %s" % message)
    parse_request(message)