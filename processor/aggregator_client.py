import zmq
import json

context = zmq.Context()
socket = None

def start():
    print("Connecting to aggregator…")
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:5555")

def send_choice_request(available_periods, rated_power):
    str = f"choose {rated_power} {json.dumps(available_periods)}".encode("utf-8")
    socket.send(str)
    response = socket.recv().decode("utf-8")
    print("Received reply: %s" % response)
    return response


# #  Do 10 requests, waiting each time for a response
# for request in range(10):
#     print("Sending request %s …" % request)
#     socket.send(b"Hello")

#     #  Get the reply.
#     message = socket.recv()
#     print("Received reply %s [ %s ]" % (request, message))