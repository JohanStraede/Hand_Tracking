from pythonosc import dispatcher, osc_server

def handler(address, *args):
    print(address, *args)

disp = dispatcher.Dispatcher()
disp.map("/spell", handler)
disp.map("/right/*", handler)

server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", 9000), disp)
print("Listening on 0.0.0.0:9000")
server.serve_forever()