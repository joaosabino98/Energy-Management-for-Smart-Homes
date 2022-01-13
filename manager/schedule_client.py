import zmq

class ScheduleClient():
    def start(self):
        context = zmq.Context()
        print("Connecting to scheduler server…")
        self.socket = context.socket(zmq.REQ)
        self.socket.connect("tcp://localhost:5555")

    def send_treshold_change_request(self, threshold):
        message = f"threshold {threshold}".encode("utf-8") 
        self.socket.send(message)
        response = self.socket.recv()
        print("Received reply: %s" % (response.decode("utf-8")))

    def send_schedule_request(self, appliance_id, profile_id):
        message = f"schedule {appliance_id} {profile_id}".encode("utf-8") 
        self.socket.send(message)
        response = self.socket.recv()
        print("Received reply: %s" % (response.decode("utf-8")))

    def send_finish_request(self, execution_id):
        message = f"finish {execution_id}".encode("utf-8")
        self.socket.send(message)
        response = self.socket.recv()
        print("Received reply: %s" % (response.decode("utf-8")))

    def send_exit_request(self):
        self.socket.send(b'exit')
        
# cli = ScheduleClient()
# cli.start()
# cli.send_schedule_request(12, 13)
# cli.send_finish_request(2)

"""
import zmq

context = zmq.Context()

#  Socket to talk to server
print("Connecting to scheduler server…")
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

#  Do 10 requests, waiting each time for a response
for request in range(10):
    print("Sending request %s …" % request)
    socket.send(b"start 12 13")
    # socket.send(b"finish 1")

    #  Get the reply.
    message = socket.recv()
    print("Received reply %s [ %s ]" % (request, message))
"""

